#!/usr/bin/env python3
"""Analyse recent Linux system logs or Windows Event Logs for key events."""

from __future__ import annotations

import argparse
import json
import logging
import platform
import subprocess
import sys
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_NAME = "log_analysis"
OPERATING_SYSTEM = platform.system()
HOSTNAME = platform.node()
RUN_TIME = datetime.now(timezone.utc)
RUN_ID = f"LOG-ANALYSIS-{RUN_TIME:%Y%m%d-%H%M%S}"


def get_platform_paths() -> dict[str, Path]:
    """Select the correct managed-server hierarchy before analysing logs."""
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

LOG_FILE = PATHS["log"] / f"{SCRIPT_NAME}_{RUN_TIME:%Y%m%d_%H%M%S}.log"
CONFIG_FILE = PATHS["data"] / f"{SCRIPT_NAME}.json"

DEFAULT_CONFIG: dict[str, Any] = {
    "lines_to_read": 500,
    "event_keywords": {
        "ERROR": ["error", "failed", "failure", "critical", "fatal"],
        "WARNING": ["warning", "warn"],
        "AUTHENTICATION_FAILURE": ["authentication failure", "failed password", "login failed", "invalid user", "access denied"],
    },
    "linux_log_sources": ["/var/log/auth.log", "/var/log/syslog", "/var/log/kern.log", "/var/log/dpkg.log"],
    "windows_event_logs": ["System", "Security", "Application"],
}


def load_configuration() -> dict[str, Any]:
    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text(json.dumps(DEFAULT_CONFIG, indent=2), encoding="utf-8")
        return DEFAULT_CONFIG.copy()
    try:
        loaded = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        return {**DEFAULT_CONFIG, **loaded}
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
    parser = argparse.ArgumentParser(description="Enterprise Log Analysis Automation")
    parser.add_argument("--lines", type=int, help="Override the configured number of recent records per source.")
    return parser.parse_args()


def get_log_sources() -> list[Path] | list[str]:
    if OPERATING_SYSTEM == "Linux":
        return [Path(item) for item in CONFIG["linux_log_sources"]]
    if OPERATING_SYSTEM == "Windows":
        return [str(item) for item in CONFIG["windows_event_logs"]]
    return []


def read_linux_log(log_file: Path, lines_to_read: int) -> dict[str, Any]:
    if not log_file.exists():
        logging.warning("Log file not found: %s", log_file)
        return {"source": str(log_file), "status": "NOT_FOUND", "message": "Log file missing", "lines": []}
    try:
        with log_file.open("r", encoding="utf-8", errors="replace") as handle:
            lines = list(deque(handle, maxlen=lines_to_read))
        return {"source": str(log_file), "status": "READ_SUCCESS", "message": "Log read successfully", "lines": lines}
    except PermissionError:
        logging.warning("Permission denied: %s", log_file)
        return {"source": str(log_file), "status": "PERMISSION_DENIED", "message": "Permission denied", "lines": []}
    except OSError as error:
        logging.exception("Linux log reading failed for %s", log_file)
        return {"source": str(log_file), "status": "FAILED", "message": str(error), "lines": []}


def read_windows_log(log_name: str, lines_to_read: int) -> dict[str, Any]:
    """Read Windows Event Logs only when the OS detection selected Windows."""
    command = (
        f"Get-WinEvent -LogName '{log_name}' -MaxEvents {lines_to_read} -ErrorAction Stop | "
        "Select-Object TimeCreated,Id,LevelDisplayName,ProviderName,Message | ConvertTo-Json -Depth 3"
    )
    try:
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
            capture_output=True, text=True, timeout=60, check=False,
        )
        if completed.returncode != 0:
            message = completed.stderr.strip() or "Get-WinEvent failed"
            logging.warning("Unable to read Event Log %s: %s", log_name, message)
            return {"source": log_name, "status": "FAILED", "message": message, "events": []}
        if not completed.stdout.strip():
            return {"source": log_name, "status": "NO_EVENTS", "message": "No events found", "events": []}
        parsed = json.loads(completed.stdout)
        events = parsed if isinstance(parsed, list) else [parsed]
        return {"source": log_name, "status": "READ_SUCCESS", "message": "Event log read successfully", "events": events}
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as error:
        logging.exception("Windows event reading failed for %s", log_name)
        return {"source": log_name, "status": "FAILED", "message": str(error), "events": []}


