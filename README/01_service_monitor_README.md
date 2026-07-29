# Service Monitor

## Purpose

Service Monitor is a cross-platform Python automation script designed to monitor important system services on Windows Server and Ubuntu/Linux systems.

It helps system administrators quickly identify stopped, failed, or unavailable services and provides a structured report of the current service status.

---

## What It Does

The script automatically performs the following tasks:

* Monitors predefined enterprise services.
* Detects whether a service is:

  * Running
  * Stopped
  * Disabled
  * Missing
  * Not installed
* Collects service status information.
* Detects service state changes.
* Automatically restarts services that were previously running but unexpectedly stopped (where supported).
* Prevents unnecessary restarts of services that are intentionally stopped.
* Handles missing services gracefully without terminating execution.
* Creates detailed logs for every execution.
* Generates structured JSON reports for future analysis.
* Maintains historical execution data for monitoring trends.

---

## Supported Platforms

* Windows Server
* Windows 10/11
* Ubuntu Server
* Ubuntu Desktop
* Other Linux distributions supporting systemd

---

## Project Structure

```text
python-scripts/
│
├── scripts/
│   └── service_monitor.py
│
├── logs/
│   └── service_monitor/
│
├── reports/
│   └── service_monitor/
│
├── data/
├── integrity/
├── state/
├── backups/
└── archives/
```

---

## Output

Each execution automatically generates:

### Console Output

Displays a summary including:

* Hostname
* Operating System
* Services Checked
* Current Service Status
* Restart Actions (if required)

### Log File

```text
logs/service_monitor/
```

Example:

```text
service_monitor_YYYYMMDD_HHMMSS.log
```

### JSON Report

```text
reports/service_monitor/
```

Example:

```text
service_report_YYYYMMDD_HHMMSS.json
```

The report contains:

* Run ID
* Host information
* Operating System
* Service status
* Restart actions
* Summary statistics
* Execution timestamp

---

## Enterprise Use Cases

This automation can be used for monitoring services such as:

### Windows

* Active Directory Domain Services
* DNS Server
* DHCP Server
* IIS
* Windows Time
* Print Spooler
* Remote Desktop Services

### Linux

* SSH
* Nginx
* Apache
* Docker
* MariaDB
* MySQL
* PostgreSQL
* Cron
* Samba

---

## Why This Script Was Created

System administrators frequently need to verify that critical infrastructure services remain operational.

Instead of manually checking each service, this script automates the process by detecting failures, generating reports, and optionally restarting services when appropriate.

This reduces administrative effort while improving operational reliability.

---

## Prerequisites

* Python 3.10 or later
* Administrative privileges (Windows)
* Root or sudo privileges (Linux, when restarting services)
* Required Python modules installed

---

## How to Run

### Windows

```powershell
python service_monitor.py
```

### Ubuntu / Linux

```bash
python3 service_monitor.py
```

---

## Scheduling

### Windows

Schedule the script using **Task Scheduler** to perform automated health checks every 5 or 15 minutes.

### Ubuntu/Linux

Schedule the script using **Cron**.

Example:

```cron
*/5 * * * * cd /home/cloudadmin/python-scripts && python3 scripts/service_monitor.py
```

---

## Error Handling

The script safely handles situations such as:

* Missing services
* Permission errors
* Unsupported operating systems
* Restart failures
* Unexpected exceptions

Execution continues wherever possible, and errors are recorded in the log.

---

## Best Practices

* Run the script using an account with sufficient privileges.
* Review generated reports regularly.
* Avoid enabling automatic restart for intentionally disabled services.
* Schedule periodic execution for continuous monitoring.
* Store generated logs and reports for troubleshooting and auditing purposes.

---

## Related Project Folders

* `scripts/` – Python automation scripts
* `logs/` – Execution logs
* `reports/` – Generated reports
* `data/` – Runtime data
* `integrity/` – Integrity verification
* `state/` – Script state information
* `backups/` – Backup files
* `archives/` – Archived data
