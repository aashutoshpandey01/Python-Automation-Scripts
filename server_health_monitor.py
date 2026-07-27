import platform
import socket
import shutil
import psutil
import logging
import json
from pathlib import Path
from datetime import datetime


# ============================================================
# CONFIGURATION
# ============================================================

CPU_WARNING_THRESHOLD = 80
CPU_CRITICAL_THRESHOLD = 90

MEMORY_WARNING_THRESHOLD = 80
MEMORY_CRITICAL_THRESHOLD = 90

DISK_WARNING_THRESHOLD = 80
DISK_CRITICAL_THRESHOLD = 90


# ============================================================
# PATHS
# ============================================================

BASE_DIRECTORY = Path(__file__).parent

HOSTNAME = socket.gethostname()

SERVER_DIRECTORY = (
    BASE_DIRECTORY
    / "server_data"
    / HOSTNAME
)

REPORT_DIRECTORY = (
    SERVER_DIRECTORY
    / "reports"
)

LOG_DIRECTORY = (
    SERVER_DIRECTORY
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
    / "server_health.log"
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
# SYSTEM INFORMATION
# ============================================================

def get_system_information():

    return {

        "hostname": socket.gethostname(),

        "operating_system":
        platform.system(),

        "platform":
        platform.platform(),

        "processor":
        platform.processor(),

        "python_version":
        platform.python_version(),

        "boot_time":
        datetime.fromtimestamp(
            psutil.boot_time()
        ).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

    }


# ============================================================
# CPU CHECK
# ============================================================

def check_cpu():

    cpu_usage = psutil.cpu_percent(
        interval=1
    )


    if cpu_usage >= CPU_CRITICAL_THRESHOLD:

        status = "CRITICAL"


    elif cpu_usage >= CPU_WARNING_THRESHOLD:

        status = "WARNING"


    else:

        status = "HEALTHY"


    return {

        "usage_percentage":
        cpu_usage,

        "status":
        status

    }


# ============================================================
# MEMORY CHECK
# ============================================================

def check_memory():

    memory = psutil.virtual_memory()


    total_gb = (
        memory.total
        / (1024 ** 3)
    )

    used_gb = (
        memory.used
        / (1024 ** 3)
    )

    available_gb = (
        memory.available
        / (1024 ** 3)
    )


    usage_percentage = memory.percent


    if usage_percentage >= MEMORY_CRITICAL_THRESHOLD:

        status = "CRITICAL"


    elif usage_percentage >= MEMORY_WARNING_THRESHOLD:

        status = "WARNING"


    else:

        status = "HEALTHY"


    return {

        "total_gb":
        round(total_gb, 2),

        "used_gb":
        round(used_gb, 2),

        "available_gb":
        round(available_gb, 2),

        "usage_percentage":
        usage_percentage,

        "status":
        status

    }


# ============================================================
# GET VOLUMES / FILESYSTEMS
# ============================================================

def get_volumes():

    operating_system = platform.system()


    if operating_system == "Windows":

        return [

            "C:\\",
            "D:\\",
            "E:\\",
            "F:\\"

        ]


    elif operating_system == "Linux":

        return [

            "/",
            "/home",
            "/var",
            "/mnt"

        ]


    else:

        return []


# ============================================================
# DISK CHECK
# ============================================================

def check_disk(volume):

    try:

        total, used, free = (
            shutil.disk_usage(volume)
        )


        total_gb = (
            total
            / (1024 ** 3)
        )

        used_gb = (
            used
            / (1024 ** 3)
        )

        free_gb = (
            free
            / (1024 ** 3)
        )


        usage_percentage = (
            used
            / total
        ) * 100


        if usage_percentage >= DISK_CRITICAL_THRESHOLD:

            status = "CRITICAL"


        elif usage_percentage >= DISK_WARNING_THRESHOLD:

            status = "WARNING"


        else:

            status = "HEALTHY"


        return {

            "volume":
            volume,

            "total_gb":
            round(total_gb, 2),

            "used_gb":
            round(used_gb, 2),

            "free_gb":
            round(free_gb, 2),

            "usage_percentage":
            round(
                usage_percentage,
                2
            ),

            "status":
            status

        }


    except FileNotFoundError:

        return {

            "volume":
            volume,

            "status":
            "NOT_FOUND",

            "message":
            "Volume not found - skipped"

        }


    except PermissionError:

        return {

            "volume":
            volume,

            "status":
            "PERMISSION_DENIED",

            "message":
            "Permission denied"

        }


# ============================================================
# OVERALL HEALTH STATUS
# ============================================================

def get_overall_status(

    cpu_result,
    memory_result,
    disk_results

):

    statuses = [

        cpu_result["status"],

        memory_result["status"]

    ]


    for disk in disk_results:

        statuses.append(
            disk["status"]
        )


    if "CRITICAL" in statuses:

        return "CRITICAL"


    elif "WARNING" in statuses:

        return "WARNING"


    else:

        return "HEALTHY"


# ============================================================
# RUN HEALTH CHECK
# ============================================================

def run_health_check():

    logging.info(
        "Server health check started"
    )


    system_information = (
        get_system_information()
    )


    cpu_result = (
        check_cpu()
    )


    memory_result = (
        check_memory()
    )


    disk_results = []


    for volume in get_volumes():

        result = check_disk(
            volume
        )


        disk_results.append(
            result
        )


    overall_status = (
        get_overall_status(

            cpu_result,

            memory_result,

            disk_results

        )
    )


    health_report = {

        "timestamp":
        datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        ),

        "overall_status":
        overall_status,

        "system":
        system_information,

        "cpu":
        cpu_result,

        "memory":
        memory_result,

        "disks":
        disk_results

    }


    return health_report


