# User and Account Automation

## Purpose

User and Account Automation is a cross-platform Python automation script designed to automate common local user administration tasks on Windows Server and Ubuntu/Linux systems.

It simplifies user lifecycle management by automating account creation, modification, group membership, and account maintenance while following administrative best practices.

---

## What It Does

The script can automate common account administration tasks including:

* Create local user accounts
* Remove user accounts
* Disable user accounts
* Enable disabled accounts
* Reset user account properties
* Add users to groups
* Remove users from groups
* Create service accounts
* Verify existing accounts before making changes
* Generate user management reports
* Record every operation in execution logs

The script validates operations before execution and reports failures without terminating unexpectedly.

---

## Supported Platforms

* Windows Server
* Windows 10/11
* Ubuntu Server
* Ubuntu Desktop
* Other Linux distributions

---

## Project Structure

```text id="jz4gxm"
python-scripts/
│
├── scripts/
│   ├── user_account_automation.py
│   └── user_test_data.json
│
├── logs/
│   └── user_account_automation/
│
├── reports/
│   └── user_account_automation/
│
├── data/
├── integrity/
├── state/
└── backups/
```

---

## Supported Operations

The automation supports tasks such as:

* User Creation
* User Deletion
* Account Disable
* Account Enable
* Group Membership Management
* Service Account Creation
* User Validation
* User Reporting

The exact operation performed depends on the configuration or input data provided to the script.

---

## Output

Each execution automatically generates:

### Console Output

Displays a summary including:

* Users Created
* Users Removed
* Accounts Disabled
* Groups Updated
* Failed Operations
* Overall Execution Status

---

### Log File

Stored in:

```text id="x3nr0d"
logs/user_account_automation/
```

Example:

```text id="jvx9k9"
user_account_automation_YYYYMMDD_HHMMSS.log
```

---

### JSON Report

Stored in:

```text id="d5cr7i"
reports/user_account_automation/
```

Example:

```text id="gmpvww"
user_account_report_YYYYMMDD_HHMMSS.json
```

The report contains:

* Run ID
* Timestamp
* Users Processed
* Successful Operations
* Failed Operations
* Group Changes
* Summary Statistics

---

## Enterprise Use Cases

This automation can be used for:

* Employee onboarding
* Employee offboarding
* Temporary account management
* Service account creation
* Group membership updates
* Standardised user provisioning
* Compliance reporting
* Routine account maintenance

---

## Why This Script Was Created

Managing user accounts manually is repetitive and increases the risk of administrative mistakes.

This script automates common user administration tasks to improve consistency, reduce manual effort, and provide detailed audit records of every operation.

---

## Enterprise Relevance

The same automation concepts are widely used in:

* Windows Server Administration
* Active Directory
* Linux User Administration
* Microsoft Entra ID (Azure AD)
* AWS IAM
* Google Cloud IAM
* Enterprise Identity and Access Management (IAM)

Although this project focuses on **local user management**, the workflow closely resembles enterprise identity management processes.

---

## Recommended Schedule

Run:

* On demand for onboarding/offboarding
* During maintenance windows
* After HR or administrative requests
* As part of automated provisioning workflows

This script is typically **not scheduled on a fixed interval**, since user management is event-driven rather than time-driven.

---

## Prerequisites

* Python 3.10 or later
* Administrator privileges (Windows)
* Root or sudo privileges (Linux)
* Appropriate permissions to manage local users and groups

---

## How to Run

### Windows

```powershell id="qdxln6"
python user_account_automation.py
```

### Ubuntu / Linux

```bash id="m8crbi"
python3 user_account_automation.py
```

---

## Security

To follow security best practices:

* Never hardcode passwords.
* Never store credentials in source code.
* Use secure credential storage when required.
* Apply the principle of least privilege.
* Audit user-management activities regularly.
* Review generated reports after execution.

---

## Error Handling

The script safely handles:

* Existing user accounts
* Missing user accounts
* Missing groups
* Duplicate account creation
* Permission errors
* Invalid operations

Errors are recorded in the log while allowing remaining operations to continue whenever possible.

---

## Best Practices

* Verify account information before execution.
* Test changes in a non-production environment.
* Review generated reports after every run.
* Keep user provisioning consistent across systems.
* Combine this automation with central identity management solutions when available.

---

## Related Project Folders

* `scripts/` – Python automation scripts
* `user_test_data.json` – Sample input data for testing
* `logs/` – Execution logs
* `reports/` – User management reports
* `data/` – Runtime data
* `integrity/` – Integrity verification
* `state/` – Script state information
* `backups/` – Backup files
