#!/usr/bin/env python3

import os
import sys
import json
import platform
import subprocess
from datetime import datetime
from pathlib import Path


# ============================================================
# PATCH AND UPDATE AUTOMATION
# Cross-platform: Windows + Ubuntu/Linux
# Non-interactive: suitable for cron and scheduled automation
# ============================================================


SCRIPT_DIR = Path(__file__).resolve().parent
REPORT_DIR = SCRIPT_DIR / "patch_update_reports"
REPORT_DIR.mkdir(exist_ok=True)

TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
REPORT_FILE = REPORT_DIR / f"patch_update_report_{TIMESTAMP}.json"


def run_command(command, shell=False):
    """Run a system command and return result."""

    try:
        result = subprocess.run(
            command,
            shell=shell,
            capture_output=True,
            text=True,
            timeout=1800
        )

        return {
            "command": command if isinstance(command, str) else " ".join(command),
            "return_code": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "success": result.returncode == 0
        }

    except subprocess.TimeoutExpired:
        return {
            "command": command if isinstance(command, str) else " ".join(command),
            "return_code": -1,
            "stdout": "",
            "stderr": "Command timed out",
            "success": False
        }

    except Exception as error:
        return {
            "command": command if isinstance(command, str) else " ".join(command),
            "return_code": -1,
            "stdout": "",
            "stderr": str(error),
            "success": False
        }


def detect_operating_system():
    system = platform.system()

    if system == "Windows":
        return "Windows"

    if system == "Linux":
        return "Linux"

    return system


def ubuntu_update():
    """Update Ubuntu/Debian systems automatically."""

    print("\nOperating System: Ubuntu/Linux")
    print("Mode: AUTOMATIC - No confirmation required")

    report = {
        "platform": "Linux",
        "update_check": None,
        "upgrade": None,
        "autoremove": None,
        "reboot_required": False
    }

    print("\nUpdating package information...")

    update_result = run_command(
        ["sudo", "apt-get", "update", "-y"]
    )

    report["update_check"] = update_result

    if not update_result["success"]:
        print("FAILED: apt update")
        return report

    print("Package information updated successfully.")

    print("\nInstalling available updates automatically...")

    upgrade_result = run_command(
        ["sudo", "DEBIAN_FRONTEND=noninteractive", "apt-get", "upgrade", "-y"]
    )

    # If the above environment syntax is unsupported by subprocess,
    # use the environment variable properly.
    if not upgrade_result["success"]:
        environment = os.environ.copy()
        environment["DEBIAN_FRONTEND"] = "noninteractive"

        try:
            result = subprocess.run(
                ["sudo", "apt-get", "upgrade", "-y"],
                capture_output=True,
                text=True,
                timeout=1800,
                env=environment
            )

            upgrade_result = {
                "command": "sudo apt-get upgrade -y",
                "return_code": result.returncode,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "success": result.returncode == 0
            }

        except Exception as error:
            upgrade_result = {
                "command": "sudo apt-get upgrade -y",
                "return_code": -1,
                "stdout": "",
                "stderr": str(error),
                "success": False
            }

    report["upgrade"] = upgrade_result

    if upgrade_result["success"]:
        print("Updates installed successfully.")
    else:
        print("WARNING: Some updates may have failed.")

    print("\nRemoving unused packages automatically...")

    autoremove_result = run_command(
        ["sudo", "apt-get", "autoremove", "-y"]
    )

    report["autoremove"] = autoremove_result

    if autoremove_result["success"]:
        print("Unused packages removed.")
    else:
        print("WARNING: Autoremove failed.")

    reboot_check = Path("/var/run/reboot-required")

    if reboot_check.exists():
        report["reboot_required"] = True
        print("\nREBOOT REQUIRED")
        print("A reboot is required to complete some updates.")
        print("Automatic reboot was NOT performed.")
    else:
        print("\nNo reboot required.")

    return report


def windows_update():
    """Update Windows using PowerShell and Windows Update."""

    print("\nOperating System: Windows")
    print("Mode: AUTOMATIC - No confirmation required")

    report = {
        "platform": "Windows",
        "update_status": None
    }

    print("\nChecking Windows Update...")

    powershell_command = """
$ErrorActionPreference = "Continue"

if (-not (Get-Module -ListAvailable -Name PSWindowsUpdate)) {
    Write-Output "PSWindowsUpdate module is not installed."
    Write-Output "Install it with:"
    Write-Output "Install-Module PSWindowsUpdate -Force"
    exit 2
}

Import-Module PSWindowsUpdate

Get-WindowsUpdate -AcceptAll -Install -IgnoreReboot
"""

    result = run_command(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", powershell_command]
    )

    report["update_status"] = result

    if result["success"]:
        print("Windows updates processed automatically.")
    else:
        print("WARNING: Windows Update operation failed or requires configuration.")

    return report


def save_report(report):
    final_report = {
        "timestamp": datetime.now().isoformat(),
        "hostname": platform.node(),
        "operating_system": detect_operating_system(),
        "automation_mode": "non-interactive",
        "report": report
    }

    with open(REPORT_FILE, "w", encoding="utf-8") as file:
        json.dump(final_report, file, indent=4)

    print("\nReport saved:")
    print(REPORT_FILE)


def main():
    print("=" * 60)
    print("PATCH AND UPDATE AUTOMATION")
    print("=" * 60)

    operating_system = detect_operating_system()

    if operating_system == "Windows":
        report = windows_update()

    elif operating_system == "Linux":
        report = ubuntu_update()

    else:
        print(f"Unsupported operating system: {operating_system}")
        sys.exit(1)

    save_report(report)

    print("\nPatch automation completed.")


if __name__ == "__main__":
    main()