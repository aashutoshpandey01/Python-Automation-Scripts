# Inventory and Asset Collection

## Purpose
Automatically collects hardware, operating-system, network, software, and service inventory.

## Information Collected
- Hostname.
- Operating system.
- OS version.
- CPU information.
- RAM.
- Disk information.
- IP addresses.
- Installed software.
- Running services.

## Reports Generated
- JSON.
- CSV.
- Excel.
- SQLite database.

## Supported Platforms
- Windows.
- Ubuntu/Linux.

## Enterprise Use
Inventory data is useful for:
- Asset management.
- Compliance.
- Capacity planning.
- Troubleshooting.
- Software tracking.
- Configuration management.

## Required Python Packages
```bash
pip install psutil openpyxl
```

Ubuntu may use:
```bash
sudo apt install python3-psutil python3-openpyxl
```

## Recommended Schedule
Daily or weekly depending on how frequently the environment changes.

## Run
```bash
python inventory_asset_collection.py
```
