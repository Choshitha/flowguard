"""Reproducible, dependency-free demonstration ETL. All sites/readings are fictional."""
from pathlib import Path
import csv, json, math, random, sqlite3
from datetime import datetime, timedelta
ROOT = Path(__file__).resolve().parents[1]
SITES = [("S01", "Coastal reserve", "Coastal", 950), ("S02", "Hillcrest station", "Inland", 720), ("S03", "North harbour", "Coastal", 1100), ("S04", "Valley junction", "Inland", 860), ("S05", "Southern works", "Urban", 1250), ("S06", "Central exchange", "Urban", 980)]
def build():
    rng = random.Random(42)
    out = ROOT / "docs"; out.mkdir(exist_ok=True)
    raw = []
    start = datetime(2026, 9, 21)
    for hour in range(720):
        for i,(sid,name,region,capacity) in enumerate(SITES):
            t = start + timedelta(hours=hour)
            flow = round(15+i*2+6*math.sin((t.hour-7)*math.pi/12)+rng.uniform(-2,2),2)
            level = round(65+14*math.sin(hour/18+i)+rng.uniform(-4,4),1)
            energy = round(flow*(0.39+i*0.025)+rng.uniform(0,1.5),2)
            # Seeded faults for a useful investigation; they are not real events.
            if sid == "S02" and hour >= 710: level = round(24-(hour-710)*1.4,1)
            if sid == "S05" and hour >= 700: energy *= 2
            if sid == "S03" and hour % 89 == 0: level = -9
            if sid == "S06" and hour % 83 == 0: flow = None
            raw.append((sid,t.isoformat(),level,flow,round(energy,2)))
    raw += raw[:18]
    with (ROOT / "pipeline" / "raw_readings.csv").open("w",newline="") as f:
        w=csv.writer(f); w.writerow(["site_id","timestamp","level_pct","flow_kl","energy_kwh"]); w.writerows(raw)
    db=sqlite3.connect(ROOT / "pipeline" / "flowguard.sqlite")
    db.executescript((ROOT / "sql" / "schema.sql").read_text())
    db.executemany("INSERT INTO sites VALUES (?,?,?,?)",SITES)
    seen=set(); valid=[]; invalid=duplicates=0
    for r in raw:
        key=r[:2]
        if key in seen: duplicates+=1; continue
        seen.add(key)
        if r[3] is None or not 0<=r[2]<=100 or r[3]<0 or r[4]<0:
            invalid+=1; continue
        valid.append(r)
    db.executemany("INSERT INTO readings VALUES (?,?,?,?,?)",valid)
    db.executescript((ROOT / "sql" / "analytics.sql").read_text())
    db.commit()
    keys=["site","time","level","flow","energy"]
    readings=[dict(zip(keys,r)) for r in db.execute("SELECT * FROM readings ORDER BY timestamp, site_id")]
    data={"meta":{"source":"Seeded synthetic demonstration • not live telemetry","start":start.isoformat(),"end":(start+timedelta(hours=719)).isoformat(),"timezone":"Australia/Brisbane","raw":len(raw),"accepted":len(valid),"invalid":invalid,"duplicates":duplicates,"expected":4320,"seed":42},"sites":[dict(zip(["id","name","region","capacity"],s)) for s in SITES],"readings":readings}
    (out / "data.js").write_text("window.FLOWGUARD_DATA="+json.dumps(data,separators=(",",":"))+";\n")
    db.close()
    print(json.dumps(data["meta"],indent=2))
if __name__ == "__main__": build()
