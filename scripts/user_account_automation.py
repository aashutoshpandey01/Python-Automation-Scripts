#!/usr/bin/env python3
"""Cross-platform local user and group automation for Windows and Ubuntu."""

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


SCRIPT_NAME = "user_account_automation"
OPERATING_SYSTEM = platform.system()
HOSTNAME = platform.node()
RUN_TIME = datetime.now(timezone.utc)
RUN_ID = f"USER-ACCOUNT-{RUN_TIME:%Y%m%d-%H%M%S}"


def get_platform_paths() -> dict[str, Path]:
    """Return the approved hierarchy before selecting account-management commands."""
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
    "groups": [],
    "users": [],
    "linux_create_home_directories": True,
    "command_timeout_seconds": 60,
}


def load_configuration() -> dict[str, Any]:
    """Create an empty, safe account-definition file once and preserve edits."""
    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text(json.dumps(DEFAULT_CONFIG, indent=2), encoding="utf-8")
        return DEFAULT_CONFIG.copy()
    try:
        configured = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        if not isinstance(configured, dict):
            raise ValueError("configuration root must be an object")
        return {**DEFAULT_CONFIG, **configured}
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Configuration error; using empty defaults: {error}", file=sys.stderr)
        return DEFAULT_CONFIG.copy()


CONFIG = load_configuration()
logging.basicConfig(
    filename=LOG_FILE,
    encoding="utf-8",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cross-platform local user and group automation")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Create missing groups/users and add configured memberships. Without this flag, only audit and verify.",
    )
    parser.add_argument(
        "--schedule-info",
        action="store_true",
        help="Create the Windows launcher when applicable and print Task Scheduler/cron examples.",
    )
    return parser.parse_args()


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
        logging.exception("Account command failed to start: %s", executable)
        return {"success": False, "output": "", "error": str(error), "return_code": -1}


def run_powershell(script: str) -> dict[str, Any]:
    executable = shutil.which("powershell.exe") or shutil.which("powershell")
    if executable is None:
        return {"success": False, "output": "", "error": "Windows PowerShell was not found.", "return_code": -1}
    return run_command([executable, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script])


def ubuntu_command(command: list[str]) -> list[str]:
    """Use direct root commands or non-interactive sudo for cron-compatible execution."""
    if os.geteuid() == 0:
        return command
    return ["sudo", "-n", *command]


def powershell_quote(value: str) -> str:
    return value.replace("'", "''")


def configured_groups() -> list[str]:
    groups = CONFIG.get("groups", [])
    if not isinstance(groups, list):
        logging.warning("groups must be a list")
        return []
    return list(dict.fromkeys(item.strip() for item in groups if isinstance(item, str) and item.strip()))


def configured_users() -> list[dict[str, str]]:
    users = CONFIG.get("users", [])
    if not isinstance(users, list):
        logging.warning("users must be a list")
        return []
    valid_users: list[dict[str, str]] = []
    for entry in users:
        if not isinstance(entry, dict) or not isinstance(entry.get("username"), str) or not entry["username"].strip():
            logging.warning("Skipping invalid user definition: %r", entry)
            continue
        user = {"username": entry["username"].strip()}
        if isinstance(entry.get("group"), str) and entry["group"].strip():
            user["group"] = entry["group"].strip()
        valid_users.append(user)
    return valid_users


def group_exists(group: str) -> bool:
    if OPERATING_SYSTEM == "Linux":
        return run_command(["getent", "group", group])["success"]
    result = run_powershell(f"Get-LocalGroup -Name '{powershell_quote(group)}' -ErrorAction SilentlyContinue | Select-Object Name | ConvertTo-Json -Compress")
    return result["success"] and bool(result["output"])


def user_exists(username: str) -> bool:
    if OPERATING_SYSTEM == "Linux":
        return run_command(["id", "-u", username])["success"]
    result = run_powershell(f"Get-LocalUser -Name '{powershell_quote(username)}' -ErrorAction SilentlyContinue | Select-Object Name | ConvertTo-Json -Compress")
    return result["success"] and bool(result["output"])


