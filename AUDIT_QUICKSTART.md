# Audit Trail & Compliance - Quick Start

## 5-Minute Overview

Every API call in Cloud Document Archive can be automatically logged for:
- **Compliance**: HIPAA, GDPR, PCI-DSS, SOC 2 requirements
- **Security**: Track who accessed what, when, and from where
- **Troubleshooting**: Understand what happened during failures

## Enable Audit Logging

```yaml
# config.yaml
audit:
  enabled: true
  log_file: audit.log
  include_request_body: false  # Never log passwords/PII!
  include_response_body: false
```

Or set environment variable:
```bash
export AUDIT_ENABLED=true
export AUDIT_LOG_FILE=audit.log
```

## What Gets Logged

Every audit entry includes:
- **What**: Event type (document_upload, login, access_denied, etc.)
- **Who**: User ID and username
- **When**: Timestamp with timezone
- **Where**: IP address and User-Agent
- **Action**: Operation performed (upload, delete, read, etc.)
- **Result**: Success or failure with reason
- **Context**: Associated user agent, API endpoint

## View Audit Logs

### All Logs

```bash
curl -X GET "http://localhost:8000/api/v1/audit/logs?limit=100" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Logs for Specific Event

```bash
# All document uploads
curl -X GET "http://localhost:8000/api/v1/audit/logs?event_type=document_upload" \
  -H "Authorization: Bearer YOUR_TOKEN"

# All login events
curl -X GET "http://localhost:8000/api/v1/audit/logs?event_type=login" \
  -H "Authorization: Bearer YOUR_TOKEN"

# All access denied events (security incidents)
curl -X GET "http://localhost:8000/api/v1/audit/logs?event_type=access_denied" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Logs for Specific User

```bash
# All actions by user ID 5
curl -X GET "http://localhost:8000/api/v1/audit/logs?user_id=5" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Logs in Date Range

```bash
# Yesterday's logs
curl -X GET "http://localhost:8000/api/v1/audit/logs?start_date=2026-02-20T00:00:00&end_date=2026-02-20T23:59:59" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Filter by Status

```bash
# Only failed operations
curl -X GET "http://localhost:8000/api/v1/audit/logs?status=failure" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Audit Event Types

| Event | When | Purpose |
|-------|------|---------|
| `login` | User authenticates | Authentication tracking |
| `logout` | User exits | Session tracking |
| `token_refresh` | Token refreshed | Session management |
| `document_upload` | File added | Upload tracking |
| `document_download` | File retrieved | Access tracking |
| `document_update` | Metadata changed | Change tracking |
| `document_delete` | File removed | Deletion tracking |
| `document_share` | Access granted | Sharing tracking |
| `user_create` | New user added | User management |
| `user_update` | User changed | Modification tracking |
| `user_delete` | User removed | Removal tracking |
| `role_assign` | Role changed | Authorization updates |
| `permission_change` | Permissions updated | Access control changes |
| `access_denied` | Action blocked | Security incidents |
| `encryption_enable` | Encryption activated | Security events |
| `encryption_disable` | Encryption deactivated | Security events |
| `system_config_change` | Settings modified | Configuration tracking |

## Audit Log Entry Structure

```json
{
  "id": 12345,
  "timestamp": "2026-02-21T10:30:45.123456",
  "event_type": "document_upload",
  "user_id": 1,
  "username": "john.doe",
  "resource_type": "document",
  "resource_id": "doc-abc-123",
  "action": "upload",
  "status": "success",
  "http_method": "POST",
  "http_endpoint": "/api/v1/archive",
  "http_status": 201,
  "ip_address": "192.168.1.100",
  "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
  "details": {
    "filename": "financial_report_2026.pdf",
    "size_bytes": 2048576,
    "storage_provider": "aws_s3",
    "encryption_enabled": true
  }
}
```

## Real-World Scenarios

### Scenario 1: Track Document Access

**Goal**: Find who accessed confidential document

```bash
# Get document ID first
DOC_ID="financial-report-2026"

