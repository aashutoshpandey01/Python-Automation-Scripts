import ssl
import socket
import json
import logging
import smtplib
import urllib.request
import urllib.error

from pathlib import Path
from datetime import datetime, timezone

from email.message import EmailMessage


# ============================================================
# AUTOMATIC DIRECTORIES
# ============================================================

BASE_DIRECTORY = Path(__file__).parent

HOSTNAME = socket.gethostname()

DATA_DIRECTORY = (
    BASE_DIRECTORY
    / "certificate_domain_monitoring_data"
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
    / "certificate_domain_monitoring.log"
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

DOMAINS = [

    "google.com",

    "github.com"

]


CERTIFICATE_WARNING_DAYS = 30


# ============================================================
# EMAIL CONFIGURATION
# ============================================================

EMAIL_ENABLED = False


SMTP_SERVER = "smtp.gmail.com"

SMTP_PORT = 587

SENDER_EMAIL = "your-email@gmail.com"

SENDER_PASSWORD = "your-app-password"

RECEIVER_EMAIL = "your-email@gmail.com"


# ============================================================
# SSL CERTIFICATE CHECK
# ============================================================

def check_ssl_certificate(

    domain

):

    try:

        context = (

            ssl.create_default_context()

        )


        with socket.create_connection(

            (

                domain,

                443

            ),

            timeout=10

        ) as connection:

            with context.wrap_socket(

                connection,

                server_hostname=domain

            ) as secure_socket:

                certificate = (

                    secure_socket.getpeercert()

                )


        expiry_date = (

            datetime.strptime(

                certificate["notAfter"],

                "%b %d %H:%M:%S %Y %Z"

            )

        )


        days_remaining = (

            expiry_date

            - datetime.now()

        ).days


        if days_remaining <= 0:

            status = (

                "CRITICAL: Certificate expired"

            )


        elif (

            days_remaining

            <= CERTIFICATE_WARNING_DAYS

        ):

            status = (

                "WARNING: Certificate expires soon"

            )


        else:

            status = (

                "OK: Certificate valid"

            )


        return {

            "domain": domain,

            "expiry_date": (

                str(expiry_date)

            ),

            "days_remaining": (

                days_remaining

            ),

            "status": status

        }


    except Exception as error:

        return {

            "domain": domain,

            "status": (

                "ERROR: Certificate check failed"

            ),

            "error": str(error)

        }


# ============================================================
# DNS RECORD CHECK
# ============================================================

def check_dns_records(

    domain

):

    results = {}


    # --------------------------------------------------------
    # A RECORD
    # --------------------------------------------------------

    try:

        ipv4_addresses = (

            socket.gethostbyname_ex(

                domain

            )[2]

        )


        results["A"] = (

            ipv4_addresses

        )


    except socket.gaierror:

        results["A"] = (

            "A record not resolved"

        )


    # --------------------------------------------------------
    # CNAME / BASIC DNS NAME
    # --------------------------------------------------------

    try:

        canonical_name = (

            socket.getfqdn(

                domain

            )

        )


        results["canonical_name"] = (

            canonical_name

        )


    except Exception as error:

        results["canonical_name"] = (

            str(error)

        )


    return results


# ============================================================
# HTTPS AVAILABILITY CHECK
# ============================================================

def check_https_availability(

    domain

):

    url = (

        f"https://{domain}"

    )


    try:

        request = (

            urllib.request.Request(

                url,

                method="HEAD",

                headers={

                    "User-Agent":

                    "Python-Monitor"

                }

            )

        )


        with urllib.request.urlopen(

            request,

            timeout=10

        ) as response:

            return {

                "url": url,

                "status_code": (

                    response.status

                ),

                "https_available": True,

                "status": "OK"

            }


    except urllib.error.HTTPError as error:

        return {

            "url": url,

            "status_code": (

                error.code

            ),

            "https_available": True,

            "status": (

                "HTTPS available "

                "but server returned HTTP error"

            )

        }


    except Exception as error:

        return {

            "url": url,

            "https_available": False,

            "status": (

                "ERROR: HTTPS unavailable"

            ),

            "error": str(error)

        }


# ============================================================
# DOMAIN EXPIRY CHECK
# ============================================================

def check_domain_expiry(

    domain

):

    """

    Basic domain expiry check.

    WHOIS data depends on the domain registry

    and available lookup services.

    """

    return {

        "domain": domain,

        "status": (

            "Domain expiry lookup "

            "requires WHOIS/API integration"

        ),

        "action": (

            "Use a WHOIS or domain registrar API"

        )

    }


# ============================================================
# EMAIL ALERT
# ============================================================

def send_email_alert(

    alerts

):

    if not EMAIL_ENABLED:

        print(

            "\nEmail alerts disabled"

        )

        return


    if not alerts:

        return


    message = EmailMessage()


    message["Subject"] = (

        "Certificate and Domain Monitoring Alert"

    )


    message["From"] = (

        SENDER_EMAIL

    )


    message["To"] = (

        RECEIVER_EMAIL

    )


    message.set_content(

        "\n".join(

            alerts

        )

    )


    try:

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

            "Email alert sent"

        )


        logging.info(

            "Email alert sent"

        )


    except Exception as error:

        print(

            "Email alert failed:",

            error

        )


        logging.error(

            "Email alert failed: %s",

            error

        )


