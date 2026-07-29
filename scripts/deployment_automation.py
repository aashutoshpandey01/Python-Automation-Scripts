#!/usr/bin/env python3
"""Deploy a staged application copy with backup, service validation, and rollback.

The default data folders retain the original automation's self-contained demo
application.  Administrators can replace their contents with the application
they want to deploy; the script always deploys ``new_application`` over
``current_application`` after taking a per-run backup.
"""

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


SCRIPT_NAME = "deployment_automation"
OPERATING_SYSTEM = platform.system()
HOSTNAME = platform.node()
RUN_TIME = datetime.now(timezone.utc)
RUN_ID = f"DEPLOY-{RUN_TIME:%Y%m%d-%H%M%S}"


def get_platform_paths() -> dict[str, Path]:
    """Use the approved platform hierarchy before any deployment work starts."""
    if OPERATING_SYSTEM == "Windows":
        suite_root = Path(r"C:\AdminAutomation\python-scripts")
        script_directory = suite_root / "scripts"
    elif OPERATING_SYSTEM == "Linux":
        suite_root = Path("/home/cloudadmin/python-scripts")
        script_directory = suite_root
    else:
        raise RuntimeError(f"Unsupported operating system: {OPERATING_SYSTEM}")

    data_directory = suite_root / "data" / SCRIPT_NAME
    return {
        "suite_root": suite_root,
        "script_directory": script_directory,
        "data": data_directory,
        "current_application": data_directory / "current_application",
        "new_application": data_directory / "new_application",
        "staging": data_directory / "staging",
        "backup": suite_root / "backups" / SCRIPT_NAME,
        "log": suite_root / "logs" / SCRIPT_NAME,
        "report": suite_root / "reports" / SCRIPT_NAME,
    }


PATHS = get_platform_paths()
for directory_name, directory in PATHS.items():
    if directory_name != "suite_root":
        directory.mkdir(parents=True, exist_ok=True)

