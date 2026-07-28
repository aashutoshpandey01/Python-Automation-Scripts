#!/usr/bin/env python3
"""Collect network state and run configured connectivity, DNS, and port checks."""

from __future__ import annotations

import argparse
import json
import logging
import platform
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_NAME = "network_automation"
OPERATING_SYSTEM = platform.system()
HOSTNAME = socket.gethostname()
RUN_TIME = datetime.now(timezone.utc)
RUN_ID = f"NETWORK-{RUN_TIME:%Y%m%d-%H%M%S}"


def get_platform_paths() -> dict[str, Path]:
    """Choose the managed-server hierarchy before issuing OS-specific commands."""
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
    "ping_targets": ["8.8.8.8", "1.1.1.1", "google.com"],
    "dns_targets": ["google.com", "github.com", "microsoft.com"],
    "port_checks": [
        {"host": "google.com", "port": 443, "service": "HTTPS"},
        {"host": "google.com", "port": 80, "service": "HTTP"},
        {"host": "github.com", "port": 443, "service": "GitHub HTTPS"},
    ],
    "command_timeout_seconds": 60,
    "network_timeout_seconds": 5,
}


def load_configuration() -> dict[str, Any]:
    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text(json.dumps(DEFAULT_CONFIG, indent=2), encoding="utf-8")
        return json.loads(json.dumps(DEFAULT_CONFIG))
    try:
        configured = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        return {**DEFAULT_CONFIG, **configured}
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
    parser = argparse.ArgumentParser(description="Enterprise Network Automation")
    parser.add_argument("--no-active-connections", action="store_true", help="Skip the active-connection collection step.")
    return parser.parse_args()


def run_command(command: list[str]) -> dict[str, Any]:
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=int(CONFIG["command_timeout_seconds"]), check=False,
        )
        if result.returncode != 0:
            logging.warning("Command failed (%s): %s", result.returncode, " ".join(command))
        return {
            "command": " ".join(command), "return_code": result.returncode,
            "stdout": result.stdout.strip(), "stderr": result.stderr.strip(), "success": result.returncode == 0,
        }
    except subprocess.TimeoutExpired:
        return {"command": " ".join(command), "return_code": -1, "stdout": "", "stderr": "Command timeout", "success": False}
    except OSError as error:
        logging.warning("Command execution failed: %s", error)
        return {"command": " ".join(command), "return_code": -1, "stdout": "", "stderr": str(error), "success": False}


def collect_network_information() -> dict[str, Any]:
    if OPERATING_SYSTEM == "Linux":
        commands = {"interfaces": ["ip", "addr"], "routes": ["ip", "route"]}
    elif OPERATING_SYSTEM == "Windows":
        commands = {"interfaces": ["ipconfig", "/all"], "routes": ["route", "print"]}
    else:
        return {"status": "UNSUPPORTED_OS"}
    return {"status": "COMPLETED", "network_data": {name: run_command(command) for name, command in commands.items()}}


def active_connection_check() -> dict[str, Any]:
    if OPERATING_SYSTEM == "Linux":
        command = ["ss", "-tun"]
    elif OPERATING_SYSTEM == "Windows":
        command = ["powershell", "-NoProfile", "-NonInteractive", "-Command", "Get-NetTCPConnection | ConvertTo-Json"]
    else:
        return {"status": "UNSUPPORTED_OS", "connections": []}
    result = run_command(command)
    if not result["success"]:
        return {"status": "FAILED", "connections": [], "details": result}
    if OPERATING_SYSTEM == "Windows":
        try:
            parsed = json.loads(result["stdout"])
            connections = parsed if isinstance(parsed, list) else [parsed]
        except json.JSONDecodeError:
            connections = result["stdout"].splitlines()
    else:
        connections = result["stdout"].splitlines()
    return {"status": "COMPLETED", "connections": connections}


def ping_check(target: str) -> dict[str, Any]:
    if OPERATING_SYSTEM == "Windows":
        command = ["ping", "-n", "2", "-w", "3000", target]
    elif OPERATING_SYSTEM == "Linux":
        command = ["ping", "-c", "2", "-W", "3", target]
    else:
        return {"target": target, "status": "UNSUPPORTED_OS"}
    details = run_command(command)
    return {"target": target, "status": "REACHABLE" if details["success"] else "UNREACHABLE", "details": details}


def port_check(host: str, port: int, service: str) -> dict[str, Any]:
    try:
        with socket.create_connection((host, int(port)), timeout=float(CONFIG["network_timeout_seconds"])):
            status, message = "OPEN", "Connection established"
    except (socket.timeout, ConnectionRefusedError, OSError) as error:
        status, message = "CLOSED_OR_UNREACHABLE", str(error)
    return {"host": host, "port": int(port), "service": service, "status": status, "details": message}


def dns_check(hostname: str) -> dict[str, str]:
    try:
        return {"hostname": hostname, "status": "RESOLVED", "ip_address": socket.gethostbyname(hostname)}
    except socket.gaierror as error:
        return {"hostname": hostname, "status": "DNS_FAILED", "details": str(error)}


def network_health_summary(ping_results: list[dict[str, Any]], port_results: list[dict[str, Any]], dns_results: list[dict[str, Any]]) -> dict[str, Any]:
    failed_ping = sum(item["status"] != "REACHABLE" for item in ping_results)
    closed_ports = sum(item["status"] != "OPEN" for item in port_results)
    failed_dns = sum(item["status"] != "RESOLVED" for item in dns_results)
    status = "HIGH" if failed_dns else "MEDIUM" if failed_ping > 1 or closed_ports > 1 else "LOW"
    return {
        "network_status": status, "failed_ping_checks": failed_ping,
        "closed_services": closed_ports, "dns_failures": failed_dns,
    }


def save_report(data: dict[str, Any]) -> Path:
    report_file = PATHS["report"] / f"network_report_{RUN_TIME:%Y%m%d_%H%M%S}.json"
    report = {
        "run_id": RUN_ID, "timestamp": RUN_TIME.isoformat(), "hostname": HOSTNAME,
        "operating_system": OPERATING_SYSTEM, "automation": "NETWORK_AUTOMATION",
        "log_file": str(LOG_FILE), "result": data,
    }
    report_file.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    logging.info("Network report saved: %s", report_file)
    return report_file


def main() -> int:
    args = parse_arguments()
    logging.info("Network automation started: %s on %s", RUN_ID, OPERATING_SYSTEM)
    network_information = collect_network_information()
    active_connections = {"status": "SKIPPED", "connections": []} if args.no_active_connections else active_connection_check()
    ping_results = [ping_check(str(target)) for target in CONFIG["ping_targets"]]
    port_results = [port_check(str(item["host"]), int(item["port"]), str(item["service"])) for item in CONFIG["port_checks"]]
    dns_results = [dns_check(str(hostname)) for hostname in CONFIG["dns_targets"]]
    health = network_health_summary(ping_results, port_results, dns_results)
    report_file = save_report({
        "network_information": network_information, "active_connections": active_connections,
        "ping_monitoring": ping_results, "service_port_monitoring": port_results,
        "dns_monitoring": dns_results, "network_health": health,
    })
    print(json.dumps({
        "run_id": RUN_ID, "hostname": HOSTNAME, "operating_system": OPERATING_SYSTEM,
        "network_health": health, "report": str(report_file), "log": str(LOG_FILE),
    }, indent=2))
    logging.info("Network automation completed: %s", RUN_ID)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        logging.exception("Network automation failed")
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
