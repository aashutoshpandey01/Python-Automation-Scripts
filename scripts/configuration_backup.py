#!/usr/bin/env python3
"""Copy selected Windows or Ubuntu configuration items into a per-run backup set."""

from __future__ import annotations

import argparse
import json
import logging
import platform
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_NAME = "configuration_backup"
OPERATING_SYSTEM = platform.system()
HOSTNAME = platform.node()
RUN_TIME = datetime.now(timezone.utc)
RUN_ID = f"CONFIG-BACKUP-{RUN_TIME:%Y%m%d-%H%M%S}"


def get_platform_paths() -> dict[str, Path]:
    """Select the approved hierarchy before selecting OS-specific source paths."""
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
        "backup": suite_root / "backups" / SCRIPT_NAME,
        "log": suite_root / "logs" / SCRIPT_NAME,
        "report": suite_root / "reports" / SCRIPT_NAME,
        "data": suite_root / "data" / SCRIPT_NAME,
    }


PATHS = get_platform_paths()
for path_name in ("script_directory", "backup", "log", "report", "data"):
    PATHS[path_name].mkdir(parents=True, exist_ok=True)



def get_run_backup_directory() -> Path:
    """Keep every backup run separate, even when two runs start in one second."""
    candidate = PATHS["backup"] / RUN_ID
    sequence = 2
    while candidate.exists():
        candidate = PATHS["backup"] / f"{RUN_ID}-{sequence:02d}"
        sequence += 1
    return candidate


RUN_BACKUP_DIRECTORY = get_run_backup_directory()
LOG_FILE = PATHS["log"] / f"{SCRIPT_NAME}_{RUN_TIME:%Y%m%d_%H%M%S}.log"
CONFIG_FILE = PATHS["data"] / f"{SCRIPT_NAME}.json"
DEFAULT_CONFIG: dict[str, Any] = {
    "linux_sources": [
        "/etc/ssh/sshd_config",
        "/etc/hosts",
        "/etc/hostname",
        "/etc/fstab",
        "/etc/resolv.conf",
        "/etc/apt/sources.list",
        "/etc/nginx/nginx.conf",
        "/etc/systemd/system",
    ],
    "windows_sources": [
        r"C:\Windows\System32\drivers\etc\hosts",
        r"C:\Windows\System32\GroupPolicy",
        r"C:\Windows\System32\inetsrv\config",
    ],
}


def load_configuration() -> dict[str, Any]:
    """Create the source-list configuration once and reuse administrator edits."""
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
    parser = argparse.ArgumentParser(description="Cross-platform configuration backup")
    parser.add_argument("--dry-run", action="store_true", help="Preview the configuration items that would be copied without writing a backup.")
    parser.add_argument(
        "--schedule-info",
        action="store_true",
        help="Create the Windows launcher when applicable and print Task Scheduler/cron examples.",
    )
    return parser.parse_args()


def get_configuration_files() -> list[Path]:
    config_key = "windows_sources" if OPERATING_SYSTEM == "Windows" else "linux_sources"
    configured = CONFIG.get(config_key, [])
    if not isinstance(configured, list):
        logging.warning("%s must be a list; no configuration items selected", config_key)
        return []
    sources: list[Path] = []
    seen: set[str] = set()
    for item in configured:
        if not isinstance(item, str) or not item.strip():
            continue
        source = Path(item).expanduser()
        comparison_key = str(source).casefold() if OPERATING_SYSTEM == "Windows" else str(source)
        if comparison_key in seen:
            logging.warning("Ignoring duplicate configuration source: %s", source)
            continue
        seen.add(comparison_key)
        sources.append(source)
    return sources


def destination_for(source: Path) -> Path:
    """Map an absolute source to a portable hierarchy inside this run's folder."""
    normalized = str(source).replace(":", "").replace("\\", "/").lstrip("/")
    return RUN_BACKUP_DIRECTORY / normalized


def source_safety_error(source: Path) -> str | None:
    """Prevent relative paths and backup recursion from administrator configuration."""
    if not source.is_absolute():
        return "Configuration sources must use absolute paths."
    try:
        source.resolve().relative_to(PATHS["backup"].resolve())
        return "The backup destination cannot be a source."
    except (OSError, ValueError):
        pass
    try:
        PATHS["backup"].resolve().relative_to(source.resolve())
        return "The source contains the backup destination and would cause recursive backups."
    except (OSError, ValueError):
        return None


def backup_configuration_item(source: Path, dry_run: bool) -> dict[str, Any]:
    result: dict[str, Any] = {"source": str(source), "status": "", "backup": "", "message": ""}
    safety_error = source_safety_error(source)
    if safety_error:
        logging.warning("Skipping unsafe configuration source %s: %s", source, safety_error)
        return {**result, "status": "SKIPPED_UNSAFE_SOURCE", "message": safety_error}
    if not source.exists():
        logging.warning("Configuration item not found: %s", source)
        return {**result, "status": "NOT_FOUND", "message": "Configuration item not found."}

    destination = destination_for(source)
    result["backup"] = str(destination)
    if dry_run:
        return {**result, "status": "WOULD_BACK_UP", "message": "Dry run; no files were copied."}
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, destination, symlinks=True)
        else:
            # Copy the configuration content.  This is important for Linux files
            # such as /etc/resolv.conf, which are commonly symbolic links.
            shutil.copy2(source, destination, follow_symlinks=True)
        logging.info("Configuration item backed up: %s -> %s", source, destination)
        return {**result, "status": "BACKED_UP", "message": "Backup completed successfully."}
    except PermissionError:
        logging.error("Permission denied while backing up: %s", source)
        return {**result, "status": "PERMISSION_DENIED", "message": "Permission denied."}
    except (OSError, shutil.Error) as error:
        logging.exception("Configuration backup failed: %s", source)
        return {**result, "status": "FAILED", "message": str(error)}


