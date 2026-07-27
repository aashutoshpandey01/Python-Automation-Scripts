import platform
import subprocess
import hashlib
import socket
import ssl
import json
import logging
import re

from pathlib import Path
from datetime import datetime


# ============================================================
# AUTOMATIC DIRECTORIES
# ============================================================

BASE_DIRECTORY = Path(__file__).parent

HOSTNAME = platform.node()

DATA_DIRECTORY = (
    BASE_DIRECTORY
    / "security_automation_data"
    / HOSTNAME
)

LOG_DIRECTORY = (
    DATA_DIRECTORY
    / "logs"
)

REPORT_DIRECTORY = (
    DATA_DIRECTORY
    / "reports"
)

INTEGRITY_DIRECTORY = (
    DATA_DIRECTORY
    / "integrity"
)


LOG_DIRECTORY.mkdir(
    parents=True,
    exist_ok=True
)

REPORT_DIRECTORY.mkdir(
    parents=True,
    exist_ok=True
)

INTEGRITY_DIRECTORY.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# LOGGING
# ============================================================

LOG_FILE = (
    LOG_DIRECTORY
    / "security_automation.log"
)


logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format=(
        "%(asctime)s "
        "- %(levelname)s "
        "- %(message)s"
    )
)


# ============================================================
# CONFIGURATION
# ============================================================

# Files to monitor for changes.
# These are created automatically for lab testing.

MONITORED_FILES = [

    BASE_DIRECTORY
    / "security_test_file.txt"

]


# Certificate expiry checks

CERTIFICATE_HOSTS = [

    {

        "hostname": "google.com",

        "port": 443

    },

    {

        "hostname": "github.com",

        "port": 443

    }

]


# ============================================================
# RUN COMMAND
# ============================================================

def run_command(

    command

):

    try:

        result = subprocess.run(

            command,

            capture_output=True,

            text=True

        )

        return result

    except Exception as error:

        logging.error(

            "Command failed: %s",

            error

        )

        return None


# ============================================================
# CREATE TEST FILE AUTOMATICALLY
# ============================================================

def create_test_file():

    test_file = (

        BASE_DIRECTORY

        / "security_test_file.txt"

    )


    if not test_file.exists():

        test_file.write_text(

            "Security automation test file\n"

        )


    return test_file


# ============================================================
# FILE HASH
# ============================================================

def calculate_file_hash(

    file_path

):

    try:

        sha256 = (

            hashlib.sha256()

        )


        with open(

            file_path,

            "rb"

        ) as file:

            while True:

                data = file.read(

                    4096

                )


                if not data:

                    break


                sha256.update(

                    data

                )


        return (

            sha256.hexdigest()

        )


    except Exception as error:

        logging.error(

            "Hash calculation failed: %s",

            error

        )

        return None


# ============================================================
# FILE INTEGRITY CHECK
# ============================================================

def file_integrity_check():

    results = []


    baseline_file = (

        INTEGRITY_DIRECTORY

        / "file_baseline.json"

    )


    current_hashes = {}


    for file_path in MONITORED_FILES:

        if not file_path.exists():

            results.append(

                {

                    "file": str(file_path),

                    "status": "File not found"

                }

            )

            continue


        file_hash = (

            calculate_file_hash(

                file_path

            )

        )


        current_hashes[

            str(file_path)

        ] = file_hash


    # --------------------------------------------------------
    # FIRST RUN
    # --------------------------------------------------------

    if not baseline_file.exists():

        with open(

            baseline_file,

            "w"

        ) as file:

            json.dump(

                current_hashes,

                file,

                indent=4

            )


        for file_path in MONITORED_FILES:

            if file_path.exists():

                results.append(

                    {

                        "file": str(file_path),

                        "status": (

                            "Baseline created"

                        )

                    }

                )


        return results


    # --------------------------------------------------------
    # LOAD OLD BASELINE
    # --------------------------------------------------------

    with open(

        baseline_file,

        "r"

    ) as file:

        old_hashes = json.load(

            file

        )


    for file_path, current_hash in (

        current_hashes.items()

    ):

        old_hash = (

            old_hashes.get(

                file_path

            )

        )


        if old_hash == current_hash:

            status = "No change"


        else:

            status = (

                "WARNING: File changed"

            )


            logging.warning(

                "File integrity change: %s",

                file_path

            )


        results.append(

            {

                "file": file_path,

                "status": status,

                "current_hash": current_hash

            }

        )


    return results