def analyse_text_records(records: list[dict[str, str]], text_key: str) -> dict[str, Any]:
    keywords: dict[str, list[str]] = CONFIG["event_keywords"]
    counts = {category: 0 for category in keywords}
    detected: list[dict[str, Any]] = []
    for record in records:
        text = str(record[text_key]).lower()
        categories = [category for category, values in keywords.items() if any(keyword.lower() in text for keyword in values)]
        if categories:
            for category in categories:
                counts[category] += 1
            detected.append({**record, "categories": categories})
    return {"event_counts": counts, "events": detected}


def analyse_linux_lines(lines: list[str]) -> dict[str, Any]:
    return analyse_text_records([{"log": line.strip()} for line in lines], "log")


def analyse_windows_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    records = []
    for event in events:
        message = str(event.get("Message", ""))
        records.append({
            "time": str(event.get("TimeCreated", "")), "event_id": event.get("Id", ""),
            "provider": str(event.get("ProviderName", "")), "level": str(event.get("LevelDisplayName", "")),
            "message": message, "analysis_text": f"{message} {event.get('LevelDisplayName', '')}",
        })
    analysis = analyse_text_records(records, "analysis_text")
    for event in analysis["events"]:
        event.pop("analysis_text", None)
    return analysis


def save_report(report: dict[str, Any]) -> Path:
    report_file = PATHS["report"] / f"log_analysis_{RUN_TIME:%Y%m%d_%H%M%S}.json"
    report["report_path"] = str(report_file)
    report_file.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    logging.info("Report saved: %s", report_file)
    return report_file


def main() -> int:
    args = parse_arguments()
    lines_to_read = args.lines if args.lines is not None else int(CONFIG["lines_to_read"])
    if lines_to_read < 1:
        raise ValueError("--lines must be at least 1")
    logging.info("Log analysis started: %s on %s", RUN_ID, OPERATING_SYSTEM)
    all_events: list[dict[str, Any]] = []
    total_counts = {category: 0 for category in CONFIG["event_keywords"]}
    source_results: list[dict[str, str]] = []

    if OPERATING_SYSTEM == "Linux":
        for source in get_log_sources():
            result = read_linux_log(source, lines_to_read)
            source_results.append({key: str(value) for key, value in result.items() if key != "lines"})
            if result["status"] == "READ_SUCCESS":
                analysis = analyse_linux_lines(result["lines"])
                all_events.extend({"source": str(source), **event} for event in analysis["events"])
                for category, count in analysis["event_counts"].items():
                    total_counts[category] += count
    elif OPERATING_SYSTEM == "Windows":
        for source in get_log_sources():
            result = read_windows_log(source, lines_to_read)
            source_results.append({key: str(value) for key, value in result.items() if key != "events"})
            if result["status"] == "READ_SUCCESS":
                analysis = analyse_windows_events(result["events"])
                all_events.extend({"source": str(source), **event} for event in analysis["events"])
                for category, count in analysis["event_counts"].items():
                    total_counts[category] += count
    else:
        raise RuntimeError(f"Unsupported operating system: {OPERATING_SYSTEM}")

    report: dict[str, Any] = {
        "run_id": RUN_ID, "timestamp": RUN_TIME.isoformat(), "hostname": HOSTNAME,
        "operating_system": OPERATING_SYSTEM, "python_version": platform.python_version(),
        "lines_per_source": lines_to_read, "source_results": source_results,
        "total_detected_events": len(all_events), "event_counts": total_counts,
        "detected_events": all_events, "log_file": str(LOG_FILE),
    }
    report_file = save_report(report)
    print(json.dumps({
        "run_id": RUN_ID, "operating_system": OPERATING_SYSTEM, "total_detected_events": len(all_events),
        "event_counts": total_counts, "report": str(report_file), "log": str(LOG_FILE),
    }, indent=2))
    logging.info("Log analysis completed successfully: %s", RUN_ID)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        logging.exception("Log analysis crashed")
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
