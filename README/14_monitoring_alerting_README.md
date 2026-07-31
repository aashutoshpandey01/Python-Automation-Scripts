# Monitoring and Alerting

## Purpose

Monitoring and Alerting is a cross-platform Python automation script designed to continuously monitor system health and generate alerts whenever configured thresholds are exceeded on Windows Server and Ubuntu/Linux systems.

It helps administrators detect resource issues early, reducing downtime and improving infrastructure reliability.

---

## What It Does

The script continuously monitors important system resources such as:

* CPU utilisation
* Memory utilisation
* Disk utilisation
* Hostname
* Operating System
* System uptime
* Basic server health indicators

When configured thresholds are exceeded, the script generates alerts and records the results in structured reports.

---

## Monitoring Workflow

```text id="6o3x3m"
Start
   │
   ▼
Collect System Information
   │
   ▼
Check CPU Usage
   │
   ▼
Check Memory Usage
   │
   ▼
Check Disk Usage
   │
   ▼
Compare With Thresholds
   │
   ▼
Generate Alerts
   │
   ▼
Save Logs & Reports
   │
   ▼
Send Notifications
   │
   ▼
Complete
```

---

## Supported Platforms

* Windows Server
* Windows 10/11
* Ubuntu Server
* Ubuntu Desktop
* Other Linux distributions

---

## Project Structure

```text id="vqxvqt"
python-scripts/
│
├── scripts/
│   └── monitoring_alerting.py
│
├── logs/
│   └── monitoring_alerting/
│
├── reports/
│   └── monitoring_alerting/
│
├── data/
├── integrity/
├── state/
└── backups/
```

---

## Health Checks Performed

The script may monitor:

* CPU Usage
* Memory Usage
* Disk Usage
* Hostname
* Operating System
* Uptime
* Overall System Health

Thresholds can be adjusted according to organisational requirements.

---

## Notification Methods

The notification system is designed to be extensible and can support:

* Email
* Microsoft Teams
* Slack
* Discord
* Generic Webhooks
* Ticketing Systems
* Monitoring Platforms

If a notification service is unavailable or not configured, the script records the error without interrupting the monitoring process.

---

## Email Configuration

Current alert recipient:

```text id="jlkd5x"e
<Your Email>
```

For production environments, SMTP credentials or App Passwords should be stored securely using environment variables or a secure credential manager rather than hardcoded into scripts.

---

## Output

Each execution automatically generates:

### Console Output

Displays information such as:

* Hostname
* Operating System
* CPU Usage
* Memory Usage
* Disk Usage
* Alert Status
* Overall Health

---

### Log File

Stored in:

```text id="3p2v9x"
logs/monitoring_alerting/
```

Example:

```text id="0hwrmz"
monitoring_alerting_YYYYMMDD_HHMMSS.log
```

---

### JSON Report

Stored in:

```text id="58nh0g"
reports/monitoring_alerting/
```

Example:

```text id="2oqtb6"
monitoring_report_YYYYMMDD_HHMMSS.json
```

The report contains:

* Run ID
* Timestamp
* Hostname
* Operating System
* CPU Usage
* Memory Usage
* Disk Usage
* Threshold Status
* Alerts Generated
* Notification Results

---

## Enterprise Use Cases

This automation is useful for:

* Infrastructure monitoring
* Server administration
* Cloud administration
* NOC monitoring
* System health monitoring
* Operations support
* Capacity planning
* Early incident detection

---

## Why This Script Was Created

Continuous monitoring allows administrators to identify performance issues before they become outages.

This project demonstrates how Python can automate routine health monitoring while generating consistent reports and alert notifications.

---

## Enterprise Relevance

The same concepts are used in:

* Microsoft Azure Monitor
* AWS CloudWatch
* Google Cloud Monitoring
* Zabbix
* Nagios
* PRTG
* Datadog
* Prometheus
* Grafana
* Splunk Monitoring

This project introduces monitoring fundamentals before using enterprise monitoring platforms.

---

## Recommended Schedule

Run:

* Every 5 minutes for critical infrastructure
* Every 15 minutes for standard servers
* More frequently if required

Example Cron entry:

```cron id="1grmvj"
*/5 * * * * cd /home/cloudadmin/python-scripts && python3 scripts/monitoring_alerting.py
```

---

## Prerequisites

* Python 3.10 or later
* Administrator privileges (Windows)
* Root or sudo privileges (Linux) where required
* Network connectivity for notification services
* Required Python modules installed

---

## How to Run

### Windows

```powershell id="3gqemv"
python monitoring_alerting.py
```

### Ubuntu / Linux

```bash id="vmb5tv"
python3 monitoring_alerting.py
```

---

## Error Handling

The script safely handles:

* Notification failures
* SMTP authentication errors
* Network connectivity issues
* Missing notification services
* Resource collection failures
* Permission errors

Errors are written to execution logs while allowing monitoring to continue whenever possible.

---

## Best Practices

* Review monitoring reports regularly.
* Configure realistic alert thresholds.
* Test notification channels periodically.
* Avoid alert fatigue by tuning thresholds appropriately.
* Secure notification credentials.
* Integrate monitoring with enterprise monitoring platforms whenever possible.

---

## Related Project Folders

* `scripts/` – Python automation scripts
* `logs/` – Monitoring logs
* `reports/` – Monitoring reports
* `data/` – Runtime data
* `integrity/` – Integrity verification
* `state/` – Runtime state
* `backups/` – Backup files
