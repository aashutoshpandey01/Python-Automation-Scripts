import platform
import psutil
import smtplib
import json
import logging
import urllib.request
import urllib.error

from pathlib import Path
from datetime import datetime, timezone
from email.message import EmailMessage


# ============================================================
# BASIC CONFIGURATION
# ============================================================

HOSTNAME = platform.node()

BASE_DIRECTORY = Path(__file__).parent

DATA_DIRECTORY = (
    BASE_DIRECTORY
    / "monitoring_alerting_data"
    / HOSTNAME
)

LOG_DIRECTORY = DATA_DIRECTORY / "logs"

REPORT_DIRECTORY = DATA_DIRECTORY / "reports"

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

LOG_FILE = LOG_DIRECTORY / "monitoring_alerting.log"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


# ============================================================
# THRESHOLDS
# ============================================================

CPU_WARNING_THRESHOLD = 80

RAM_WARNING_THRESHOLD = 80

DISK_WARNING_THRESHOLD = 80


# ============================================================
# EMAIL CONFIGURATION
# ============================================================

# The email that receives alerts
ALERT_EMAIL = "exoticaashu325@gmail.com"


# The Gmail account sending the email
SENDER_EMAIL = "exoticaashu325@gmail.com"


# Paste your NEW Gmail App Password here locally.
#
# Do NOT share it publicly.
#
SENDER_PASSWORD = "ibldkjvbzqnwkagt"


SMTP_SERVER = "smtp.gmail.com"

SMTP_PORT = 587


# ============================================================
# MICROSOFT TEAMS
# ============================================================

TEAMS_ENABLED = False

TEAMS_WEBHOOK_URL = ""


# ============================================================
# SLACK
# ============================================================

SLACK_ENABLED = False

SLACK_WEBHOOK_URL = ""


# ============================================================
# GENERIC WEBHOOK
# ============================================================

WEBHOOK_ENABLED = False

WEBHOOK_URL = ""


# ============================================================
# TICKETING SYSTEM
# ============================================================

TICKETING_ENABLED = False

TICKETING_API_URL = ""

TICKETING_API_TOKEN = ""


# ============================================================
# CPU CHECK
# ============================================================

def check_cpu():

    cpu_usage = psutil.cpu_percent(
        interval=1
    )

    if cpu_usage >= CPU_WARNING_THRESHOLD:

        status = "WARNING: High CPU usage"

    else:

        status = "OK"

    return {

        "usage_percent": cpu_usage,

        "status": status

    }


# ============================================================
# MEMORY CHECK
# ============================================================

def check_memory():

    memory = psutil.virtual_memory()

    memory_usage = memory.percent

    if memory_usage >= RAM_WARNING_THRESHOLD:

        status = "WARNING: High memory usage"

    else:

        status = "OK"

    return {

        "usage_percent": memory_usage,

        "total_gb": round(
            memory.total / (1024 ** 3),
            2
        ),

        "used_gb": round(
            memory.used / (1024 ** 3),
            2
        ),

        "available_gb": round(
            memory.available / (1024 ** 3),
            2
        ),

        "status": status

    }


# ============================================================
# DISK CHECK
# ============================================================

def check_disk():

    if platform.system() == "Windows":

        drive = "C:\\"

    else:

        drive = "/"


    disk = psutil.disk_usage(drive)

    disk_usage = disk.percent

    if disk_usage >= DISK_WARNING_THRESHOLD:

        status = "WARNING: High disk usage"

    else:

        status = "OK"

    return {

        "drive": drive,

        "usage_percent": disk_usage,

        "total_gb": round(
            disk.total / (1024 ** 3),
            2
        ),

        "used_gb": round(
            disk.used / (1024 ** 3),
            2
        ),

        "free_gb": round(
            disk.free / (1024 ** 3),
            2
        ),

        "status": status

    }


# ============================================================
# CREATE ALERTS
# ============================================================

def create_alerts(
    cpu_data,
    memory_data,
    disk_data
):

    alerts = []


    if cpu_data["status"] != "OK":

        alerts.append(
            f"CPU alert on {HOSTNAME}: "
            f"{cpu_data['usage_percent']}%"
        )


    if memory_data["status"] != "OK":

        alerts.append(
            f"Memory alert on {HOSTNAME}: "
            f"{memory_data['usage_percent']}%"
        )


    if disk_data["status"] != "OK":

        alerts.append(
            f"Disk alert on {HOSTNAME}: "
            f"{disk_data['usage_percent']}%"
        )


    return alerts


