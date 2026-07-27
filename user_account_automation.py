import platform
import subprocess
import argparse
import json
import logging
from pathlib import Path
from datetime import datetime


# ============================================================
# DIRECTORIES
# ============================================================

BASE_DIRECTORY = Path(__file__).parent

HOSTNAME = platform.node()

DATA_DIRECTORY = (
    BASE_DIRECTORY
    / "user_account_automation_data"
    / HOSTNAME
)

REPORT_DIRECTORY = (
    DATA_DIRECTORY
    / "reports"
)

LOG_DIRECTORY = (
    DATA_DIRECTORY
    / "logs"
)

REPORT_DIRECTORY.mkdir(
    parents=True,
    exist_ok=True
)

LOG_DIRECTORY.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# LOGGING
# ============================================================

LOG_FILE = (

    LOG_DIRECTORY

    / "user_account_automation.log"

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


        return {

            "success":

            result.returncode == 0,

            "output":

            result.stdout.strip(),

            "error":

            result.stderr.strip(),

            "return_code":

            result.returncode

        }


    except Exception as error:

        return {

            "success":

            False,

            "output":

            "",

            "error":

            str(error),

            "return_code":

            -1

        }


# ============================================================
# LINUX USER OPERATIONS
# ============================================================

def linux_create_user(

    username

):

    return run_command(

        [

            "sudo",

            "useradd",

            "-m",

            username

        ]

    )


def linux_remove_user(

    username

):

    return run_command(

        [

            "sudo",

            "userdel",

            "-r",

            username

        ]

    )


def linux_disable_user(

    username

):

    return run_command(

        [

            "sudo",

            "usermod",

            "--lock",

            username

        ]

    )


def linux_add_to_group(

    username,

    group

):

    return run_command(

        [

            "sudo",

            "usermod",

            "-aG",

            group,

            username

        ]

    )


def linux_create_service_account(

    username

):

    return run_command(

        [

            "sudo",

            "useradd",

            "--system",

            "--no-create-home",

            "--shell",

            "/usr/sbin/nologin",

            username

        ]

    )


# ============================================================
# WINDOWS USER OPERATIONS
# ============================================================

def windows_create_user(

    username

):

    return run_command(

        [

            "powershell",

            "-Command",

            f"New-LocalUser "

            f"-Name '{username}' "

            f"-NoPassword"

        ]

    )


def windows_remove_user(

    username

):

    return run_command(

        [

            "powershell",

            "-Command",

            f"Remove-LocalUser "

            f"-Name '{username}'"

        ]

    )


def windows_disable_user(

    username

):

    return run_command(

        [

            "powershell",

            "-Command",

            f"Disable-LocalUser "

            f"-Name '{username}'"

        ]

    )


def windows_add_to_group(

    username,

    group

):

    return run_command(

        [

            "powershell",

            "-Command",

            f"Add-LocalGroupMember "

            f"-Group '{group}' "

            f"-Member '{username}'"

        ]

    )


def windows_create_service_account(

    username

):

    return run_command(

        [

            "powershell",

            "-Command",

            f"New-LocalUser "

            f"-Name '{username}' "

            f"-NoPassword"

        ]

    )


# ============================================================
# EXECUTE USER OPERATION
# ============================================================

def execute_operation(

    operation,

    username,

    group=None

):

    operating_system = (

        platform.system()

    )


    if operating_system == "Linux":

        if operation == "create":

            return linux_create_user(

                username

            )


        elif operation == "remove":

            return linux_remove_user(

                username

            )


        elif operation == "disable":

            return linux_disable_user(

                username

            )


        elif operation == "add-to-group":

            return linux_add_to_group(

                username,

                group

            )


        elif operation == "service-account":

            return linux_create_service_account(

                username

            )


    elif operating_system == "Windows":

        if operation == "create":

            return windows_create_user(

                username

            )


        elif operation == "remove":

            return windows_remove_user(

                username

            )


        elif operation == "disable":

            return windows_disable_user(

                username

            )


        elif operation == "add-to-group":

            return windows_add_to_group(

                username,

                group

            )


        elif operation == "service-account":

            return windows_create_service_account(

                username

            )


    return {

        "success":

        False,

        "output":

        "",

        "error":

        "Unsupported operation or operating system",

        "return_code":

        -1

    }


# ============================================================
# CREATE REPORT
# ============================================================

def create_report(

    operation,

    username,

    group,

    result

):

    report = {

        "timestamp":

        datetime.now().strftime(

            "%Y-%m-%d %H:%M:%S"

        ),

        "hostname":

        HOSTNAME,

        "operating_system":

        platform.system(),

        "operation":

        operation,

        "username":

        username,

        "group":

        group,

        "success":

        result["success"],

        "output":

        result["output"],

        "error":

        result["error"],

        "return_code":

        result["return_code"]

    }


    timestamp = (

        datetime.now().strftime(

            "%Y%m%d_%H%M%S"

        )

    )


    report_file = (

        REPORT_DIRECTORY

        / f"user_operation_{timestamp}.json"

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


    return report_file


# ============================================================
# ARGUMENTS
# ============================================================

def parse_arguments():

    parser = argparse.ArgumentParser(

        description=

        "Cross-platform user account automation"

    )


    parser.add_argument(

        "operation",

        choices=[

            "create",

            "remove",

            "disable",

            "add-to-group",

            "service-account"

        ]

    )


    parser.add_argument(

        "username"

    )


    parser.add_argument(

        "--group"

    )


    return parser.parse_args()


# ============================================================
# MAIN
# ============================================================

def main():

    args = (

        parse_arguments()

    )


    if (

        args.operation

        == "add-to-group"

        and not args.group

    ):

        print(

            "ERROR: --group is required"

        )

        return


    logging.info(

        "User operation started: %s",

        args.operation

    )


    result = (

        execute_operation(

            args.operation,

            args.username,

            args.group

        )

    )


    report_file = (

        create_report(

            args.operation,

            args.username,

            args.group,

            result

        )

    )


    if result["success"]:

        print(

            "SUCCESS:",

            args.operation,

            args.username

        )


    else:

        print(

            "FAILED:",

            result["error"]

        )


    print(

        "Report:",

        report_file

    )


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":

    try:

        main()


    except Exception as error:

        logging.exception(

            "User automation failed"

        )


        print(

            "ERROR:",

            error

        )