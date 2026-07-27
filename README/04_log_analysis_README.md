# Log Analysis

## Purpose
Automates basic analysis of operating-system and application logs.

## What It Does
- Reads available logs.
- Searches for errors, warnings, failed events, and suspicious patterns.
- Counts detected events.
- Generates a structured report.
- Handles unavailable log sources gracefully.

## Supported Platforms
- Windows
- Ubuntu/Linux

## Enterprise Use
Useful for troubleshooting, operational monitoring, and basic security-event analysis.

## Recommended Schedule
Hourly or every 15 minutes for important systems.

## Run
```bash
python log_analysis.py
```