# Check all access to this document (upload, download, share)
curl -X GET "http://localhost:8000/api/v1/audit/logs?resource_id=$DOC_ID" \
  -H "Authorization: Bearer AUDITOR_TOKEN"

# Result: See list of all users who touched this document
```

### Scenario 2: Security Incident Investigation

**Goal**: Find unauthorized access attempts

```bash
# All access denied events in last 24 hours
curl -X GET "http://localhost:8000/api/v1/audit/logs?event_type=access_denied&status=failure&start_date=2026-02-20T00:00:00" \
  -H "Authorization: Bearer AUDITOR_TOKEN"

# Check if specific user had failed attempts
curl -X GET "http://localhost:8000/api/v1/audit/logs?user_id=10&event_type=access_denied" \
  -H "Authorization: Bearer AUDITOR_TOKEN"
```

### Scenario 3: Compliance Report

**Goal**: Generate monthly compliance report

```bash
# All user activities for February
curl -X GET "http://localhost:8000/api/v1/audit/logs?start_date=2026-02-01T00:00:00&end_date=2026-02-28T23:59:59&limit=10000" \
  -H "Authorization: Bearer AUDITOR_TOKEN" > compliance_report_feb.json
```

### Scenario 4: User Activity Report

**Goal**: See what a specific user did

```bash
# All actions by user john.doe in last 7 days
USER_ID=5
DAYS_AGO="2026-02-14T00:00:00"
TODAY="2026-02-21T23:59:59"

curl -X GET "http://localhost:8000/api/v1/audit/logs?user_id=$USER_ID&start_date=$DAYS_AGO&end_date=$TODAY" \
  -H "Authorization: Bearer AUDITOR_TOKEN"
```

## Compliance Specifications

### HIPAA (Healthcare)
Audit must track:
- ✅ User identities for all PHI access
- ✅ Timestamps for all operations
- ✅ Success/failure of access attempts
- ✅ IP addresses and locations
- ✅ Device information (User-Agent)

### GDPR (Data Privacy)
Requirements met:
- ✅ Track data access (document_download)
- ✅ Track data modifications (document_update, document_delete)
- ✅ Track data sharing (document_share)
- ✅ Detailed user event logs (user_create, user_delete)
- ✅ Purge capability via API events

### PCI-DSS (Payment Card Data)
Audit covers:
- ✅ All access to cardholder data (resource_type: document)
- ✅ User authentication (login, logout, token_refresh)
- ✅ Authorization changes (role_assign, permission_change)
- ✅ Failed access attempts (access_denied)
- ✅ Administrator activities (user_create, system_config_change)

### SOC 2 (Controls & Compliance)
Evidence provided by:
- ✅ CC6.1: Logical access controls (permission tracking)
- ✅ CC6.2: User access rights (role/permission logs)
- ✅ CC7.2: User authentication (login events)
- ✅ A1.1: Change management (config/permission changes)
- ✅ A1.2: Monitoring (all events with status)

## Python API Usage

```python
from app.audit_service import get_audit_service, AuditEventType, AuditLog, AuditStatus
from datetime import datetime, timedelta

audit = get_audit_service()

# Log a custom event
log = AuditLog(
    event_type=AuditEventType.DOCUMENT_UPLOAD,
    user_id=1,
    username="john.doe",
    resource_type="document",
    resource_id="report-123",
    action="upload",
    status=AuditStatus.SUCCESS,
    details={
        "filename": "report.pdf",
        "size_bytes": 2048,
        "encryption": "AES-256-GCM"
    }
)
audit.log_event(log)

# Query logs with filters
logs = audit.get_audit_logs(
    event_type=AuditEventType.DOCUMENT_DOWNLOAD,
    user_id=1,
    start_date=datetime.now() - timedelta(days=7),
    end_date=datetime.now(),
    limit=100
)

