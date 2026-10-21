"""Import an official Seqwater historical CSV ZIP; no simulated observations."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import argparse,csv,hashlib,io,json,math,sqlite3,zipfile
ROOT=Path(__file__).resolve().parents[1]
SOURCE='https://www.seqwater.com.au/historic-dam-levels'
NAMES=['Baroon Pocket','Hinze','Little Nerang','North Pine (Lake Samsonvale)','Somerset','Wivenhoe','SEQ Water Grid']
def parse_export(path):
    rows=[];rejected=[];seen=set();duplicates=0;raw=0;sources=[]
    with zipfile.ZipFile(path) as z:
        for member in z.namelist():
            if not member.endswith('.csv'):continue
            payload=z.read(member);sources.append({'file':member,'sha256':hashlib.sha256(payload).hexdigest()})
            reader=csv.DictReader(io.StringIO(payload.decode('utf-8-sig')))
            required={'Name','Date','Last Observation (%)','Last Observation (ML)'}
            if not required.issubset(reader.fieldnames or []):raise ValueError(f'Unexpected CSV columns: {member}')
            for index,r in enumerate(reader,2):
                raw+=1
                try:
                    name=r['Name'];day=datetime.strptime(r['Date'],'%d-%m-%Y').date().isoformat()
                    pct=float(r['Last Observation (%)']);ml=float(r['Last Observation (ML)'])
                    # Storage can exceed 100% during spilling; never clamp it to 100.
                    if name not in NAMES or not math.isfinite(pct) or not math.isfinite(ml) or pct<0 or ml<0:raise ValueError('Invalid name or non-finite/negative measurement')
                    key=(name,day)
                    if key in seen:duplicates+=1;continue
                    seen.add(key);rows.append((name,day,pct,ml))
                except (ValueError,TypeError) as e:rejected.append({'file':member,'row':index,'reason':str(e)})
    if not rows:raise ValueError('No accepted observations')
    return sorted(rows,key=lambda r:(r[1],r[0])),raw,duplicates,rejected,sources

def build(path,retrieved="2026-10-21"):
    datetime.strptime(retrieved,"%Y-%m-%d")
    rows,raw,duplicates,rejected,sources=parse_export(path)
    if {r[0] for r in rows} != set(NAMES):raise ValueError('Export must include all six configured dams and SEQ Water Grid')
    db=sqlite3.connect(ROOT/'pipeline/flowguard.sqlite');db.executescript((ROOT/'sql/schema.sql').read_text())
    sites=[{'id':f'D{i+1:02}','name':n,'kind':'grid' if n=='SEQ Water Grid' else 'dam'} for i,n in enumerate(NAMES) if any(r[0]==n for r in rows)]
    ids={s['name']:s['id'] for s in sites}
    db.executemany('INSERT INTO sites VALUES (?,?,?)',[(s['id'],s['name'],s['kind']) for s in sites])
    db.executemany('INSERT INTO observations VALUES (?,?,?,?)',[(ids[n],d,p,m) for n,d,p,m in rows]);db.executescript((ROOT/'sql/analytics.sql').read_text());db.commit();db.execute('VACUUM')
    start=min(r[1] for r in rows);end=max(r[1] for r in rows);days=(datetime.fromisoformat(end)-datetime.fromisoformat(start)).days+1
    data={'meta':{'source':'Seqwater historical CSV export','url':SOURCE,'start':start,'end':end,'retrieved':retrieved,'timezone':'Australia/Brisbane','frequency':'Last observation per calendar day','raw':raw,'accepted':len(rows),'invalid':len(rejected),'duplicates':duplicates,'expected':days*len(sites),'missing':days*len(sites)-len(rows),'archive_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'members':sources},'sites':sites,'records':[{'site':ids[n],'date':d,'pct':p,'ml':m} for n,d,p,m in rows]}
    (ROOT/'docs/data.js').write_text('window.FLOWGUARD_DATA='+json.dumps(data,separators=(',',':'))+';\n')
    (ROOT/'pipeline/rejections.json').write_text(json.dumps(rejected,indent=2))
    db.close();print(json.dumps({k:v for k,v in data['meta'].items() if k!='members'},indent=2))
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--input',type=Path,default=ROOT/'pipeline/raw/seqwater-history.zip');parser.add_argument('--retrieved',default='2026-10-21');args=parser.parse_args();build(args.input,args.retrieved)
