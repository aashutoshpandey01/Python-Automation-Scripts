#!/usr/bin/env python3
"""Scan for or apply Ubuntu and Windows Server operating-system updates."""

from __future__ import annotations

import argparse
import json
import logging
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_NAME = "patch_update_automation"
OPERATING_SYSTEM = platform.system()
HOSTNAME = platform.node()
RUN_TIME = datetime.now(timezone.utc)
RUN_ID = f"PATCH-{RUN_TIME:%Y%m%d-%H%M%S}"


def get_platform_paths() -> dict[str, Path]:
    """Choose the approved hierarchy before selecting the OS update mechanism."""
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
# ``script_directory`` is separate from the Linux suite root on Windows.  It
# must exist before the Task Scheduler launcher can be created there.
for key in ("script_directory", "log", "report", "data"):
    PATHS[key].mkdir(parents=True, exist_ok=True)

LOG_FILE = PATHS["log"] / f"{SCRIPT_NAME}_{RUN_TIME:%Y%m%d_%H%M%S}.log"
CONFIG_FILE = PATHS["data"] / f"{SCRIPT_NAME}.json"
DEFAULT_CONFIG: dict[str, Any] = {
    "command_timeout_seconds": 1800,
    "ubuntu_autoremove_after_upgrade": True,
    "ubuntu_noninteractive": True,
}


def load_configuration() -> dict[str, Any]:
    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text(json.dumps(DEFAULT_CONFIG, indent=2), encoding="utf-8")
        return DEFAULT_CONFIG.copy()
    try:
        return {**DEFAULT_CONFIG, **json.loads(CONFIG_FILE.read_text(encoding="utf-8"))}
    except (OSError, json.JSONDecodeError) as error:
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
    parser = argparse.ArgumentParser(description="Enterprise Patch and Update Automation")
    parser.add_argument("--apply", action="store_true", help="Download and install updates. Without this flag, only scan for updates.")
    parser.add_argument(
        "--schedule-info",
        action="store_true",
        help="Create the Windows PowerShell launcher when applicable and print safe Task Scheduler/cron examples.",
    )
    return parser.parse_args()


def run_command(command: list[str], environment: dict[str, str] | None = None) -> dict[str, Any]:
    executable = command[0]
    if shutil.which(executable) is None:
        message = f"Required executable was not found: {executable}"
        logging.error(message)
        return {"command": " ".join(command[:3]), "return_code": -1, "stdout": "", "stderr": message, "success": False}
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=int(CONFIG["command_timeout_seconds"]),
            env=environment, check=False,
        )
        if result.returncode != 0:
            logging.warning("Command failed (%s): %s", result.returncode, " ".join(command[:3]))
        return {
            "command": " ".join(command[:3]) + (" ..." if len(command) > 3 else ""),
            "return_code": result.returncode, "stdout": result.stdout.strip(), "stderr": result.stderr.strip(),
            "success": result.returncode == 0,
        }
    except subprocess.TimeoutExpired:
        return {"command": " ".join(command[:3]), "return_code": -1, "stdout": "", "stderr": "Command timeout", "success": False}
    except OSError as error:
        logging.exception("Update command failed to start")
        return {"command": " ".join(command[:3]), "return_code": -1, "stdout": "", "stderr": str(error), "success": False}


def ubuntu_command(command: list[str]) -> list[str]:
    """Use direct apt as root or non-interactive sudo for cron-compatible privilege handling."""
    if os.geteuid() == 0:
        return command
    return ["sudo", "-n", *command]