for log_entry in logs:
    print(f"{log_entry.timestamp}: {log_entry.username} {log_entry.action}")
```

## Log Files

Default location: `audit.log`

Format:
```
[2026-02-21 10:30:45] user:john.doe action:document_upload status:success ip:192.168.1.100 resource:doc-123
```

### Rotate Logs

```bash
# Archive current log
mv audit.log audit.log.2026-02-21

# Application creates new audit.log automatically
```

### Export to CSV for Analysis

```python
import json
import csv

# Read audit.log and export to CSV
with open('audit.log', 'r') as f_in, open('audit.csv', 'w', newline='') as f_out:
    writer = csv.writer(f_out)
    writer.writerow(['timestamp', 'user', 'action', 'resource_type', 'status', 'ip_address'])
    
    for line in f_in:
        # Parse JSON from log line
        data = json.loads(line)
        writer.writerow([
            data['timestamp'],
            data['username'],
            data['action'],
            data['resource_type'],
            data['status'],
            data['ip_address']
        ])
```

## Audit Log Permissions

Only "Auditor" and "Admin" roles can view audit logs:

```python
from app.user_management import Permission

# Only allow these users to view audit logs
required_permission = Permission.AUDIT_READ
```

## FAQ

**Q: Are audit logs encrypted?**
A: On disk, no. For compliance requirements, encrypt the audit.log file using your system's encryption.

**Q: How long are logs kept?**
A: By default, forever in database and audit.log file. Implement log rotation to manage disk space.

**Q: Can logs be deleted?**
A: Only system administrator can delete logs. Auditors cannot modify logs (integrity requirement).

**Q: What if someone tries to delete a log entry?**
A: This event is logged as `system_config_change` with status=failure.

**Q: Can I add custom audit events?**
A: Yes, see [USER_MANAGEMENT.md#custom-audit-events](USER_MANAGEMENT.md#custom-audit-events)

## Integration Examples

### Monitor Failed Logins

```bash
#!/bin/bash
# Check for failed login attempts in last hour
curl -s -X GET "http://localhost:8000/api/v1/audit/logs?event_type=login&status=failure&start_date=$(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S)" \
  -H "Authorization: Bearer $AUDIT_TOKEN" | jq '.logs[] | "\(.username) failed at \(.timestamp)"'
```

### Daily Compliance Email

```python
import requests
from datetime import datetime, timedelta

def send_compliance_report(api_token, email):
    yesterday = (datetime.now() - timedelta(days=1)).isoformat()
    today = datetime.now().isoformat()
    
    response = requests.get(
        "http://localhost:8000/api/v1/audit/logs",
        headers={"Authorization": f"Bearer {api_token}"},
        params={
            "start_date": yesterday,
            "end_date": today,
            "limit": 1000
        }
    )
    
    logs = response.json()['logs']
    print(f"Daily Compliance Report\n{len(logs)} events logged\n")
    # Send email...
```

### Real-time Alerts

See [USER_MANAGEMENT.md#real-time-alerts](USER_MANAGEMENT.md#real-time-alerts) for webhooks and streaming.

## Next Steps

1. Read [USER_MANAGEMENT.md](USER_MANAGEMENT.md) for complete documentation
2. Configure audit log rotation
3. Set up log archival process
4. Enable HTTPS for secure audit transmission
5. Implement custom audit event types
6. Set up compliance reports

## Documentation References

- Complete guide: [USER_MANAGEMENT.md](USER_MANAGEMENT.md)
- User management: [USER_MANAGEMENT_QUICKSTART.md](USER_MANAGEMENT_QUICKSTART.md)
- All audit events: [USER_MANAGEMENT.md#audit-events](USER_MANAGEMENT.md#audit-events)
- Compliance details: [USER_MANAGEMENT.md#compliance](USER_MANAGEMENT.md#compliance)