def create_windows_launcher() -> Path | None:
    """Create the Task Scheduler PowerShell entry point on Windows only."""
    if OPERATING_SYSTEM != "Windows":
        return None
    launcher_directory = PATHS["suite_root"] / "taskscheduler" / SCRIPT_NAME
    launcher_directory.mkdir(parents=True, exist_ok=True)

    launcher_file = launcher_directory / f"{SCRIPT_NAME}.ps1"
    launcher = r'''# Generated by configuration_backup.py.
[CmdletBinding()]
param([switch]$DryRun)

$ErrorActionPreference = 'Stop'
$ScriptPath = Join-Path $PSScriptRoot 'configuration_backup.py'
$PyLauncher = Get-Command py.exe -ErrorAction SilentlyContinue
$Arguments = @()
if ($PyLauncher) { $PythonCommand = $PyLauncher.Source; $Arguments += '-3' } else { $PythonCommand = 'python.exe' }
$Arguments += $ScriptPath
if ($DryRun) { $Arguments += '--dry-run' }
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
            "note": "The default task copies configured Windows configuration items into a new timestamped backup set.",
        }
    return {
        "cron_example": f"0 0 * * * /usr/bin/python3 {PATHS['script_directory'] / f'{SCRIPT_NAME}.py'} >> {PATHS['log'] / 'cron.log'} 2>&1",
        "dry_run_cron_example": f"0 0 * * * /usr/bin/python3 {PATHS['script_directory'] / f'{SCRIPT_NAME}.py'} --dry-run >> {PATHS['log'] / 'cron.log'} 2>&1",
        "note": "The default cron example copies configured Ubuntu configuration items into a new timestamped backup set daily.",
    }


def save_report(results: list[dict[str, Any]], dry_run: bool) -> Path:
    report_file = PATHS["report"] / f"configuration_backup_report_{RUN_TIME:%Y%m%d_%H%M%S}.json"
    report = {
        "run_id": RUN_ID,
        "timestamp": RUN_TIME.isoformat(),
        "hostname": HOSTNAME,
        "operating_system": OPERATING_SYSTEM,
        "automation": "CONFIGURATION_BACKUP",
        "dry_run": dry_run,
        "total_items": len(results),
        "backed_up": sum(item["status"] == "BACKED_UP" for item in results),
        "not_found": sum(item["status"] == "NOT_FOUND" for item in results),
        "skipped": sum(item["status"].startswith("SKIPPED_") for item in results),
        "failed": sum(item["status"] in {"FAILED", "PERMISSION_DENIED"} for item in results),
        "items": results,
        "backup_directory": str(RUN_BACKUP_DIRECTORY),
        "log_file": str(LOG_FILE),
    }
    report_file.write_text(json.dumps(report, indent=2), encoding="utf-8")
    logging.info("Configuration backup report saved: %s", report_file)
    return report_file


def main() -> int:
    args = parse_arguments()
    launcher_file = create_windows_launcher()
    if args.schedule_info:
        print(json.dumps({"run_id": RUN_ID, "operating_system": OPERATING_SYSTEM, "schedule": get_schedule_information(launcher_file)}, indent=2))
        logging.info("Scheduler information requested for %s", RUN_ID)
        return 0

    logging.info("Configuration backup started: %s on %s; dry_run=%s", RUN_ID, OPERATING_SYSTEM, args.dry_run)
    if not args.dry_run:
        RUN_BACKUP_DIRECTORY.mkdir(parents=True, exist_ok=True)
    results = [backup_configuration_item(source, args.dry_run) for source in get_configuration_files()]
    report_file = save_report(results, args.dry_run)
    print(json.dumps({
        "run_id": RUN_ID,
        "hostname": HOSTNAME,
        "operating_system": OPERATING_SYSTEM,
        "dry_run": args.dry_run,
        "items_processed": len(results),
        "backed_up": sum(item["status"] == "BACKED_UP" for item in results),
        "skipped": sum(item["status"].startswith("SKIPPED_") for item in results),
        "not_found": sum(item["status"] == "NOT_FOUND" for item in results),
        "failed": sum(item["status"] in {"FAILED", "PERMISSION_DENIED"} for item in results),
        "backup_directory": str(RUN_BACKUP_DIRECTORY),
        "report": str(report_file),
        "log": str(LOG_FILE),
        "scheduler": get_schedule_information(launcher_file),
    }, indent=2))
    logging.info("Configuration backup completed: %s", RUN_ID)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        logging.exception("Configuration backup failed")
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
