# Backup Automation

## Purpose

Backup Automation is a cross-platform Python automation script designed to create reliable, timestamped backups of important files and directories on Windows Server and Ubuntu/Linux systems.

It automates the backup process, manages backup retention, and helps administrators maintain recoverable copies of critical business data.

---

## What It Does

The script automatically performs the following tasks:

* Identifies configured backup targets.
* Verifies that files and directories exist.
* Creates backup copies.
* Compresses backup data.
* Adds timestamps to every backup.
* Organises backups into structured directories.
* Removes expired backups based on the retention policy.
* Generates backup reports.
* Records every operation in execution logs.
* Handles missing files and backup errors gracefully.

---

## Backup Workflow

```text id="dzwy4l"
Identify Backup Targets
          │
          ▼
Verify Files & Directories
          │
          ▼
Create Backup
          │
          ▼
Compress Backup
          │
          ▼
Apply Timestamp
          │
          ▼
Store Backup
          │
          ▼
Verify Backup
          │
          ▼
Remove Expired Backups
          │
          ▼
Generate Report & Log
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

```text id="t7oivn"
python-scripts/
│
├── scripts/
│   └── backup_automation.py
│
├── backups/
│
├── archives/
│
├── logs/
│   └── backup_automation/
│
├── reports/
│   └── backup_automation/
│
├── integrity/
├── data/
└── state/
```

---

## Backup Targets

The script can back up:

* Configuration files
* Application files
* Important project directories
* Log files
* Reports
* Scripts
* User data
* Database dumps (when available)
* Custom backup locations

---

## Output

Each execution automatically generates:

### Backup Files

Stored in:

```text id="zh5pxe"
backups/
```

Each backup includes a timestamp to preserve multiple recovery points.

---

### Log File

Stored in:

```text id="a3vjy4"
logs/backup_automation/
```

Example:

```text id="4rn7fg"
backup_automation_YYYYMMDD_HHMMSS.log
```

---

### JSON Report

Stored in:

```text id="o89hnd"
reports/backup_automation/
```

Example:

```text id="bhf2ti"
backup_report_YYYYMMDD_HHMMSS.json
```

The report includes:

* Run ID
* Timestamp
* Backup Targets
* Files Processed
* Archive Name
* Backup Size
* Retention Actions
* Overall Backup Status

---

## Enterprise Use Cases

This automation is commonly used for:

* Daily operational backups
* Configuration backups
* Project backups
* Log retention
* Disaster recovery preparation
* Server migration
* Change management
* Compliance requirements

---

## Why This Script Was Created

Creating backups manually is repetitive and prone to human error.

This script automates the complete backup process, ensuring backups are created consistently, stored correctly, and retained according to organisational policies.

---

## Recommended Schedule

Run:

* Daily for important business data.
* Before major software updates.
* Before infrastructure changes.
* Before server maintenance.
* Before migrations.

Example Cron entry:

```cron id="0oc2l4"
30 2 * * 0 cd /home/cloudadmin/python-scripts && python3 scripts/backup_automation.py
```

---

## Retention Policy

The script supports automated retention management by:

* Keeping recent backups.
* Removing backups older than the configured retention period.
* Preventing unnecessary storage growth.
* Maintaining organised backup directories.

Retention periods should be configured according to organisational requirements.

---

## Prerequisites

* Python 3.10 or later
* Read permission for backup sources
* Write permission for the backup directory
* Sufficient available storage space

---

## How to Run

### Windows

```powershell id="9wp0yz"
python backup_automation.py
```

### Ubuntu / Linux

```bash id="h2vvff"
python3 backup_automation.py
```

---

## Important

A backup is only valuable if it can be successfully restored.

Always:

* Test restoration procedures regularly.
* Verify backup integrity.
* Store backup copies securely.
* Maintain multiple recovery points.
* Keep at least one backup separate from the production server.

---

## Error Handling

The script safely handles:

* Missing files
* Missing directories
* Permission errors
* Insufficient storage
* Archive failures
* Compression failures

Errors are logged while allowing remaining backup operations to continue whenever possible.

---

## Best Practices

* Schedule automatic backups.
* Verify backups regularly.
* Monitor available storage space.
* Review backup reports after execution.
* Store important backups on separate storage or remote systems.
* Combine operational backups with full disaster recovery strategies.

---

## Related Project Folders

* `scripts/` – Python automation scripts
* `backups/` – Backup files
* `archives/` – Archived backup data
* `logs/` – Execution logs
* `reports/` – Backup reports
* `integrity/` – Integrity verification
* `data/` – Runtime data
* `state/` – Script state information
