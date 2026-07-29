# File and Directory Automation

## Purpose

File and Directory Automation is a cross-platform Python automation script designed to automate routine file management tasks on Windows Server and Ubuntu/Linux systems.

It helps administrators organise files, clean up unnecessary data, archive old files, and reduce manual maintenance while keeping storage usage under control.

---

## What It Does

The script automatically performs common file management operations such as:

* Creating directories
* Creating missing folder structures
* Copying files
* Moving files
* Renaming files
* Archiving files
* Deleting temporary files
* Deleting files older than a configured number of days
* Finding large files
* Finding files older than a specified age
* Generating cleanup reports
* Recording all operations in execution logs

The script supports safe file handling and reports every operation performed.

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
│   └── file_directory_automation.py
│
├── logs/
│   └── file_directory_automation/
│
├── reports/
│   └── file_directory_automation/
│
├── archives/
├── backups/
├── data/
├── integrity/
└── state/
```

---

## Output

Each execution automatically generates:

### Console Output

Displays a summary including:

* Directories Created
* Files Copied
* Files Moved
* Files Renamed
* Files Archived
* Files Deleted
* Cleanup Summary

---

### Log File

Stored in:

```text
logs/file_directory_automation/
```

Example:

```text
file_directory_automation_YYYYMMDD_HHMMSS.log
```

---

### Report

Stored in:

```text
reports/file_directory_automation/
```

Example:

```text
report_YYYYMMDD_HHMMSS.csv
```

The report contains:

* Run ID
* Timestamp
* Operations Performed
* Files Processed
* Files Deleted
* Archive Information
* Summary Statistics

---

## Typical Operations

The automation can be configured to:

* Remove temporary files
* Archive completed reports
* Rotate log files
* Organise downloaded files
* Move completed backups
* Create project directories
* Rename files according to naming standards
* Clean application cache directories

---

## Enterprise Example

Automatically delete log files older than **30 days** while preserving recent operational data.

Additional examples include:

* Archive monthly reports.
* Move completed backup files to long-term storage.
* Clean temporary directories every night.
* Organise departmental folders automatically.
* Rotate application log files.

---

## Enterprise Use Cases

This automation is commonly used for:

* File housekeeping
* Storage management
* Log rotation
* Backup organisation
* Archive management
* Automated cleanup
* Server maintenance
* Scheduled file operations

---

## Why This Script Was Created

File management is one of the most repetitive administrative tasks.

This script automates routine maintenance activities, reducing manual effort, preventing unnecessary storage growth, and ensuring consistent file organisation across systems.

---

## Recommended Schedule

Run:

* Daily for cleanup tasks
* Weekly for archive operations
* Monthly for long-term maintenance

Example Cron entry:

```cron
0 1 * * * cd /home/cloudadmin/python-scripts && python3 scripts/file_directory_automation.py
```

---

## Prerequisites

* Python 3.10 or later
* Read and write permission for target directories
* Required Python modules installed

---

## How to Run

### Windows

```powershell
python file_directory_automation.py
```

### Ubuntu / Linux

```bash
python3 file_directory_automation.py
```

---

## Important

Deletion operations should always be tested carefully before production deployment.

Recommended practices include:

* Test using non-production data.
* Verify file selection rules.
* Maintain backup copies.
* Review generated reports before enabling automatic deletion.

---

## Error Handling

The script safely handles:

* Missing files
* Missing directories
* Permission errors
* Locked files
* Invalid paths
* File access failures

Errors are logged while allowing remaining operations to continue whenever possible.

---

## Best Practices

* Always maintain backups before enabling automated deletion.
* Use archive operations instead of permanent deletion whenever possible.
* Review cleanup reports regularly.
* Schedule maintenance during low-usage periods.
* Retain important business files according to organisational policies.

---

## Related Project Folders

* `scripts/` – Python automation scripts
* `logs/` – Execution logs
* `reports/` – Generated reports
* `archives/` – Archived files
* `backups/` – Backup files
* `data/` – Runtime data
* `integrity/` – Integrity verification
* `state/` – Script state information
