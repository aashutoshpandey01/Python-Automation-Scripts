import platform
import subprocess
import json
import logging
from pathlib import Path
from datetime import datetime


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIRECTORY = Path(__file__).parent

DATA_DIRECTORY = (
    BASE_DIRECTORY
    / "service_monitor_data"
)

DATA_DIRECTORY.mkdir(
    parents=True,
    exist_ok=True
)

STATE_FILE = (
    DATA_DIRECTORY
    / "service_state.json"
)

REPORT_FILE = (
    DATA_DIRECTORY
    / "service_report.json"
)

LOG_FILE = (
    DATA_DIRECTORY
    / "service_monitor.log"
)


# ============================================================
# LOGGING
# ============================================================

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
# LOAD PREVIOUS SERVICE STATES
# ============================================================

def load_previous_states():

    if not STATE_FILE.exists():

        return {}


    try:

        with open(
            STATE_FILE,
            "r"
        ) as file:

            return json.load(file)


    except json.JSONDecodeError:

        return {}


# ============================================================
# SAVE CURRENT SERVICE STATES
# ============================================================

def save_current_states(
    service_states
):

    with open(

        STATE_FILE,

        "w"

    ) as file:

        json.dump(

            service_states,

            file,

            indent=4

        )


# ============================================================
# GET ALL LINUX SERVICES
# ============================================================

def get_linux_services():

    result = subprocess.run(

        [

            "systemctl",

            "list-unit-files",

            "--type=service",

            "--no-legend",

            "--no-pager"

        ],

        capture_output=True,

        text=True

    )


    services = []


    for line in result.stdout.splitlines():

        parts = line.split()


        if len(parts) >= 2:

            service_name = parts[0]

            enabled_status = parts[1]


            services.append(

                {

                    "name":
                    service_name,

                    "enabled":
                    enabled_status

                }

            )


    return services


# ============================================================
# CHECK LINUX SERVICE STATUS
# ============================================================

def check_linux_service(
    service_name
):

    result = subprocess.run(

        [

            "systemctl",

            "is-active",

            service_name

        ],

        capture_output=True,

        text=True

    )


    status = (
        result.stdout.strip()
    )


    return status


# ============================================================
# GET ALL WINDOWS SERVICES
# ============================================================

def get_windows_services():

    result = subprocess.run(

        [

            "powershell",

            "-Command",

            "Get-Service | "
            "Select-Object Name,Status,StartType | "
            "ConvertTo-Json"

        ],

        capture_output=True,

        text=True

    )


    if not result.stdout.strip():

        return []


    services = json.loads(
        result.stdout
    )


    # If only one service exists,
    # PowerShell may return a dictionary
    # instead of a list.

    if isinstance(
        services,
        dict
    ):

        services = [

            services

        ]


    return services


# ============================================================
# CHECK ALL LINUX SERVICES
# ============================================================

def monitor_linux_services(
    previous_states
):

    services = (
        get_linux_services()
    )


    current_states = []

    report = []


    for service in services:

        service_name = (
            service["name"]
        )


        enabled_status = (
            service["enabled"]
        )


        current_status = (
            check_linux_service(
                service_name
            )
        )


        previous_status = (
            previous_states.get(
                service_name
            )
        )


        action = (
            "NO ACTION"
        )


        # ----------------------------------------------------
        # SERVICE RUNNING
        # ----------------------------------------------------

        if current_status == "active":

            action = (
                "SERVICE RUNNING"
            )


        # ----------------------------------------------------
        # SERVICE FAILED
        # ----------------------------------------------------

        elif current_status == "failed":

            if previous_status == "active":

                restart_result = (
                    subprocess.run(

                        [

                            "sudo",

                            "systemctl",

                            "restart",

                            service_name

                        ],

                        capture_output=True,

                        text=True

                    )
                )


                if restart_result.returncode == 0:

                    action = (
                        "SERVICE RESTARTED"
                    )

                else:

                    action = (
                        "RESTART FAILED"
                    )


            else:

                action = (
                    "FAILED - NO RESTART"
                )


        # ----------------------------------------------------
        # SERVICE INACTIVE
        # ----------------------------------------------------

        elif current_status == "inactive":

            if (

                previous_status == "active"

                and enabled_status
                not in [

                    "disabled",

                    "masked"

                ]

            ):

                restart_result = (
                    subprocess.run(

                        [

                            "sudo",

                            "systemctl",

                            "restart",

                            service_name

                        ],

                        capture_output=True,

                        text=True

                    )
                )


                if restart_result.returncode == 0:

                    action = (
                        "SERVICE RESTARTED"
                    )

                else:

                    action = (
                        "RESTART FAILED"
                    )


            else:

                action = (
                    "INACTIVE - NO ACTION"
                )


        # ----------------------------------------------------
        # OTHER STATUS
        # ----------------------------------------------------

        else:

            action = (
                "STATUS: "
                + current_status
            )


        current_states.append(

            {

                "name":
                service_name,

                "status":
                current_status,

                "enabled":
                enabled_status

            }

        )


        report.append(

            {

                "service":
                service_name,

                "previous_status":
                previous_status,

                "current_status":
                current_status,

                "enabled":
                enabled_status,

                "action":
                action

            }

        )


    return (

        current_states,

        report

    )


