#!/usr/bin/env python3
"""Collect a Windows Server or Ubuntu Server hardware and software inventory."""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import platform
import socket
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_NAME = "inventory_asset_collection"
OPERATING_SYSTEM = platform.system()
HOSTNAME = platform.node()
RUN_TIME = datetime.now(timezone.utc)
COLLECTION_ID = f"INV-{RUN_TIME:%Y%m%d-%H%M%S}"


def get_platform_paths() -> dict[str, Path]:
    """Select the approved hierarchy before any OS-specific collection occurs."""
    if OPERATING_SYSTEM == "Windows":
        suite_root = Path(r"C:\AdminAutomation\python-scripts")
        script_directory = suite_root / "scripts"
    elif OPERATING_SYSTEM == "Linux":
        suite_root = Path("/home/cloudadmin/python-scripts")
        script_directory = suite_root
    else:
        raise RuntimeError(f"Unsupported operating system: {OPERATING_SYSTEM}")
    return {
        "suite_root": suite_root,
        "script_directory": script_directory,
        "log": suite_root / "logs" / SCRIPT_NAME,
        "report": suite_root / "reports" / SCRIPT_NAME,
        "data": suite_root / "data" / SCRIPT_NAME,
    }


PATHS = get_platform_paths()
for key in ("log", "report", "data"):
    PATHS[key].mkdir(parents=True, exist_ok=True)

