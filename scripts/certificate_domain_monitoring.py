#!/usr/bin/env python3
"""Monitor TLS certificates, DNS, HTTPS availability, and optional email alerts."""

from __future__ import annotations

import argparse
import json
import logging
import os
import platform
import smtplib
import socket
import ssl
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Any

try:
    import certifi
except ImportError:
    certifi = None  # type: ignore[assignment]


SCRIPT_NAME = "certificate_domain_monitoring"
OPERATING_SYSTEM = platform.system()
HOSTNAME = socket.gethostname()
RUN_TIME = datetime.now(timezone.utc)
RUN_ID = f"CERTIFICATE-{RUN_TIME:%Y%m%d-%H%M%S}"


def get_platform_paths() -> dict[str, Path]:
    """Select the approved hierarchy before creating monitor files."""
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
    "domains": ["google.com", "github.com"],
    "certificate_port": 443,
    "certificate_warning_days": 30,
    "network_timeout_seconds": 10,
    "https_host_overrides": {"google.com": "www.google.com"},
    "email": {
        "enabled": False,
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "sender": "",
        "receiver": "",
        "password_environment_variable": "CERTIFICATE_MONITOR_SMTP_PASSWORD",
    },
}


def load_configuration() -> dict[str, Any]:
    """Create the editable monitor configuration once and retain its changes."""
    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text(json.dumps(DEFAULT_CONFIG, indent=2), encoding="utf-8")
        return DEFAULT_CONFIG.copy()
    try:
        loaded = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise ValueError("configuration root must be an object")
        merged = {**DEFAULT_CONFIG, **loaded}
        if isinstance(loaded.get("email"), dict):
            merged["email"] = {**DEFAULT_CONFIG["email"], **loaded["email"]}
        return merged
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
    parser = argparse.ArgumentParser(description="Cross-platform certificate and domain monitoring")
    parser.add_argument("--no-email", action="store_true", help="Suppress optional configured email alerts for this run.")
    parser.add_argument(
        "--schedule-info",
        action="store_true",
        help="Create the Windows launcher when applicable and print Task Scheduler/cron examples.",
    )
    return parser.parse_args()


def ssl_context() -> ssl.SSLContext:
    return ssl.create_default_context(cafile=certifi.where()) if certifi is not None else ssl.create_default_context()


def monitor_domains() -> list[str]:
    configured = CONFIG.get("domains", [])
    if not isinstance(configured, list):
        logging.warning("domains must be a list")
        return []
    return list(dict.fromkeys(item.strip() for item in configured if isinstance(item, str) and item.strip()))


def network_timeout() -> float:
    try:
        timeout = float(CONFIG["network_timeout_seconds"])
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        return timeout
    except (KeyError, TypeError, ValueError) as error:
        logging.warning("Invalid network timeout; using 10 seconds: %s", error)
        return 10.0


def certificate_warning_days() -> int:
    try:
        days = int(CONFIG["certificate_warning_days"])
        if days < 0:
            raise ValueError("warning days cannot be negative")
        return days
    except (KeyError, TypeError, ValueError) as error:
        logging.warning("Invalid certificate warning period; using 30 days: %s", error)
        return 30


def certificate_port() -> int:
    try:
        port = int(CONFIG["certificate_port"])
        if not 1 <= port <= 65535:
            raise ValueError("port must be between 1 and 65535")
        return port
    except (KeyError, TypeError, ValueError) as error:
        logging.warning("Invalid certificate port; using 443: %s", error)
        return 443


