import platform
import shutil
import subprocess
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
    / "deployment_automation_data"
    / HOSTNAME
)

CURRENT_APPLICATION = (
    DATA_DIRECTORY
    / "current_application"
)

NEW_APPLICATION = (
    DATA_DIRECTORY
    / "new_application"
)

BACKUP_DIRECTORY = (
    DATA_DIRECTORY
    / "backups"
)

LOG_DIRECTORY = (
    DATA_DIRECTORY
    / "logs"
)


# Create everything automatically

for directory in [

    CURRENT_APPLICATION,

    NEW_APPLICATION,

    BACKUP_DIRECTORY,

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

    / "deployment.log"

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
# AUTOMATIC TEST APPLICATION
# ============================================================

CURRENT_FILE = (

    CURRENT_APPLICATION

    / "application.txt"

)

NEW_FILE = (

    NEW_APPLICATION

    / "application.txt"

)


# Create old version automatically

if not CURRENT_FILE.exists():

    CURRENT_FILE.write_text(

        "Application Version 1\n"

    )


# Create new version automatically

if not NEW_FILE.exists():

    NEW_FILE.write_text(

        "Application Version 2\n"

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

        return result

    except Exception as error:

        logging.error(

            "Command failed: %s",

            error

        )

        return None


# ============================================================
# GET SERVICE
# ============================================================

def get_service_name():

    if platform.system() == "Linux":

        return "nginx"

    elif platform.system() == "Windows":

        return "Spooler"

    return None


# ============================================================
# CHECK SERVICE
# ============================================================

def check_service():

    service_name = (

        get_service_name()

    )


    if not service_name:

        return False


    if platform.system() == "Linux":

        result = run_command(

            [

                "systemctl",

                "is-active",

                service_name

            ]

        )


        return (

            result

            and result.stdout.strip()

            == "active"

        )


    elif platform.system() == "Windows":

        result = run_command(

            [

                "powershell",

                "-Command",

                f"(Get-Service "

                f"-Name '{service_name}').Status"

            ]

        )


        return (

            result

            and result.stdout.strip()

            == "Running"

        )


    return False


# ============================================================
# BACKUP OLD VERSION
# ============================================================

def backup_current_version():

    timestamp = (

        datetime.now().strftime(

            "%Y%m%d_%H%M%S"

        )

    )


    backup_path = (

        BACKUP_DIRECTORY

        / f"application_{timestamp}"

    )


    try:

        shutil.copytree(

            CURRENT_APPLICATION,

            backup_path

        )


        logging.info(

            "Old version backed up"

        )


        return backup_path


    except Exception as error:

        logging.error(

            "Backup failed: %s",

            error

        )


        return None


# ============================================================
# DEPLOY NEW VERSION
# ============================================================

def deploy_new_version():

    try:

        # Remove old application

        if CURRENT_APPLICATION.exists():

            shutil.rmtree(

                CURRENT_APPLICATION

            )


        # Create application directory again

        CURRENT_APPLICATION.mkdir(

            parents=True,

            exist_ok=True

        )


        # Copy new version

        for item in NEW_APPLICATION.iterdir():

            destination = (

                CURRENT_APPLICATION

                / item.name

            )


            if item.is_dir():

                shutil.copytree(

                    item,

                    destination

                )

            else:

                shutil.copy2(

                    item,

                    destination

                )


        logging.info(

            "New version deployed"

        )


        return True


    except Exception as error:

        logging.error(

            "Deployment failed: %s",

            error

        )


        return False


# ============================================================
# RESTART SERVICE
# ============================================================

def restart_service():

    service_name = (

        get_service_name()

    )


    if not service_name:

        return False


    if platform.system() == "Linux":

        result = run_command(

            [

                "sudo",

                "systemctl",

                "restart",

                service_name

            ]

        )


        return (

            result

            and result.returncode

            == 0

        )


    elif platform.system() == "Windows":

        result = run_command(

            [

                "powershell",

                "-Command",

                f"Restart-Service "

                f"-Name '{service_name}'"

            ]

        )


        return (

            result

            and result.returncode

            == 0

        )


    return False


# ============================================================
# ROLLBACK
# ============================================================

def rollback(

    backup_path

):

    try:

        if CURRENT_APPLICATION.exists():

            shutil.rmtree(

                CURRENT_APPLICATION

            )


        shutil.copytree(

            backup_path,

            CURRENT_APPLICATION

        )


        logging.warning(

            "Rollback completed"

        )


        return True


    except Exception as error:

        logging.error(

            "Rollback failed: %s",

            error

        )


        return False


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

        "\nCurrent application:"

    )


    print(

        CURRENT_FILE.read_text()

    )


    print(

        "Starting deployment..."

    )


    # --------------------------------------------------------
    # 1. BACKUP
    # --------------------------------------------------------

    backup_path = (

        backup_current_version()

    )


    if not backup_path:

        print(

            "ERROR: Backup failed"

        )

        return


    print(

        "Old version backed up"

    )


    # --------------------------------------------------------
    # 2. DEPLOY NEW VERSION
    # --------------------------------------------------------

    if not deploy_new_version():

        print(

            "ERROR: Deployment failed"

        )


        rollback(

            backup_path

        )


        return


    print(

        "New version deployed"

    )


    # --------------------------------------------------------
    # 3. RESTART SERVICE
    # --------------------------------------------------------

    if not restart_service():

        print(

            "WARNING: Service restart failed"

        )


        print(

            "Rolling back..."

        )


        rollback(

            backup_path

        )


        return


    print(

        "Service restarted"

    )


    # --------------------------------------------------------
    # 4. HEALTH CHECK
    # --------------------------------------------------------

    if check_service():

        print(

            "\nDEPLOYMENT SUCCESSFUL"

        )


        print(

            "Current application:"

        )


        print(

            CURRENT_FILE.read_text()

        )


        logging.info(

            "Deployment successful"

        )


    else:

        print(

            "\nHEALTH CHECK FAILED"

        )


        print(

            "Rolling back..."

        )


        rollback(

            backup_path

        )


        print(

            "Rollback completed"

        )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    try:

        main()

    except Exception as error:

        logging.exception(

            "Deployment automation failed"

        )

        print(

            "ERROR:",

            error

        )