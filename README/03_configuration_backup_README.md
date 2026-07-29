# Configuration Backup

## Purpose

Configuration Backup is a cross-platform Python automation script designed to create timestamped backups of important operating system and application configuration files.

It helps administrators preserve working configurations so they can quickly restore services after accidental changes, corruption, or system failures.

---

## What It Does

The script automatically performs the following tasks:

* Detects supported operating systems.
* Locates important system configuration files.
* Verifies that configuration files exist before backing them up.
* Creates timestamped configuration backups.
* Organises backups into a structured backup directory.
* Reports missing configuration files without terminating execution.
* Generates execution logs.
* Creates structured backup reports.
* Prevents backup failures from affecting other configuration files.

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
│   └── configuration_backup.py
│
├── backups/
│   └── configuration_backup/
│
├── logs/
│   └── configuration_backup/
│
├── reports/
│   └── configuration_backup/
│
├── data/
├── integrity/
├── state/
└── archives/
```

---

## Output

Each execution automatically creates:

### Configuration Backups

Stored in:

```text
backups/configuration_backup/
```

Each backup includes a timestamp to preserve multiple versions.

---

### Log File

Stored in:

```text
logs/configuration_backup/
```

Example:

```text
configuration_backup_YYYYMMDD_HHMMSS.log
```

---

### JSON Report

Stored in:

```text
reports/configuration_backup/
```

Example:

```text
configuration_backup_report_YYYYMMDD_HHMMSS.json
```

The report contains:

* Run ID
* Timestamp
* Host Information
* Files Backed Up
* Missing Files
* Backup Status
* Summary Statistics

---

## Typical Configuration Files

### Windows

Examples include:

* Windows Firewall configuration
* Scheduled Task configuration
* Network configuration
* IIS configuration
* PowerShell profiles

### Ubuntu / Linux

Examples include:

* SSH configuration
* Nginx configuration
* Apache configuration
* UFW configuration
* Cron configuration
* Systemd service files
* Network configuration

---

## Enterprise Use Cases

Configuration backups are commonly used for:

* Disaster recovery
* Change management
* Configuration rollback
* Infrastructure maintenance
* Server migration
* Compliance and auditing
* Rapid service restoration

---

## Why This Script Was Created

Configuration files change frequently during server administration.

This script automates configuration backups to ensure administrators always have a recent, recoverable copy of important settings before or after changes are made.

---

## Recommended Schedule

Run:

* Daily
* Before major maintenance
* Before software updates
* Before server migrations
* Before configuration changes

Example Cron entry:

```cron
30 1 * * * cd /home/cloudadmin/python-scripts && python3 scripts/configuration_backup.py
```

---

## Prerequisites

* Python 3.10 or later
* Read permission for configuration files
* Write permission to the backup directory

---

## How to Run

### Windows

```powershell
python configuration_backup.py
```

### Ubuntu / Linux

```bash
python3 configuration_backup.py
```

---

## Important

This script is intended for **configuration recovery only**.

It does **not** replace:

* Full system backups
* Disk imaging
* Virtual machine snapshots
* Disaster recovery solutions

It should be used alongside a complete backup strategy.

---

## Error Handling

The script safely handles:

* Missing configuration files
* Permission errors
* Unsupported operating systems
* Backup failures
* File access errors

Errors are recorded in the execution log while allowing remaining backup operations to continue.

---

## Best Practices

* Run the script before making configuration changes.
* Store backups on a separate storage location when possible.
* Periodically verify backup integrity.
* Retain multiple backup versions.
* Combine configuration backups with full server backups for complete disaster recovery.

---

## Related Project Folders

* `scripts/` – Python automation scripts
* `backups/` – Configuration backup files
* `logs/` – Execution logs
* `reports/` – Backup reports
* `data/` – Runtime data
* `integrity/` – Integrity verification
* `state/` – Script state information
* `archives/` – Archived backup files
