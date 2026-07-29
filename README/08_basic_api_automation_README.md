# Basic API Automation

## Purpose

Basic API Automation is a cross-platform Python automation script that demonstrates how Python communicates with REST APIs and processes structured data.

It introduces the core concepts used in modern cloud administration, infrastructure automation, monitoring systems, and DevOps workflows.

---

## What It Does

The script demonstrates how to:

* Send HTTP requests
* Connect to REST APIs
* Retrieve JSON responses
* Parse API data
* Process dictionaries and lists
* Handle API errors
* Validate HTTP status codes
* Display useful information
* Save API responses to reports
* Record execution logs

The script focuses on learning API communication rather than interacting with production cloud environments.

---

## API Workflow

```text id="f2mv9t"
Python Script
      │
      ▼
Send HTTP Request
      │
      ▼
API Endpoint
      │
      ▼
Receive JSON Response
      │
      ▼
Validate Response
      │
      ▼
Process Data
      │
      ▼
Display Results
      │
      ▼
Generate Report & Log
```

---

## Supported Platforms

* Windows Server
* Windows 10/11
* Ubuntu Server
* Ubuntu Desktop
* Other Linux distributions

---

## Project Structure

```text id="wnc62p"
python-scripts/
│
├── scripts/
│   └── basic_api_automation.py
│
├── logs/
│   └── basic_api_automation/
│
├── reports/
│   └── basic_api_automation/
│
├── data/
├── integrity/
├── state/
└── archives/
```

---

## What You'll Learn

This project introduces the following concepts:

* HTTP GET requests
* REST APIs
* API endpoints
* JSON responses
* Python dictionaries
* Python lists
* Response validation
* HTTP status codes
* Exception handling
* Basic API automation workflow

---

## Output

Each execution automatically generates:

### Console Output

Displays information such as:

* Request Status
* HTTP Status Code
* Response Summary
* Parsed API Data
* Execution Status

---

### Log File

Stored in:

```text id="l4w3rm"
logs/basic_api_automation/
```

Example:

```text id="2utjlwm"
basic_api_automation_YYYYMMDD_HHMMSS.log
```

---

### JSON Report

Stored in:

```text id="3p6vb2"
reports/basic_api_automation/
```

Example:

```text id="gcdxux"
api_report_YYYYMMDD_HHMMSS.json
```

The report may contain:

* Run ID
* Timestamp
* Endpoint
* HTTP Status Code
* Response Summary
* Parsed Data
* Execution Status

---

## Enterprise Use Cases

The same automation pattern is widely used with:

* Cloud APIs
* Monitoring APIs
* Microsoft Graph API
* Microsoft Azure APIs
* AWS APIs
* Google Cloud APIs
* ServiceNow APIs
* Jira APIs
* GitHub APIs
* Docker APIs
* Kubernetes APIs
* Network Device APIs
* Ticketing Systems

---

## Why This Script Was Created

Modern infrastructure relies heavily on APIs rather than graphical interfaces.

Understanding how to send requests, process responses, and automate repetitive API interactions is one of the most important skills for Cloud Engineers, DevOps Engineers, Infrastructure Engineers, and System Administrators.

---

## Enterprise Relevance

API automation forms the foundation of:

* Cloud Automation
* Infrastructure as Code
* DevOps
* CI/CD Pipelines
* Monitoring Automation
* Ticket Automation
* Identity Management
* Server Provisioning
* Configuration Management

Almost every modern cloud platform provides REST APIs for automation.

---

## Recommended Schedule

This script is primarily intended as a learning example and is normally run:

* On demand
* During development
* While testing API integrations

It is generally **not scheduled** as a recurring task unless adapted for a specific production workflow.

---

## Prerequisites

* Python 3.10 or later
* Internet connectivity (if using public APIs)
* Required Python modules installed (for example, `requests`)

---

## How to Run

### Windows

```powershell id="7kjlwm"
python basic_api_automation.py
```

### Ubuntu / Linux

```bash id="nvq8yy"
python3 basic_api_automation.py
```

---

## Error Handling

The script safely handles:

* Network failures
* Connection timeouts
* Invalid URLs
* Invalid JSON responses
* API request failures
* HTTP error codes
* Unexpected responses

Errors are logged without causing unexpected termination whenever possible.

---

## Best Practices

* Always validate HTTP status codes.
* Never assume API responses are valid.
* Handle exceptions gracefully.
* Protect API keys and tokens.
* Avoid hardcoding credentials.
* Follow API rate limits.
* Read API documentation before integration.

---

## Related Project Folders

* `scripts/` – Python automation scripts
* `logs/` – Execution logs
* `reports/` – API reports
* `data/` – Runtime data
* `integrity/` – Integrity verification
* `state/` – Script state information
* `archives/` – Archived files
