# Server Health Monitor

## Purpose

Server Health Monitor is a cross-platform Python automation script designed to perform routine health checks on Windows Server and Ubuntu/Linux systems.

It continuously monitors critical system resources and generates detailed reports that help administrators identify performance issues before they become service outages.

---

## What It Checks

The script automatically collects important system information including:

* Operating System
* Hostname
* IP Address
* System Uptime
* CPU Utilisation
* Memory Usage
* Disk Usage
* Available Disk Space
* System Load
* Running Processes
* Basic Resource Health Status
* Warning and Critical Thresholds

Each resource is evaluated against predefined limits and classified as healthy, warning, or critical.

---

## Supported Platforms

* Windows Server
* Windows 10/11
* Ubuntu Server
* Ubuntu Desktop
* Other Linux distributions

---

## Project Structure

```text
python-scripts/
│
├── scripts/
│   └── server_health_monitor.py
│
├── logs/
│   └── server_health_monitor/
│
├── reports/
│   └── server_health_monitor/
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
* CPU Usage
* Memory Usage
* Disk Usage
* Uptime
* Overall Health Status

### Log File

Stored in:

```text
logs/server_health_monitor/
```

Example:

```text
server_health_monitor_YYYYMMDD_HHMMSS.log
```

### JSON Report

Stored in:

```text
reports/server_health_monitor/
```

Example:

```text
health_report_YYYYMMDD_HHMMSS.json
```

The report includes:

* Run ID
* Timestamp
* Host Information
* Resource Utilisation
* Health Status
* Warning Thresholds
* Summary Statistics

---

## Enterprise Use Cases

This script is useful for:

* Scheduled infrastructure health monitoring
* Daily server health reporting
* Capacity planning
* Performance monitoring
* Resource utilisation tracking
* Early detection of CPU, memory, or storage problems
* Supporting cloud and infrastructure operations

---

## Why This Script Was Created

Server administrators routinely verify that servers are operating within acceptable resource limits.

This script automates those checks, providing consistent monitoring, detailed reporting, and historical records without requiring manual intervention.

---

## Recommended Schedule

Run every **15 minutes** using:

* Windows Task Scheduler
* Ubuntu/Linux Cron

Example Cron entry:

```cron
*/15 * * * * cd /home/cloudadmin/python-scripts && python3 scripts/server_health_monitor.py
```

---

## Prerequisites

* Python 3.10 or later
* Appropriate permissions to read system performance information
* Required Python modules installed

---

## How to Run

### Windows

```powershell
python server_health_monitor.py
```

### Ubuntu / Linux

```bash
python3 server_health_monitor.py
```

---

## Error Handling

The script safely handles:

* Missing performance counters
* Permission issues
* Platform-specific differences
* Unexpected exceptions

Errors are recorded in the log while allowing the script to complete whenever possible.

---

## Best Practices

* Schedule the script for automatic execution.
* Review generated reports regularly.
* Monitor warning trends over time.
* Archive reports for historical analysis.
* Adjust warning thresholds to match your production environment.

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