def create_group(group: str) -> dict[str, Any]:
    if group_exists(group):
        return {"group": group, "status": "ALREADY_EXISTS"}
    if OPERATING_SYSTEM == "Linux":
        result = run_command(ubuntu_command(["groupadd", "--", group]))
    else:
        result = run_powershell(f"New-LocalGroup -Name '{powershell_quote(group)}' -ErrorAction Stop | Out-Null")
    return {"group": group, "status": "CREATED" if result["success"] else "FAILED", "error": result["error"]}


def create_user(user: dict[str, str]) -> dict[str, Any]:
    username = user["username"]
    if user_exists(username):
        return {"username": username, "status": "ALREADY_EXISTS"}
    if OPERATING_SYSTEM == "Linux":
        command = ["useradd"]
        if bool(CONFIG["linux_create_home_directories"]):
            command.append("--create-home")
        command.extend(["--", username])
        result = run_command(ubuntu_command(command))
    else:
        # Preserves the original NoPassword behavior. Secure credentials must be set separately by an administrator.
        result = run_powershell(f"New-LocalUser -Name '{powershell_quote(username)}' -NoPassword -ErrorAction Stop | Out-Null")
    return {"username": username, "status": "CREATED" if result["success"] else "FAILED", "error": result["error"]}


def user_is_group_member(username: str, group: str) -> tuple[bool, str]:
    if OPERATING_SYSTEM == "Linux":
        result = run_command(["id", "-nG", username])
        if not result["success"]:
            return False, result["error"]
        return group in result["output"].split(), ""
    script = f"""
$Member = Get-LocalGroupMember -Group '{powershell_quote(group)}' -ErrorAction Stop |
    Where-Object {{ $_.Name -like '*\\{powershell_quote(username)}' }}
if ($Member) {{ 'MEMBER' }} else {{ 'NOT_MEMBER' }}
"""
    result = run_powershell(script)
    return result["success"] and result["output"].strip() == "MEMBER", result["error"]


def add_user_to_group(user: dict[str, str]) -> dict[str, Any]:
    username = user["username"]
    group = user.get("group")
    if not group:
        return {"username": username, "status": "NO_GROUP_REQUESTED"}
    member, error = user_is_group_member(username, group)
    if member:
        return {"username": username, "group": group, "status": "ALREADY_MEMBER"}
    if OPERATING_SYSTEM == "Linux":
        result = run_command(ubuntu_command(["usermod", "-aG", group, username]))
    else:
        result = run_powershell(
            f"Add-LocalGroupMember -Group '{powershell_quote(group)}' -Member '{powershell_quote(username)}' -ErrorAction Stop"
        )
    return {
        "username": username,
        "group": group,
        "status": "ADDED" if result["success"] else "FAILED",
        "error": result["error"] or error,
    }


def audit_groups(groups: list[str]) -> list[dict[str, Any]]:
    return [{"group": group, "exists": group_exists(group)} for group in groups]


def audit_users(users: list[dict[str, str]]) -> list[dict[str, Any]]:
    audit = []
    for user in users:
        username = user["username"]
        item: dict[str, Any] = {"username": username, "exists": user_exists(username)}
        if user.get("group"):
            member, error = user_is_group_member(username, user["group"])
            item.update(group=user["group"], group_member=member)
            if error:
                item["membership_error"] = error
        audit.append(item)
    return audit


def apply_account_changes(groups: list[str], users: list[dict[str, str]]) -> dict[str, list[dict[str, Any]]]:
    group_results = [create_group(group) for group in groups]
    user_results = [create_user(user) for user in users]
    membership_results = [add_user_to_group(user) for user in users]
    return {"group_creation": group_results, "user_creation": user_results, "membership": membership_results}