# ============================================================
# FAILED LOGIN DETECTION
# ============================================================

def failed_login_detection():

    operating_system = (

        platform.system()

    )


    if operating_system == "Linux":

        result = run_command(

            [

                "journalctl",

                "-p",

                "warning",

                "-n",

                "100",

                "--no-pager"

            ]

        )


        if not result:

            return {

                "status": "Command failed"

            }


        lines = (

            result.stdout.splitlines()

        )


        failed_lines = [

            line

            for line in lines

            if (

                "failed"

                in line.lower()

                or

                "authentication failure"

                in line.lower()

                or

                "invalid user"

                in line.lower()

            )

        ]


        return {

            "status": "Completed",

            "failed_event_count": (

                len(failed_lines)

            ),

            "events": failed_lines

        }


    elif operating_system == "Windows":

        result = run_command(

            [

                "powershell",

                "-Command",

                (

                    "Get-WinEvent "

                    "-FilterHashtable "

                    "@{LogName='Security'; "

                    "Id=4625} "

                    "-MaxEvents 50 "

                    "| Format-List"

                )

            ]

        )


        if not result:

            return {

                "status": "Command failed"

            }


        return {

            "status": "Completed",

            "events": result.stdout

        }


    return {

        "status": "Unsupported OS"

    }


# ============================================================
# IP BLOCKING RECOMMENDATION
# ============================================================

def ip_blocking_recommendation(

    failed_login_data

):

    print(

        "\nIP Blocking: REPORT ONLY"

    )


    print(

        "No automatic firewall changes "

        "will be made."

    )


    return {

        "status": (

            "Report only"

        ),

        "action": (

            "Review suspicious IPs "

            "before firewall blocking"

        )

    }


# ============================================================
# SECURITY LOG ANALYSIS
# ============================================================

def security_log_analysis():

    operating_system = (

        platform.system()

    )


    if operating_system == "Linux":

        result = run_command(

            [

                "journalctl",

                "-p",

                "err",

                "-n",

                "100",

                "--no-pager"

            ]

        )


        if not result:

            return {

                "status": "Command failed"

            }


        return {

            "status": "Completed",

            "errors": (

                result.stdout.splitlines()

            )

        }


    elif operating_system == "Windows":

        result = run_command(

            [

                "powershell",

                "-Command",

                (

                    "Get-WinEvent "

                    "-FilterHashtable "

                    "@{LogName='System'; "

                    "Level=2} "

                    "-MaxEvents 50 "

                    "| Format-List"

                )

            ]

        )


        if not result:

            return {

                "status": "Command failed"

            }


        return {

            "status": "Completed",

            "errors": result.stdout

        }


    return {

        "status": "Unsupported OS"

    }


# ============================================================
# CERTIFICATE EXPIRY CHECK
# ============================================================

def certificate_expiry_check(

    hostname,

    port

):

    try:

        context = (

            ssl.create_default_context()

        )


        with socket.create_connection(

            (

                hostname,

                port

            ),

            timeout=10

        ) as connection:

            with context.wrap_socket(

                connection,

                server_hostname=hostname

            ) as secure_socket:

                certificate = (

                    secure_socket.getpeercert()

                )


        expiry_date = (

            datetime.strptime(

                certificate["notAfter"],

                "%b %d %H:%M:%S %Y %Z"

            )

        )


        days_remaining = (

            expiry_date

            - datetime.now()

        ).days


        if days_remaining <= 30:

            status = (

                "WARNING: Certificate expires "

                "within 30 days"

            )


        else:

            status = (

                "Certificate valid"

            )


        return {

            "hostname": hostname,

            "port": port,

            "expiry_date": (

                str(expiry_date)

            ),

            "days_remaining": (

                days_remaining

            ),

            "status": status

        }


    except Exception as error:

        return {

            "hostname": hostname,

            "port": port,

            "status": "Certificate check failed",

            "error": str(error)

        }


# ============================================================
# USER ACCESS AUDIT
# ============================================================

