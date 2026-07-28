#!/usr/bin/env python3
"""Cross-platform server health monitoring for Ubuntu Server and Windows Server."""

from __future__ import annotations

import argparse
import json
import logging
import os
import platform
import shutil
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import psutil
except ImportError:  # Report a clear dependency error after the log path exists.
    psutil = None  # type: ignore[assignment]


SCRIPT_NAME = "server_health_monitor"
OPERATING_SYSTEM = platform.system()
HOSTNAME = socket.gethostname()
RUN_TIME = datetime.now(timezone.utc)
RUN_ID = f"HEALTH-{RUN_TIME:%Y%m%d-%H%M%S}"


def get_platform_paths() -> dict[str, Path]:
    """Select the approved hierarchy before performing any OS-specific checks."""
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
for path_name in ("script_directory", "log", "report", "data"):
    PATHS[path_name].mkdir(parents=True, exist_ok=True)

LOG_FILE = PATHS["log"] / f"{SCRIPT_NAME}_{RUN_TIME:%Y%m%d_%H%M%S}.log"
CONFIG_FILE = PATHS["data"] / f"{SCRIPT_NAME}.json"
DEFAULT_CONFIG: dict[str, Any] = {
    "cpu_warning_percent": 80,
    "cpu_critical_percent": 90,
    "memory_warning_percent": 80,
    "memory_critical_percent": 90,
    "disk_warning_percent": 80,
    "disk_critical_percent": 90,
    "command_timeout_seconds": 30,
}


def load_configuration() -> dict[str, Any]:
    """Create the per-script configuration once, then preserve user changes."""
    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text(json.dumps(DEFAULT_CONFIG, indent=2), encoding="utf-8")
        return DEFAULT_CONFIG.copy()
    try:
        loaded = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise ValueError("configuration root must be an object")
        return {**DEFAULT_CONFIG, **loaded}
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Configuration error; using defaults: {error}", file=sys.stderr)
        return DEFAULT_CONFIG.copy()


CONFIG = load_configuration()
logging.basicConfig(
    filename=LOG_FILE,
    encoding="utf-8",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cross-platform server health monitor")
    parser.add_argument(
        "--schedule-info",
        action="store_true",
        help="Create the Windows launcher when applicable and print Task Scheduler/cron examples.",
    )
    return parser.parse_args()


def require_psutil() -> Any:
    if psutil is None:
        raise RuntimeError("The psutil package is required. Install it in the server's Python environment before running this monitor.")
    return psutil


def status_for(value: float, warning: float, critical: float) -> str:
    if value >= critical:
        return "CRITICAL"
    if value >= warning:
        return "WARNING"
    return "HEALTHY"


def run_command(command: list[str]) -> dict[str, Any]:
    executable = command[0]
    if shutil.which(executable) is None:
        return {"success": False, "output": "", "error": f"Required executable was not found: {executable}", "return_code": -1}
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=int(CONFIG["command_timeout_seconds"]),
            check=False,
        )
        if result.returncode != 0:
            logging.warning("Command failed (%s): %s", result.returncode, " ".join(command[:3]))
        return {
            "success": result.returncode == 0,
            "output": result.stdout.strip(),
            "error": result.stderr.strip(),
            "return_code": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "output": "", "error": "Command timed out", "return_code": -1}
    except OSError as error:
        logging.exception("Health command failed to start: %s", executable)
        return {"success": False, "output": "", "error": str(error), "return_code": -1}


def run_powershell(script: str) -> dict[str, Any]:
    executable = shutil.which("powershell.exe") or shutil.which("powershell")
    if executable is None:
        return {"success": False, "output": "", "error": "Windows PowerShell was not found.", "return_code": -1}
    return run_command([executable, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script])


def get_system_information() -> dict[str, Any]:
    module = require_psutil()
    boot_time = datetime.fromtimestamp(module.boot_time(), timezone.utc)
    uptime_hours = (datetime.now(timezone.utc) - boot_time).total_seconds() / 3600
    return {
        "hostname": HOSTNAME,
        "operating_system": OPERATING_SYSTEM,
        "platform": platform.platform(),
        "processor": platform.processor(),
        "architecture": platform.machine(),
        "python_version": platform.python_version(),
        "boot_time": boot_time.isoformat(),
        "uptime_hours": round(uptime_hours, 2),
    }


