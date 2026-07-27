# Certificate and Domain Monitoring

## Purpose
Monitors domains, HTTPS availability, DNS records, and SSL/TLS certificate expiry.

## What It Checks
- HTTPS availability.
- SSL/TLS certificate validity.
- Certificate expiry date.
- Remaining certificate days.
- Domain availability.
- DNS records.

## Alert Example
```text
Certificate expires in 10 days
        ↓
Python
        ↓
WARNING
        ↓
Notification
```

## Enterprise Use
Prevents unexpected certificate expiry and service outages.

## Recommended Schedule
Daily or more frequently for critical domains.

## Run
```bash
python certificate_domain_monitoring.py
```
