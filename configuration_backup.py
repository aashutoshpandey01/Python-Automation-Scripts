import platform
import shutil
import json
import logging
from pathlib import Path
from datetime import datetime


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIRECTORY = Path(__file__).parent

HOSTNAME = platform.node()

SERVER_DIRECTORY = (
    BASE_DIRECTORY
    / "configuration_backup_data"
    / HOSTNAME
)

BACKUP_DIRECTORY = (
    SERVER_DIRECTORY
    / "backups"
)

REPORT_DIRECTORY = (
    SERVER_DIRECTORY
    / "reports"
)

LOG_DIRECTORY = (
    SERVER_DIRECTORY
    / "logs"
)


# Automatically create directories

BACKUP_DIRECTORY.mkdir(
    parents=True,
    exist_ok=True
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
    / "configuration_backup.log"
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
# CONFIGURATION FILES TO BACK UP
# ============================================================

def get_configuration_files():

    operating_system = platform.system()


    if operating_system == "Linux":

        return [

            Path("/etc/ssh/sshd_config"),

            Path("/etc/hosts"),

            Path("/etc/hostname"),

            Path("/etc/fstab"),

            Path("/etc/resolv.conf"),

            Path("/etc/apt/sources.list"),

            Path("/etc/nginx/nginx.conf"),

            Path("/etc/systemd/system")

        ]


    elif operating_system == "Windows":

        windows_directory = Path(
            r"C:\Windows\System32"
        )


        return [

            windows_directory
            / "drivers/etc/hosts",

            Path(
                r"C:\Windows\System32\GroupPolicy"
            ),

            Path(
                r"C:\Windows\System32\inetsrv\config"
            )

        ]


    else:

        return []


# ============================================================
# BACKUP ONE CONFIGURATION ITEM
# ============================================================

def backup_configuration_item(
    source
):

    result = {

        "source":
        str(source),

        "status":
        "",

        "backup":
        "",

        "message":
        ""

    }


    # --------------------------------------------------------
    # FILE OR DIRECTORY DOES NOT EXIST
    # --------------------------------------------------------

    if not source.exists():

        result["status"] = (
            "NOT_FOUND"
        )

        result["message"] = (
            "Configuration item not found"
        )


        logging.warning(

            "Configuration item not found: %s",

            source

        )


        return result


    # --------------------------------------------------------
    # CREATE UNIQUE BACKUP NAME
    # --------------------------------------------------------

    timestamp = (

        datetime.now().strftime(

            "%Y%m%d_%H%M%S"

        )

    )


    backup_name = (

        source.name

        + "_"

        + timestamp

    )


    destination = (

        BACKUP_DIRECTORY
        / backup_name

    )


    try:

        # ----------------------------------------------------
        # BACK UP DIRECTORY
        # ----------------------------------------------------

        if source.is_dir():

            shutil.copytree(

                source,

                destination

            )


        # ----------------------------------------------------
        # BACK UP FILE
        # ----------------------------------------------------

        else:

            shutil.copy2(

                source,

                destination

            )


        result["status"] = (
            "BACKED_UP"
        )

        result["backup"] = (
            str(destination)
        )

        result["message"] = (
            "Backup completed successfully"
        )


        logging.info(

            "Backup completed: %s",

            source

        )


    except PermissionError:

        result["status"] = (
            "PERMISSION_DENIED"
        )

        result["message"] = (
            "Permission denied"
        )


        logging.error(

            "Permission denied: %s",

            source

        )


    except Exception as error:

        result["status"] = (
            "FAILED"
        )

        result["message"] = (
            str(error)
        )


        logging.exception(

            "Backup failed: %s",

            source

        )


    return result


# ============================================================
# CREATE REPORT
# ============================================================

def create_report(
    results
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

        "total_items":
        len(results),

        "backed_up":
        sum(

            1

            for item in results

            if item["status"]
            == "BACKED_UP"

        ),

        "not_found":
        sum(

            1

            for item in results

            if item["status"]
            == "NOT_FOUND"

        ),

        "failed":
        sum(

            1

            for item in results

            if item["status"]
            not in [

                "BACKED_UP",

                "NOT_FOUND"

            ]

        ),

        "items":
        results

    }


    timestamp = (

        datetime.now().strftime(

            "%Y%m%d_%H%M%S"

        )

    )


    report_file = (

        REPORT_DIRECTORY

        / f"backup_report_{timestamp}.json"

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


    return report, report_file


# ============================================================
# DISPLAY RESULTS
# ============================================================

def display_results(

    results,

    report_file

):

    print("\n")

    print("=" * 70)

    print(

        "CONFIGURATION BACKUP"

    )

    print("=" * 70)


    print(

        "Operating System:",

        platform.system()

    )


    print(

        "Hostname:",

        HOSTNAME

    )


    print("\nRESULTS")


    for item in results:

        print(

            item["status"],

            "→",

            item["source"]

        )


    print(

        "\nReport saved to:",

        report_file

    )


    print(

        "Backup directory:",

        BACKUP_DIRECTORY

    )


# ============================================================
# MAIN
# ============================================================

def main():

    logging.info(

        "Configuration backup started"

    )


    configuration_files = (

        get_configuration_files()

    )


    results = []


    for source in configuration_files:

        result = (

            backup_configuration_item(

                source

            )

        )


        results.append(result)


    report, report_file = (

        create_report(

            results

        )

    )


    display_results(

        results,

        report_file

    )


    logging.info(

        "Configuration backup completed"

    )


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":

    try:

        main()


    except Exception as error:

        logging.exception(

            "Configuration backup failed"

        )


        print(

            "ERROR:",

            error

        )