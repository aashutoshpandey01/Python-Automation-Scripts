#!/usr/bin/env python3
"""Create ZIP backups of platform-specific server configuration and log sources."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import platform
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


SCRIPT_NAME = "backup_automation"
OPERATING_SYSTEM = platform.system()
HOSTNAME = platform.node()
RUN_TIME = datetime.now(timezone.utc)
RUN_ID = f"BACKUP-{RUN_TIME:%Y%m%d-%H%M%S}"


def get_platform_paths() -> dict[str, Path]:
    """Select the approved hierarchy before reading platform backup sources."""
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

LOG_FILE = PATHS["log"] / f"{SCRIPT_NAME}_{RUN_TIME:%Y%m%d_%H%M%S}.log"
CONFIG_FILE = PATHS["data"] / f"{SCRIPT_NAME}.json"
DEFAULT_CONFIG: dict[str, Any] = {
    "retention_days": 30,
    "linux_sources": ["/etc/ssh", "/etc/systemd/system", "/var/log"],
    "windows_sources": [r"C:\Windows\System32\drivers\etc", r"C:\Windows\System32\GroupPolicy"],
}


def load_configuration() -> dict[str, Any]:
    """Create the backup settings once and reuse administrator changes thereafter."""
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
    parser = argparse.ArgumentParser(description="Cross-platform ZIP backup automation")
    parser.add_argument("--dry-run", action="store_true", help="List archives and retention deletions without writing or deleting files.")
    parser.add_argument("--skip-retention", action="store_true", help="Create backups without removing expired archives.")
    parser.add_argument(
        "--schedule-info",
        action="store_true",
        help="Create the Windows launcher when applicable and print Task Scheduler/cron examples.",
    )
    return parser.parse_args()


def get_backup_sources() -> list[Path]:
    """Return only source paths configured for the active operating system."""
    config_key = "windows_sources" if OPERATING_SYSTEM == "Windows" else "linux_sources"
    configured = CONFIG.get(config_key, [])
    if not isinstance(configured, list):
        logging.warning("%s must be a list; no sources selected", config_key)
        return []
    return [Path(item) for item in configured if isinstance(item, str) and item.strip()]


def archive_stem(source: Path, source_number: int) -> Path:
    """Avoid same-name source collisions while keeping a human-readable archive name."""
    path_hash = hashlib.sha256(str(source).encode("utf-8")).hexdigest()[:8]
    name = source.name or "root"
    return PATHS["backup"] / f"{name}_{source_number:02d}_{RUN_TIME:%Y%m%d_%H%M%S}_{path_hash}"


def is_backup_directory(source: Path) -> bool:
    try:
        source.resolve().relative_to(PATHS["backup"].resolve())
        return True
    except ValueError:
        return False
    except OSError:
        return False


def create_backup(source: Path, source_number: int, dry_run: bool) -> dict[str, Any]:
    result: dict[str, Any] = {"source": str(source), "status": "", "backup_file": "", "message": ""}
    if is_backup_directory(source):
        result.update(status="SKIPPED_BACKUP_DESTINATION", message="The backup destination cannot be a source.")
        return result
    if not source.exists():
        result.update(status="NOT_FOUND", message="Backup source does not exist.")
        logging.warning("Backup source missing: %s", source)
        return result

    archive_path = archive_stem(source, source_number)
    expected_archive = archive_path.with_suffix(".zip")
    result["backup_file"] = str(expected_archive)
    if dry_run:
        result.update(status="WOULD_CREATE", message="Dry run; no archive was written.")
        return result

    try:
        created_archive = shutil.make_archive(str(archive_path), "zip", root_dir=source.parent, base_dir=source.name)
        result.update(status="SUCCESS", backup_file=created_archive, message="Backup created successfully.")
        logging.info("Backup created: %s", created_archive)
    except PermissionError:
        result.update(status="PERMISSION_DENIED", message="Permission denied while reading the backup source.")
        logging.error("Permission denied while backing up: %s", source)
    except (OSError, shutil.Error) as error:
        result.update(status="FAILED", message=str(error))
        logging.exception("Backup failed: %s", source)
    return result


def retention_days() -> int:
    try:
        days = int(CONFIG["retention_days"])
        if days < 0:
            raise ValueError("retention_days cannot be negative")
        return days
    except (KeyError, TypeError, ValueError) as error:
        logging.warning("Invalid retention setting; using 30 days: %s", error)
        return 30


def delete_old_backups(dry_run: bool) -> list[dict[str, str]]:
    """Retain the original automatic cleanup, with dry-run visibility when requested."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days())
    deleted: list[dict[str, str]] = []
    for backup in PATHS["backup"].glob("*.zip"):
        try:
            modified = datetime.fromtimestamp(backup.stat().st_mtime, timezone.utc)
            if modified >= cutoff:
                continue
            if dry_run:
                deleted.append({"file": str(backup), "status": "WOULD_DELETE"})
            else:
                backup.unlink()
                deleted.append({"file": str(backup), "status": "DELETED"})
                logging.info("Deleted expired backup: %s", backup)
        except OSError as error:
            logging.exception("Backup cleanup failed for %s", backup)
            deleted.append({"file": str(backup), "status": f"FAILED: {error}"})
    return deleted