def check_cpu() -> dict[str, Any]:
    usage = require_psutil().cpu_percent(interval=1)
    return {
        "usage_percentage": usage,
        "status": status_for(usage, float(CONFIG["cpu_warning_percent"]), float(CONFIG["cpu_critical_percent"])),
    }


def check_memory() -> dict[str, Any]:
    memory = require_psutil().virtual_memory()
    return {
        "total_gb": round(memory.total / 1024**3, 2),
        "used_gb": round(memory.used / 1024**3, 2),
        "available_gb": round(memory.available / 1024**3, 2),
        "usage_percentage": memory.percent,
        "status": status_for(memory.percent, float(CONFIG["memory_warning_percent"]), float(CONFIG["memory_critical_percent"])),
    }


def get_disks() -> list[dict[str, Any]]:
    module = require_psutil()
    disks: list[dict[str, Any]] = []
    seen_mounts: set[str] = set()
    for partition in module.disk_partitions(all=False):
        if partition.mountpoint in seen_mounts:
            continue
        seen_mounts.add(partition.mountpoint)
        try:
            usage = module.disk_usage(partition.mountpoint)
        except (OSError, PermissionError) as error:
            logging.warning("Could not read disk usage for %s: %s", partition.mountpoint, error)
            continue
        disks.append(
            {
                "mount": partition.mountpoint,
                "filesystem": partition.fstype,
                "total_gb": round(usage.total / 1024**3, 2),
                "free_gb": round(usage.free / 1024**3, 2),
                "usage_percentage": round(usage.percent, 2),
                "status": status_for(usage.percent, float(CONFIG["disk_warning_percent"]), float(CONFIG["disk_critical_percent"])),
            }
        )
    return disks


def check_network() -> dict[str, Any]:
    network = require_psutil().net_io_counters()
    return {
        "bytes_sent_mb": round(network.bytes_sent / 1024**2, 2),
        "bytes_received_mb": round(network.bytes_recv / 1024**2, 2),
        "packets_sent": network.packets_sent,
        "packets_received": network.packets_recv,
        "errors_in": network.errin,
        "errors_out": network.errout,
    }


def check_processes() -> dict[str, int]:
    module = require_psutil()
    count = 0
    for _ in module.process_iter():
        count += 1
    return {"total_processes": count}


def platform_health_details() -> dict[str, Any]:
    """Collect an additional health indicator using commands for the active OS only."""
    if OPERATING_SYSTEM == "Linux":
        load_average: list[float] | None
        try:
            load_average = [round(value, 2) for value in os.getloadavg()]
        except (AttributeError, OSError):
            load_average = None
        if shutil.which("systemctl"):
            command = run_command(["systemctl", "is-system-running"])
            service_manager_state = command["output"] or command["error"]
        else:
            service_manager_state = "systemctl not available"
        return {"platform": "Linux", "load_average_1_5_15": load_average, "systemd_state": service_manager_state}

    if OPERATING_SYSTEM == "Windows":
        command = run_powershell("""
$OperatingSystem = Get-CimInstance Win32_OperatingSystem
[PSCustomObject]@{
    LastBootUpTime = $OperatingSystem.LastBootUpTime
    FreePhysicalMemoryMB = [math]::Round($OperatingSystem.FreePhysicalMemory / 1024, 2)
    TotalVisibleMemoryMB = [math]::Round($OperatingSystem.TotalVisibleMemorySize / 1024, 2)
} | ConvertTo-Json -Compress
""")
        try:
            details: Any = json.loads(command["output"]) if command["success"] else {}
        except json.JSONDecodeError:
            details = {"raw_output": command["output"]}
        return {"platform": "Windows", "windows_operating_system": details, "error": command["error"]}

    return {"platform": OPERATING_SYSTEM, "status": "UNSUPPORTED"}