LOG_FILE = PATHS["log"] / f"{SCRIPT_NAME}_{RUN_TIME:%Y%m%d}.log"
DATABASE_FILE = PATHS["data"] / "inventory.db"
logging.basicConfig(
    filename=LOG_FILE,
    encoding="utf-8",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Enterprise Inventory Asset Collection")
    parser.add_argument("--no-excel", action="store_true", help="Do not create the optional Excel report.")
    return parser.parse_args()


def run_command(command: list[str], timeout: int = 60) -> str:
    """Run only a command selected by the current OS branch and log failures."""
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
        if completed.returncode != 0:
            logging.warning("Command failed (%s): %s", completed.returncode, completed.stderr.strip())
        return completed.stdout
    except (OSError, subprocess.SubprocessError) as error:
        logging.warning("Command could not run %s: %s", command[0], error)
        return ""


def powershell_json(script: str) -> list[dict[str, Any]]:
    output = run_command(["powershell", "-NoProfile", "-Command", script])
    if not output.strip():
        return []
    try:
        parsed = json.loads(output)
        return parsed if isinstance(parsed, list) else [parsed]
    except json.JSONDecodeError as error:
        logging.warning("PowerShell returned invalid JSON: %s", error)
        return []


def collect_system_information() -> dict[str, str]:
    return {
        "hostname": HOSTNAME,
        "operating_system": OPERATING_SYSTEM,
        "platform": platform.platform(),
        "kernel": platform.release(),
        "architecture": platform.machine(),
        "python_version": sys.version.split()[0],
    }


def collect_cpu_information() -> dict[str, Any]:
    result: dict[str, Any] = {
        "processor": platform.processor(),
        "architecture": platform.machine(),
        "logical_cpu_count": os.cpu_count(),
    }
    if OPERATING_SYSTEM == "Windows":
        rows = powershell_json("Get-CimInstance Win32_Processor | Select-Object Name,NumberOfLogicalProcessors | ConvertTo-Json")
        if rows:
            result["processor"] = rows[0].get("Name") or result["processor"]
            result["logical_cpu_count"] = sum(int(row.get("NumberOfLogicalProcessors") or 0) for row in rows)
    elif OPERATING_SYSTEM == "Linux":
        output = run_command(["lscpu", "-J"])
        try:
            fields = {item["field"].rstrip(":"): item["data"] for item in json.loads(output)["lscpu"]}
            result["processor"] = fields.get("Model name", result["processor"])
            result["logical_cpu_count"] = int(fields.get("CPU(s)", result["logical_cpu_count"] or 0))
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            logging.warning("lscpu output was unavailable or unreadable")
    return result


def collect_memory_information() -> dict[str, Any]:
    try:
        import psutil  # Optional but available on most managed servers.
        memory = psutil.virtual_memory()
        return {
            "total_gb": round(memory.total / 1024**3, 2),
            "available_gb": round(memory.available / 1024**3, 2),
            "used_gb": round(memory.used / 1024**3, 2),
            "usage_percent": memory.percent,
        }
    except ImportError:
        logging.warning("psutil is not installed; memory inventory is unavailable")
        return {"status": "psutil missing"}
    except Exception as error:
        logging.exception("Memory collection failed: %s", error)
        return {"status": "failed"}


def collect_disk_information() -> list[dict[str, Any]]:
    try:
        import psutil
        disks: list[dict[str, Any]] = []
        for partition in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disks.append({
                    "device": partition.device, "mountpoint": partition.mountpoint, "filesystem": partition.fstype,
                    "total_gb": round(usage.total / 1024**3, 2), "used_gb": round(usage.used / 1024**3, 2),
                    "free_gb": round(usage.free / 1024**3, 2), "usage_percent": usage.percent,
                })
            except (OSError, PermissionError) as error:
                logging.warning("Disk partition skipped %s: %s", partition.mountpoint, error)
        return disks
    except ImportError:
        logging.warning("psutil is not installed; disk inventory is unavailable")
        return []


def collect_network_information() -> dict[str, Any]:
    network: dict[str, Any] = {"hostname": socket.gethostname(), "ip_addresses": []}
    try:
        for address in socket.getaddrinfo(socket.gethostname(), None):
            ip_address = address[4][0]
            if ip_address not in network["ip_addresses"]:
                network["ip_addresses"].append(ip_address)
    except OSError as error:
        logging.warning("Network collection failed: %s", error)
    return network


def collect_installed_software() -> list[dict[str, str]]:
    """Use Windows Registry only on Windows and package managers only on Linux."""
    if OPERATING_SYSTEM == "Windows":
        return [
            {"name": str(item.get("DisplayName") or ""), "version": str(item.get("DisplayVersion") or "")}
            for item in powershell_json(
                "Get-ItemProperty 'HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*',"
                "'HKLM:\\Software\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*' "
                "-ErrorAction SilentlyContinue | Where-Object DisplayName | "
                "Select-Object DisplayName,DisplayVersion | ConvertTo-Json"
            )
        ]
    if OPERATING_SYSTEM == "Linux":
        output = run_command(["dpkg-query", "-W", "-f=${binary:Package}\t${Version}\n"])
        if output:
            return [{"name": line.partition("\t")[0], "version": line.partition("\t")[2]}
                    for line in output.splitlines() if line]
        output = run_command(["rpm", "-qa", "--qf", "%{NAME}\t%{VERSION}-%{RELEASE}\n"])
        return [{"name": line.partition("\t")[0], "version": line.partition("\t")[2]}
                for line in output.splitlines() if line]
    return []


def collect_running_services() -> list[dict[str, str]]:
    if OPERATING_SYSTEM == "Windows":
        return [
            {"name": str(item.get("Name") or ""), "display_name": str(item.get("DisplayName") or ""),
             "status": str(item.get("Status") or "")}
            for item in powershell_json("Get-Service | Select-Object Name,DisplayName,Status | ConvertTo-Json")
        ]
    if OPERATING_SYSTEM == "Linux":
        output = run_command(["systemctl", "list-units", "--type=service", "--all", "--no-pager", "--no-legend"])
        services: list[dict[str, str]] = []
        for line in output.splitlines():
            parts = line.split(maxsplit=4)
            if len(parts) >= 4:
                services.append({"name": parts[0], "load": parts[1], "active": parts[2], "sub": parts[3],
                                 "status": parts[2]})
        return services
    return []


def collect_inventory() -> dict[str, Any]:
    logging.info("Inventory collection started: %s", COLLECTION_ID)
    inventory: dict[str, Any] = {
        "collection_id": COLLECTION_ID, "collection_time": RUN_TIME.isoformat(), "hostname": HOSTNAME,
        "system": collect_system_information(), "cpu": collect_cpu_information(),
        "memory": collect_memory_information(), "disks": collect_disk_information(),
        "network": collect_network_information(), "installed_software": collect_installed_software(),
        "running_services": collect_running_services(),
    }
    inventory["collection_summary"] = {
        "total_disks": len(inventory["disks"]), "total_ips": len(inventory["network"]["ip_addresses"]),
        "total_software": len(inventory["installed_software"]), "total_services": len(inventory["running_services"]),
    }
    return inventory


def report_path(extension: str) -> Path:
    return PATHS["report"] / f"inventory_{RUN_TIME:%Y%m%d_%H%M%S}.{extension}"


def save_json_report(inventory: dict[str, Any]) -> Path:
    file_path = report_path("json")
    file_path.write_text(json.dumps(inventory, indent=2, default=str), encoding="utf-8")
    return file_path


def save_csv_report(inventory: dict[str, Any]) -> Path:
    file_path = report_path("csv")
    rows: list[dict[str, str]] = []
    for category, data in inventory.items():
        if isinstance(data, dict):
            rows.extend({"category": category, "name": str(key), "value": json.dumps(value, default=str)}
                        for key, value in data.items())
        elif isinstance(data, list):
            rows.extend({"category": category, "name": str(item.get("name", "")), "value": json.dumps(item, default=str)}
                        for item in data)
    with file_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["category", "name", "value"])
        writer.writeheader()
        writer.writerows(rows)
    return file_path


