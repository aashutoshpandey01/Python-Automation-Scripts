# Service Monitor

## Purpose
Cross-platform service monitoring automation for Windows and Linux systems.

## What It Does
- Checks enterprise-relevant services.
- Detects whether a service is running, stopped, missing, or not installed.
- Reports the current service state.
- If a service was previously running and has stopped, it can restart it.
- Avoids blindly starting services that were not previously running.
- Handles missing services gracefully.

## Supported Platforms
- Windows
- Ubuntu/Linux

## Output
The script generates console output and automatically stores execution data/logs under a machine-specific data directory.

## Enterprise Use
Useful for monitoring critical infrastructure services such as web servers, SSH, DNS, DHCP, database services, and other platform-specific services.

## Important
Some service operations require Administrator/root privileges.

## Run
```bash
python service_monitor.py
```

Linux:
```bash
python3 service_monitor.py
```
