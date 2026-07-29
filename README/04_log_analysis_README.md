# Log Analysis

## Purpose

Log Analysis is a cross-platform Python automation script designed to analyse operating system and application logs on Windows Server and Ubuntu/Linux systems.

It helps administrators quickly identify errors, warnings, failed events, and suspicious activity by automatically processing log files and generating structured reports.

---

## What It Does

The script automatically performs the following tasks:

* Reads available operating system and application logs.
* Detects errors and warning messages.
* Searches for failed login attempts and authentication failures.
* Identifies suspicious log patterns.
* Counts matching events by category.
* Generates summary statistics.
* Creates structured JSON reports.
* Produces detailed execution logs.
* Handles unavailable log sources gracefully without terminating execution.
* Supports repeated execution for continuous monitoring.

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
│   └── log_analysis.py
│
├── logs/
│   └── log_analysis/
│
├── reports/
│   └── log_analysis/
│
├── data/
├── integrity/
├── state/
└── archives/
```

---

## Output

Each execution automatically generates:

### Console Output

Displays a summary including:

* Hostname
* Operating System
* Logs Processed
* Errors Found
* Warnings Found
* Failed Events
* Suspicious Events
* Overall Analysis Summary

---

### Log File

Stored in:

```text
logs/log_analysis/
```

Example:

```text
log_analysis_YYYYMMDD_HHMMSS.log
```

---

### JSON Report

Stored in:

```text
reports/log_analysis/
```

Example:

```text
log_analysis_YYYYMMDD_HHMMSS.json
```

The report contains:

* Run ID
* Timestamp
* Host Information
* Log Sources Analysed
* Errors
* Warnings
* Failed Events
* Suspicious Events
* Summary Statistics

---

## Typical Log Sources

### Windows

Examples include:

* System Event Log
* Application Event Log
* Security Event Log
* Windows Defender Logs
* PowerShell Logs

### Ubuntu / Linux

Examples include:

* Syslog
* Auth Log
* Kernel Log
* Nginx Logs
* Apache Logs
* SSH Logs
* Systemd Journal

---

## Enterprise Use Cases

Log analysis is commonly used for:

* System troubleshooting
* Performance monitoring
* Security monitoring
* Failed login detection
* Operational reporting
* Compliance auditing
* Infrastructure monitoring
* Early issue detection

---

## Why This Script Was Created

System administrators often spend significant time manually reviewing logs to diagnose problems or investigate incidents.

This script automates that process by identifying important events, summarising findings, and producing structured reports for faster analysis.

---

## Recommended Schedule

Run:

* Every hour
* Every 15 minutes for critical servers
* After major deployments
* During incident investigations

Example Cron entry:

```cron
0 * * * * cd /home/cloudadmin/python-scripts && python3 scripts/log_analysis.py
```

---

## Prerequisites

* Python 3.10 or later
* Permission to read system log files
* Required Python modules installed

---

## How to Run

### Windows

```powershell
python log_analysis.py
```

### Ubuntu / Linux

```bash
python3 log_analysis.py
```

---

## Error Handling

The script safely handles:

* Missing log files
* Permission errors
* Unsupported operating systems
* Corrupted log entries
* File access failures

Errors are recorded in the execution log while allowing analysis of remaining log sources to continue.

---

## Best Practices

* Schedule the script to run automatically.
* Archive reports for historical analysis.
* Review recurring warnings and failed events.
* Combine with monitoring and alerting automation.
* Retain logs according to organisational retention policies.

---

## Related Project Folders

* `scripts/` – Python automation scripts
* `logs/` – Execution logs
* `reports/` – Analysis reports
* `data/` – Runtime data
* `integrity/` – Integrity verification
* `state/` – Script state information
* `archives/` – Archived files
