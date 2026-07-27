# Deployment Automation

## Purpose
Automates application deployment tasks.

## Workflow
```text
New version
    ↓
Backup old version
    ↓
Deploy new files
    ↓
Install dependencies
    ↓
Restart service
    ↓
Health check
    ↓
Success or rollback
```

## What It Automates
- Copy application files.
- Install dependencies.
- Restart services.
- Verify deployment.
- Detect deployment failure.
- Support rollback logic.

## Supported Platforms
- Windows
- Ubuntu/Linux

## Enterprise Use
This is the basic foundation of CI/CD and release automation.

## Run
```bash
python deployment_automation.py
```
