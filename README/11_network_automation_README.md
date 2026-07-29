# Network Automation

## Purpose

Network Automation is a cross-platform Python automation script designed to automate common network administration, connectivity testing, and infrastructure validation tasks on Windows Server and Ubuntu/Linux systems.

It helps administrators quickly identify connectivity issues, verify service availability, collect network information, and generate structured reports.

---

## What It Does

The script can automate common network administration tasks such as:

* Test network connectivity
* Ping local or remote hosts
* Verify TCP port availability
* Perform DNS resolution checks
* Collect local network configuration
* Detect network interface information
* Validate IP configuration
* Generate network reports
* Record execution logs

The script is designed to work safely even if a host, service, or network resource is unavailable.

---

## Network Automation Workflow

```text
Start
   │
   ▼
Collect Network Information
   │
   ▼
Check Connectivity
   │
   ▼
Ping Target Hosts
   │
   ▼
Verify TCP Ports
   │
   ▼
Perform DNS Checks
   │
   ▼
Generate Report
   │
   ▼
Store Logs
   │
   ▼
Complete
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

```text
python-scripts/
│
├── scripts/
│   └── network_automation.py
│
├── logs/
│   └── network_automation/
│
├── reports/
│   └── network_automation/
│
├── data/
├── integrity/
├── state/
└── backups/
```

---

## Network Checks Performed

Depending on the operating system, the script may perform:

* ICMP Ping Tests
* Host Reachability
* TCP Port Checks
* DNS Resolution
* IP Address Collection
* Default Gateway Detection
* Network Interface Information
* Hostname Verification
* Basic Connectivity Validation

The exact checks performed depend on the operating system and available network resources.

---

## Output

Each execution automatically generates:

### Console Output

Displays information such as:

* Hostname
* IP Address
* Gateway
* DNS Status
* Ping Results
* Port Status
* Connectivity Status
* Overall Network Health

---

### Log File

Stored in:

```text
logs/network_automation/
```

Example:

```text
network_automation_YYYYMMDD_HHMMSS.log
```

---

### JSON Report

Stored in:

```text
reports/network_automation/
```

Example:

```text
network_report_YYYYMMDD_HHMMSS.json
```

The report contains:

* Run ID
* Timestamp
* Network Information
* Connectivity Results
* Port Status
* DNS Results
* Summary Statistics

---

## Enterprise Use Cases

This automation is useful for:

* Infrastructure troubleshooting
* Network monitoring
* Connectivity validation
* Service availability testing
* Server deployment verification
* Remote host validation
* Network health checks
* Operational support

---

## Why This Script Was Created

Network troubleshooting is one of the most common responsibilities of System Administrators and Cloud Engineers.

This script automates routine network validation tasks, reducing manual effort while providing consistent and repeatable results.

---

## Enterprise Relevance

The same concepts are widely used in:

* Network Operations Center (NOC)
* Cloud Infrastructure Monitoring
* Windows Server Administration
* Linux Server Administration
* Azure Networking
* AWS Networking
* Google Cloud Networking
* Cisco Network Administration
* Monitoring Platforms
* Infrastructure Automation

This project provides a practical foundation before working with enterprise monitoring and network management tools.

---

## Recommended Schedule

Run:

* Every 15 minutes for infrastructure monitoring
* Before application deployments
* During troubleshooting
* After configuration changes

Example Cron entry:

```cron
*/15 * * * * cd /home/cloudadmin/python-scripts && python3 scripts/network_automation.py
```

---

## Prerequisites

* Python 3.10 or later
* Network connectivity
* Permission to perform network operations
* Required Python modules installed

---

## How to Run

### Windows

```powershell
python network_automation.py
```

### Ubuntu / Linux

```bash
python3 network_automation.py
```

---

## Future Enhancements

This project can easily be extended to support:

* SSH automation
* SNMP monitoring
* REST API communication
* Network device automation
* Firewall validation
* VLAN information
* Routing verification
* Cloud networking APIs
* Cisco IOS automation
* Network inventory collection

---

## Error Handling

The script safely handles:

* Network timeouts
* DNS failures
* Host unreachable errors
* Closed ports
* Invalid hostnames
* Connection failures
* Permission issues

Errors are recorded in execution logs without causing unexpected termination whenever possible.

---

## Best Practices

* Verify network connectivity before troubleshooting applications.
* Monitor critical servers regularly.
* Review generated reports after execution.
* Keep DNS records accurate.
* Validate firewall rules during connectivity testing.
* Perform routine health checks for production infrastructure.

---

## Related Project Folders

* `scripts/` – Python automation scripts
* `logs/` – Network execution logs
* `reports/` – Network reports
* `data/` – Runtime data
* `integrity/` – Integrity verification
* `state/` – Script state information
* `backups/` – Backup files
