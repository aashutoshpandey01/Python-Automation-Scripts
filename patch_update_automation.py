import platform
import subprocess
import logging
from pathlib import Path


# ============================================================
# AUTOMATIC DIRECTORIES
# ============================================================

BASE_DIRECTORY = Path(__file__).parent

HOSTNAME = platform.node()

DATA_DIRECTORY = (
    BASE_DIRECTORY
    / "patch_update_automation_data"
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
    / "patch_update.log"
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

def run_command(command):

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
# UBUNTU UPDATE AUTOMATION
# ============================================================

def ubuntu_update():

    print(
        "Checking Ubuntu updates..."
    )

    logging.info(
        "Running apt update"
    )


    # --------------------------------------------------------
    # REFRESH PACKAGE INFORMATION
    # --------------------------------------------------------

    update_result = run_command(
        [
            "sudo",
            "apt",
            "update"
        ]
    )


    if not update_result:

        print(
            "ERROR: apt command failed"
        )

        return


    if update_result.returncode != 0:

        print(
            "ERROR: apt update failed"
        )

        logging.error(
            update_result.stderr
        )

        return


    print(
        "Package information updated"
    )


    # --------------------------------------------------------
    # CHECK AVAILABLE UPDATES
    # --------------------------------------------------------

    upgrade_result = run_command(
        [
            "apt",
            "list",
            "--upgradable"
        ]
    )


    if not upgrade_result:

        return


    print(
        "\nAvailable updates:"
    )


    print(
        upgrade_result.stdout
    )


    logging.info(
        "Available updates checked"
    )


    # --------------------------------------------------------
    # ASK USER TO INSTALL
    # --------------------------------------------------------

    answer = input(
        "\nInstall updates? (yes/no): "
    )


    if answer.lower() == "yes":

        print(
            "\nInstalling updates..."
        )


        install_result = run_command(
            [
                "sudo",
                "apt",
                "upgrade",
                "-y"
            ]
        )


        if install_result.returncode == 0:

            print(
                "Updates installed successfully"
            )


            logging.info(
                "Ubuntu updates installed"
            )


        else:

            print(
                "Update installation failed"
            )


            logging.error(
                install_result.stderr
            )


    else:

        print(
            "Updates not installed"
        )


# ============================================================
# WINDOWS UPDATE AUTOMATION
# ============================================================

def windows_update():

    print(
        "Checking Windows updates..."
    )


    logging.info(
        "Checking Windows updates"
    )


    # --------------------------------------------------------
    # CHECK PSWINDOWSUPDATE MODULE
    # --------------------------------------------------------

    module_check = run_command(
        [
            "powershell",
            "-Command",
            "Get-Module "
            "-ListAvailable "
            "-Name "
            "PSWindowsUpdate"
        ]
    )


    if not module_check:

        return


    if not module_check.stdout.strip():

        print(
            "PSWindowsUpdate module "
            "is not installed"
        )


        print(
            "Install it with: "
            "Install-Module PSWindowsUpdate"
        )


        logging.warning(
            "PSWindowsUpdate module "
            "not installed"
        )


        return


    # --------------------------------------------------------
    # GET AVAILABLE UPDATES
    # --------------------------------------------------------

    update_result = run_command(
        [
            "powershell",
            "-Command",
            "Get-WindowsUpdate"
        ]
    )


    if not update_result:

        return


    print(
        "\nAvailable Windows updates:"
    )


    print(
        update_result.stdout
    )


    # --------------------------------------------------------
    # ASK USER TO INSTALL
    # --------------------------------------------------------

    answer = input(
        "\nInstall updates? (yes/no): "
    )


    if answer.lower() == "yes":

        install_result = run_command(
            [
                "powershell",
                "-Command",
                "Install-WindowsUpdate "
                "-AcceptAll "
                "-IgnoreReboot"
            ]
        )


        if install_result.returncode == 0:

            print(
                "Windows updates "
                "installed successfully"
            )


            logging.info(
                "Windows updates installed"
            )


        else:

            print(
                "Windows update installation "
                "failed"
            )


            logging.error(
                install_result.stderr
            )


    else:

        print(
            "Updates not installed"
        )


# ============================================================
# MAIN
# ============================================================

def main():

    operating_system = (
        platform.system()
    )


    print(
        "Operating System:",
        operating_system
    )


    print(
        "Hostname:",
        HOSTNAME
    )


    logging.info(
        "Patch automation started"
    )


    if operating_system == "Linux":

        ubuntu_update()


    elif operating_system == "Windows":

        windows_update()


    else:

        print(
            "Unsupported operating system"
        )


    logging.info(
        "Patch automation completed"
    )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    try:

        main()


    except Exception as error:

        logging.exception(
            "Patch automation failed"
        )


        print(
            "ERROR:",
            error
        )