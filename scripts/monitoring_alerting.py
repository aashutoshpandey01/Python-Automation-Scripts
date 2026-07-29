#!/usr/bin/env python3
"""Monitor CPU, memory, and disk use and send configured threshold alerts."""

from __future__ import annotations

import argparse
import json
import logging
import os
from dotenv import load_dotenv
import platform
import smtplib
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Any


if platform.system() == "Windows":
    load_dotenv("../config/windows-server.env")
else:
    load_dotenv("../config/ubuntu-server.env")


SCRIPT_NAME = "monitoring_alerting"
OPERATING_SYSTEM = platform.system()
HOSTNAME = platform.node()
RUN_TIME = datetime.now(timezone.utc)
RUN_ID = f"MONITOR-{RUN_TIME:%Y%m%d-%H%M%S}"


def get_platform_paths() -> dict[str, Path]:
    """Select the allowed hierarchy before choosing an OS-specific disk path."""
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
    "cpu_warning_threshold": 80,
    "memory_warning_threshold": 80,
    "disk_warning_threshold": 80,
    "windows_disk_path": "C:\\",
    "linux_disk_path": "/",
    "email": {
        "enabled": True,
        "recipient": os.getenv("ALERT_RECEIVER", ""),
        "sender": os.getenv("SMTP_EMAIL", ""),
        "smtp_server": os.getenv("SMTP_SERVER", "smtp.gmail.com"),
        "smtp_port": int(os.getenv("SMTP_PORT", "587")),
        "password_environment_variable": "MONITORING_SMTP_PASSWORD",
    },
    "microsoft_teams": {"enabled": False, "webhook_url": ""},
    "slack": {"enabled": False, "webhook_url": ""},
    "generic_webhook": {"enabled": False, "webhook_url": ""},
    "ticketing": {
        "enabled": False,
        "api_url": "",
        "token_environment_variable": "MONITORING_TICKETING_API_TOKEN",
    },
}


def load_configuration() -> dict[str, Any]:
    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text(json.dumps(DEFAULT_CONFIG, indent=2), encoding="utf-8")
        return json.loads(json.dumps(DEFAULT_CONFIG))
    try:
        configured = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        merged = {**DEFAULT_CONFIG, **configured}
        for section in ("email", "microsoft_teams", "slack", "generic_webhook", "ticketing"):
            merged[section] = {**DEFAULT_CONFIG[section], **configured.get(section, {})}
        return merged
    except (OSError, json.JSONDecodeError) as error:
        print(f"Configuration error; using defaults: {error}", file=sys.stderr)
        return json.loads(json.dumps(DEFAULT_CONFIG))


