# Security Automation

## Purpose

Security Automation is a cross-platform Python automation script designed to automate common defensive security monitoring, system auditing, and administrative security checks on Windows Server and Ubuntu/Linux systems.

It helps administrators identify security-related events, detect potential issues early, verify system integrity, and generate structured security reports for routine monitoring.

---

## What It Does

The script can automate common security administration tasks such as:

* Detect failed login attempts
* Analyse operating system security logs
* Monitor authentication events
* Verify file integrity
* Check SSL/TLS certificate status
* Audit local user accounts
* Review administrative privileges
* Detect suspicious security events
* Generate security reports
* Record execution logs

The script focuses on **defensive monitoring** and does not perform offensive security testing.

---

## Security Monitoring Workflow

```text id="sn4xka"
Start
   │
   ▼
Collect Security Information
   │
   ▼
Analyse Security Logs
   │
   ▼
Check Authentication Events
   │
   ▼
Verify File Integrity
   │
   ▼
Audit User Access
   │
   ▼
Check Certificates
   │
   ▼
Generate Security Report
   │
   ▼
Store Logs
   │
   ▼
Complete
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

```text id="fln6z8"
python-scripts/
│
├── scripts/
│   └── security_automation.py
│
├── logs/
│   └── security_automation/
│
├── reports/
│   └── security_automation/
│
├── integrity/
├── state/
├── data/
└── backups/
```

---

## Security Checks Performed

Depending on the operating system, the script may perform:

* Failed Login Detection
* Security Log Analysis
* Authentication Event Review
* User Account Auditing
* Administrative Privilege Review
* File Integrity Verification
* SSL/TLS Certificate Validation
* Security Event Collection
* Basic Security Health Assessment

The exact checks depend on platform capabilities and available log sources.

---

## Output

Each execution automatically generates:

### Console Output

Displays information such as:

* Failed Login Attempts
* Security Events Found
* User Audit Results
* Certificate Status
* File Integrity Status
* Overall Security Summary

---

### Log File

Stored in:

```text id="9v1mgb"
logs/security_automation/
```

Example:

```text id="ylt5a5"
security_automation_YYYYMMDD_HHMMSS.log
```

---

### JSON Report

Stored in:

```text id="mb7kfw"
reports/security_automation/
```

Example:

```text id="5g4gso"
security_report_YYYYMMDD_HHMMSS.json
```

The report contains:

* Run ID
* Timestamp
* Security Events
* Failed Login Count
* User Audit Results
* Integrity Status
* Certificate Status
* Summary Statistics

---

## Enterprise Use Cases

This automation is useful for:

* Security Operations Centre (SOC)
* Blue Team monitoring
* Windows Server security
* Linux server security
* Infrastructure security
* Compliance auditing
* User account auditing
* Routine security monitoring

---

## Why This Script Was Created

Routine security monitoring is essential for identifying suspicious activity before it becomes a larger incident.

This project demonstrates how repetitive defensive security tasks can be automated, allowing administrators to detect common issues more efficiently while maintaining consistent reporting.

---

## Enterprise Relevance

The same concepts are used in:

* Microsoft Sentinel
* Splunk
* IBM QRadar
* Elastic Security
* Microsoft Defender
* CrowdStrike
* Security Information and Event Management (SIEM)
* Endpoint Detection and Response (EDR)
* Infrastructure Security Monitoring
* Compliance Auditing

This project introduces defensive automation concepts that support modern security operations.

---

## Recommended Schedule

Run:

* Every 15 minutes for critical servers
* Hourly for standard infrastructure
* After major configuration changes
* During routine security monitoring

Example Cron entry:

```cron id="tpb2yt"
*/15 * * * * cd /home/cloudadmin/python-scripts && python3 scripts/security_automation.py
```

---

## Prerequisites

* Python 3.10 or later
* Administrator privileges (Windows)
* Root or sudo privileges (Linux)
* Access to security logs
* Required Python modules installed

---

## How to Run

### Windows

```powershell id="rv2lga"
python security_automation.py
```

### Ubuntu / Linux

```bash id="m7hm8i"
python3 security_automation.py
```

---

## Important

This project is designed for **defensive security automation**.

It does **not**:

* Exploit vulnerabilities
* Perform penetration testing
* Bypass security controls
* Attack systems

For enterprise environments, this automation should complement:

* Centralised logging
* SIEM platforms
* Incident response procedures
* Security monitoring tools
* Compliance reporting

---

## Error Handling

The script safely handles:

* Missing log files
* Permission restrictions
* Missing certificates
* File access errors
* Missing user accounts
* Unsupported operating system features
* Unexpected security event formats

Errors are recorded in execution logs without interrupting the remaining checks whenever possible.

---

## Best Practices

* Review security reports regularly.
* Investigate repeated failed login attempts.
* Verify administrative accounts periodically.
* Monitor certificate expiration dates.
* Validate file integrity after major updates.
* Integrate with enterprise monitoring platforms where possible.

---

## Related Project Folders

* `scripts/` – Python automation scripts
* `logs/` – Security execution logs
* `reports/` – Security reports
* `integrity/` – File integrity information
* `state/` – Runtime state
* `data/` – Runtime data
* `backups/` – Backup files
