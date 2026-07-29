#!/usr/bin/env python3
"""Cross-platform security auditing for Ubuntu Server and Windows Server.

The automation performs read-only security checks, maintains a SHA-256 file
integrity baseline, stores per-run reports, and is safe to run unattended from
cron or Windows Task Scheduler.  It does not block IP addresses, change
firewall rules, or alter system security settings.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import platform
import re
import shutil
import socket
import ssl
import subprocess
import sys
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_NAME = "security_automation"
OPERATING_SYSTEM = platform.system()
HOSTNAME = socket.gethostname()
RUN_TIME = datetime.now(timezone.utc)
RUN_ID = f"SECURITY-{RUN_TIME:%Y%m%d-%H%M%S}"


def get_platform_paths() -> dict[str, Path]:
    """Select only the approved hierarchy for the platform running the script."""
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
        "integrity": suite_root / "integrity" / SCRIPT_NAME,
        "data": suite_root / "data" / SCRIPT_NAME,
    }


PATHS = get_platform_paths()
for path_name in ("script_directory", "log", "report", "integrity", "data"):
    PATHS[path_name].mkdir(parents=True, exist_ok=True)

LOG_FILE = PATHS["log"] / f"{SCRIPT_NAME}_{RUN_TIME:%Y%m%d_%H%M%S}.log"
CONFIG_FILE = PATHS["data"] / f"{SCRIPT_NAME}.json"
BASELINE_FILE = PATHS["integrity"] / "baseline.json"
TEST_FILE = PATHS["data"] / "security_test_file.txt"

DEFAULT_CONFIG: dict[str, Any] = {
    "command_timeout_seconds": 60,
    "failed_login_event_limit": 200,
    "failed_login_risk_threshold": 10,
    "certificate_warning_days": 30,
    "certificate_hosts": [
        {"hostname": "google.com", "port": 443},
        {"hostname": "github.com", "port": 443},
    ],
    "monitored_files": [str(TEST_FILE)],
    "linux_login_log_files": ["/var/log/auth.log", "/var/log/secure"],
}


def load_configuration() -> dict[str, Any]:
    """Create or load the per-automation configuration without overwriting it."""
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
logging.basicConfig(
    filename=LOG_FILE,
    encoding="utf-8",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cross-platform security audit automation")
    parser.add_argument(
        "--refresh-baseline",
        action="store_true",
        help="Replace the file-integrity baseline with the current monitored-file hashes.",
    )
    parser.add_argument(
        "--schedule-info",
        action="store_true",
        help="Create the Windows launcher when applicable and print Task Scheduler/cron examples.",
    )
    return parser.parse_args()


def run_command(command: list[str]) -> dict[str, Any]:
    """Run one OS-specific read-only command and capture a reportable result."""
    executable = command[0]
    if shutil.which(executable) is None:
        message = f"Required executable was not found: {executable}"
        logging.warning(message)
        return {"success": False, "command": executable, "output": "", "error": message, "return_code": -1}
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
            "command": " ".join(command[:3]) + (" ..." if len(command) > 3 else ""),
            "output": result.stdout.strip(),
            "error": result.stderr.strip(),
            "return_code": result.returncode,
        }
    except subprocess.TimeoutExpired:
        message = f"Command timed out after {CONFIG['command_timeout_seconds']} seconds"
        logging.warning("%s: %s", message, executable)
        return {"success": False, "command": executable, "output": "", "error": message, "return_code": -1}
    except OSError as error:
        logging.exception("Command execution failed: %s", executable)
        return {"success": False, "command": executable, "output": "", "error": str(error), "return_code": -1}


def run_powershell(script: str) -> dict[str, Any]:
    """Run a PowerShell audit only after the Windows platform branch selected it."""
    executable = shutil.which("powershell.exe") or shutil.which("powershell")
    if executable is None:
        return {
            "success": False,
            "command": "powershell.exe",
            "output": "",
            "error": "Windows PowerShell was not found.",
            "return_code": -1,
        }
    return run_command([executable, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script])


def json_output(result: dict[str, Any]) -> Any:
    """Decode PowerShell JSON while preserving command failures in the report."""
    if not result["success"] or not result["output"]:
        return []
    try:
        return json.loads(result["output"])
    except json.JSONDecodeError:
        logging.warning("PowerShell returned non-JSON output: %s", result["output"][:500])
        return result["output"].splitlines()


def create_test_file() -> Path:
    """Keep the original test-file baseline behavior inside the automation data area."""
    if not TEST_FILE.exists():
        TEST_FILE.write_text("Security automation baseline\n", encoding="utf-8")
    return TEST_FILE


def calculate_file_hash(file_path: Path) -> str | None:
    digest = hashlib.sha256()
    try:
        with file_path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()
    except OSError as error:
        logging.warning("Could not hash %s: %s", file_path, error)
        return None


def monitored_files() -> list[Path]:
    configured = CONFIG.get("monitored_files", [])
    if not isinstance(configured, list):
        logging.warning("monitored_files must be a list; using the default test file")
        return [TEST_FILE]
    return [Path(item) for item in configured if isinstance(item, str) and item.strip()]


def file_integrity_check(refresh_baseline: bool) -> list[dict[str, Any]]:
    """Compare monitored files with their saved SHA-256 hashes."""
    current_hashes: dict[str, str] = {}
    results: list[dict[str, Any]] = []

    for file_path in monitored_files():
        if not file_path.exists():
            results.append({"file": str(file_path), "status": "NOT_FOUND"})
            continue
        file_hash = calculate_file_hash(file_path)
        if file_hash is None:
            results.append({"file": str(file_path), "status": "HASH_FAILED"})
            continue
        current_hashes[str(file_path)] = file_hash

    old_hashes: dict[str, str] = {}
    baseline_created = not BASELINE_FILE.exists()
    if not baseline_created and not refresh_baseline:
        try:
            loaded = json.loads(BASELINE_FILE.read_text(encoding="utf-8"))
            if not isinstance(loaded, dict):
                raise ValueError("baseline root must be an object")
            old_hashes = {str(key): str(value) for key, value in loaded.items()}
        except (OSError, ValueError, json.JSONDecodeError) as error:
            logging.error("Integrity baseline could not be loaded: %s", error)
            return results + [{"file": str(BASELINE_FILE), "status": "BASELINE_READ_FAILED", "error": str(error)}]

    if baseline_created or refresh_baseline:
        BASELINE_FILE.write_text(json.dumps(current_hashes, indent=2), encoding="utf-8")
        status = "BASELINE_CREATED" if baseline_created else "BASELINE_REFRESHED"
        results.extend({"file": file_name, "status": status, "hash": file_hash} for file_name, file_hash in current_hashes.items())
        return results

    for file_name, file_hash in current_hashes.items():
        status = "NO_CHANGE" if old_hashes.get(file_name) == file_hash else "WARNING_FILE_CHANGED"
        if status == "WARNING_FILE_CHANGED":
            logging.warning("Integrity change detected: %s", file_name)
        results.append({"file": file_name, "status": status, "hash": file_hash})
    return results


def failed_login_detection() -> dict[str, Any]:
    limit = int(CONFIG["failed_login_event_limit"])
    pattern = re.compile(r"failed|invalid user|authentication failure", re.IGNORECASE)
    if OPERATING_SYSTEM == "Linux":
        if shutil.which("journalctl"):
            result = run_command(["journalctl", "-n", str(limit), "--no-pager"])
            lines = result["output"].splitlines()
            source = "journalctl"
        else:
            lines = []
            source = "log files"
            for log_file in CONFIG.get("linux_login_log_files", []):
                path = Path(log_file)
                if not path.exists():
                    continue
                try:
                    with path.open("r", encoding="utf-8", errors="ignore") as handle:
                        lines.extend(deque(handle, maxlen=limit))
                except OSError as error:
                    logging.warning("Could not read login log %s: %s", path, error)
            result = {"success": bool(lines), "error": "No readable login log was found" if not lines else ""}
        events = [line.strip() for line in lines if pattern.search(line)]
        return {
            "status": "COMPLETED" if result["success"] else "FAILED",
            "source": source,
            "failed_events": len(events),
            "events": events,
            "error": result.get("error", ""),
        }

    if OPERATING_SYSTEM == "Windows":
        result = run_powershell(f"""