def user_access_audit():

    operating_system = (

        platform.system()

    )


    if operating_system == "Linux":

        result = run_command(

            [

                "getent",

                "passwd"

            ]

        )


        if not result:

            return {

                "status": "Command failed"

            }


        users = []


        for line in (

            result.stdout.splitlines()

        ):

            parts = line.split(":")


            if len(parts) >= 7:

                username = parts[0]

                home_directory = parts[5]

                shell = parts[6]


                users.append(

                    {

                        "username": username,

                        "home": home_directory,

                        "shell": shell

                    }

                )


        return {

            "status": "Completed",

            "users": users

        }


    elif operating_system == "Windows":

        result = run_command(

            [

                "powershell",

                "-Command",

                (

                    "Get-LocalUser "

                    "| Select-Object "

                    "Name,Enabled,LastLogon "

                    "| ConvertTo-Json"

                )

            ]

        )


        if not result:

            return {

                "status": "Command failed"

            }


        try:

            users = json.loads(

                result.stdout

            )


        except json.JSONDecodeError:

            users = result.stdout


        return {

            "status": "Completed",

            "users": users

        }


    return {

        "status": "Unsupported OS"

    }


# ============================================================
# MAIN
# ============================================================

def main():

    print(

        "Operating System:",

        platform.system()

    )


    print(

        "Hostname:",

        HOSTNAME

    )


    print(

        "\nRunning security automation..."

    )


    # --------------------------------------------------------
    # CREATE TEST FILE
    # --------------------------------------------------------

    create_test_file()


    # --------------------------------------------------------
    # FAILED LOGIN DETECTION
    # --------------------------------------------------------

    print(

        "\nChecking failed logins..."

    )


    failed_logins = (

        failed_login_detection()

    )


    print(

        "Failed-login analysis completed"

    )


    # --------------------------------------------------------
    # IP BLOCKING RECOMMENDATION
    # --------------------------------------------------------

    ip_blocking = (

        ip_blocking_recommendation(

            failed_logins

        )

    )


    # --------------------------------------------------------
    # SECURITY LOG ANALYSIS
    # --------------------------------------------------------

    print(

        "\nAnalyzing security logs..."

    )


    security_logs = (

        security_log_analysis()

    )


    print(

        "Security log analysis completed"

    )


    # --------------------------------------------------------
    # FILE INTEGRITY
    # --------------------------------------------------------

    print(

        "\nChecking file integrity..."

    )


    integrity_results = (

        file_integrity_check()

    )


    for result in integrity_results:

        print(

            result["file"],

            "→",

            result["status"]

        )


    # --------------------------------------------------------
    # CERTIFICATE CHECK
    # --------------------------------------------------------

    print(

        "\nChecking certificates..."

    )


    certificate_results = []


    for certificate in (

        CERTIFICATE_HOSTS

    ):

        result = (

            certificate_expiry_check(

                certificate["hostname"],

                certificate["port"]

            )

        )


        certificate_results.append(

            result

        )


        print(

            certificate["hostname"],

            "→",

            result["status"]

        )


    # --------------------------------------------------------
    # USER ACCESS AUDIT
    # --------------------------------------------------------

    print(

        "\nAuditing user access..."

    )


    user_audit = (

        user_access_audit()

    )


    print(

        "User access audit completed"

    )


    # ========================================================
    # CREATE SECURITY REPORT
    # ========================================================

    report = {

        "timestamp": (

            datetime.now().strftime(

                "%Y-%m-%d %H:%M:%S"

            )

        ),

        "hostname": HOSTNAME,

        "operating_system": (

            platform.system()

        ),

        "failed_login_detection": (

            failed_logins

        ),

        "ip_blocking": (

            ip_blocking

        ),

        "security_log_analysis": (

            security_logs

        ),

        "file_integrity": (

            integrity_results

        ),

        "certificate_expiry": (

            certificate_results

        ),

        "user_access_audit": (

            user_audit

        )

    }


    timestamp = (

        datetime.now().strftime(

            "%Y%m%d_%H%M%S"

        )

    )


    report_file = (

        REPORT_DIRECTORY

        / f"security_report_{timestamp}.json"

    )


    with open(

        report_file,

        "w"

    ) as file:

        json.dump(

            report,

            file,

            indent=4

        )


    print(

        "\nSecurity report saved:"

    )


    print(

        report_file

    )


    logging.info(

        "Security automation completed successfully"

    )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    try:

        main()


    except Exception as error:

        logging.exception(

            "Security automation failed"

        )


        print(

            "ERROR:",

            error

        )