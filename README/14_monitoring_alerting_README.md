# Monitoring and Alerting

## Purpose
Collects system health data and sends alerts when thresholds are exceeded.

## What It Monitors
- CPU usage.
- Memory usage.
- Disk usage.
- Hostname.
- Operating system.

## Notification Methods
The script supports an extensible notification model for:
- Email.
- Microsoft Teams.
- Slack.
- Generic webhooks.
- Ticketing systems.

Unavailable or unconfigured notification methods are reported without stopping the monitoring process.

## Email
The configured alert recipient is:
`exoticaashu325@gmail.com`

Email authentication must be configured securely using an appropriate SMTP credential/App Password.

## Output
- Console status.
- JSON monitoring report.
- Log file.
- Notification results.

## Recommended Schedule
Every 5 to 15 minutes.

## Run
```bash
python monitoring_alerting.py
```