def create_windows_launcher() -> Path | None:
    """Create the Task Scheduler entry point on Windows only."""
    if OPERATING_SYSTEM != "Windows":
        return None
    launcher_directory = PATHS["suite_root"] / "taskscheduler" / SCRIPT_NAME
    launcher_directory.mkdir(parents=True, exist_ok=True)

    launcher_file = launcher_directory / f"{SCRIPT_NAME}.ps1"
    launcher = r'''# Generated by backup_automation.py.
[CmdletBinding()]
param([switch]$DryRun, [switch]$SkipRetention)

$ErrorActionPreference = 'Stop'
$ScriptPath = Join-Path $PSScriptRoot 'backup_automation.py'
$PyLauncher = Get-Command py.exe -ErrorAction SilentlyContinue
$Arguments = @()
if ($PyLauncher) { $PythonCommand = $PyLauncher.Source; $Arguments += '-3' } else { $PythonCommand = 'python.exe' }
$Arguments += $ScriptPath
if ($DryRun) { $Arguments += '--dry-run' }
if ($SkipRetention) { $Arguments += '--skip-retention' }
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
            "note": "The default task creates configured ZIP backups and enforces retention. Use -DryRun to validate first.",
        }
    return {
        "cron_example": f"0 1 * * * /usr/bin/python3 {PATHS['script_directory'] / f'{SCRIPT_NAME}.py'} >> {PATHS['log'] / 'cron.log'} 2>&1",
        "dry_run_cron_example": f"0 1 * * * /usr/bin/python3 {PATHS['script_directory'] / f'{SCRIPT_NAME}.py'} --dry-run >> {PATHS['log'] / 'cron.log'} 2>&1",
        "note": "The default cron example creates backups and removes archives older than the configured retention period.",
    }


def save_report(backup_results: list[dict[str, Any]], retention_results: list[dict[str, str]], dry_run: bool, skip_retention: bool) -> Path:
    report_file = PATHS["report"] / f"backup_report_{RUN_TIME:%Y%m%d_%H%M%S}.json"
    report = {
        "run_id": RUN_ID,
        "timestamp": RUN_TIME.isoformat(),
        "hostname": HOSTNAME,
        "operating_system": OPERATING_SYSTEM,
        "automation": "BACKUP_AUTOMATION",
        "dry_run": dry_run,
        "retention_days": retention_days(),
        "retention_skipped": skip_retention,
        "total_sources": len(backup_results),
        "successful_backups": sum(item["status"] == "SUCCESS" for item in backup_results),
        "failed_backups": sum(item["status"] in {"FAILED", "PERMISSION_DENIED"} for item in backup_results),
        "backup_results": backup_results,
        "retention_results": retention_results,
        "backup_directory": str(PATHS["backup"]),
        "log_file": str(LOG_FILE),
    }
    report_file.write_text(json.dumps(report, indent=2), encoding="utf-8")
    logging.info("Backup report saved: %s", report_file)
    return report_file


def main() -> int:
    args = parse_arguments()
    launcher_file = create_windows_launcher()
    if args.schedule_info:
        print(json.dumps({"run_id": RUN_ID, "operating_system": OPERATING_SYSTEM, "schedule": get_schedule_information(launcher_file)}, indent=2))
        logging.info("Scheduler information requested for %s", RUN_ID)
        return 0

    logging.info("Backup automation started: %s on %s; dry_run=%s", RUN_ID, OPERATING_SYSTEM, args.dry_run)
    results = [create_backup(source, number, args.dry_run) for number, source in enumerate(get_backup_sources(), start=1)]
    retention_results = [] if args.skip_retention else delete_old_backups(args.dry_run)
    report_file = save_report(results, retention_results, args.dry_run, args.skip_retention)
    print(json.dumps({
        "run_id": RUN_ID,
        "hostname": HOSTNAME,
        "operating_system": OPERATING_SYSTEM,
        "dry_run": args.dry_run,
        "sources_processed": len(results),
        "successful_backups": sum(item["status"] == "SUCCESS" for item in results),
        "retention_actions": len(retention_results),
        "backup_directory": str(PATHS["backup"]),
        "report": str(report_file),
        "log": str(LOG_FILE),
        "scheduler": get_schedule_information(launcher_file),
    }, indent=2))
    logging.info("Backup automation completed: %s", RUN_ID)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        logging.exception("Backup automation crashed")
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
