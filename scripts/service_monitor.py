#!/usr/bin/env python3
"""Monitor important Ubuntu or Windows services and report state transitions."""

from __future__ import annotations

import argparse
import json
import logging
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_NAME = "service_monitor"
OPERATING_SYSTEM = platform.system()
HOSTNAME = platform.node()
RUN_TIME = datetime.now(timezone.utc)
RUN_ID = f"SERVICE-{RUN_TIME:%Y%m%d-%H%M%S}"


def get_platform_paths() -> dict[str, Path]:
    """Choose the approved suite hierarchy before executing service commands."""
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
        "state": suite_root / "state" / SCRIPT_NAME,
        "data": suite_root / "data" / SCRIPT_NAME,
    }


PATHS = get_platform_paths()
for path_name in ("script_directory", "log", "report", "state", "data"):
    PATHS[path_name].mkdir(parents=True, exist_ok=True)

LOG_FILE = PATHS["log"] / f"{SCRIPT_NAME}_{RUN_TIME:%Y%m%d_%H%M%S}.log"
STATE_FILE = PATHS["state"] / "service_state.json"
CONFIG_FILE = PATHS["data"] / f"{SCRIPT_NAME}.json"
DEFAULT_CONFIG: dict[str, Any] = {
    "linux_services": ["ssh", "nginx", "cron"],
    "windows_services": ["Spooler", "W32Time", "WinDefend"],
    "auto_restart_on_transition": True,
    "command_timeout_seconds": 60,
}


def load_configuration() -> dict[str, Any]:
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
    parser = argparse.ArgumentParser(description="Cross-platform service monitoring")
    parser.add_argument(
        "--no-restart",
        action="store_true",
        help="Report service transitions without restarting a service that has gone down.",
    )
    parser.add_argument(
        "--schedule-info",
        action="store_true",
        help="Create the Windows launcher when applicable and print Task Scheduler/cron examples.",
    )
    return parser.parse_args()


def run_command(command: list[str]) -> dict[str, Any]:
    """Run a command for the already-selected operating system."""
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
        logging.exception("Service command failed to start: %s", executable)
        return {"success": False, "output": "", "error": str(error), "return_code": -1}


def run_powershell(script: str) -> dict[str, Any]:
    executable = shutil.which("powershell.exe") or shutil.which("powershell")
    if executable is None:
        return {"success": False, "output": "", "error": "Windows PowerShell was not found.", "return_code": -1}
    return run_command([executable, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script])


def load_previous_state() -> dict[str, str]:
    if not STATE_FILE.exists():
        return {}
    try:
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        if not isinstance(state, dict):
            raise ValueError("state root must be an object")
        return {str(service): str(status) for service, status in state.items()}
    except (OSError, ValueError, json.JSONDecodeError) as error:
        logging.warning("Could not load service state; starting a new state file: %s", error)
        return {}


def save_state(state: dict[str, str]) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def check_linux_service(service: str) -> dict[str, Any]:
    result = run_command(["systemctl", "is-active", service])
    status = result["output"].lower()
    if not status:
        status = "ERROR" if result["error"] else "UNKNOWN"
    return {"status": status, "success": result["success"], "error": result["error"]}


def restart_linux_service(service: str) -> dict[str, Any]:
    return run_command(["systemctl", "restart", service])


def check_windows_service(service: str) -> dict[str, Any]:
    safe_service = service.replace("'", "''")
    result = run_powershell(
        f"Get-Service -Name '{safe_service}' -ErrorAction Stop | Select-Object Status | ConvertTo-Json -Compress"
    )
    if not result["success"]:
        return {"status": "ERROR", "success": False, "error": result["error"]}
    try:
        data = json.loads(result["output"])
        status = str(data.get("Status", "UNKNOWN")) if isinstance(data, dict) else "UNKNOWN"
    except json.JSONDecodeError:
        status = "UNKNOWN"
    return {"status": status, "success": status != "UNKNOWN", "error": ""}


def restart_windows_service(service: str) -> dict[str, Any]:
    safe_service = service.replace("'", "''")
    return run_powershell(f"Restart-Service -Name '{safe_service}' -ErrorAction Stop")


def services_for_active_platform() -> list[str]:
    key = "linux_services" if OPERATING_SYSTEM == "Linux" else "windows_services"
    configured = CONFIG.get(key, [])
    if not isinstance(configured, list):
        logging.warning("%s must be a list; no services will be checked", key)
        return []
    return [item for item in configured if isinstance(item, str) and item.strip()]


def service_is_down(status: str) -> bool:
    return status.lower() in {"inactive", "failed", "stopped"}


def service_was_running(status: str | None) -> bool:
    return status is not None and status.lower() in {"active", "running"}


