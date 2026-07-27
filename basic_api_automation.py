import urllib.request
import json
from pathlib import Path
from datetime import datetime


API_URL = "https://jsonplaceholder.typicode.com/todos/1"


REPORT_DIRECTORY = Path("api_reports")

REPORT_DIRECTORY.mkdir(
    exist_ok=True
)


try:

    with urllib.request.urlopen(
        API_URL,
        timeout=10
    ) as response:

        data = json.loads(
            response.read().decode()
        )


    print("API request successful")

    print("User ID:", data["userId"])

    print("Task ID:", data["id"])

    print("Title:", data["title"])

    print("Completed:", data["completed"])


    report = {

        "timestamp":
        datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        ),

        "api_url":
        API_URL,

        "data":
        data

    }


    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )


    report_file = (

        REPORT_DIRECTORY

        / f"api_report_{timestamp}.json"

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
        "Report saved:",
        report_file
    )


except Exception as error:

    print(
        "API request failed:",
        error
    )