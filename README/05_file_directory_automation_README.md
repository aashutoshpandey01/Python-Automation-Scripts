# File and Directory Automation

## Purpose
Automates routine file and directory management.

## Operations
- Create directories.
- Delete old files.
- Move files.
- Copy files.
- Rename files.
- Archive files.
- Find files older than a configured number of days.

## Enterprise Example
Automatically remove log files older than 30 days while preserving recent operational data.

## Supported Platforms
- Windows
- Ubuntu/Linux

## Enterprise Use
Reduces manual file-management work and helps control storage usage.

## Recommended Schedule
Daily or weekly depending on the cleanup task.

## Run
```bash
python file_directory_automation.py
```

## Important
Deletion operations should be tested carefully before production use.
