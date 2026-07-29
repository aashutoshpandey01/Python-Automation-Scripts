# Python Automation Scripts

A collection of practical Python automation scripts for Windows Server and Ubuntu Server administration.

## What is this project?

This project contains practical Python scripts designed to automate common system administration tasks across Windows Server and Ubuntu Server.

The scripts perform server monitoring, service monitoring, security checks, network monitoring, backup operations, reporting, inventory collection, configuration management, and other day-to-day administrative tasks.

## Why was this project created?

This project was created to practise real-world Python automation for system administration and cloud support environments.

The goal is to reduce repetitive manual work, improve operational efficiency, and build reusable automation that reflects enterprise infrastructure administration.

## What scripts are included?

### `backup_automation.py`

Performs automated backup operations and verifies backup integrity.

### `basic_api_automation.py`

Demonstrates API integration and automated data retrieval.

### `certificate_domain_monitoring.py`

Monitors SSL certificates and domain expiration dates.

### `configuration_backup.py`

Creates automated backups of important configuration files.

### `deployment_automation.py`

Automates application deployment and deployment-related tasks.

### `file_directory_automation.py`

Automates common file and directory management tasks.

### `inventory_asset_collection.py`

Collects system inventory and hardware/software asset information.

### `log_analysis.py`

Analyses log files and generates useful reports.

### `monitoring_alerting.py`

Monitors system resources and generates alerts when required.

### `network_automation.py`

Automates network checks and connectivity verification.

### `patch_update_automation.py`

Checks and automates operating system patch and update tasks.

### `security_automation.py`

Performs security-related system checks and generates security reports.

### `server_health_monitor.py`

Performs a complete server health check by monitoring CPU, memory, disk usage, uptime, and system status.

### `service_monitor.py`

Checks important services and reports their operational status.

### `user_account_automation.py`

Automates user account management and generates user-related reports.

## How do I run the scripts?

First, navigate to the project directory:

```bash
cd python-scripts/scripts
```

Run any script using Python:

```bash
python3 server_health_monitor.py
```

or on Windows:

```powershell
python server_health_monitor.py
```

## Project Structure

* **scripts/** – Python automation scripts
* **logs/** – Execution logs
* **reports/** – Generated reports
* **data/** – Runtime data
* **integrity/** – Integrity verification files
* **state/** – State information used by automation
* **archives/** – Archived files
* **backups/** – Backup files

## Platforms

* Windows Server
* Ubuntu Server

## Technologies Used

* Python
* Windows Task Scheduler
* Ubuntu Cron
* PowerShell
* Bash
* Git
* GitHub
