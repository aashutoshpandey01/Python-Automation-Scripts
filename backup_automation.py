import platform
import shutil
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIRECTORY = Path(__file__).parent

HOSTNAME = platform.node()

DATA_DIRECTORY = (
    BASE_DIRECTORY
    / "backup_automation_data"
    / HOSTNAME
)

BACKUP_DIRECTORY = (
    DATA_DIRECTORY
    / "backups"
)

REPORT_DIRECTORY = (
    DATA_DIRECTORY
    / "reports"
)

LOG_DIRECTORY = (
    DATA_DIRECTORY
    / "logs"
)


# Delete backups older than this many days

DELETE_BACKUPS_OLDER_THAN_DAYS = 30


# ============================================================
# CREATE DIRECTORIES
# ============================================================

for directory in [

    BACKUP_DIRECTORY,

    REPORT_DIRECTORY,

    LOG_DIRECTORY

]:

    directory.mkdir(

        parents=True,

        exist_ok=True

    )


# ============================================================
# LOGGING
# ============================================================

LOG_FILE = (

    LOG_DIRECTORY

    / "backup_automation.log"

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
# SELECT IMPORTANT DATA
# ============================================================

def get_backup_sources():

    operating_system = (

        platform.system()

    )


    if operating_system == "Linux":

        return [

            Path(

                "/etc/ssh"

            ),

            Path(

                "/etc/systemd/system"

            ),

            Path(

                "/var/log"

            )

        ]


    elif operating_system == "Windows":

        return [

            Path(

                r"C:\Windows\System32\drivers\etc"

            ),

            Path(

                r"C:\Windows\System32\GroupPolicy"

            )

        ]


    else:

        return []


# ============================================================
# CREATE TIMESTAMP
# ============================================================

def get_timestamp():

    return datetime.now().strftime(

        "%Y%m%d_%H%M%S"

    )


# ============================================================
# BACKUP ONE SOURCE
# ============================================================

def create_backup(

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


    if not source.exists():

        result["status"] = (

            "NOT_FOUND"

        )

        result["message"] = (

            "Source does not exist"

        )


        logging.warning(

            "Backup source not found: %s",

            source

        )


        return result


    timestamp = (

        get_timestamp()

    )


    backup_name = (

        source.name

        + "_"

        + timestamp

    )


    archive_base_path = (

        BACKUP_DIRECTORY

        / backup_name

    )


    try:

        archive_path = (

            shutil.make_archive(

                str(

                    archive_base_path

                ),

                "zip",

                root_dir=source.parent,

                base_dir=source.name

            )

        )


        result["status"] = (

            "BACKUP_CREATED"

        )

        result["backup"] = (

            archive_path

        )

        result["message"] = (

            "Backup created successfully"

        )


        logging.info(

            "Backup created: %s",

            archive_path

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
# DELETE OLD BACKUPS
# ============================================================

def delete_old_backups():

    deleted_backups = []

    cutoff_time = (

        datetime.now()

        - timedelta(

            days=

            DELETE_BACKUPS_OLDER_THAN_DAYS

        )

    )


    for backup in (

        BACKUP_DIRECTORY.glob(

            "*.zip"

        )

    ):

        try:

            modified_time = (

                datetime.fromtimestamp(

                    backup.stat().st_mtime

                )

            )


            if modified_time < cutoff_time:

                backup.unlink()


                deleted_backups.append(

                    str(

                        backup

                    )

                )


                logging.info(

                    "Deleted old backup: %s",

                    backup

                )


        except PermissionError:

            logging.warning(

                "Permission denied: %s",

                backup

            )


        except FileNotFoundError:

            continue


    return deleted_backups


# ============================================================
# CREATE REPORT
# ============================================================

def create_report(

    backup_results,

    deleted_backups

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

        "backup_retention_days":

        DELETE_BACKUPS_OLDER_THAN_DAYS,

        "total_sources":

        len(

            backup_results

        ),

        "successful_backups":

        len(

            [

                item

                for item in backup_results

                if item["status"]

                == "BACKUP_CREATED"

            ]

        ),

        "failed_backups":

        len(

            [

                item

                for item in backup_results

                if item["status"]

                == "FAILED"

            ]

        ),

        "deleted_old_backups":

        len(

            deleted_backups

        ),

        "backup_results":

        backup_results,

        "deleted_backups":

        deleted_backups

    }


    timestamp = (

        get_timestamp()

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


    return report_file


# ============================================================
# DISPLAY RESULTS
# ============================================================

def display_results(

    backup_results,

    deleted_backups,

    report_file

):

    print("\n")

    print("=" * 70)

    print(

        "ENTERPRISE BACKUP AUTOMATION"

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


    print("\nBACKUP RESULTS")


    for result in backup_results:

        print(

            result["status"],

            "→",

            result["source"]

        )


    print(

        "\nOld backups deleted:",

        len(

            deleted_backups

        )

    )


    print(

        "Report saved to:",

        report_file

    )


# ============================================================
# MAIN
# ============================================================

def main():

    logging.info(

        "Backup automation started"

    )


    backup_sources = (

        get_backup_sources()

    )


    backup_results = []


    for source in (

        backup_sources

    ):

        result = (

            create_backup(

                source

            )

        )


        backup_results.append(

            result

        )


    deleted_backups = (

        delete_old_backups()

    )


    report_file = (

        create_report(

            backup_results,

            deleted_backups

        )

    )


    display_results(

        backup_results,

        deleted_backups,

        report_file

    )


    logging.info(

        "Backup automation completed"

    )


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":

    try:

        main()


    except Exception as error:

        logging.exception(

            "Backup automation failed"

        )


        print(

            "ERROR:",

            error

        )