def ubuntu_patch_update(apply_updates: bool) -> dict[str, Any]:
    report: dict[str, Any] = {"platform": "Linux", "mode": "APPLY" if apply_updates else "SCAN", "apt_update": None,
                              "upgrade": None, "autoremove": None, "reboot_required": Path("/var/run/reboot-required").exists()}
    if shutil.which("apt-get") is None:
        report["upgrade"] = {
            "command": "apt-get", "return_code": -1, "stdout": "",
            "stderr": "This Linux host does not provide apt-get; patch_update_automation supports Ubuntu Server only.",
            "success": False,
        }
        return report
    if os.geteuid() != 0 and shutil.which("sudo") is None:
        report["upgrade"] = {
            "command": "sudo apt-get", "return_code": -1, "stdout": "",
            "stderr": "Update installation requires root or passwordless sudo for cron execution.", "success": False,
        }
        return report
    environment = os.environ.copy()
    if CONFIG["ubuntu_noninteractive"]:
        environment["DEBIAN_FRONTEND"] = "noninteractive"

    if not apply_updates:
        report["upgrade"] = run_command(ubuntu_command(["apt-get", "-s", "upgrade"]), environment)
        return report

    report["apt_update"] = run_command(ubuntu_command(["apt-get", "update"]), environment)
    if not report["apt_update"]["success"]:
        return report
    report["upgrade"] = run_command(ubuntu_command(["apt-get", "upgrade", "-y"]), environment)
    if report["upgrade"]["success"] and CONFIG["ubuntu_autoremove_after_upgrade"]:
        report["autoremove"] = run_command(ubuntu_command(["apt-get", "autoremove", "-y"]), environment)
    report["reboot_required"] = Path("/var/run/reboot-required").exists()
    return report