def create_windows_launcher() -> Path | None:
    """Create a Task Scheduler launcher beside the deployed Windows Python script."""
    if OPERATING_SYSTEM != "Windows":
        return None
    launcher_directory = PATHS["base_directory"] / "taskscheduler" / SCRIPT_NAME
    launcher_directory.mkdir(parents=True, exist_ok=True)

    launcher_file = launcher_directory / f"{SCRIPT_NAME}.ps1"
    launcher = r'''# Generated by user_account_automation.py. Audits by default.
[CmdletBinding()]
param([switch]$Apply)

$ErrorActionPreference = 'Stop'
$ScriptPath = Join-Path $PSScriptRoot 'user_account_automation.py'
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
        logging.exception("Could not create the Windows launcher: %s", error)
        return None


def get_schedule_information(launcher_file: Path | None) -> dict[str, str]:
    if OPERATING_SYSTEM == "Windows":
        launcher = launcher_file or (PATHS["base_directory"] / "taskscheduler" / SCRIPT_NAME / f"{SCRIPT_NAME}.ps1")
        return {
            "task_scheduler_program": "powershell.exe",
            "task_scheduler_arguments": f'-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "{launcher}"',
            "apply_arguments": f'-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "{launcher}" -Apply',
            "note": "The default task audits accounts only. Apply mode requires an Administrator account and creates configured local accounts.",
        }
    return {
        "cron_audit_example": f"30 2 * * * /usr/bin/python3 {PATHS['script_directory'] / f'{SCRIPT_NAME}.py'} >> {PATHS['log'] / 'cron.log'} 2>&1",
        "cron_apply_example": f"30 2 * * 0 /usr/bin/python3 {PATHS['script_directory'] / f'{SCRIPT_NAME}.py'} --apply >> {PATHS['log'] / 'cron.log'} 2>&1",
        "note": "The default cron example audits only. Apply mode needs root or passwordless sudo for useradd, groupadd, and usermod.",
    }


def save_report(report: dict[str, Any]) -> Path:
    report_file = PATHS["report"] / f"user_account_report_{RUN_TIME:%Y%m%d_%H%M%S}.json"
    report_file.write_text(json.dumps(report, indent=2), encoding="utf-8")
    logging.info("User account report saved: %s", report_file)
    return report_file


def main() -> int:
    args = parse_arguments()
    launcher_file = create_windows_launcher()
    if args.schedule_info:
        print(json.dumps({"run_id": RUN_ID, "operating_system": OPERATING_SYSTEM, "schedule": get_schedule_information(launcher_file)}, indent=2))
        logging.info("Scheduler information requested for %s", RUN_ID)
        return 0

    groups = configured_groups()
    users = configured_users()
    logging.info("User account automation started: %s on %s; apply=%s", RUN_ID, OPERATING_SYSTEM, args.apply)
    changes: dict[str, list[dict[str, Any]]] = {}
    if args.apply:
        changes = apply_account_changes(groups, users)
    verification = {"groups": audit_groups(groups), "users": audit_users(users)}
    report: dict[str, Any] = {
        "run_id": RUN_ID,
        "timestamp": RUN_TIME.isoformat(),
        "hostname": HOSTNAME,
        "operating_system": OPERATING_SYSTEM,
        "automation": "USER_ACCOUNT_AUTOMATION",
        "mode": "APPLY" if args.apply else "AUDIT",
        "groups": groups,
        "users": users,
        "changes": changes,
        "verification": verification,
        "configuration_file": str(CONFIG_FILE),
        "log_file": str(LOG_FILE),
    }
    report_file = save_report(report)
    print(json.dumps({
        "run_id": RUN_ID,
        "hostname": HOSTNAME,
        "operating_system": OPERATING_SYSTEM,
        "mode": report["mode"],
        "groups_configured": len(groups),
        "users_configured": len(users),
        "report": str(report_file),
        "log": str(LOG_FILE),
        "scheduler": get_schedule_information(launcher_file),
    }, indent=2))
    logging.info("User account automation completed: %s", RUN_ID)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        logging.exception("User account automation failed")
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
