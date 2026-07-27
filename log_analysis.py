import platform
import json
import logging
from pathlib import Path
from datetime import datetime


# ============================================================
# PATHS
# ============================================================

BASE_DIRECTORY = Path(__file__).parent

HOSTNAME = platform.node()

DATA_DIRECTORY = (
    BASE_DIRECTORY
    / "log_analysis_data"
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

AUTOMATION_LOG = (
    LOG_DIRECTORY
    / "log_analysis_automation.log"
)


logging.basicConfig(

    filename=AUTOMATION_LOG,

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

# Number of latest lines to analyse

LINES_TO_READ = 500


# Events we want to detect

EVENT_KEYWORDS = {

    "ERROR": [

        "error",

        "failed",

        "failure",

        "critical",

        "fatal"

    ],

    "WARNING": [

        "warning",

        "warn"

    ],

    "AUTHENTICATION_FAILURE": [

        "authentication failure",

        "login failed",

        "failed password",

        "invalid user",

        "access denied"

    ]

}


# ============================================================
# GET LOG FILES
# ============================================================

def get_log_files():

    operating_system = platform.system()


    if operating_system == "Linux":

        return [

            Path(
                "/var/log/auth.log"
            ),

            Path(
                "/var/log/syslog"
            ),

            Path(
                "/var/log/kern.log"
            ),

            Path(
                "/var/log/dpkg.log"
            )

        ]


    elif operating_system == "Windows":

        return [

            "System",

            "Security",

            "Application"

        ]


    else:

        return []


# ============================================================
# READ LINUX LOG FILE
# ============================================================

def read_linux_log(
    log_file
):

    if not log_file.exists():

        return {

            "status":
            "NOT_FOUND",

            "message":
            "Log file not found",

            "lines":
            []

        }


    try:

        with open(

            log_file,

            "r",

            errors="ignore"

        ) as file:

            lines = file.readlines()


        return {

            "status":
            "READ_SUCCESS",

            "message":
            "Log read successfully",

            "lines":
            lines[-LINES_TO_READ:]

        }


    except PermissionError:

        return {

            "status":
            "PERMISSION_DENIED",

            "message":
            "Permission denied",

            "lines":
            []

        }


# ============================================================
# READ WINDOWS EVENT LOGS
# ============================================================

def read_windows_log(
    log_name
):

    import subprocess


    command = (

        f"Get-WinEvent "

        f"-LogName '{log_name}' "

        f"-MaxEvents {LINES_TO_READ} "

        f"| Select-Object "

        f"TimeCreated,Id,LevelDisplayName,ProviderName,Message "

        f"| ConvertTo-Json -Depth 3"

    )


    result = subprocess.run(

        [

            "powershell",

            "-Command",

            command

        ],

        capture_output=True,

        text=True

    )


    if not result.stdout.strip():

        return {

            "status":
            "NO_EVENTS",

            "message":
            "No events found",

            "lines":
            []

        }


    try:

        events = json.loads(

            result.stdout

        )


        if isinstance(

            events,

            dict

        ):

            events = [

                events

            ]


        return {

            "status":
            "READ_SUCCESS",

            "message":
            "Event log read successfully",

            "lines":
            events

        }


    except json.JSONDecodeError:

        return {

            "status":
            "READ_FAILED",

            "message":
            "Could not parse Windows event data",

            "lines":
            []

        }


# ============================================================
# ANALYSE LINUX LOGS
# ============================================================

def analyse_linux_lines(
    lines
):

    results = []

    keyword_counts = {

        "ERROR":
        0,

        "WARNING":
        0,

        "AUTHENTICATION_FAILURE":
        0

    }


    for line in lines:

        lower_line = (
            line.lower()
        )


        matched_categories = []


        for category, keywords in (

            EVENT_KEYWORDS.items()

        ):

            for keyword in keywords:

                if keyword in lower_line:

                    keyword_counts[
                        category
                    ] += 1


                    matched_categories.append(

                        category

                    )


                    break


        if matched_categories:

            results.append(

                {

                    "categories":
                    matched_categories,

                    "log":
                    line.strip()

                }

            )


    return {

        "total_detected_events":
        len(results),

        "event_counts":
        keyword_counts,

        "events":
        results

    }


# ============================================================
# ANALYSE WINDOWS EVENTS
# ============================================================

def analyse_windows_events(
    events
):

    results = []

    keyword_counts = {

        "ERROR":
        0,

        "WARNING":
        0,

        "AUTHENTICATION_FAILURE":
        0

    }


    for event in events:

        message = str(

            event.get(

                "Message",

                ""

            )

        )


        level = str(

            event.get(

                "LevelDisplayName",

                ""

            )

        )


        combined_text = (

            message

            + " "

            + level

        ).lower()


        matched_categories = []


        for category, keywords in (

            EVENT_KEYWORDS.items()

        ):

            for keyword in keywords:

                if keyword in combined_text:

                    keyword_counts[
                        category
                    ] += 1


                    matched_categories.append(

                        category

                    )


                    break


        if matched_categories:

            results.append(

                {

                    "categories":
                    matched_categories,

                    "time":
                    str(

                        event.get(

                            "TimeCreated",

                            ""

                        )

                    ),

                    "event_id":
                    event.get(

                        "Id",

                        ""

                    ),

                    "provider":
                    event.get(

                        "ProviderName",

                        ""

                    ),

                    "message":
                    message

                }

            )


    return {

        "total_detected_events":
        len(results),

        "event_counts":
        keyword_counts,

        "events":
        results

    }


# ============================================================
# SAVE REPORT
# ============================================================

def save_report(
    report
):

    timestamp = (

        datetime.now().strftime(

            "%Y%m%d_%H%M%S"

        )

    )


    report_file = (

        REPORT_DIRECTORY

        / f"log_analysis_{timestamp}.json"

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
    report
):

    print("\n")

    print("=" * 70)

    print(

        "ENTERPRISE LOG ANALYSIS"

    )

    print("=" * 70)


    print(

        "Operating System:",

        report[

            "operating_system"

        ]

    )


    print(

        "Hostname:",

        report[

            "hostname"

        ]

    )


    print(

        "Total Detected Events:",

        report[

            "total_detected_events"

        ]

    )


    print("\nEVENT COUNTS")


    for category, count in (

        report[

            "event_counts"

        ].items()

    ):

        print(

            category,

            ":",

            count

        )


    print(

        "\nReport saved to:",

        report[

            "report_file"

        ]

    )


# ============================================================
# MAIN
# ============================================================

def main():

    logging.info(

        "Log analysis started"

    )


    operating_system = (

        platform.system()

    )


    all_events = []

    total_event_counts = {

        "ERROR":
        0,

        "WARNING":
        0,

        "AUTHENTICATION_FAILURE":
        0

    }


    if operating_system == "Linux":

        log_files = (

            get_log_files()

        )


        for log_file in log_files:

            log_result = (

                read_linux_log(

                    log_file

                )

            )


            if log_result[

                "status"

            ] != "READ_SUCCESS":

                logging.warning(

                    "%s: %s",

                    log_file,

                    log_result[

                        "message"

                    ]

                )


                continue


            analysis = (

                analyse_linux_lines(

                    log_result[

                        "lines"

                    ]

                )

            )


            all_events.extend(

                analysis[

                    "events"

                ]

            )


            for category, count in (

                analysis[

                    "event_counts"

                ].items()

            ):

                total_event_counts[

                    category

                ] += count


    elif operating_system == "Windows":

        log_files = (

            get_log_files()

        )


        for log_name in log_files:

            log_result = (

                read_windows_log(

                    log_name

                )

            )


            if log_result[

                "status"

            ] != "READ_SUCCESS":

                logging.warning(

                    "%s: %s",

                    log_name,

                    log_result[

                        "message"

                    ]

                )


                continue


            analysis = (

                analyse_windows_events(

                    log_result[

                        "lines"

                    ]

                )

            )


            all_events.extend(

                analysis[

                    "events"

                ]

            )


            for category, count in (

                analysis[

                    "event_counts"

                ].items()

            ):

                total_event_counts[

                    category

                ] += count


    else:

        print(

            "Unsupported operating system."

        )

        return


    report = {

        "timestamp":

        datetime.now().strftime(

            "%Y-%m-%d %H:%M:%S"

        ),

        "hostname":

        platform.node(),

        "operating_system":

        operating_system,

        "total_detected_events":

        len(all_events),

        "event_counts":

        total_event_counts,

        "events":

        all_events

    }


    report_file = (

        save_report(

            report

        )

    )


    report[

        "report_file"

    ] = str(

        report_file

    )


    display_results(

        report

    )


    logging.info(

        "Log analysis completed"

    )


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":

    try:

        main()


    except Exception as error:

        logging.exception(

            "Log analysis failed"

        )


        print(

            "ERROR:",

            error

        )