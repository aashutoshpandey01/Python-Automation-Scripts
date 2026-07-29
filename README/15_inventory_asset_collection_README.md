# Inventory and Asset Collection

## Purpose

Inventory and Asset Collection is a cross-platform Python automation script designed to automatically collect hardware, operating system, software, network, and service inventory from Windows Server and Ubuntu/Linux systems.

It provides a centralised snapshot of system assets that can be used for administration, reporting, auditing, troubleshooting, and infrastructure management.

---

## What It Does

The script automatically gathers important inventory information including:

* Hostname
* Operating System
* OS Version
* System Architecture
* CPU Information
* RAM Information
* Disk Information
* Storage Usage
* Network Interfaces
* IP Addresses
* MAC Addresses
* Installed Software
* Running Services
* Python Version
* Collection Timestamp

The collected information is organised into structured reports for easy analysis.

---

## Inventory Collection Workflow

```text id="l8yqhk"
Start
   │
   ▼
Collect Hardware Information
   │
   ▼
Collect Operating System Details
   │
   ▼
Collect Network Information
   │
   ▼
Collect Installed Software
   │
   ▼
Collect Running Services
   │
   ▼
Generate Reports
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

```text id="f6t0er"
python-scripts/
│
├── scripts/
│   └── inventory_asset_collection.py
│
├── logs/
│   └── inventory_asset_collection/
│
├── reports/
│   └── inventory_asset_collection/
│
├── data/
├── integrity/
├── state/
└── backups/
```

---

## Information Collected

### System Information

* Hostname
* Operating System
* OS Version
* Kernel Version
* Machine Architecture
* Boot Time

---

### Hardware Information

* Processor Model
* CPU Core Count
* Logical Processors
* RAM Size
* Disk Capacity
* Disk Usage
* Storage Devices

---

### Network Information

* IP Addresses
* MAC Addresses
* Network Interfaces
* Hostname Resolution
* Default Network Information

---

### Software Information

* Installed Applications
* Python Version
* Important Packages
* Platform Information

---

### Service Information

* Running Services
* Service Status
* Platform-specific Services

---

## Output

Each execution automatically generates:

### Console Output

Displays collected inventory information and collection status.

---

### Log File

Stored in:

```text id="a7d5xv"
logs/inventory_asset_collection/
```

Example:

```text id="p08o2w"
inventory_asset_collection_YYYYMMDD_HHMMSS.log
```

---

## Reports Generated

The script can generate reports in multiple formats.

### JSON

Suitable for automation and APIs.

Example:

```text id="cwtjlwm"
inventory_YYYYMMDD_HHMMSS.json
```

---

### CSV

Suitable for spreadsheets and reporting.

Example:

```text id="rkq8jn"
inventory_YYYYMMDD_HHMMSS.csv
```

---

### Excel

Suitable for management reports.

Example:

```text id="ur2x0z"
inventory_YYYYMMDD_HHMMSS.xlsx
```

---

### SQLite Database

Suitable for maintaining historical inventory records and asset tracking.

Example:

```text id="6umhfc"
inventory.db
```

---

## Enterprise Use Cases

Inventory information is useful for:

* Asset Management
* Configuration Management
* Capacity Planning
* Compliance Auditing
* Infrastructure Documentation
* Troubleshooting
* Software Tracking
* Hardware Lifecycle Management
* CMDB Population
* Server Administration

---

## Why This Script Was Created

Maintaining an accurate inventory is essential for managing enterprise infrastructure.

This project automates the collection of asset information, reducing manual documentation while producing consistent and reusable reports.

---

## Enterprise Relevance

The same concepts are used in:

* Microsoft Configuration Manager (SCCM)
* Microsoft Intune
* Lansweeper
* ServiceNow CMDB
* ManageEngine AssetExplorer
* GLPI
* OCS Inventory
* Azure Arc
* AWS Systems Manager
* Enterprise Asset Management Platforms

---

## Recommended Schedule

Run:

* Daily for rapidly changing environments
* Weekly for stable infrastructure
* Before infrastructure audits
* After hardware or software changes

Example Cron entry:

```cron id="gppbtg"
0 7 * * * cd /home/cloudadmin/python-scripts && python3 scripts/inventory_asset_collection.py
```

---

## Required Python Packages

Install the required dependencies:

```bash id="bsayj5"
pip install psutil openpyxl
```

Ubuntu packages:

```bash id="4lpm5d"
sudo apt install python3-psutil python3-openpyxl
```

---

## How to Run

### Windows

```powershell id="1h9r3x"
python inventory_asset_collection.py
```

### Ubuntu / Linux

```bash id="sxuzan"
python3 inventory_asset_collection.py
```

---

## Error Handling

The script safely handles:

* Missing hardware information
* Permission restrictions
* Missing software entries
* Unsupported operating system features
* Network information errors
* Service enumeration failures

Errors are recorded in execution logs while allowing inventory collection to continue whenever possible.

---

## Best Practices

* Collect inventory on a regular schedule.
* Maintain historical reports.
* Use reports for capacity planning.
* Review installed software periodically.
* Track hardware changes.
* Integrate inventory data into an asset management or CMDB solution where appropriate.

---

## Related Project Folders

* `scripts/` – Python automation scripts
* `logs/` – Inventory logs
* `reports/` – Inventory reports
* `data/` – Runtime data
* `integrity/` – Integrity verification
* `state/` – Runtime state
* `backups/` – Backup files