# ============================================================
# MAIN
# ============================================================

def main():

    print(

        "Certificate and Domain Monitoring"

    )


    print(

        "Hostname:",

        HOSTNAME

    )


    certificate_results = []

    dns_results = []

    https_results = []

    domain_expiry_results = []


    alerts = []


    for domain in DOMAINS:

        print(

            f"\nChecking: {domain}"

        )


        # ----------------------------------------------------
        # SSL CERTIFICATE
        # ----------------------------------------------------

        certificate = (

            check_ssl_certificate(

                domain

            )

        )


        certificate_results.append(

            certificate

        )


        print(

            "Certificate:",

            certificate["status"]

        )


        if (

            "days_remaining"

            in certificate

            and

            certificate["days_remaining"]

            <= CERTIFICATE_WARNING_DAYS

        ):

            alerts.append(

                (

                    f"WARNING: {domain} "

                    f"SSL certificate expires in "

                    f"{certificate['days_remaining']} days"

                )

            )


        # ----------------------------------------------------
        # DNS
        # ----------------------------------------------------

        dns = (

            check_dns_records(

                domain

            )

        )


        dns_results.append(

            {

                "domain": domain,

                "records": dns

            }

        )


        print(

            "DNS:",

            dns

        )


        # ----------------------------------------------------
        # HTTPS
        # ----------------------------------------------------

        https = (

            check_https_availability(

                domain

            )

        )


        https_results.append(

            https

        )


        print(

            "HTTPS:",

            https["status"]

        )


        if not https.get(

            "https_available",

            False

        ):

            alerts.append(

                (

                    f"WARNING: HTTPS unavailable "

                    f"for {domain}"

                )

            )


        # ----------------------------------------------------
        # DOMAIN EXPIRY
        # ----------------------------------------------------

        domain_expiry = (

            check_domain_expiry(

                domain

            )

        )


        domain_expiry_results.append(

            domain_expiry

        )


        print(

            "Domain expiry:",

            domain_expiry["status"]

        )


    # ========================================================
    # REPORT
    # ========================================================

    report = {

        "timestamp": (

            datetime.now(

                timezone.utc

            ).isoformat()

        ),

        "hostname": HOSTNAME,

        "certificate_checks": (

            certificate_results

        ),

        "dns_checks": (

            dns_results

        ),

        "https_checks": (

            https_results

        ),

        "domain_expiry_checks": (

            domain_expiry_results

        ),

        "alerts": alerts

    }


    timestamp = (

        datetime.now().strftime(

            "%Y%m%d_%H%M%S"

        )

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


    # ========================================================
    # ALERT
    # ========================================================

    if alerts:

        print(

            "\nALERTS:"

        )


        for alert in alerts:

            print(

                alert

            )


        send_email_alert(

            alerts

        )


    else:

        print(

            "\nNo alerts"

        )


    logging.info(

        "Certificate and domain monitoring completed"

    )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    try:

        main()


    except Exception as error:

        logging.exception(

            "Monitoring failed"

        )


        print(

            "ERROR:",

            error

        )