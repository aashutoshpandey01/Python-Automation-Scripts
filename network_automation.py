import platform
import subprocess
import socket
import json
import logging
from pathlib import Path
from datetime import datetime


# ============================================================
# AUTOMATIC DIRECTORIES
# ============================================================

BASE_DIRECTORY = Path(__file__).parent

HOSTNAME = platform.node()

DATA_DIRECTORY = (
    BASE_DIRECTORY
    / "network_automation_data"
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


LOG_DIRECTORY.mkdir(
    parents=True,
    exist_ok=True
)

REPORT_DIRECTORY.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# LOGGING
# ============================================================

LOG_FILE = (
    LOG_DIRECTORY
    / "network_automation.log"
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

PING_TARGETS = [

    "8.8.8.8",

    "1.1.1.1",

    "google.com"

]


DNS_NAMES = [

    "google.com",

    "github.com",

    "microsoft.com"

]


PORT_CHECKS = [

    {

        "host": "google.com",

        "port": 443,

        "name": "HTTPS"

    },

    {

        "host": "google.com",

        "port": 80,

        "name": "HTTP"

    },

    {

        "host": "github.com",

        "port": 443,

        "name": "GitHub HTTPS"

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
# COLLECT NETWORK INFORMATION
# ============================================================

def collect_network_information():

    operating_system = (

        platform.system()

    )


    if operating_system == "Windows":

        result = run_command(

            [

                "ipconfig",

                "/all"

            ]

        )


    elif operating_system == "Linux":

        result = run_command(

            [

                "ip",

                "addr"

            ]

        )


    else:

        return {

            "status": "Unsupported OS"

        }


    if not result:

        return {

            "status": "Failed"

        }


    return {

        "status": (

            "Success"

            if result.returncode == 0

            else "Failed"

        ),

        "output": result.stdout

    }


# ============================================================
# PING CHECK
# ============================================================

def ping_check(

    target

):

    operating_system = (

        platform.system()

    )


    if operating_system == "Windows":

        command = [

            "ping",

            "-n",

            "2",

            target

        ]


    elif operating_system == "Linux":

        command = [

            "ping",

            "-c",

            "2",

            target

        ]


    else:

        return {

            "target": target,

            "status": "Unsupported OS"

        }


    result = run_command(

        command

    )


    if not result:

        return {

            "target": target,

            "status": "Failed"

        }


    if result.returncode == 0:

        status = "Reachable"

    else:

        status = "Unreachable"


    return {

        "target": target,

        "status": status,

        "output": result.stdout

    }


# ============================================================
# PORT CHECK
# ============================================================

def port_check(

    host,

    port,

    name

):

    try:

        with socket.create_connection(

            (

                host,

                port

            ),

            timeout=5

        ):

            return {

                "host": host,

                "port": port,

                "service": name,

                "status": "Open"

            }


    except (

        socket.timeout,

        ConnectionRefusedError,

        OSError

    ):

        return {

            "host": host,

            "port": port,

            "service": name,

            "status": "Closed or Unreachable"

        }


# ============================================================
# DNS CHECK
# ============================================================

def dns_check(

    hostname

):

    try:

        ip_address = (

            socket.gethostbyname(

                hostname

            )

        )


        return {

            "hostname": hostname,

            "status": "Resolved",

            "ip_address": ip_address

        }


    except socket.gaierror:

        return {

            "hostname": hostname,

            "status": "DNS Resolution Failed"

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

        "\nCollecting network information..."

    )


    network_information = (

        collect_network_information()

    )


    print(

        "Network information collected"

    )


    # --------------------------------------------------------
    # PING CHECKS
    # --------------------------------------------------------

    ping_results = []


    print(

        "\nPing checks:"

    )


    for target in PING_TARGETS:

        result = ping_check(

            target

        )


        ping_results.append(

            result

        )


        print(

            target,

            "→",

            result["status"]

        )


    # --------------------------------------------------------
    # PORT CHECKS
    # --------------------------------------------------------

    port_results = []


    print(

        "\nPort checks:"

    )


    for item in PORT_CHECKS:

        result = port_check(

            item["host"],

            item["port"],

            item["name"]

        )


        port_results.append(

            result

        )


        print(

            item["host"],

            item["port"],

            "→",

            result["status"]

        )


    # --------------------------------------------------------
    # DNS CHECKS
    # --------------------------------------------------------

    dns_results = []


    print(

        "\nDNS checks:"

    )


    for hostname in DNS_NAMES:

        result = dns_check(

            hostname

        )


        dns_results.append(

            result

        )


        print(

            hostname,

            "→",

            result["status"]

        )


    # --------------------------------------------------------
    # CREATE REPORT
    # --------------------------------------------------------

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

        "network_information": (

            network_information

        ),

        "ping_checks": (

            ping_results

        ),

        "port_checks": (

            port_results

        ),

        "dns_checks": (

            dns_results

        )

    }


    timestamp = (

        datetime.now().strftime(

            "%Y%m%d_%H%M%S"

        )

    )


    report_file = (

        REPORT_DIRECTORY

        / f"network_report_{timestamp}.json"

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

        "\nNetwork report saved:"

    )


    print(

        report_file

    )


    logging.info(

        "Network automation completed successfully"

    )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    try:

        main()


    except Exception as error:

        logging.exception(

            "Network automation failed"

        )


        print(

            "ERROR:",

            error

        )