CONFIG = load_configuration()
logging.basicConfig(
    filename=LOG_FILE,
    encoding="utf-8",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Enterprise Monitoring and Alerting")
    parser.add_argument("--no-notify", action="store_true", help="Collect metrics and write a report without sending alerts.")
    return parser.parse_args()


def system_information() -> dict[str, str]:
    return {
        "hostname": HOSTNAME,
        "operating_system": OPERATING_SYSTEM,
        "platform": platform.platform(),
        "python_version": platform.python_version(),
    }


def get_psutil() -> Any | None:
    try:
        import psutil
        return psutil
    except ImportError:
        logging.error("psutil is not installed; monitoring checks cannot run")
        return None


def metric_failure(metric: str, message: str) -> dict[str, Any]:
    return {"metric": metric, "status": "FAILED", "error": message}


def check_cpu(psutil_module: Any | None) -> dict[str, Any]:
    if psutil_module is None:
        return metric_failure("cpu", "psutil missing")
    try:
        usage = psutil_module.cpu_percent(interval=1)
        threshold = float(CONFIG["cpu_warning_threshold"])
        return {"usage_percent": usage, "threshold": threshold, "status": "WARNING" if usage >= threshold else "OK"}
    except Exception as error:
        logging.exception("CPU check failed")
        return metric_failure("cpu", str(error))


def check_memory(psutil_module: Any | None) -> dict[str, Any]:
    if psutil_module is None:
        return metric_failure("memory", "psutil missing")
    try:
        memory = psutil_module.virtual_memory()
        threshold = float(CONFIG["memory_warning_threshold"])
        return {
            "usage_percent": memory.percent, "threshold": threshold,
            "total_gb": round(memory.total / 1024**3, 2), "used_gb": round(memory.used / 1024**3, 2),
            "available_gb": round(memory.available / 1024**3, 2),
            "status": "WARNING" if memory.percent >= threshold else "OK",
        }
    except Exception as error:
        logging.exception("Memory check failed")
        return metric_failure("memory", str(error))


def check_disk(psutil_module: Any | None) -> dict[str, Any]:
    if psutil_module is None:
        return metric_failure("disk", "psutil missing")
    if OPERATING_SYSTEM == "Windows":
        disk_path = CONFIG["windows_disk_path"]
    elif OPERATING_SYSTEM == "Linux":
        disk_path = CONFIG["linux_disk_path"]
    else:
        return metric_failure("disk", f"Unsupported operating system: {OPERATING_SYSTEM}")
    try:
        disk = psutil_module.disk_usage(disk_path)
        threshold = float(CONFIG["disk_warning_threshold"])
        return {
            "path": disk_path, "usage_percent": disk.percent, "threshold": threshold,
            "total_gb": round(disk.total / 1024**3, 2), "used_gb": round(disk.used / 1024**3, 2),
            "free_gb": round(disk.free / 1024**3, 2),
            "status": "WARNING" if disk.percent >= threshold else "OK",
        }
    except Exception as error:
        logging.exception("Disk check failed for %s", disk_path)
        return metric_failure("disk", str(error))


def create_alerts(cpu: dict[str, Any], memory: dict[str, Any], disk: dict[str, Any]) -> list[dict[str, str]]:
    checks = [("CPU", cpu), ("MEMORY", memory), ("DISK", disk)]
    return [
        {"type": name, "message": f"High {name.lower()} usage detected: {data['usage_percent']}%"}
        for name, data in checks if data.get("status") == "WARNING"
    ]


def alert_text(alerts: list[dict[str, str]]) -> str:
    return "\n".join(item["message"] for item in alerts)


def send_email_alert(alerts: list[dict[str, str]]) -> str:
    settings = CONFIG["email"]
    if not settings["enabled"]:
        return "NOT_CONFIGURED"
    password = os.environ.get(settings["password_environment_variable"], "")
    if not all((settings["recipient"], settings["sender"], password)):
        logging.warning("Email notification is enabled but recipient, sender, or password is unavailable")
        return "INCOMPLETE_CONFIGURATION"
    message = EmailMessage()
    message["Subject"] = f"SERVER ALERT - {HOSTNAME}"
    message["From"] = settings["sender"]
    message["To"] = settings["recipient"]
    message.set_content(f"Monitoring alert detected on {HOSTNAME}\n\n{alert_text(alerts)}\n\nOperating System: {OPERATING_SYSTEM}\nTime: {RUN_TIME.isoformat()}")
    try:
        with smtplib.SMTP(settings["smtp_server"], int(settings["smtp_port"]), timeout=20) as server:
            server.starttls()
            server.login(settings["sender"], password)
            server.send_message(message)
        logging.info("Email notification sent")
        return "SENT"
    except (OSError, smtplib.SMTPException) as error:
        logging.error("Email notification failed: %s", error)
        return "FAILED"


def send_webhook(name: str, settings: dict[str, Any], alerts: list[dict[str, str]]) -> str:
    if not settings["enabled"] or not settings["webhook_url"]:
        return "NOT_CONFIGURED"
    payload = json.dumps({"hostname": HOSTNAME, "message": alert_text(alerts), "timestamp": RUN_TIME.isoformat()}).encode("utf-8")
    request = urllib.request.Request(settings["webhook_url"], data=payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            logging.info("%s webhook sent: HTTP %s", name, response.status)
            return f"SENT_HTTP_{response.status}"
    except (urllib.error.URLError, OSError) as error:
        logging.error("%s webhook failed: %s", name, error)
        return "FAILED"


def create_ticket(alerts: list[dict[str, str]]) -> str:
    settings = CONFIG["ticketing"]
    if not settings["enabled"] or not settings["api_url"]:
        return "NOT_CONFIGURED"
    headers = {"Content-Type": "application/json"}
    token = os.environ.get(settings["token_environment_variable"], "")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    payload = json.dumps({"title": f"Monitoring Alert - {HOSTNAME}", "description": alert_text(alerts)}).encode("utf-8")
    request = urllib.request.Request(settings["api_url"], data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            logging.info("Ticket created: HTTP %s", response.status)
            return f"SENT_HTTP_{response.status}"
    except (urllib.error.URLError, OSError) as error:
        logging.error("Ticket creation failed: %s", error)
        return "FAILED"


def send_notifications(alerts: list[dict[str, str]], no_notify: bool) -> dict[str, str]:
    if not alerts:
        return {"status": "NO_ALERTS"}
    if no_notify:
        return {"status": "SUPPRESSED_BY_ARGUMENT"}
    return {
        "email": send_email_alert(alerts),
        "microsoft_teams": send_webhook("Microsoft Teams", CONFIG["microsoft_teams"], alerts),
        "slack": send_webhook("Slack", CONFIG["slack"], alerts),
        "generic_webhook": send_webhook("Generic webhook", CONFIG["generic_webhook"], alerts),
        "ticketing": create_ticket(alerts),
    }


def save_report(data: dict[str, Any]) -> Path:
    report_file = PATHS["report"] / f"monitoring_report_{RUN_TIME:%Y%m%d_%H%M%S}.json"
    final_report = {
        "run_id": RUN_ID, "timestamp": RUN_TIME.isoformat(), "hostname": HOSTNAME,
        "operating_system": OPERATING_SYSTEM, "automation": "MONITORING_ALERTING",
        "log_file": str(LOG_FILE), "result": data,
    }
    report_file.write_text(json.dumps(final_report, indent=2, default=str), encoding="utf-8")
    logging.info("Monitoring report saved: %s", report_file)
    return report_file


def main() -> int:
    args = parse_arguments()
    logging.info("Monitoring started: %s on %s", RUN_ID, OPERATING_SYSTEM)
    psutil_module = get_psutil()
    cpu = check_cpu(psutil_module)
    memory = check_memory(psutil_module)
    disk = check_disk(psutil_module)
    alerts = create_alerts(cpu, memory, disk)
    notifications = send_notifications(alerts, args.no_notify)
    report_file = save_report({
        "system_information": system_information(), "monitoring": {"cpu": cpu, "memory": memory, "disk": disk},
        "alerts": alerts, "notifications": notifications,
    })
    print(json.dumps({
        "run_id": RUN_ID, "hostname": HOSTNAME, "operating_system": OPERATING_SYSTEM,
        "cpu": cpu.get("status"), "memory": memory.get("status"), "disk": disk.get("status"),
        "alerts": len(alerts), "report": str(report_file), "log": str(LOG_FILE),
    }, indent=2))
    logging.info("Monitoring completed: %s", RUN_ID)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        logging.exception("Monitoring automation failed")
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