def windows_patch_update(apply_updates: bool) -> dict[str, Any]:
    # This script is executed only after the platform branch selected Windows.
    if apply_updates:
        action = r'''
$Collection = New-Object -ComObject Microsoft.Update.UpdateColl
foreach ($Update in $Updates.Updates) {
    if (-not $Update.EulaAccepted) { $Update.AcceptEula() }
    [void]$Collection.Add($Update)
}
$Downloader = $Session.CreateUpdateDownloader()
$Downloader.Updates = $Collection
$DownloadResult = $Downloader.Download()
$Installer = $Session.CreateUpdateInstaller()
$Installer.Updates = $Collection
$InstallResult = $Installer.Install()
[PSCustomObject]@{ Mode='APPLY'; UpdateCount=$Collection.Count; DownloadResult=$DownloadResult.ResultCode; InstallResult=$InstallResult.ResultCode; RebootRequired=$InstallResult.RebootRequired } | ConvertTo-Json -Compress
'''
    else:
        action = r'''
[PSCustomObject]@{ Mode='SCAN'; UpdateCount=$Updates.Updates.Count; Titles=@($Updates.Updates | ForEach-Object Title); RebootRequired=$false } | ConvertTo-Json -Compress
'''
    powershell_script = r'''
$ErrorActionPreference = 'Stop'
$Session = New-Object -ComObject Microsoft.Update.Session
$Searcher = $Session.CreateUpdateSearcher()
$Updates = $Searcher.Search('IsInstalled=0 and IsHidden=0')
''' + action
    powershell = shutil.which("powershell.exe") or shutil.which("powershell")
    if powershell is None:
        result = {
            "command": "powershell", "return_code": -1, "stdout": "",
            "stderr": "Windows PowerShell was not found. Windows Update automation requires powershell.exe.", "success": False,
        }
    else:
        result = run_command([powershell, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", powershell_script])

    update_details: dict[str, Any] = {}
    if result["success"] and result["stdout"]:
        try:
            update_details = json.loads(result["stdout"])
        except json.JSONDecodeError:
            logging.warning("Windows Update returned non-JSON output: %s", result["stdout"][:500])
    reboot_required = bool(update_details.get("RebootRequired", False))
    return {
        "platform": "Windows", "mode": "APPLY" if apply_updates else "SCAN", "windows_update": result,
        "update_details": update_details, "reboot_required": reboot_required,
    }


def create_windows_launcher() -> Path | None:
    """Create the PowerShell entry point used by Task Scheduler on Windows only."""
    if OPERATING_SYSTEM != "Windows":
        return None

    launcher_directory = PATHS["suite_root"] / "taskscheduler" / SCRIPT_NAME
    launcher_directory.mkdir(parents=True, exist_ok=True)

    launcher_file = launcher_directory / f"{SCRIPT_NAME}.ps1"
    launcher = r'''# Generated by patch_update_automation.py. Safe by default: scans only.
[CmdletBinding()]
param([switch]$Apply)

$ErrorActionPreference = 'Stop'
$ScriptPath = Join-Path $PSScriptRoot 'patch_update_automation.py'
$PyLauncher = Get-Command py.exe -ErrorAction SilentlyContinue

if ($PyLauncher) {
    $Arguments = @('-3', $ScriptPath)
    if ($Apply) { $Arguments += '--apply' }
    & $PyLauncher.Source @Arguments
} else {
    $Arguments = @($ScriptPath)
    if ($Apply) { $Arguments += '--apply' }
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
        logging.exception("Could not create the Windows launcher")
        return None


def get_schedule_information(launcher_file: Path | None) -> dict[str, str]:
    """Return non-destructive scheduler commands for the platform in use."""
    if OPERATING_SYSTEM == "Windows":
        launcher = launcher_file or (PATHS["suite_root"] / "taskscheduler" / SCRIPT_NAME / f"{SCRIPT_NAME}.ps1")
        return {
            "task_scheduler_program": "powershell.exe",
            "task_scheduler_arguments": f'-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "{launcher}"',
            "apply_updates_arguments": f'-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "{launcher}" -Apply',
            "note": "Run the task with an account allowed to install Windows updates. The default command scans only.",
        }
    return {
        "cron_scan_example": f"0 2 * * * /usr/bin/python3 {PATHS['script_directory'] / f'{SCRIPT_NAME}.py'} >> {PATHS['log'] / 'cron.log'} 2>&1",
        "cron_apply_example": f"0 2 * * 0 /usr/bin/python3 {PATHS['script_directory'] / f'{SCRIPT_NAME}.py'} --apply >> {PATHS['log'] / 'cron.log'} 2>&1",
        "note": "Use root's crontab or configure passwordless sudo for apt-get. The scan example does not install updates.",
    }


def save_report(data: dict[str, Any]) -> Path:
    report_file = PATHS["report"] / f"patch_update_report_{RUN_TIME:%Y%m%d_%H%M%S}.json"
    report = {
        "run_id": RUN_ID, "timestamp": RUN_TIME.isoformat(), "hostname": HOSTNAME,
        "operating_system": OPERATING_SYSTEM, "automation": "PATCH_UPDATE_AUTOMATION",
        "log_file": str(LOG_FILE), "result": data,
    }
    report_file.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    logging.info("Patch report saved: %s", report_file)
    return report_file


def main() -> int:
    args = parse_arguments()
    launcher_file = create_windows_launcher()
    if args.schedule_info:
        schedule = get_schedule_information(launcher_file)
        print(json.dumps({"run_id": RUN_ID, "operating_system": OPERATING_SYSTEM, "schedule": schedule}, indent=2))
        logging.info("Scheduler information requested for %s", RUN_ID)
        return 0

    logging.info("Patch automation started: %s on %s; apply=%s", RUN_ID, OPERATING_SYSTEM, args.apply)
    if OPERATING_SYSTEM == "Linux":
        result = ubuntu_patch_update(args.apply)
    elif OPERATING_SYSTEM == "Windows":
        result = windows_patch_update(args.apply)
    else:
        raise RuntimeError(f"Unsupported operating system: {OPERATING_SYSTEM}")
    report_file = save_report(result)
    command_result = result.get("upgrade") if OPERATING_SYSTEM == "Linux" else result.get("windows_update")
    success = command_result is not None and command_result.get("success", False)
    print(json.dumps({
        "run_id": RUN_ID, "hostname": HOSTNAME, "operating_system": OPERATING_SYSTEM,
        "mode": result["mode"], "success": success, "reboot_required": result["reboot_required"],
        "report": str(report_file), "log": str(LOG_FILE), "scheduler": get_schedule_information(launcher_file),
    }, indent=2))
    logging.info("Patch automation completed: %s", RUN_ID)
    return 0 if success else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        logging.exception("Patch automation failed")
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