# ============================================================
# EMAIL ALERT
# ============================================================

def send_email_alert(alerts):

    if not alerts:

        return "No alert"


    if (

        not SENDER_EMAIL

        or not SENDER_PASSWORD

        or SENDER_PASSWORD
        == "PASTE_NEW_APP_PASSWORD_HERE"

    ):

        print(
            "\nEmail: Not configured."
        )

        print(
            "Please add your Gmail App Password."
        )

        return "Not configured"


    message = EmailMessage()


    message["Subject"] = (

        f"SERVER ALERT - {HOSTNAME}"

    )


    message["From"] = SENDER_EMAIL

    message["To"] = ALERT_EMAIL


    message.set_content(

        (

            f"Monitoring alert detected "
            f"on {HOSTNAME}.\n\n"

            + "\n".join(alerts)

            + "\n\n"

            f"Operating System: "
            f"{platform.system()}\n"

            f"Time: "
            f"{datetime.now().isoformat()}"

        )

    )


    try:

        print(
            "\nEmail: Connecting to Gmail..."
        )


        with smtplib.SMTP(
            SMTP_SERVER,
            SMTP_PORT
        ) as server:

            server.starttls()


            server.login(
                SENDER_EMAIL,
                SENDER_PASSWORD
            )


            server.send_message(
                message
            )


        print(
            "\nEmail: Alert sent successfully to:"
        )

        print(
            ALERT_EMAIL
        )


        logging.info(
            "Email alert sent successfully"
        )


        return "Sent"


    except Exception as error:

        print(
            "\nEmail: Failed"
        )

        print(
            "Reason:",
            error
        )


        logging.error(
            "Email sending failed: %s",
            error
        )


        return "Failed"


# ============================================================
# GENERIC WEBHOOK
# ============================================================

