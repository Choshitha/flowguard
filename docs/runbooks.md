# FlowGuard demonstration runbooks

These are original portfolio reference notes for fictional sites. They are not approved field procedures. No control action is implemented.

## RB-01
### Low tank level

**Signal:** latest accepted tank level below 30%; critical below 20%.

1. Verify sensor validity using an independent observation.
2. Compare supply, demand and pump activity around the decline.
3. Review recent maintenance and instrumentation events.
4. If confirmed, follow an authorised site's escalation procedures.

**Limit:** a low level alone cannot distinguish a sensor fault, high demand, supply failure or leak. FlowGuard does not detect or establish any of these causes.

## RB-02
### Elevated energy intensity

**Signal:** latest hourly energy divided by hourly throughput exceeds 0.85 kWh/kL.

1. Compare runtime, energy and pumped volume for the same interval.
2. Check meter consistency and data completeness.
3. Review equipment performance and maintenance history.
4. Establish a validated, site-specific baseline before making operational decisions.

**Limit:** the threshold is illustrative. Different site characteristics affect energy intensity. This metric does not identify a cybersecurity incident.
