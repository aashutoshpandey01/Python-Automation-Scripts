#!/usr/bin/env python3
"""Cross-platform file and directory maintenance automation.

Scans configured OS-specific directories, backs up discovered files, optionally
removes files older than the retention period, archives the backup set, checks
disk capacity, and writes a per-run JSON/CSV report plus a SQLite history row.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import platform
import shutil
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


SCRIPT_NAME = "file_directory_automation"
OS_NAME = platform.system()
HOSTNAME = platform.node()
RUN_TIME = datetime.now()
RUN_ID = f"FILE-AUTO-{RUN_TIME:%Y%m%d-%H%M%S}"


def get_platform_paths() -> dict[str, Path]:
    """Return only the approved hierarchy for the OS running this script."""
    if OS_NAME == "Windows":
        suite_root = Path(r"C:\AdminAutomation\python-scripts")
        script_directory = suite_root / "scripts"
    elif OS_NAME == "Linux":
        suite_root = Path("/home/cloudadmin/python-scripts")
        script_directory = suite_root
    else:
        raise RuntimeError(f"Unsupported operating system: {OS_NAME}")

    return {
        "suite_root": suite_root,
        "script_directory": script_directory,
        "log": suite_root / "logs" / SCRIPT_NAME,
        "report": suite_root / "reports" / SCRIPT_NAME,
        "backup": suite_root / "backups" / SCRIPT_NAME,
        "archive": suite_root / "archives" / SCRIPT_NAME,
        "data": suite_root / "data" / SCRIPT_NAME,
    }


PATHS = get_platform_paths()
for directory in PATHS.values():
    if directory.name != "suite_root":
        directory.mkdir(parents=True, exist_ok=True)

CONFIG_FILE = PATHS["data"] / f"{SCRIPT_NAME}.json"
LOG_FILE = PATHS["log"] / f"{SCRIPT_NAME}_{RUN_TIME:%Y%m%d}.log"
DATABASE_FILE = PATHS["data"] / "automation_history.db"

DEFAULT_CONFIG: dict[str, Any] = {
    "delete_after_days": 30,
    "backup_enabled": True,
    "archive_enabled": True,
    "checksum_enabled": True,
    "disk_threshold": 85,
    # Empty lists use these original-purpose platform defaults.
    "windows_target_directories": [r"C:\Temp", r"C:\Logs", r"C:\Windows\Temp"],
    "linux_target_directories": ["/tmp", "/var/log", "/home"],
}


def load_configuration() -> dict[str, Any]:
    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text(json.dumps(DEFAULT_CONFIG, indent=2), encoding="utf-8")
        return DEFAULT_CONFIG.copy()
    try:
        configured = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        return {**DEFAULT_CONFIG, **configured}
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
    parser = argparse.ArgumentParser(description="Enterprise File Directory Automation")
    parser.add_argument("--dry-run", action="store_true", help="Preview without backup, deletion, or archive writes.")
    parser.add_argument("--targets", nargs="+", type=Path, help="Override configured targets for this one run.")
    return parser.parse_args()


def get_target_directories(overrides: list[Path] | None) -> list[Path]:
    if overrides:
        return overrides
    if OS_NAME == "Windows":
        return [Path(item) for item in CONFIG["windows_target_directories"]]
    if OS_NAME == "Linux":
        return [Path(item) for item in CONFIG["linux_target_directories"]]
    return []


def collect_system_information() -> dict[str, str]:
    return {
        "hostname": HOSTNAME,
        "operating_system": OS_NAME,
        "platform": platform.platform(),
        "kernel": platform.release(),
        "architecture": platform.machine(),
        "python_version": sys.version.split()[0],
    }


def scan_directory(directory: Path) -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = []
    if not directory.exists():
        logging.warning("Directory not found: %s", directory)
        return files
    logging.info("Scanning directory: %s", directory)
    try:
        for item in directory.rglob("*"):
            try:
                if item.is_file():
                    stat = item.stat()
                    files.append({"path": str(item), "name": item.name, "size": stat.st_size,
                                  "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()})
            except (PermissionError, FileNotFoundError) as error:
                logging.warning("Skipping %s: %s", item, error)
    except (OSError, PermissionError) as error:
        logging.exception("File scanner failed for %s: %s", directory, error)
    return files


def find_old_files(directory: Path) -> list[Path]:
    cutoff = datetime.now() - timedelta(days=int(CONFIG["delete_after_days"]))
    old_files: list[Path] = []
    if not directory.exists():
        return old_files
    try:
        for item in directory.rglob("*"):
            try:
                if item.is_file() and datetime.fromtimestamp(item.stat().st_mtime) < cutoff:
                    old_files.append(item)
            except (PermissionError, FileNotFoundError) as error:
                logging.warning("Skipping %s: %s", item, error)
    except (OSError, PermissionError) as error:
        logging.exception("Old-file scan failed for %s: %s", directory, error)
    return old_files


def backup_destination(source: Path) -> Path:
    # Drive names and absolute-root markers are normalized into a portable hierarchy.
    normalized = str(source).replace(":", "").lstrip("/\\")
    destination = PATHS["backup"] / normalized
    destination.parent.mkdir(parents=True, exist_ok=True)
    return destination


def sha256(file_path: Path) -> str:
    digest = hashlib.sha256()
    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def backup_file(source: Path, dry_run: bool) -> dict[str, Any]:
    result: dict[str, Any] = {"source": str(source), "status": ""}
    if not source.exists():
        return {**result, "status": "NOT_FOUND"}
    destination = backup_destination(source)
    result["destination"] = str(destination)
    if dry_run:
        return {**result, "status": "WOULD_BACKUP"}
    if not CONFIG["backup_enabled"]:
        return {**result, "status": "DISABLED"}
    try:
        shutil.copy2(source, destination)
        if CONFIG["checksum_enabled"]:
            checksum = sha256(destination)
            destination.with_suffix(destination.suffix + ".sha256").write_text(checksum + "\n", encoding="utf-8")
            result["checksum"] = checksum
        result["status"] = "BACKED_UP"
    except (OSError, shutil.Error) as error:
        logging.exception("Backup failed for %s", source)
        result.update(status="FAILED", error=str(error))
    return result


def delete_old_files(files: list[Path], dry_run: bool) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    for file_path in files:
        result = {"file": str(file_path), "status": ""}
        try:
            if dry_run:
                result["status"] = "WOULD_DELETE"
            else:
                file_path.unlink()
                result["status"] = "DELETED"
        except PermissionError:
            result["status"] = "PERMISSION_DENIED"
        except FileNotFoundError:
            result["status"] = "NOT_FOUND"
        except OSError as error:
            result.update(status="FAILED", error=str(error))
        results.append(result)
    return results


def create_archive(dry_run: bool) -> dict[str, str]:
    if not CONFIG["archive_enabled"]:
        return {"status": "DISABLED"}
    if dry_run:
        return {"status": "WOULD_CREATE", "archive": str(PATHS["archive"] / f"backup_{RUN_TIME:%Y%m%d_%H%M%S}.zip")}
    archive_base = PATHS["archive"] / f"backup_{RUN_TIME:%Y%m%d_%H%M%S}"
    try:
        archive = shutil.make_archive(str(archive_base), "zip", root_dir=PATHS["backup"])
        return {"status": "CREATED", "archive": archive}
    except (OSError, shutil.Error) as error:
        logging.exception("Archive creation failed")
        return {"status": "FAILED", "error": str(error)}


def check_disk_usage() -> list[dict[str, Any]]:
    paths = [Path("C:/")] if OS_NAME == "Windows" else [Path("/"), Path("/home")]
    result: list[dict[str, Any]] = []
    for path in paths:
        if not path.exists():
            continue
        usage = shutil.disk_usage(path)
        percent = round(usage.used / usage.total * 100, 2)
        result.append({"path": str(path), "total_gb": round(usage.total / 1024**3, 2),
                       "used_gb": round(usage.used / 1024**3, 2), "free_gb": round(usage.free / 1024**3, 2),
                       "usage_percent": percent, "status": "WARNING" if percent >= CONFIG["disk_threshold"] else "NORMAL"})
    return result


def create_reports(report: dict[str, Any]) -> tuple[Path, Path]:
    stamp = RUN_TIME.strftime("%Y%m%d_%H%M%S")
    json_file = PATHS["report"] / f"report_{stamp}.json"
    csv_file = PATHS["report"] / f"report_{stamp}.csv"
    json_file.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    with csv_file.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["CATEGORY", "VALUE"])
        writer.writerows((key, json.dumps(value, default=str)) for key, value in report.items())
    return json_file, csv_file


def save_database(report: dict[str, Any]) -> None:
    with sqlite3.connect(DATABASE_FILE) as connection:
        connection.execute("""CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, hostname TEXT,
            operating_system TEXT, timestamp TEXT, files_found INTEGER,
            deleted INTEGER, archive_status TEXT)""")
        connection.execute("INSERT INTO runs VALUES (NULL,?,?,?,?,?,?,?)", (
            RUN_ID, HOSTNAME, OS_NAME, RUN_TIME.isoformat(), report["files_found"],
            report["deleted"], report["archive"]["status"]))


def main() -> int:
    args = parse_arguments()
    targets = get_target_directories(args.targets)
    logging.info("Started %s on %s; targets=%s; dry_run=%s", RUN_ID, OS_NAME, targets, args.dry_run)
    scanned = [file for target in targets for file in scan_directory(target)]
    old_files = [file for target in targets for file in find_old_files(target)]
    backups = [backup_file(Path(file["path"]), args.dry_run) for file in scanned]
    cleanup = delete_old_files(old_files, args.dry_run)
    archive = create_archive(args.dry_run)
    report: dict[str, Any] = {
        "run_id": RUN_ID, "collection_time": RUN_TIME.isoformat(), "dry_run": args.dry_run,
        "system": collect_system_information(), "target_directories": [str(item) for item in targets],
        "files_found": len(scanned), "old_files": len(old_files),
        "deleted": sum(item["status"] == "DELETED" for item in cleanup), "backup": backups,
        "cleanup": cleanup, "archive": archive, "disk": check_disk_usage(), "log_file": str(LOG_FILE),
    }
    json_report, csv_report = create_reports(report)
    report.update(json_report=str(json_report), csv_report=str(csv_report))
    save_database(report)
    print(json.dumps({key: report[key] for key in ("run_id", "files_found", "old_files", "deleted", "archive", "json_report", "csv_report", "log_file")}, indent=2))
    logging.info("Completed %s", RUN_ID)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        logging.exception("Fatal automation error")
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
