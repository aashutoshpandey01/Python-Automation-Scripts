#!/usr/bin/env python3
"""Perform a configurable HTTPS GET request and save a per-run API report."""

from __future__ import annotations

import argparse
import json
import logging
import platform
import ssl
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from socket import gethostname
from typing import Any

try:
    import certifi
except ImportError:
    certifi = None  # type: ignore[assignment]


SCRIPT_NAME = "basic_api_automation"
OPERATING_SYSTEM = platform.system()
HOSTNAME = gethostname()
RUN_TIME = datetime.now(timezone.utc)
RUN_ID = f"API-{RUN_TIME:%Y%m%d-%H%M%S}"


def get_platform_paths() -> dict[str, Path]:
    """Select the approved hierarchy before creating API outputs."""
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
    "api_url": "https://jsonplaceholder.typicode.com/todos/1",
    "timeout_seconds": 10,
    "max_response_bytes": 1_048_576,
    "headers": {"Accept": "application/json", "User-Agent": "AdminAutomation/basic_api_automation"},
}


def load_configuration() -> dict[str, Any]:
    """Create the endpoint configuration once, then retain user changes."""
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
    parser = argparse.ArgumentParser(description="Cross-platform basic API automation")
    parser.add_argument("--url", help="Override the configured API URL for this one request.")
    parser.add_argument(
        "--schedule-info",
        action="store_true",
        help="Create the Windows launcher when applicable and print Task Scheduler/cron examples.",
    )
    return parser.parse_args()


def ssl_context() -> ssl.SSLContext:
    """Use certifi when available, otherwise use the operating system trust store."""
    return ssl.create_default_context(cafile=certifi.where()) if certifi is not None else ssl.create_default_context()


def response_data(body: bytes, content_type: str) -> Any:
    text = body.decode("utf-8", errors="replace")
    if "json" in content_type.lower():
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            logging.warning("Response declared JSON but could not be decoded")
    return text


def request_api(url: str) -> dict[str, Any]:
    """Perform the original HTTPS GET request without invoking shell commands."""
    headers = CONFIG.get("headers", {})
    if not isinstance(headers, dict):
        headers = DEFAULT_CONFIG["headers"]
    request = urllib.request.Request(url, headers={str(key): str(value) for key, value in headers.items()}, method="GET")
    try:
        max_bytes = int(CONFIG["max_response_bytes"])
        timeout_seconds = float(CONFIG["timeout_seconds"])
        if max_bytes < 1 or timeout_seconds <= 0:
            raise ValueError("max_response_bytes and timeout_seconds must be positive")
    except (KeyError, TypeError, ValueError) as error:
        return {"success": False, "status_code": None, "content_type": "", "response_truncated": False, "data": None, "error": f"Invalid API configuration: {error}"}
    try:
        with urllib.request.urlopen(request, context=ssl_context(), timeout=timeout_seconds) as response:
            body = response.read(max_bytes + 1)
            truncated = len(body) > max_bytes
            if truncated:
                body = body[:max_bytes]
            content_type = response.headers.get_content_type()
            return {
                "success": True,
                "status_code": response.status,
                "content_type": content_type,
                "response_truncated": truncated,
                "data": response_data(body, content_type),
                "error": "",
            }
    except urllib.error.HTTPError as error:
        error_body = error.read(max_bytes).decode("utf-8", errors="replace")
        return {
            "success": False,
            "status_code": error.code,
            "content_type": error.headers.get_content_type() if error.headers else "",
            "response_truncated": False,
            "data": error_body,
            "error": f"HTTP {error.code}: {error.reason}",
        }
    except (urllib.error.URLError, TimeoutError, ValueError, ssl.SSLError, OSError) as error:
        return {"success": False, "status_code": None, "content_type": "", "response_truncated": False, "data": None, "error": str(error)}


def create_windows_launcher() -> Path | None:
    """Create the Task Scheduler PowerShell entry point on Windows only."""
    if OPERATING_SYSTEM != "Windows":
        return None
    launcher_directory = PATHS["suite_root"] / "taskscheduler" / SCRIPT_NAME
    launcher_directory.mkdir(parents=True, exist_ok=True)

    launcher_file = launcher_directory / f"{SCRIPT_NAME}.ps1"
    launcher = r'''# Generated by basic_api_automation.py. Performs a GET request.
[CmdletBinding()]
param([string]$Url)

$ErrorActionPreference = 'Stop'
$ScriptPath = Join-Path $PSScriptRoot 'basic_api_automation.py'
$PyLauncher = Get-Command py.exe -ErrorAction SilentlyContinue
$Arguments = @()
if ($PyLauncher) { $PythonCommand = $PyLauncher.Source; $Arguments += '-3' } else { $PythonCommand = 'python.exe' }
$Arguments += $ScriptPath
if ($Url) { $Arguments += @('--url', $Url) }
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
            "note": "The task performs a safe GET request to the configured endpoint and saves the API result report.",
        }
    return {
        "cron_example": f"0 * * * * /usr/bin/python3 {PATHS['script_directory'] / f'{SCRIPT_NAME}.py'} >> {PATHS['log'] / 'cron.log'} 2>&1",
        "note": "The example requests the configured endpoint hourly and writes its report under this automation's reports directory.",
    }


def save_report(url: str, result: dict[str, Any]) -> Path:
    report_file = PATHS["report"] / f"api_report_{RUN_TIME:%Y%m%d_%H%M%S}.json"
    report = {
        "run_id": RUN_ID,
        "timestamp": RUN_TIME.isoformat(),
        "hostname": HOSTNAME,
        "operating_system": OPERATING_SYSTEM,
        "automation": "BASIC_API_AUTOMATION",
        "api_url": url,
        "log_file": str(LOG_FILE),
        "result": result,
    }
    report_file.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    logging.info("API report saved: %s", report_file)
    return report_file


def main() -> int:
    args = parse_arguments()
    launcher_file = create_windows_launcher()
    if args.schedule_info:
        print(json.dumps({"run_id": RUN_ID, "operating_system": OPERATING_SYSTEM, "schedule": get_schedule_information(launcher_file)}, indent=2))
        logging.info("Scheduler information requested for %s", RUN_ID)
        return 0

    url = args.url or str(CONFIG["api_url"])
    logging.info("API automation started: %s; url=%s", RUN_ID, url)
    result = request_api(url)
    report_file = save_report(url, result)
    print(json.dumps({
        "run_id": RUN_ID,
        "hostname": HOSTNAME,
        "operating_system": OPERATING_SYSTEM,
        "api_url": url,
        "success": result["success"],
        "status_code": result["status_code"],
        "report": str(report_file),
        "log": str(LOG_FILE),
        "scheduler": get_schedule_information(launcher_file),
    }, indent=2))
    if result["success"]:
        logging.info("API automation completed successfully: %s", RUN_ID)
        return 0
    logging.error("API automation failed: %s", result["error"])
    return 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        logging.exception("API automation failed unexpectedly")
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