def monitor_services(disable_restart: bool) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """Preserve the original policy: restart only a running-to-down transition."""
    previous_state = load_previous_state()
    current_state: dict[str, str] = {}
    service_report: list[dict[str, Any]] = []
    restart_enabled = bool(CONFIG["auto_restart_on_transition"]) and not disable_restart

    for service in services_for_active_platform():
        check = check_linux_service(service) if OPERATING_SYSTEM == "Linux" else check_windows_service(service)
        status = str(check["status"])
        previous = previous_state.get(service)
        action = "SERVICE RUNNING"
        restart_result: dict[str, Any] | None = None

        if service_is_down(status):
            if service_was_running(previous) and restart_enabled:
                restart_result = restart_linux_service(service) if OPERATING_SYSTEM == "Linux" else restart_windows_service(service)
                action = "SERVICE RESTARTED" if restart_result["success"] else "RESTART FAILED"
            elif service_was_running(previous) and not restart_enabled:
                action = "RESTART SUPPRESSED"
            else:
                action = "SERVICE DOWN"
        elif status in {"ERROR", "UNKNOWN"}:
            action = "SERVICE CHECK FAILED"

        current_state[service] = status
        item: dict[str, Any] = {
            "service": service,
            "previous_status": previous,
            "current_status": status,
            "action": action,
            "check_error": check.get("error", ""),
        }
        if restart_result is not None:
            item["restart_error"] = restart_result.get("error", "")
        service_report.append(item)

    save_state(current_state)
    return service_report, current_state


def create_windows_launcher() -> Path | None:
    """Create the Task Scheduler PowerShell entry point on Windows only."""
    if OPERATING_SYSTEM != "Windows":
        return None
    launcher_file = PATHS["script_directory"] / f"{SCRIPT_NAME}.ps1"
    launcher = r'''# Generated by service_monitor.py.
[CmdletBinding()]
param([switch]$NoRestart)

$ErrorActionPreference = 'Stop'
$ScriptPath = Join-Path $PSScriptRoot 'service_monitor.py'
$PyLauncher = Get-Command py.exe -ErrorAction SilentlyContinue

if ($PyLauncher) {
    $Arguments = @('-3', $ScriptPath)
    if ($NoRestart) { $Arguments += '--no-restart' }
    & $PyLauncher.Source @Arguments
} else {
    $Arguments = @($ScriptPath)
    if ($NoRestart) { $Arguments += '--no-restart' }
    & python.exe @Arguments
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
            "no_restart_arguments": f'-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "{launcher}" -NoRestart',
            "note": "The default preserves transition-based automatic restarts. Use -NoRestart for monitoring only.",
        }
    return {
        "cron_example": f"*/5 * * * * /usr/bin/python3 {PATHS['script_directory'] / f'{SCRIPT_NAME}.py'} >> {PATHS['log'] / 'cron.log'} 2>&1",
        "no_restart_cron_example": f"*/5 * * * * /usr/bin/python3 {PATHS['script_directory'] / f'{SCRIPT_NAME}.py'} --no-restart >> {PATHS['log'] / 'cron.log'} 2>&1",
        "note": "The default cron example preserves transition-based automatic restarts and needs suitable service-control permission.",
    }


def save_report(services: list[dict[str, Any]], state: dict[str, str], restart_disabled: bool) -> Path:
    report_file = PATHS["report"] / f"service_report_{RUN_TIME:%Y%m%d_%H%M%S}.json"
    report = {
        "run_id": RUN_ID,
        "timestamp": RUN_TIME.isoformat(),
        "hostname": HOSTNAME,
        "operating_system": OPERATING_SYSTEM,
        "automation": "SERVICE_MONITOR",
        "automatic_restart_enabled": bool(CONFIG["auto_restart_on_transition"]) and not restart_disabled,
        "services": services,
        "current_state": state,
        "state_file": str(STATE_FILE),
        "log_file": str(LOG_FILE),
    }
    report_file.write_text(json.dumps(report, indent=2), encoding="utf-8")
    logging.info("Service report saved: %s", report_file)
    return report_file


def main() -> int:
    args = parse_arguments()
    launcher_file = create_windows_launcher()
    if args.schedule_info:
        print(json.dumps({"run_id": RUN_ID, "operating_system": OPERATING_SYSTEM, "schedule": get_schedule_information(launcher_file)}, indent=2))
        logging.info("Scheduler information requested for %s", RUN_ID)
        return 0

    logging.info("Service monitoring started: %s on %s", RUN_ID, OPERATING_SYSTEM)
    services, state = monitor_services(args.no_restart)
    report_file = save_report(services, state, args.no_restart)
    actions = {action: sum(item["action"] == action for item in services) for action in sorted({item["action"] for item in services})}
    print(json.dumps({
        "run_id": RUN_ID,
        "hostname": HOSTNAME,
        "operating_system": OPERATING_SYSTEM,
        "services_checked": len(services),
        "actions": actions,
        "report": str(report_file),
        "log": str(LOG_FILE),
        "scheduler": get_schedule_information(launcher_file),
    }, indent=2))
    logging.info("Service monitoring completed: %s", RUN_ID)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        logging.exception("Service monitoring crashed")
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