# ============================================================
# CHECK ALL WINDOWS SERVICES
# ============================================================

def monitor_windows_services(
    previous_states
):

    services = (
        get_windows_services()
    )


    current_states = []

    report = []


    for service in services:

        service_name = (
            service["Name"]
        )


        current_status = str(

            service["Status"]

        )


        start_type = str(

            service.get(
                "StartType",
                "Unknown"
            )

        )


        previous_status = (

            previous_states.get(
                service_name
            )

        )


        action = (
            "NO ACTION"
        )


        # ----------------------------------------------------
        # SERVICE RUNNING
        # ----------------------------------------------------

        if current_status == "Running":

            action = (
                "SERVICE RUNNING"
            )


        # ----------------------------------------------------
        # SERVICE STOPPED
        # ----------------------------------------------------

        elif current_status == "Stopped":

            if (

                previous_status == "Running"

                and start_type
                not in [

                    "Disabled"

                ]

            ):

                restart_result = subprocess.run(

                    [

                        "powershell",

                        "-Command",

                        f"Start-Service "
                        f"-Name '{service_name}'"

                    ],

                    capture_output=True,

                    text=True

                )


                if restart_result.returncode == 0:

                    action = (
                        "SERVICE RESTARTED"
                    )

                else:

                    action = (
                        "RESTART FAILED"
                    )


            else:

                action = (
                    "STOPPED - NO ACTION"
                )


        # ----------------------------------------------------
        # OTHER STATUS
        # ----------------------------------------------------

        else:

            action = (

                "STATUS: "

                + current_status

            )


        current_states.append(

            {

                "name":
                service_name,

                "status":
                current_status,

                "start_type":
                start_type

            }

        )


        report.append(

            {

                "service":
                service_name,

                "previous_status":
                previous_status,

                "current_status":
                current_status,

                "start_type":
                start_type,

                "action":
                action

            }

        )


    return (

        current_states,

        report

    )


# ============================================================
# SAVE REPORT
# ============================================================

def save_report(
    report
):

    final_report = {

        "timestamp":
        datetime.now().strftime(

            "%Y-%m-%d %H:%M:%S"

        ),

        "hostname":
        platform.node(),

        "operating_system":
        platform.system(),

        "total_services":
        len(report),

        "services":
        report

    }


    with open(

        REPORT_FILE,

        "w"

    ) as file:

        json.dump(

            final_report,

            file,

            indent=4

        )


    return final_report


# ============================================================
# DISPLAY IMPORTANT RESULTS
# ============================================================

def display_results(
    report
):

    print("\n")
    print("=" * 70)

    print(
        "ENTERPRISE SERVICE MONITORING"
    )

    print("=" * 70)


    print(

        "Operating System:",

        platform.system()

    )


    print(

        "Hostname:",

        platform.node()

    )


    print(

        "Total Services:",

        len(report)

    )


    print("\nSERVICE RESULTS")


    for service in report:

        action = (
            service["action"]
        )


        if action != "SERVICE RUNNING":

            print(

                service["service"],

                "→",

                action

            )


    print("\nMonitoring completed.")


# ============================================================
# MAIN
# ============================================================

def main():

    logging.info(
        "Service monitoring started"
    )


    previous_states = (
        load_previous_states()
    )


    if platform.system() == "Linux":

        current_states, report = (

            monitor_linux_services(

                previous_states

            )

        )


    elif platform.system() == "Windows":

        current_states, report = (

            monitor_windows_services(

                previous_states

            )

        )


    else:

        print(
            "Unsupported operating system."
        )

        return


    # Convert current states
    # into a simple dictionary
    # for the next execution.

    state_dictionary = {}


    for service in current_states:

        state_dictionary[
            service["name"]
        ] = service["status"]


    save_current_states(
        state_dictionary
    )


    final_report = (
        save_report(
            report
        )
    )


    display_results(
        report
    )


    logging.info(
        "Service monitoring completed"
    )


    print(

        "\nReport saved to:",

        REPORT_FILE

    )


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":

    try:

        main()


    except Exception as error:

        logging.exception(

            "Service monitoring failed"

        )


        print(

            "ERROR:",

            error

        )