def send_webhook(
    platform_name,
    webhook_url,
    message
):

    if not webhook_url:

        print(
            f"\n{platform_name}: "
            "Not configured."
        )

        print(
            f"Please configure "
            f"{platform_name} to enable "
            f"this notification method."
        )

        return "Not configured"


    payload = json.dumps({

        "hostname": HOSTNAME,

        "message": message,

        "timestamp": (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

    }).encode("utf-8")


    request = urllib.request.Request(

        webhook_url,

        data=payload,

        headers={
            "Content-Type":
            "application/json"
        },

        method="POST"

    )


    try:

        with urllib.request.urlopen(
            request,
            timeout=10
        ) as response:

            print(
                f"\n{platform_name}: "
                "Alert sent."
            )


            return (
                f"Sent - HTTP "
                f"{response.status}"
            )


    except urllib.error.URLError as error:

        print(
            f"\n{platform_name}: Failed."
        )


        logging.error(
            "%s failed: %s",
            platform_name,
            error
        )


        return "Failed"


# ============================================================
# MICROSOFT TEAMS
# ============================================================

def send_teams_alert(alerts):

    if not TEAMS_ENABLED:

        print(
            "\nMicrosoft Teams: "
            "Not configured."
        )

        print(
            "Please configure Teams "
            "to enable this method."
        )

        return "Not configured"


    return send_webhook(

        "Microsoft Teams",

        TEAMS_WEBHOOK_URL,

        "\n".join(alerts)

    )


# ============================================================
# SLACK
# ============================================================

def send_slack_alert(alerts):

    if not SLACK_ENABLED:

        print(
            "\nSlack: Not configured."
        )

        print(
            "Please configure Slack "
            "to enable this method."
        )

        return "Not configured"


    return send_webhook(

        "Slack",

        SLACK_WEBHOOK_URL,

        "\n".join(alerts)

    )


# ============================================================
# GENERIC WEBHOOK
# ============================================================

def send_generic_webhook(alerts):

    if not WEBHOOK_ENABLED:

        print(
            "\nGeneric Webhook: "
            "Not configured."
        )

        print(
            "Please configure a webhook "
            "to enable this method."
        )

        return "Not configured"


    return send_webhook(

        "Generic Webhook",

        WEBHOOK_URL,

        "\n".join(alerts)

    )


# ============================================================
# TICKETING SYSTEM
# ============================================================

def create_ticket(alerts):

    if not TICKETING_ENABLED:

        print(
            "\nTicketing System: "
            "Not configured."
        )

        print(
            "Please configure a ticketing API "
            "to enable this method."
        )

        return "Not configured"


    if not TICKETING_API_URL:

        print(
            "\nTicketing System: "
            "API URL missing."
        )

        return "Not configured"


    payload = json.dumps({

        "title": (
            f"Monitoring Alert - "
            f"{HOSTNAME}"
        ),

        "description": "\n".join(alerts)

    }).encode("utf-8")


    headers = {

        "Content-Type":
        "application/json"

    }


    if TICKETING_API_TOKEN:

        headers["Authorization"] = (

            f"Bearer "
            f"{TICKETING_API_TOKEN}"

        )


    request = urllib.request.Request(

        TICKETING_API_URL,

        data=payload,

        headers=headers,

        method="POST"

    )


    try:

        with urllib.request.urlopen(

            request,

            timeout=10

        ) as response:

            print(
                "\nTicketing System: "
                "Ticket request sent."
            )


            return (
                f"Sent - HTTP "
                f"{response.status}"
            )


    except Exception as error:

        print(
            "\nTicketing System: Failed."
        )


        logging.error(
            "Ticketing system failed: %s",
            error
        )


        return "Failed"


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "Monitoring and Alerting"
    )


    print(
        "Operating System:",
        platform.system()
    )


    print(
        "Hostname:",
        HOSTNAME
    )


    # --------------------------------------------------------
    # CHECK SYSTEM
    # --------------------------------------------------------

    cpu_data = check_cpu()

    memory_data = check_memory()

    disk_data = check_disk()


    print(

        "\nCPU:",

        cpu_data["usage_percent"],

        "% →",

        cpu_data["status"]

    )


    print(

        "Memory:",

        memory_data["usage_percent"],

        "% →",

        memory_data["status"]

    )


    print(

        "Disk:",

        disk_data["usage_percent"],

        "% →",

        disk_data["status"]

    )


    # --------------------------------------------------------
    # CREATE ALERTS
    # --------------------------------------------------------

    alerts = create_alerts(

        cpu_data,

        memory_data,

        disk_data

    )


    notification_results = {}


    if alerts:

        print(
            "\nALERTS DETECTED"
        )


        for alert in alerts:

            print(
                alert
            )


        # ----------------------------------------------------
        # EMAIL
        # ----------------------------------------------------

        notification_results[
            "email"
        ] = send_email_alert(
            alerts
        )


        # ----------------------------------------------------
        # MICROSOFT TEAMS
        # ----------------------------------------------------

        notification_results[
            "microsoft_teams"
        ] = send_teams_alert(
            alerts
        )


        # ----------------------------------------------------
        # SLACK
        # ----------------------------------------------------

        notification_results[
            "slack"
        ] = send_slack_alert(
            alerts
        )


        # ----------------------------------------------------
        # GENERIC WEBHOOK
        # ----------------------------------------------------

        notification_results[
            "generic_webhook"
        ] = send_generic_webhook(
            alerts
        )


        # ----------------------------------------------------
        # TICKETING SYSTEM
        # ----------------------------------------------------

        notification_results[
            "ticketing_system"
        ] = create_ticket(
            alerts
        )


    else:

        print(
            "\nNo alerts detected."
        )


    # --------------------------------------------------------
    # SAVE JSON REPORT
    # --------------------------------------------------------

    report = {

        "timestamp": (

            datetime.now(
                timezone.utc
            ).isoformat()

        ),

        "hostname": HOSTNAME,

        "operating_system": (
            platform.system()
        ),

        "monitoring": {

            "cpu": cpu_data,

            "memory": memory_data,

            "disk": disk_data

        },

        "alerts": alerts,

        "alert_recipient": ALERT_EMAIL,

        "notification_results": (
            notification_results
        )

    }


    timestamp = datetime.now().strftime(

        "%Y%m%d_%H%M%S"

    )


    report_file = (

        REPORT_DIRECTORY

        / f"monitoring_report_{timestamp}.json"

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
        "\nReport saved:"
    )


    print(
        report_file
    )


    logging.info(
        "Monitoring and alerting completed."
    )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    try:

        main()


    except Exception as error:

        logging.exception(
            "Monitoring script failed."
        )


        print(
            "ERROR:",
            error
        )