def save_excel_report(inventory: dict[str, Any]) -> Path | None:
    try:
        from openpyxl import Workbook
    except ImportError:
        logging.warning("openpyxl is not installed; Excel report was not created")
        return None
    file_path = report_path("xlsx")
    workbook = Workbook()
    summary = workbook.active
    summary.title = "Summary"
    summary.append(["Property", "Value"])
    for key, value in inventory["collection_summary"].items():
        summary.append([key, value])
    for section, data in inventory.items():
        sheet = workbook.create_sheet(section[:31])
        sheet.append(["Name", "Value"])
        if isinstance(data, dict):
            for key, value in data.items():
                sheet.append([key, json.dumps(value, default=str)])
        elif isinstance(data, list):
            for item in data:
                sheet.append([item.get("name", ""), json.dumps(item, default=str)])
    workbook.save(file_path)
    return file_path


def save_database(inventory: dict[str, Any]) -> Path:
    with sqlite3.connect(DATABASE_FILE) as connection:
        connection.execute("""CREATE TABLE IF NOT EXISTS inventory_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, collection_id TEXT, hostname TEXT,
            operating_system TEXT, collection_time TEXT, inventory_json TEXT)""")
        connection.execute("INSERT INTO inventory_runs (collection_id, hostname, operating_system, collection_time, inventory_json) VALUES (?, ?, ?, ?, ?)", (
            COLLECTION_ID, HOSTNAME, OPERATING_SYSTEM, RUN_TIME.isoformat(), json.dumps(inventory, default=str)))
    return DATABASE_FILE


def main() -> int:
    args = parse_arguments()
    logging.info("Inventory automation initialized on %s", OPERATING_SYSTEM)
    inventory = collect_inventory()
    json_file = save_json_report(inventory)
    csv_file = save_csv_report(inventory)
    excel_file = None if args.no_excel else save_excel_report(inventory)
    database_file = save_database(inventory)
    result = {
        "collection_id": COLLECTION_ID, "hostname": HOSTNAME, "operating_system": OPERATING_SYSTEM,
        "summary": inventory["collection_summary"], "json_report": str(json_file), "csv_report": str(csv_file),
        "excel_report": str(excel_file) if excel_file else None, "database": str(database_file), "log_file": str(LOG_FILE),
    }
    print(json.dumps(result, indent=2))
    logging.info("Inventory automation completed: %s", COLLECTION_ID)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        logging.exception("Inventory automation crashed")
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