def calculate_health_status(cpu: dict[str, Any], memory: dict[str, Any], disks: list[dict[str, Any]]) -> str:
    statuses = [cpu["status"], memory["status"], *(disk["status"] for disk in disks)]
    if "CRITICAL" in statuses:
        return "CRITICAL"
    if "WARNING" in statuses:
        return "WARNING"
    return "HEALTHY"


def create_windows_launcher() -> Path | None:
    """Create the safe PowerShell entry point used by Windows Task Scheduler."""
    if OPERATING_SYSTEM != "Windows":
        return None
    launcher_file = PATHS["script_directory"] / f"{SCRIPT_NAME}.ps1"
    launcher = r'''# Generated by server_health_monitor.py. Performs read-only health checks.
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$ScriptPath = Join-Path $PSScriptRoot 'server_health_monitor.py'
$PyLauncher = Get-Command py.exe -ErrorAction SilentlyContinue

if ($PyLauncher) {
    & $PyLauncher.Source -3 $ScriptPath
} else {
    & python.exe $ScriptPath
}

exit $LASTEXITCODE
'''
    try:
        if not launcher_file.exists() or launcher_file.read_text(encoding="utf-8") != launcher:
            launcher_file.write_text(launcher, encoding="utf-8")
        logging.info("Windows Task Scheduler launcher ready: %s", launcher_file)
        return launcher_file
    except OSError as error:
        logging.exception("Could not create the Windows launcher: %s", error)
        return None


def get_schedule_information(launcher_file: Path | None) -> dict[str, str]:
    if OPERATING_SYSTEM == "Windows":
        launcher = launcher_file or PATHS["script_directory"] / f"{SCRIPT_NAME}.ps1"
        return {
            "task_scheduler_program": "powershell.exe",
            "task_scheduler_arguments": f'-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "{launcher}"',
            "note": "Schedule at the desired collection interval. The monitor performs read-only checks.",
        }
    return {
        "cron_example": f"*/15 * * * * /usr/bin/python3 {PATHS['script_directory'] / f'{SCRIPT_NAME}.py'} >> {PATHS['log'] / 'cron.log'} 2>&1",
        "note": "The example collects health data every 15 minutes and redirects cron output to this monitor's log directory.",
    }


def save_report(report: dict[str, Any]) -> Path:
    report_file = PATHS["report"] / f"health_report_{RUN_TIME:%Y%m%d_%H%M%S}.json"
    report_file.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    logging.info("Health report saved: %s", report_file)
    return report_file


def main() -> int:
    args = parse_arguments()
    launcher_file = create_windows_launcher()
    if args.schedule_info:
        print(json.dumps({"run_id": RUN_ID, "operating_system": OPERATING_SYSTEM, "schedule": get_schedule_information(launcher_file)}, indent=2))
        logging.info("Scheduler information requested for %s", RUN_ID)
        return 0

    logging.info("Server health monitoring started: %s on %s", RUN_ID, OPERATING_SYSTEM)
    cpu = check_cpu()
    memory = check_memory()
    disks = get_disks()
    network = check_network()
    processes = check_processes()
    report: dict[str, Any] = {
        "run_id": RUN_ID,
        "timestamp": RUN_TIME.isoformat(),
        "automation": "SERVER_HEALTH_MONITOR",
        "hostname": HOSTNAME,
        "overall_status": calculate_health_status(cpu, memory, disks),
        "system": get_system_information(),
        "platform_health": platform_health_details(),
        "cpu": cpu,
        "memory": memory,
        "disks": disks,
        "network": network,
        "processes": processes,
        "log_file": str(LOG_FILE),
    }
    report_file = save_report(report)
    print(json.dumps({
        "run_id": RUN_ID,
        "hostname": HOSTNAME,
        "operating_system": OPERATING_SYSTEM,
        "overall_status": report["overall_status"],
        "cpu": cpu,
        "memory": memory,
        "disks_checked": len(disks),
        "report": str(report_file),
        "log": str(LOG_FILE),
        "scheduler": get_schedule_information(launcher_file),
    }, indent=2))
    logging.info("Server health monitoring completed: %s; status=%s", RUN_ID, report["overall_status"])
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        logging.exception("Health monitoring failed")
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
