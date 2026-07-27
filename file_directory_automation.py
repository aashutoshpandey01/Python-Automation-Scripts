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
    / "file_directory_automation_data"
    / HOSTNAME
)

BACKUP_DIRECTORY = (
    DATA_DIRECTORY
    / "backups"
)

ARCHIVE_DIRECTORY = (
    DATA_DIRECTORY
    / "archives"
)

REPORT_DIRECTORY = (
    DATA_DIRECTORY
    / "reports"
)

LOG_DIRECTORY = (
    DATA_DIRECTORY
    / "logs"
)


# Delete files older than this many days

DELETE_FILES_OLDER_THAN_DAYS = 30


# ============================================================
# CREATE DIRECTORIES
# ============================================================

for directory in [

    BACKUP_DIRECTORY,

    ARCHIVE_DIRECTORY,

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

    / "file_directory_automation.log"

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
# GET TARGET DIRECTORIES
# ============================================================

def get_target_directories():

    operating_system = (

        platform.system()

    )


    if operating_system == "Windows":

        return [

            Path(

                r"C:\Temp"

            ),

            Path(

                r"C:\Logs"

            )


        ]


    elif operating_system == "Linux":

        return [

            Path(

                "/tmp"

            ),

            Path(

                "/var/log"

            )


        ]


    else:

        return []


# ============================================================
# FIND OLD FILES
# ============================================================

def find_old_files(

    directory,

    older_than_days

):

    old_files = []


    if not directory.exists():

        logging.warning(

            "Directory not found: %s",

            directory

        )


        return old_files


    cutoff_time = (

        datetime.now()

        - timedelta(

            days=older_than_days

        )

    )


    for item in directory.iterdir():

        try:

            if item.is_file():

                modified_time = (

                    datetime.fromtimestamp(

                        item.stat().st_mtime

                    )

                )


                if modified_time < cutoff_time:

                    old_files.append(

                        item

                    )


        except (

            PermissionError,

            FileNotFoundError

        ) as error:

            logging.warning(

                "Could not inspect %s: %s",

                item,

                error

            )


    return old_files


# ============================================================
# DELETE OLD FILES
# ============================================================

def delete_old_files(

    files

):

    results = []


    for file in files:

        try:

            file.unlink()


            results.append(

                {

                    "file":

                    str(file),

                    "status":

                    "DELETED"

                }

            )


            logging.info(

                "Deleted old file: %s",

                file

            )


        except PermissionError:

            results.append(

                {

                    "file":

                    str(file),

                    "status":

                    "PERMISSION_DENIED"

                }

            )


        except FileNotFoundError:

            results.append(

                {

                    "file":

                    str(file),

                    "status":

                    "NOT_FOUND"

                }

            )


    return results


# ============================================================
# COPY FILES
# ============================================================

def copy_file(

    source_file

):

    if not source_file.exists():

        return {

            "source":

            str(source_file),

            "status":

            "NOT_FOUND"

        }


    try:

        destination = (

            BACKUP_DIRECTORY

            / source_file.name

        )


        shutil.copy2(

            source_file,

            destination

        )


        logging.info(

            "Copied file: %s",

            source_file

        )


        return {

            "source":

            str(source_file),

            "destination":

            str(destination),

            "status":

            "COPIED"

        }


    except Exception as error:

        return {

            "source":

            str(source_file),

            "status":

            "FAILED",

            "message":

            str(error)

        }


# ============================================================
# MOVE FILES
# ============================================================

def move_file(

    source_file

):

    if not source_file.exists():

        return {

            "source":

            str(source_file),

            "status":

            "NOT_FOUND"

        }


    try:

        destination = (

            ARCHIVE_DIRECTORY

            / source_file.name

        )


        shutil.move(

            str(source_file),

            str(destination)

        )


        logging.info(

            "Moved file: %s",

            source_file

        )


        return {

            "source":

            str(source_file),

            "destination":

            str(destination),

            "status":

            "MOVED"

        }


    except Exception as error:

        return {

            "source":

            str(source_file),

            "status":

            "FAILED",

            "message":

            str(error)

        }


# ============================================================
# RENAME FILE
# ============================================================

def rename_file(

    source_file,

    new_name

):

    if not source_file.exists():

        return {

            "source":

            str(source_file),

            "status":

            "NOT_FOUND"

        }


    try:

        new_path = (

            source_file.parent

            / new_name

        )


        source_file.rename(

            new_path

        )


        logging.info(

            "Renamed %s to %s",

            source_file,

            new_path

        )


        return {

            "source":

            str(source_file),

            "destination":

            str(new_path),

            "status":

            "RENAMED"

        }


    except Exception as error:

        return {

            "source":

            str(source_file),

            "status":

            "FAILED",

            "message":

            str(error)

        }


# ============================================================
# CREATE ZIP ARCHIVE
# ============================================================

def create_archive():

    archive_name = (

        "backup_"

        + datetime.now().strftime(

            "%Y%m%d_%H%M%S"

        )

    )


    archive_path = (

        ARCHIVE_DIRECTORY

        / archive_name

    )


    try:

        shutil.make_archive(

            str(archive_path),

            "zip",

            str(BACKUP_DIRECTORY)

        )


        logging.info(

            "Archive created: %s.zip",

            archive_path

        )


        return {

            "archive":

            str(archive_path)

            + ".zip",

            "status":

            "ARCHIVED"

        }


    except Exception as error:

        return {

            "status":

            "FAILED",

            "message":

            str(error)

        }


# ============================================================
# CREATE REPORT
# ============================================================

def create_report(

    old_files,

    delete_results,

    archive_result

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

        "delete_threshold_days":

        DELETE_FILES_OLDER_THAN_DAYS,

        "old_files_found":

        len(old_files),

        "files_deleted":

        len(

            [

                item

                for item in delete_results

                if item["status"]

                == "DELETED"

            ]

        ),

        "archive":

        archive_result,

        "deleted_files":

        delete_results

    }


    timestamp = (

        datetime.now().strftime(

            "%Y%m%d_%H%M%S"

        )

    )


    report_file = (

        REPORT_DIRECTORY

        / f"file_automation_{timestamp}.json"

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

    old_files,

    delete_results,

    archive_result,

    report_file

):

    print("\n")

    print("=" * 70)

    print(

        "FILE AND DIRECTORY AUTOMATION"

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


    print(

        "Old Files Found:",

        len(old_files)

    )


    print(

        "Files Deleted:",

        len(

            [

                item

                for item in delete_results

                if item["status"]

                == "DELETED"

            ]

        )

    )


    print(

        "Archive Status:",

        archive_result["status"]

    )


    print(

        "Report Saved:",

        report_file

    )


# ============================================================
# MAIN
# ============================================================

def main():

    logging.info(

        "File automation started"

    )


    target_directories = (

        get_target_directories()

    )


    all_old_files = []


    for directory in (

        target_directories

    ):

        old_files = (

            find_old_files(

                directory,

                DELETE_FILES_OLDER_THAN_DAYS

            )

        )


        all_old_files.extend(

            old_files

        )


    delete_results = (

        delete_old_files(

            all_old_files

        )

    )


    archive_result = (

        create_archive()

    )


    report_file = (

        create_report(

            all_old_files,

            delete_results,

            archive_result

        )

    )


    display_results(

        all_old_files,

        delete_results,

        archive_result,

        report_file

    )


    logging.info(

        "File automation completed"

    )


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":

    try:

        main()


    except Exception as error:

        logging.exception(

            "File automation failed"

        )


        print(

            "ERROR:",

            error

        )