# ============================================================
# SAVE JSON REPORT
# ============================================================

def save_report(health_report):

    timestamp = (
        datetime.now().strftime(
            "%Y-%m-%d_%H-%M-%S"
        )
    )


    report_file = (

        REPORT_DIRECTORY
        / f"health_{timestamp}.json"

    )


    with open(
        report_file,
        "w"
    ) as file:

        json.dump(

            health_report,

            file,

            indent=4

        )


    return report_file


# ============================================================
# DISPLAY RESULT
# ============================================================

def display_result(health_report):

    print("\n")
    print("=" * 60)

    print(
        "SERVER HEALTH MONITORING"
    )

    print("=" * 60)


    system = (
        health_report["system"]
    )


    print(
        "Hostname:",
        system["hostname"]
    )


    print(
        "Operating System:",
        system["operating_system"]
    )


    print(
        "Overall Status:",
        health_report[
            "overall_status"
        ]
    )


    print("\nCPU")

    print(
        "Usage:",
        health_report[
            "cpu"
        ][
            "usage_percentage"
        ],
        "%"
    )


    print(
        "Status:",
        health_report[
            "cpu"
        ][
            "status"
        ]
    )


    print("\nMEMORY")

    print(
        "Usage:",
        health_report[
            "memory"
        ][
            "usage_percentage"
        ],
        "%"
    )


    print(
        "Status:",
        health_report[
            "memory"
        ][
            "status"
        ]
    )


    print("\nDISKS")


    for disk in health_report["disks"]:

        print(
            "\nVolume:",
            disk["volume"]
        )


        print(
            "Status:",
            disk["status"]
        )


        if "usage_percentage" in disk:

            print(
                "Usage:",
                disk[
                    "usage_percentage"
                ],
                "%"
            )


            print(
                "Free:",
                disk[
                    "free_gb"
                ],
                "GB"
            )


        else:

            print(
                disk["message"]
            )


# ============================================================
# MAIN
# ============================================================

def main():

    try:

        health_report = (
            run_health_check()
        )


        report_file = (
            save_report(
                health_report
            )
        )


        display_result(
            health_report
        )


        print(
            "\nReport saved at:",
            report_file
        )


        logging.info(
            "Server health check completed"
        )


        if health_report[
            "overall_status"
        ] == "CRITICAL":

            logging.critical(
                "Server health is CRITICAL"
            )


        elif health_report[
            "overall_status"
        ] == "WARNING":

            logging.warning(
                "Server health is WARNING"
            )


    except Exception as error:

        logging.exception(
            "Health check failed"
        )


        print(
            "ERROR:",
            error
        )


# ============================================================
# START PROGRAM
# ============================================================

if __name__ == "__main__":

    main()