# Server Health Monitor

## Purpose
Performs a general health check of a Windows or Linux server.

## What It Checks
- Operating system
- Hostname
- CPU usage
- Memory usage
- Disk usage
- Uptime
- Basic system health indicators

## Output
The script reports whether system resources are healthy or above configured warning thresholds.

Reports and logs are stored automatically in a machine-specific data directory.

## Supported Platforms
- Windows
- Ubuntu/Linux

## Enterprise Use
Useful for scheduled server health checks and early detection of resource problems.

## Recommended Schedule
Every 15 minutes.

## Run
```bash
python server_health_monitor.py
```