$Events = @(Get-WinEvent -FilterHashtable @{{LogName='Security'; Id=4625}} -MaxEvents {limit} |
    ForEach-Object {{ [PSCustomObject]@{{ TimeCreated=$_.TimeCreated; Message=$_.Message }} }})
$Events | ConvertTo-Json -Compress
""")
        events = json_output(result)
        if isinstance(events, dict):
            events = [events]
        return {
            "status": "COMPLETED" if result["success"] else "FAILED",
            "source": "Windows Security event log (4625)",
            "failed_events": len(events) if isinstance(events, list) else 0,
            "events": events,
            "error": result["error"],
        }

    return {"status": "UNSUPPORTED", "failed_events": 0, "events": []}


def firewall_audit() -> dict[str, Any]:
    if OPERATING_SYSTEM == "Linux":
        if not shutil.which("ufw"):
            return {"status": "NOT_INSTALLED", "firewall": "", "active": None, "error": "ufw was not found"}
        result = run_command(["ufw", "status", "verbose"])
        firewall_output = result["output"]
        active = "status: active" in firewall_output.lower()
        return {
            "status": "COMPLETED" if result["success"] else "FAILED",
            "firewall": firewall_output,
            "active": active if result["success"] else None,
            "error": result["error"],
        }

    if OPERATING_SYSTEM == "Windows":
        result = run_powershell("Get-NetFirewallProfile | Select-Object Name,Enabled | ConvertTo-Json -Compress")
        profiles = json_output(result)
        if isinstance(profiles, dict):
            profiles = [profiles]
        active = all(bool(profile.get("Enabled")) for profile in profiles) if isinstance(profiles, list) and profiles else None
        return {
            "status": "COMPLETED" if result["success"] else "FAILED",
            "firewall": profiles,
            "active": active,
            "error": result["error"],
        }

    return {"status": "UNSUPPORTED", "firewall": "", "active": None}


def ssh_security_audit() -> dict[str, Any]:
    if OPERATING_SYSTEM != "Linux":
        return {"status": "NOT_SUPPORTED"}

    ssh_config = Path("/etc/ssh/sshd_config")
    if not ssh_config.exists():
        return {"status": "SSH_CONFIG_NOT_FOUND"}
    try:
        lines = ssh_config.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError as error:
        return {"status": "SSH_CONFIG_READ_FAILED", "error": str(error)}

    checks = ["PermitRootLogin", "PasswordAuthentication", "PermitEmptyPasswords"]
    findings = []
    for check in checks:
        values = [line.strip() for line in lines if line.strip() and not line.lstrip().startswith("#") and line.lstrip().startswith(check)]
        findings.append({"setting": check, "value": values})
    return {"status": "COMPLETED", "ssh_security": findings}


def open_port_audit() -> dict[str, Any]:
    if OPERATING_SYSTEM == "Linux":
        result = run_command(["ss", "-tulnp"])
        ports: Any = result["output"].splitlines()
    elif OPERATING_SYSTEM == "Windows":
        result = run_powershell("Get-NetTCPConnection -State Listen | Select-Object LocalAddress,LocalPort,State,OwningProcess | ConvertTo-Json -Compress")
        ports = json_output(result)
    else:
        return {"status": "UNSUPPORTED", "open_ports": []}
    return {"status": "COMPLETED" if result["success"] else "FAILED", "open_ports": ports, "error": result["error"]}


def process_security_audit() -> dict[str, Any]:
    if OPERATING_SYSTEM == "Linux":
        result = run_command(["ps", "aux"])
        processes: Any = result["output"].splitlines()
    elif OPERATING_SYSTEM == "Windows":
        result = run_powershell("Get-Process | Select-Object ProcessName,Id,CPU | ConvertTo-Json -Compress")
        processes = json_output(result)
    else:
        return {"status": "UNSUPPORTED", "processes": []}
    return {"status": "COMPLETED" if result["success"] else "FAILED", "processes": processes, "error": result["error"]}


def user_access_audit() -> dict[str, Any]:
    if OPERATING_SYSTEM == "Linux":
        result = run_command(["getent", "passwd"])
        users = []
        for line in result["output"].splitlines():
            fields = line.split(":")
            if len(fields) >= 7:
                users.append({"username": fields[0], "home": fields[5], "shell": fields[6]})
    elif OPERATING_SYSTEM == "Windows":
        result = run_powershell("Get-LocalUser | Select-Object Name,Enabled,LastLogon | ConvertTo-Json -Compress")
        users = json_output(result)
    else:
        return {"status": "UNSUPPORTED", "users": []}
    return {"status": "COMPLETED" if result["success"] else "FAILED", "users": users, "error": result["error"]}


def permission_audit() -> dict[str, Any]:
    if OPERATING_SYSTEM != "Linux":
        return {"status": "NOT_SUPPORTED"}
    result = run_command(["find", "/etc", "-type", "f", "-perm", "-o+w"])
    return {
        "status": "COMPLETED" if result["success"] else "FAILED",
        "world_writable_files": result["output"].splitlines(),
        "error": result["error"],
    }


def certificate_expiry_check(hostname: str, port: int) -> dict[str, Any]:
    try:
        context = ssl.create_default_context()
        with socket.create_connection((hostname, port), timeout=10) as connection:
            with context.wrap_socket(connection, server_hostname=hostname) as secure_socket:
                certificate = secure_socket.getpeercert()
        expiry_date = datetime.strptime(certificate["notAfter"], "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
        days_remaining = (expiry_date - datetime.now(timezone.utc)).days
        status = "WARNING_EXPIRING_SOON" if days_remaining <= int(CONFIG["certificate_warning_days"]) else "CERTIFICATE_VALID"
        return {
            "hostname": hostname,
            "port": port,
            "expiry_date": expiry_date.isoformat(),
            "days_remaining": days_remaining,
            "status": status,
        }
    except (OSError, ssl.SSLError, KeyError, ValueError) as error:
        logging.warning("Certificate check failed for %s:%s: %s", hostname, port, error)
        return {"hostname": hostname, "port": port, "status": "CERTIFICATE_CHECK_FAILED", "error": str(error)}


def certificate_checks() -> list[dict[str, Any]]:
    results = []
    for target in CONFIG.get("certificate_hosts", []):
        if not isinstance(target, dict):
            continue
        hostname = target.get("hostname")
        port = target.get("port", 443)
        if isinstance(hostname, str) and hostname and isinstance(port, int):
            results.append(certificate_expiry_check(hostname, port))
    return results


def suspicious_ip_analysis(failed_login_data: dict[str, Any]) -> dict[str, Any]:
    events = failed_login_data.get("events", [])
    if isinstance(events, str):
        events = events.splitlines()
    event_text = "\n".join(json.dumps(event, default=str) if isinstance(event, dict) else str(event) for event in events)
    suspicious_ips = sorted(set(re.findall(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", event_text)))
    return {
        "status": "COMPLETED",
        "suspicious_ips": suspicious_ips,
        "recommendation": "Review and manually block suspicious IPs.",
    }


def security_summary(
    failed_logins: dict[str, Any], integrity_results: list[dict[str, Any]], certificates: list[dict[str, Any]], firewall: dict[str, Any]
) -> dict[str, Any]:
    risk = "LOW"
    if failed_logins.get("failed_events", 0) > int(CONFIG["failed_login_risk_threshold"]):
        risk = "MEDIUM"
    if any(item.get("status") == "WARNING_FILE_CHANGED" for item in integrity_results):
        risk = "HIGH"
    if risk == "LOW" and any(item.get("status") == "WARNING_EXPIRING_SOON" for item in certificates):
        risk = "MEDIUM"
    if firewall.get("active") is False:
        risk = "HIGH"
    return {"security_risk": risk}


def system_security_information() -> dict[str, str]:
    return {
        "hostname": HOSTNAME,
        "operating_system": OPERATING_SYSTEM,
        "platform": platform.platform(),
        "kernel": platform.release(),
        "architecture": platform.machine(),
        "python_version": sys.version.split()[0],
    }


def create_windows_launcher() -> Path | None:
    """Write the Task Scheduler entry point beside the deployed Windows script."""
    if OPERATING_SYSTEM != "Windows":
        return None
    launcher_directory = PATHS["suite_root"] / "taskscheduler" / SCRIPT_NAME
    launcher_directory.mkdir(parents=True, exist_ok=True)

    launcher_file = launcher_directory / f"{SCRIPT_NAME}.ps1"
    launcher = r'''# Generated by security_automation.py. Performs read-only security checks.
[CmdletBinding()]
param([switch]$RefreshBaseline)

$ErrorActionPreference = 'Stop'
$ScriptPath = Join-Path $PSScriptRoot 'security_automation.py'
$PyLauncher = Get-Command py.exe -ErrorAction SilentlyContinue

if ($PyLauncher) {
    $Arguments = @('-3', $ScriptPath)
    if ($RefreshBaseline) { $Arguments += '--refresh-baseline' }
    & $PyLauncher.Source @Arguments
} else {
    $Arguments = @($ScriptPath)
    if ($RefreshBaseline) { $Arguments += '--refresh-baseline' }
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
        launcher = launcher_file or (PATHS["suite_root"] / "taskscheduler" / SCRIPT_NAME / f"{SCRIPT_NAME}.ps1")
        return {
            "task_scheduler_program": "powershell.exe",
            "task_scheduler_arguments": f'-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "{launcher}"',
            "note": "Use an account permitted to read the Security event log and firewall settings.",
        }
    return {
        "cron_example": f"15 2 * * * /usr/bin/python3 {PATHS['script_directory'] / f'{SCRIPT_NAME}.py'} >> {PATHS['log'] / 'cron.log'} 2>&1",
        "note": "Run with an account that can read the security logs you want to audit. The automation is read-only.",
    }


def save_report(report: dict[str, Any]) -> Path:
    report_file = PATHS["report"] / f"security_report_{RUN_TIME:%Y%m%d_%H%M%S}.json"
    report_file.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    logging.info("Security report saved: %s", report_file)
    return report_file


def main() -> int:
    args = parse_arguments()
    launcher_file = create_windows_launcher()
    if args.schedule_info:
        print(json.dumps({"run_id": RUN_ID, "operating_system": OPERATING_SYSTEM, "schedule": get_schedule_information(launcher_file)}, indent=2))
        logging.info("Scheduler information requested for %s", RUN_ID)
        return 0

    logging.info("Security automation started: %s on %s", RUN_ID, OPERATING_SYSTEM)
    create_test_file()
    failed_logins = failed_login_detection()
    firewall = firewall_audit()
    ssh_security = ssh_security_audit()
    ports = open_port_audit()
    processes = process_security_audit()
    integrity = file_integrity_check(args.refresh_baseline)
    users = user_access_audit()
    permissions = permission_audit()
    certificates = certificate_checks()
    suspicious_ips = suspicious_ip_analysis(failed_logins)
    risk = security_summary(failed_logins, integrity, certificates, firewall)

    report: dict[str, Any] = {
        "run_id": RUN_ID,
        "timestamp": RUN_TIME.isoformat(),
        "automation": "SECURITY_AUTOMATION",
        "system_information": system_security_information(),
        "security_summary": risk,
        "failed_login_detection": failed_logins,
        "firewall_audit": firewall,
        "ssh_security_audit": ssh_security,
        "open_port_audit": ports,
        "process_security_audit": processes,
        "file_integrity_monitor": integrity,
        "user_access_audit": users,
        "permission_audit": permissions,
        "certificate_monitor": certificates,
        "suspicious_ip_analysis": suspicious_ips,
        "log_file": str(LOG_FILE),
    }
    report_file = save_report(report)
    output = {
        "run_id": RUN_ID,
        "operating_system": OPERATING_SYSTEM,
        "security_risk": risk["security_risk"],
        "failed_login_events": failed_logins.get("failed_events", 0),
        "integrity_warnings": sum(item.get("status") == "WARNING_FILE_CHANGED" for item in integrity),
        "report": str(report_file),
        "log": str(LOG_FILE),
        "scheduler": get_schedule_information(launcher_file),
    }
    print(json.dumps(output, indent=2))
    logging.info("Security automation completed: %s; risk=%s", RUN_ID, risk["security_risk"])
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        logging.exception("Security automation failed")
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