LOG_FILE = PATHS["log"] / f"{SCRIPT_NAME}_{RUN_TIME:%Y%m%d_%H%M%S}.log"
CONFIG_FILE = PATHS["data"] / f"{SCRIPT_NAME}.json"
logging.basicConfig(
    filename=LOG_FILE,
    encoding="utf-8",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

DEFAULT_CONFIG: dict[str, Any] = {
    "linux_service": "nginx",
    "windows_service": "Spooler",
    "auto_create_demo_content": True,
    "command_timeout_seconds": 60,
}


def load_configuration() -> dict[str, Any]:
    """Create a reusable deployment configuration and preserve later edits."""
    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text(json.dumps(DEFAULT_CONFIG, indent=2), encoding="utf-8")
        return DEFAULT_CONFIG.copy()
    try:
        configured = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        if not isinstance(configured, dict):
            raise ValueError("configuration root must be an object")
        return {**DEFAULT_CONFIG, **configured}
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Configuration error; using defaults: {error}", file=sys.stderr)
        return DEFAULT_CONFIG.copy()


CONFIG = load_configuration()


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cross-platform application deployment automation")
    parser.add_argument("--dry-run", action="store_true", help="Preview the deployment without copying, restarting, or rolling back.")
    parser.add_argument(
        "--no-restart",
        action="store_true",
        help="Deploy without restarting or checking the configured service.",
    )
    parser.add_argument(
        "--schedule-info",
        action="store_true",
        help="Create the Windows launcher when applicable and print Task Scheduler/cron examples.",
    )
    return parser.parse_args()


def get_run_backup_directory() -> Path:
    """Use a unique backup directory even for deployments started in one second."""
    candidate = PATHS["backup"] / RUN_ID
    sequence = 2
    while candidate.exists():
        candidate = PATHS["backup"] / f"{RUN_ID}-{sequence:02d}"
        sequence += 1
    return candidate


RUN_BACKUP_DIRECTORY = get_run_backup_directory()


def configured_timeout() -> int:
    try:
        return max(1, int(CONFIG["command_timeout_seconds"]))
    except (KeyError, TypeError, ValueError):
        return int(DEFAULT_CONFIG["command_timeout_seconds"])


def run_command(command: list[str]) -> subprocess.CompletedProcess[str] | None:
    """Run one OS-specific command without invoking a shell."""
    try:
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=configured_timeout(),
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as error:
        logging.error("Command failed (%s): %s", command, error)
        return None


def command_result(command: list[str], result: subprocess.CompletedProcess[str] | None) -> dict[str, Any]:
    """Keep bounded command diagnostics in the JSON report."""
    details: dict[str, Any] = {"command": command}
    if result is None:
        return {**details, "status": "COMMAND_NOT_RUN"}
    return {
        **details,
        "status": "COMMAND_COMPLETED",
        "return_code": result.returncode,
        "stdout": result.stdout.strip()[-2000:],
        "stderr": result.stderr.strip()[-2000:],
    }


def get_service_name() -> str | None:
    """Select only the service appropriate to the detected platform."""
    key = "windows_service" if OPERATING_SYSTEM == "Windows" else "linux_service"
    service_name = CONFIG.get(key)
    return service_name.strip() if isinstance(service_name, str) and service_name.strip() else None


def powershell_string(value: str) -> str:
    """Quote a configuration value for the limited PowerShell commands below."""
    return "'" + value.replace("'", "''") + "'"


def check_service() -> tuple[bool, dict[str, Any]]:
    """Check that the configured service is active with OS-specific commands."""
    service_name = get_service_name()
    if not service_name:
        return False, {"status": "SERVICE_NOT_CONFIGURED"}

    if OPERATING_SYSTEM == "Linux":
        command = ["systemctl", "is-active", service_name]
        result = run_command(command)
        details = command_result(command, result)
        is_active = bool(result and result.returncode == 0 and result.stdout.strip() == "active")
    elif OPERATING_SYSTEM == "Windows":
        command = [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            f"(Get-Service -Name {powershell_string(service_name)} -ErrorAction Stop).Status",
        ]
        result = run_command(command)
        details = command_result(command, result)
        is_active = bool(result and result.returncode == 0 and result.stdout.strip() == "Running")
    else:
        return False, {"status": "UNSUPPORTED_OPERATING_SYSTEM"}

    details.update(service=service_name, status="ACTIVE" if is_active else "NOT_ACTIVE")
    return is_active, details


def restart_service() -> tuple[bool, dict[str, Any]]:
    """Restart only the service command for the detected operating system."""
    service_name = get_service_name()
    if not service_name:
        return False, {"status": "SERVICE_NOT_CONFIGURED"}

    if OPERATING_SYSTEM == "Linux":
        # The cron account needs permission to run systemctl; sudo is intentionally
        # not used because it can block unattended jobs waiting for a password.
        command = ["systemctl", "restart", service_name]
    elif OPERATING_SYSTEM == "Windows":
        command = [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            f"Restart-Service -Name {powershell_string(service_name)} -ErrorAction Stop",
        ]
    else:
        return False, {"status": "UNSUPPORTED_OPERATING_SYSTEM"}

    result = run_command(command)
    details = command_result(command, result)
    restarted = bool(result and result.returncode == 0)
    details.update(service=service_name, status="RESTARTED" if restarted else "RESTART_FAILED")
    return restarted, details


def ensure_application_content(dry_run: bool) -> list[dict[str, str]]:
    """Preserve the original self-contained sample application on first use."""
    required_files = {
        PATHS["current_application"] / "application.txt": "Application Version 1\n",
        PATHS["new_application"] / "application.txt": "Application Version 2\n",
    }
    results: list[dict[str, str]] = []
    create_demo = bool(CONFIG.get("auto_create_demo_content", True))
    for file_path, default_content in required_files.items():
        item = {"path": str(file_path), "status": ""}
        if file_path.exists():
            item["status"] = "READY"
        elif not create_demo:
            item["status"] = "MISSING"
        elif dry_run:
            item["status"] = "WOULD_CREATE_DEMO_CONTENT"
        else:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(default_content, encoding="utf-8")
            item["status"] = "CREATED_DEMO_CONTENT"
        results.append(item)
    return results


def backup_current_version(dry_run: bool) -> dict[str, Any]:
    """Copy the complete current application into this deployment's backup set."""
    result: dict[str, Any] = {
        "source": str(PATHS["current_application"]),
        "backup": str(RUN_BACKUP_DIRECTORY),
        "status": "",
    }
    if not PATHS["current_application"].is_dir():
        return {**result, "status": "CURRENT_APPLICATION_MISSING"}
    if dry_run:
        return {**result, "status": "WOULD_BACK_UP"}
    try:
        shutil.copytree(PATHS["current_application"], RUN_BACKUP_DIRECTORY, symlinks=True)
        logging.info("Current application backed up to %s", RUN_BACKUP_DIRECTORY)
        return {**result, "status": "BACKED_UP"}
    except (OSError, shutil.Error) as error:
        logging.exception("Application backup failed")
        return {**result, "status": "BACKUP_FAILED", "error": str(error)}


def deploy_new_version(dry_run: bool) -> dict[str, Any]:
    """Stage the new version before replacing the current application folder."""
    source = PATHS["new_application"]
    staging = PATHS["staging"] / RUN_ID
    result: dict[str, Any] = {
        "source": str(source),
        "destination": str(PATHS["current_application"]),
        "staging": str(staging),
        "status": "",
    }
    if not source.is_dir():
        return {**result, "status": "NEW_APPLICATION_MISSING"}
    if dry_run:
        return {**result, "status": "WOULD_DEPLOY"}
    try:
        shutil.copytree(source, staging, symlinks=True)
        if PATHS["current_application"].exists():
            shutil.rmtree(PATHS["current_application"])
        shutil.move(str(staging), str(PATHS["current_application"]))
        logging.info("New application deployed from %s", source)
        return {**result, "status": "DEPLOYED"}
    except (OSError, shutil.Error) as error:
        logging.exception("Deployment failed")
        return {**result, "status": "DEPLOYMENT_FAILED", "error": str(error)}


def rollback(dry_run: bool) -> dict[str, Any]:
    """Restore the backed-up application when deployment or health validation fails."""
    result: dict[str, Any] = {
        "backup": str(RUN_BACKUP_DIRECTORY),
        "destination": str(PATHS["current_application"]),
        "status": "",
    }
    if not RUN_BACKUP_DIRECTORY.is_dir():
        return {**result, "status": "BACKUP_NOT_AVAILABLE"}
    if dry_run:
        return {**result, "status": "WOULD_ROLL_BACK"}
    try:
        if PATHS["current_application"].exists():
            shutil.rmtree(PATHS["current_application"])
        shutil.copytree(RUN_BACKUP_DIRECTORY, PATHS["current_application"], symlinks=True)
        logging.warning("Rollback completed from %s", RUN_BACKUP_DIRECTORY)
        return {**result, "status": "ROLLED_BACK"}
    except (OSError, shutil.Error) as error:
        logging.exception("Rollback failed")
        return {**result, "status": "ROLLBACK_FAILED", "error": str(error)}


def application_summary(directory: Path) -> dict[str, Any]:
    """Return a small, readable description instead of dumping application data."""
    if not directory.is_dir():
        return {"exists": False, "files": []}
    files = sorted(str(path.relative_to(directory)) for path in directory.rglob("*") if path.is_file())
    version_file = directory / "application.txt"
    version = None
    if version_file.exists():
        try:
            version = version_file.read_text(encoding="utf-8", errors="replace").strip()[:500]
        except OSError as error:
            version = f"Unable to read application.txt: {error}"
    return {"exists": True, "file_count": len(files), "files": files[:20], "application_version": version}


def create_windows_launcher() -> Path | None:
    """Create the PowerShell entry point used by Windows Task Scheduler."""
    if OPERATING_SYSTEM != "Windows":
        return None
    launcher_directory = PATHS["suite_root"] / "taskscheduler" / SCRIPT_NAME
    launcher_directory.mkdir(parents=True, exist_ok=True)

    launcher_file = launcher_directory / f"{SCRIPT_NAME}.ps1"
    launcher = r'''# Generated by deployment_automation.py.
[CmdletBinding()]
param([switch]$DryRun, [switch]$NoRestart)

$ErrorActionPreference = 'Stop'
$ScriptPath = Join-Path $PSScriptRoot 'deployment_automation.py'
$PyLauncher = Get-Command py.exe -ErrorAction SilentlyContinue
$Arguments = @()
if ($PyLauncher) { $PythonCommand = $PyLauncher.Source; $Arguments += '-3' } else { $PythonCommand = 'python.exe' }
$Arguments += $ScriptPath
if ($DryRun) { $Arguments += '--dry-run' }
if ($NoRestart) { $Arguments += '--no-restart' }
& $PythonCommand @Arguments
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
        launcher = launcher_file or (PATHS["suite_root"] / "taskscheduler" / SCRIPT_NAME / f"{SCRIPT_NAME}.ps1")
        return {
            "task_scheduler_program": "powershell.exe",
            "task_scheduler_arguments": f'-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "{launcher}"',
            "dry_run_arguments": f'-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "{launcher}" -DryRun',
            "note": "Run the task using an account permitted to restart the configured Windows service.",
        }
    return {
        "cron_example": f"0 2 * * * /usr/bin/python3 {PATHS['script_directory'] / f'{SCRIPT_NAME}.py'} >> {PATHS['log'] / 'cron.log'} 2>&1",
        "dry_run_cron_example": f"0 2 * * * /usr/bin/python3 {PATHS['script_directory'] / f'{SCRIPT_NAME}.py'} --dry-run >> {PATHS['log'] / 'cron.log'} 2>&1",
        "note": "The cron account needs non-interactive permission to restart the configured Linux service.",
    }


def save_report(report: dict[str, Any]) -> Path:
    report_file = PATHS["report"] / f"deployment_report_{RUN_TIME:%Y%m%d_%H%M%S}.json"
    report_file.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    logging.info("Deployment report created: %s", report_file)
    return report_file


def print_summary(report: dict[str, Any], report_file: Path) -> None:
    print(
        json.dumps(
            {
                "run_id": RUN_ID,
                "status": report["status"],
                "operating_system": OPERATING_SYSTEM,
                "backup": report["backup"]["backup"],
                "report": str(report_file),
                "log": str(LOG_FILE),
                "scheduler": report["scheduler"],
            },
            indent=2,
        )
    )


def main() -> int:
    args = parse_arguments()
    launcher_file = create_windows_launcher()
    if args.schedule_info:
        print(
            json.dumps(
                {
                    "run_id": RUN_ID,
                    "operating_system": OPERATING_SYSTEM,
                    "schedule": get_schedule_information(launcher_file),
                },
                indent=2,
            )
        )
        logging.info("Scheduler information requested for %s", RUN_ID)
        return 0

    report: dict[str, Any] = {
        "run_id": RUN_ID,
        "timestamp": RUN_TIME.isoformat(),
        "hostname": HOSTNAME,
        "operating_system": OPERATING_SYSTEM,
        "automation": "DEPLOYMENT_AUTOMATION",
        "dry_run": args.dry_run,
        "restart_requested": not args.no_restart,
        "before": application_summary(PATHS["current_application"]),
        "preparation": [],
        "backup": {"backup": str(RUN_BACKUP_DIRECTORY), "status": "NOT_STARTED"},
        "deployment": {"status": "NOT_STARTED"},
        "service_restart": {"status": "NOT_REQUESTED"},
        "health_check": {"status": "NOT_REQUESTED"},
        "rollback": {"status": "NOT_REQUIRED"},
        "scheduler": get_schedule_information(launcher_file),
        "log_file": str(LOG_FILE),
        "status": "STARTED",
    }
    exit_code = 0

    try:
        logging.info("Deployment started: %s on %s; dry_run=%s", RUN_ID, OPERATING_SYSTEM, args.dry_run)
        report["preparation"] = ensure_application_content(args.dry_run)
        if any(item["status"] == "MISSING" for item in report["preparation"]):
            report["status"] = "PRECONDITION_FAILED"
            exit_code = 1
        elif args.dry_run:
            report["backup"] = backup_current_version(dry_run=True)
            report["deployment"] = deploy_new_version(dry_run=True)
            report["service_restart"] = {"status": "WOULD_RESTART" if not args.no_restart else "SKIPPED_BY_ARGUMENT"}
            report["health_check"] = {"status": "WOULD_CHECK" if not args.no_restart else "SKIPPED_BY_ARGUMENT"}
            report["status"] = "DRY_RUN"
        else:
            report["backup"] = backup_current_version(dry_run=False)
            if report["backup"]["status"] != "BACKED_UP":
                report["status"] = "BACKUP_FAILED"
                exit_code = 1
            else:
                report["deployment"] = deploy_new_version(dry_run=False)
                if report["deployment"]["status"] != "DEPLOYED":
                    report["status"] = "DEPLOYMENT_FAILED"
                    report["rollback"] = rollback(dry_run=False)
                    exit_code = 1
                elif args.no_restart:
                    report["service_restart"] = {"status": "SKIPPED_BY_ARGUMENT"}
                    report["health_check"] = {"status": "SKIPPED_BY_ARGUMENT"}
                    report["status"] = "SUCCESS_NO_RESTART"
                else:
                    restarted, restart_details = restart_service()
                    report["service_restart"] = restart_details
                    healthy, health_details = check_service() if restarted else (False, {"status": "SKIPPED_RESTART_FAILED"})
                    report["health_check"] = health_details
                    if restarted and healthy:
                        report["status"] = "SUCCESS"
                    else:
                        report["rollback"] = rollback(dry_run=False)
                        if report["rollback"]["status"] == "ROLLED_BACK":
                            rollback_restarted, rollback_restart = restart_service()
                            report["rollback_service_restart"] = rollback_restart
                            if rollback_restarted:
                                _, rollback_health = check_service()
                                report["rollback_health_check"] = rollback_health
                        report["status"] = "ROLLED_BACK_AFTER_SERVICE_FAILURE"
                        exit_code = 1
    except Exception as error:
        logging.exception("Fatal deployment automation error")
        report["status"] = "FATAL_ERROR"
        report["error"] = str(error)
        exit_code = 1

    report["after"] = application_summary(PATHS["current_application"])
    report_file = save_report(report)
    print_summary(report, report_file)
    logging.info("Deployment completed: %s with status %s", RUN_ID, report["status"])
    return exit_code


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        logging.exception("Deployment automation failed before its report was saved")
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