def check_ssl_certificate(domain: str) -> dict[str, Any]:
    port = certificate_port()
    try:
        with socket.create_connection((domain, port), timeout=network_timeout()) as connection:
            with ssl_context().wrap_socket(connection, server_hostname=domain) as secure_socket:
                certificate = secure_socket.getpeercert()
        expiry_date = datetime.strptime(certificate["notAfter"], "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
        days_remaining = (expiry_date - datetime.now(timezone.utc)).days
        if days_remaining <= 0:
            status = "CRITICAL: Certificate expired"
        elif days_remaining <= certificate_warning_days():
            status = "WARNING: Certificate expires soon"
        else:
            status = "OK: Certificate valid"
        return {
            "domain": domain,
            "port": port,
            "expiry_date": expiry_date.isoformat(),
            "days_remaining": days_remaining,
            "status": status,
        }
    except (OSError, ssl.SSLError, KeyError, ValueError) as error:
        logging.warning("Certificate check failed for %s:%s: %s", domain, port, error)
        return {"domain": domain, "port": port, "status": "ERROR: Certificate check failed", "error": str(error)}


def check_dns_records(domain: str) -> dict[str, Any]:
    results: dict[str, Any] = {}
    try:
        results["A"] = socket.gethostbyname_ex(domain)[2]
    except socket.gaierror as error:
        results["A"] = []
        results["a_record_error"] = str(error)
    try:
        results["canonical_name"] = socket.getfqdn(domain)
    except OSError as error:
        results["canonical_name"] = ""
        results["canonical_name_error"] = str(error)
    return results


def https_host(domain: str) -> str:
    overrides = CONFIG.get("https_host_overrides", {})
    if isinstance(overrides, dict) and isinstance(overrides.get(domain), str) and overrides[domain].strip():
        return overrides[domain].strip()
    return domain


def check_https_availability(domain: str) -> dict[str, Any]:
    host = https_host(domain)
    url = f"https://{host}"
    request = urllib.request.Request(url, method="GET", headers={"User-Agent": "AdminAutomation/certificate_domain_monitoring"})
    try:
        with urllib.request.urlopen(request, timeout=network_timeout(), context=ssl_context()) as response:
            return {"domain": domain, "url": url, "status_code": response.status, "https_available": True, "status": "OK"}
    except urllib.error.HTTPError as error:
        # The TLS connection succeeded even when the web application returned an HTTP error.
        return {
            "domain": domain,
            "url": url,
            "status_code": error.code,
            "https_available": True,
            "status": "HTTPS available but server returned HTTP error",
        }
    except (urllib.error.URLError, TimeoutError, ValueError, ssl.SSLError, OSError) as error:
        logging.warning("HTTPS availability check failed for %s: %s", domain, error)
        return {"domain": domain, "url": url, "https_available": False, "status": "ERROR: HTTPS unavailable", "error": str(error)}


def check_domain_expiry(domain: str) -> dict[str, str]:
    """Preserve the original explicit placeholder for WHOIS/registrar integration."""
    return {
        "domain": domain,
        "status": "Domain expiry lookup requires WHOIS/API integration",
        "action": "Use a WHOIS or domain registrar API.",
    }


def email_settings() -> dict[str, Any]:
    configured = CONFIG.get("email", {})
    return configured if isinstance(configured, dict) else {}


def send_email_alert(alerts: list[str], suppressed: bool) -> dict[str, Any]:
    settings = email_settings()
    if suppressed:
        return {"status": "SUPPRESSED"}
    if not settings.get("enabled", False):
        return {"status": "DISABLED"}
    if not alerts:
        return {"status": "NO_ALERTS"}

    sender = str(settings.get("sender", "")).strip()
    receiver = str(settings.get("receiver", "")).strip()
    password_variable = str(settings.get("password_environment_variable", "")).strip()
    password = os.environ.get(password_variable, "") if password_variable else ""
    if not sender or not receiver or not password:
        return {"status": "NOT_CONFIGURED", "error": "Email sender, receiver, or password environment variable is missing."}

    message = EmailMessage()
    message["Subject"] = "Certificate and Domain Monitoring Alert"
    message["From"] = sender
    message["To"] = receiver
    message.set_content("\n".join(alerts))
    try:
        with smtplib.SMTP(str(settings.get("smtp_server", "")), int(settings.get("smtp_port", 587)), timeout=network_timeout()) as server:
            server.starttls(context=ssl_context())
            server.login(sender, password)
            server.send_message(message)
        logging.info("Certificate monitor email alert sent")
        return {"status": "SENT"}
    except (OSError, smtplib.SMTPException, ValueError) as error:
        logging.error("Certificate monitor email alert failed: %s", error)
        return {"status": "FAILED", "error": str(error)}


def collect_alerts(certificates: list[dict[str, Any]], https_results: list[dict[str, Any]]) -> list[str]:
    alerts = []
    for certificate in certificates:
        domain = certificate["domain"]
        if "days_remaining" in certificate and certificate["days_remaining"] <= certificate_warning_days():
            alerts.append(f"WARNING: {domain} SSL certificate expires in {certificate['days_remaining']} days.")
        elif certificate["status"].startswith("ERROR"):
            alerts.append(f"WARNING: SSL certificate check failed for {domain}: {certificate.get('error', 'unknown error')}")
    for https in https_results:
        if not https.get("https_available", False):
            alerts.append(f"WARNING: HTTPS unavailable for {https['domain']}.")
    return alerts


def create_windows_launcher() -> Path | None:
    """Create the Task Scheduler PowerShell entry point on Windows only."""
    if OPERATING_SYSTEM != "Windows":
        return None
    launcher_file = PATHS["script_directory"] / f"{SCRIPT_NAME}.ps1"
    launcher = r'''# Generated by certificate_domain_monitoring.py.
[CmdletBinding()]
param([switch]$NoEmail)

$ErrorActionPreference = 'Stop'
$ScriptPath = Join-Path $PSScriptRoot 'certificate_domain_monitoring.py'
$PyLauncher = Get-Command py.exe -ErrorAction SilentlyContinue
$Arguments = @()
if ($PyLauncher) { $PythonCommand = $PyLauncher.Source; $Arguments += '-3' } else { $PythonCommand = 'python.exe' }
$Arguments += $ScriptPath
if ($NoEmail) { $Arguments += '--no-email' }
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
        launcher = launcher_file or PATHS["script_directory"] / f"{SCRIPT_NAME}.ps1"
        return {
            "task_scheduler_program": "powershell.exe",
            "task_scheduler_arguments": f'-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "{launcher}"',
            "no_email_arguments": f'-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "{launcher}" -NoEmail',
            "note": "Email is sent only when enabled in configuration and its password environment variable is available to the task account.",
        }
    return {
        "cron_example": f"0 7 * * * /usr/bin/python3 {PATHS['script_directory'] / f'{SCRIPT_NAME}.py'} >> {PATHS['log'] / 'cron.log'} 2>&1",
        "no_email_cron_example": f"0 7 * * * /usr/bin/python3 {PATHS['script_directory'] / f'{SCRIPT_NAME}.py'} --no-email >> {PATHS['log'] / 'cron.log'} 2>&1",
        "note": "The default cron example sends configured alerts; use --no-email for report-only monitoring.",
    }


def save_report(report: dict[str, Any]) -> Path:
    report_file = PATHS["report"] / f"monitoring_report_{RUN_TIME:%Y%m%d_%H%M%S}.json"
    report_file.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    logging.info("Certificate and domain report saved: %s", report_file)
    return report_file


def main() -> int:
    args = parse_arguments()
    launcher_file = create_windows_launcher()
    if args.schedule_info:
        print(json.dumps({"run_id": RUN_ID, "operating_system": OPERATING_SYSTEM, "schedule": get_schedule_information(launcher_file)}, indent=2))
        logging.info("Scheduler information requested for %s", RUN_ID)
        return 0

    domains = monitor_domains()
    logging.info("Certificate and domain monitoring started: %s; domains=%s", RUN_ID, domains)
    certificates = [check_ssl_certificate(domain) for domain in domains]
    dns_checks = [{"domain": domain, "records": check_dns_records(domain)} for domain in domains]
    https_checks = [check_https_availability(domain) for domain in domains]
    domain_expiry_checks = [check_domain_expiry(domain) for domain in domains]
    alerts = collect_alerts(certificates, https_checks)
    email_result = send_email_alert(alerts, args.no_email)
    report: dict[str, Any] = {
        "run_id": RUN_ID,
        "timestamp": RUN_TIME.isoformat(),
        "hostname": HOSTNAME,
        "operating_system": OPERATING_SYSTEM,
        "automation": "CERTIFICATE_DOMAIN_MONITORING",
        "certificate_checks": certificates,
        "dns_checks": dns_checks,
        "https_checks": https_checks,
        "domain_expiry_checks": domain_expiry_checks,
        "alerts": alerts,
        "email": email_result,
        "log_file": str(LOG_FILE),
    }
    report_file = save_report(report)
    print(json.dumps({
        "run_id": RUN_ID,
        "hostname": HOSTNAME,
        "operating_system": OPERATING_SYSTEM,
        "domains_checked": len(domains),
        "alerts": len(alerts),
        "email_status": email_result["status"],
        "report": str(report_file),
        "log": str(LOG_FILE),
        "scheduler": get_schedule_information(launcher_file),
    }, indent=2))
    logging.info("Certificate and domain monitoring completed: %s; alerts=%s", RUN_ID, len(alerts))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        logging.exception("Certificate and domain monitoring failed")
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
