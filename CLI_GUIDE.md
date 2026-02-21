# Cloud Document Archive CLI Module

## Overview

The CLI Module provides a command-line interface for managing Cloud Document Archive operations including file management, user administration, and audit log retrieval. This module enables system administrators and operators to perform critical tasks without requiring direct API calls.

## Installation

### 1. Install Dependencies

```bash
pip install click>=8.0.0 tabulate>=0.9.0 pyjwt>=2.8.0
```

Or install all requirements:

```bash
pip install -r requirements.txt
```

### 2. Python Entry Point

Add to `setup.py` for easy CLI access:

```python
entry_points={
    'console_scripts': [
        'archive-cli=app.cli:cli',
    ],
},
```

Then install in development mode:

```bash
pip install -e .
```

## Quick Start

### Basic Usage

```bash
# Show help
python -m app.cli --help

# Show version
python -m app.cli version

# Initialize application
python -m app.cli init
```

### Running the CLI

**Method 1: Direct Python**
```bash
python -m app.cli <command> [options]
```

**Method 2: Via Entry Point (after setup.py installation)**
```bash
archive-cli <command> [options]
```

**Method 3: Run Script**
```bash
python archive-cli <command> [options]
```

## Command Reference

### 1. File Operations

Commands for copying, deleting, and overwriting files.

#### Copy Files

**Command:**
```bash
archive-cli files copy <source> <destination> [--force]
```

**Parameters:**
- `source` (required): Path to source file or directory
- `destination` (required): Path to destination
- `--force` (optional): Overwrite if destination exists

**Examples:**

```bash
# Copy a single file
archive-cli files copy /path/to/source.txt /path/to/dest.txt

# Copy a directory
archive-cli files copy /path/to/source_dir /path/to/dest_dir

# Overwrite destination if it exists
archive-cli files copy /path/to/source.txt /path/to/dest.txt --force

# Copy with relative paths
archive-cli files copy ./documents/report.pdf ./archive/report.pdf
```

**Output:**
```
✅ File copied successfully:
   From: /path/to/source.txt
   To:   /path/to/dest.txt
```

#### Delete Files

**Command:**
```bash
archive-cli files delete <path> [--recursive] [--force]
```

**Parameters:**
- `path` (required): Path to file or directory to delete
- `--recursive, -r` (optional): Required for deleting directories
- `--force, -f` (optional): Skip confirmation prompt

**Examples:**

```bash
# Delete a file (confirms first)
archive-cli files delete /path/to/file.txt

# Delete a file without confirmation
archive-cli files delete /path/to/file.txt --force

# Delete a directory recursively
archive-cli files delete /path/to/directory --recursive

# Delete directory without confirmation
archive-cli files delete /path/to/directory --recursive --force
```

**Output:**
```
Are you sure you want to delete '/path/to/file.txt'? [y/N]: y
✅ File deleted: /path/to/file.txt
```

#### Overwrite Files

**Command:**
```bash
archive-cli files overwrite <source> <destination> [--backup]
```

**Parameters:**
- `source` (required): Path to source file (must exist and be a file)
- `destination` (required): Path to destination file
- `--backup` (optional): Create backup of destination before overwriting

**Examples:**

```bash
# Overwrite destination file
archive-cli files overwrite /path/to/source.txt /path/to/destination.txt

# Overwrite with automatic backup
archive-cli files overwrite /path/to/source.txt /path/to/destination.txt --backup

# Backup will be created as: /path/to/destination.txt.backup.20260221_143022
```

**Output:**
```
📦 Backup created: /path/to/destination.txt.backup.20260221_143022
✅ File overwritten successfully:
   Source:      /path/to/source.txt
   Destination: /path/to/destination.txt
```

---

### 2. User Management

Commands for creating, listing, managing users and assigning roles.

#### Create User

**Command:**
```bash
archive-cli users create [--username <name>] [--email <email>] [--password <pass>] [--role <role>]
```

**Parameters:**
- `--username` (prompted if not provided): User login name (must be unique)
- `--email` (prompted if not provided): User email address
- `--password` (prompted if not provided): User password (hidden input, requires confirmation)
- `--role` (optional): One of `admin`, `archive_manager`, `auditor`, `user`, `viewer` (default: `user`)

**Examples:**

```bash
# Interactive creation (prompts for all fields)
archive-cli users create

# Create with specified role
archive-cli users create --username john --email john@example.com --password SecurePass123 --role archive_manager

# Create admin user
archive-cli users create --username admin2 --email admin2@example.com --password AdminPass123 --role admin

# Create read-only viewer
archive-cli users create --username viewer1 --email viewer1@example.com --role viewer
```

**Output:**
```
✅ User created successfully:
   User ID:  1
   Username: john
   Email:    john@example.com
   Role:     archive_manager
```

#### List Users

**Command:**
```bash
archive-cli users list [--limit <number>]
```

**Parameters:**
- `--limit` (optional): Number of users to display (default: 10)

**Examples:**

```bash
# List first 10 users
archive-cli users list

# List first 50 users
archive-cli users list --limit 50
```

**Output:**
```
📋 Users (showing 3 of 5):

╒════╤═══════════╤═════════════════════╤══════════════════╤════════╤═════════════════════════════════════════════╕
│ ID │ Username  │ Email               │ Role             │ Active │ Created                                     │
╞════╪═══════════╪═════════════════════╪══════════════════╪════════╪═════════════════════════════════════════════╡
│ 1  │ admin     │ admin@example.com   │ admin            │ ✓      │ 2026-02-20 10:30:45.123456                  │
├────┼───────────┼─────────────────────┼──────────────────┼────────┼─────────────────────────────────────────────┤
│ 2  │ john      │ john@example.com    │ archive_manager  │ ✓      │ 2026-02-21 14:22:33.456789                  │
├────┼───────────┼─────────────────────┼──────────────────┼────────┼─────────────────────────────────────────────┤
│ 3  │ viewer1   │ viewer1@example.com │ viewer           │ ✓      │ 2026-02-21 15:10:22.789012                  │
╘════╧═══════════╧═════════════════════╧══════════════════╧════════╧═════════════════════════════════════════════╝
```

#### Delete User

**Command:**
```bash
archive-cli users delete-user <username> [--force]
```

**Parameters:**
- `username` (required): Username to delete
- `--force, -f` (optional): Skip confirmation

**Examples:**

```bash
# Delete user (will prompt for confirmation)
archive-cli users delete-user john

# Delete without confirmation
archive-cli users delete-user john --force
```

**Output:**
```
Are you sure you want to delete user 'john'? [y/N]: y
✅ User 'john' deleted successfully.
```

#### Assign Role

**Command:**
```bash
archive-cli users assign-role <username> --role <role>
```

**Parameters:**
- `username` (required): Username to update
- `--role` (required): New role: `admin`, `archive_manager`, `auditor`, `user`, `viewer`

**Examples:**

```bash
# Promote user to archive_manager
archive-cli users assign-role john --role archive_manager

# Demote to viewer
archive-cli users assign-role john --role viewer

# Grant admin privileges
archive-cli users assign-role john --role admin
```

**Output:**
```
✅ Role assigned successfully:
   Username: john
   New Role: archive_manager
```

#### Get User Info

**Command:**
```bash
archive-cli users info <username>
```

**Parameters:**
- `username` (required): Username to display information for

**Examples:**

```bash
# View user details with permissions
archive-cli users info john
```

**Output:**
```
👤 User Information:

  ID:        1
  Username:  john
  Email:     john@example.com
  Role:      archive_manager
  Active:    Yes
  Created:   2026-02-21 14:22:33.456789
  Updated:   2026-02-21 15:45:12.123456

  Permissions (12):
    • audit_read
    • document_download
    • document_metadata_read
    • document_search
    • document_upload
    • document_view
    • system_read
```

---

### 3. Audit Log Retrieval

Commands for retrieving, filtering, and exporting audit logs.

#### Retrieve Logs

**Command:**
```bash
archive-cli logs retrieve [options]
```

**Options:**
- `--start-date` (optional): Start date (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
- `--end-date` (optional): End date (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
- `--event-type` (optional): Filter by event type (login, document_upload, etc.)
- `--user-id` (optional): Filter by user ID
- `--resource-type` (optional): Filter by resource type (document, user, etc.)
- `--status` (optional): Filter by status: `success`, `failure`, `partial`
- `--limit` (optional): Max records to retrieve (default: 50, max: 1000)
- `--offset` (optional): Number of records to skip (default: 0)

**Examples:**

```bash
# Get last 50 logs
archive-cli logs retrieve

# Get logs from specific date
archive-cli logs retrieve --start-date 2026-02-21 --end-date 2026-02-21

# Get logs for specific user
archive-cli logs retrieve --user-id 1 --limit 100

# Get all failed authentication attempts
archive-cli logs retrieve --event-type login --status failure

# Get document uploads from specific date
archive-cli logs retrieve --start-date 2026-02-21T00:00:00 --end-date 2026-02-21T23:59:59 --event-type document_upload

# Get logs with multiple filters
archive-cli logs retrieve --event-type document_download --resource-type document --status success --limit 200
```

**Output:**
```
📊 Audit Logs (showing 3 logs):

╒═══╤═════════════════════╤════════════════════╤═════════╤═════════╤══════════╤═══════════════════╕
│ ID│ Timestamp          │ Event Type         │ User    │ Status  │ Resource │ Action            │
╞═══╪═════════════════════╪════════════════════╪═════════╪═════════╪══════════╪═══════════════════╡
│ 1 │ 2026-02-21 14:22:33│ login              │ john    │ success │ session  │ user_login        │
├───┼─────────────────────┼────────────────────┼─────────┼─────────┼──────────┼───────────────────┤
│ 2 │ 2026-02-21 14:23:15│ document_upload    │ john    │ success │ document │ file_upload       │
├───┼─────────────────────┼────────────────────┼─────────┼─────────┼──────────┼───────────────────┤
│ 3 │ 2026-02-21 14:24:02│ document_search    │ john    │ success │ document │ search_query      │
╘═══╧═════════════════════╧════════════════════╧═════════╧═════════╧══════════╧═══════════════════╝

✓ Total records retrieved: 3
```

#### Log Summary

**Command:**
```bash
archive-cli logs summary [--days <number>] [--event-type <type>]
```

**Parameters:**
- `--days` (optional): Look back period in days (default: 7)
- `--event-type` (optional): Filter by specific event type

**Examples:**

```bash
# Summary of last 7 days
archive-cli logs summary

# Summary of last 30 days
archive-cli logs summary --days 30

# Summary of document uploads in last 14 days
archive-cli logs summary --days 14 --event-type document_upload
```

**Output:**
```
📈 Audit Log Summary (Last 7 days):

Event Types:
  • login: 45
  • document_upload: 23
  • document_download: 67
  • document_search: 89
  • role_assignment: 3

Status Summary:
  • success: 215
  • failure: 12
  • partial: 0

Top Users:
  • john: 78 actions
  • admin: 45 actions
  • viewer1: 32 actions
  • archive_manager: 28 actions
  • auditor: 18 actions

Total Events: 227
```

#### Export Logs

**Command:**
```bash
archive-cli logs export --start-date <date> --end-date <date> --output <path>
```

**Parameters:**
- `--start-date` (required): Start date (YYYY-MM-DD)
- `--end-date` (required): End date (YYYY-MM-DD)
- `--output` (required): Output file path (must end with `.json` or `.csv`)

**Examples:**

```bash
# Export to JSON
archive-cli logs export --start-date 2026-02-01 --end-date 2026-02-21 --output audit_logs.json

# Export to CSV
archive-cli logs export --start-date 2026-02-01 --end-date 2026-02-21 --output audit_logs.csv

# Export with full path
archive-cli logs export --start-date 2026-02-21 --end-date 2026-02-21 --output ./reports/audit_2026-02-21.csv
```

**Output:**
```
✅ Exported 156 logs to CSV: audit_logs.csv

# CSV structure:
id,timestamp,event_type,user_id,username,resource_type,resource_id,action,status,ip_address,http_method,http_endpoint,http_status,details
1,2026-02-21 14:22:33,login,1,john,...
```

---

### 4. System Commands

#### Initialize Application

**Command:**
```bash
archive-cli init
```

**Purpose:** Initialize the application by creating database tables and the initial admin user.

**Example:**
```bash
archive-cli init
```

**Output:**
```
🔧 Initializing Cloud Document Archive...

📦 Creating database tables...
✅ Database tables created.

👤 Creating admin user...
Admin username [admin]: admin
Admin email [admin@example.com]: admin@example.com
Admin password: ****
Admin password (confirm): ****
✅ Admin user created: admin

✅ Initialization complete!
```

#### Show Version

**Command:**
```bash
archive-cli version
```

**Output:**
```
Cloud Document Archive v2.0.0
with User Management, Authentication, and Audit Trail
```

---

## Common Workflows

### Scenario 1: Set Up New Archive System

```bash
# 1. Initialize the system
archive-cli init

# 2. Create archive manager user
archive-cli users create --username manager1 --email manager@example.com --role archive_manager

# 3. Create auditor user
archive-cli users create --username auditor1 --email auditor@example.com --role auditor

# 4. Verify users were created
archive-cli users list

# 5. Check system logs
archive-cli logs retrieve --limit 50
```

### Scenario 2: Daily Audit Review

```bash
# 1. Get summary of today's activity
archive-cli logs summary --days 1

# 2. Review all failed operations
archive-cli logs retrieve --start-date 2026-02-21 --status failure

# 3. Export day's logs for compliance
archive-cli logs export --start-date 2026-02-21 --end-date 2026-02-21 --output daily_audit_2026-02-21.csv

# 4. Email the CSV to compliance team
```

### Scenario 3: User Account Management

```bash
# 1. List all active users
archive-cli users list --limit 100

# 2. Get details for specific user
archive-cli users info john

# 3. Promote user to manager
archive-cli users assign-role john --role archive_manager

# 4. Check user's recent activity
archive-cli logs retrieve --user-id 1 --limit 50
```

### Scenario 4: File Archive Maintenance

```bash
# 1. Back up archival files
archive-cli files copy /archive/active ./backups/active_backup_20260221

# 2. Clean up old temporary files
archive-cli files delete /temp/old_uploads --recursive

# 3. Archive completed projects
archive-cli files copy /projects/completed /archive/projects_2026 --force

# 4. Verify operations in audit log
archive-cli logs retrieve --resource-type document --status success
```

### Scenario 5: Month-End Compliance Report

```bash
# 1. Export all February logs
archive-cli logs export --start-date 2026-02-01 --end-date 2026-02-28 --output february_audit.csv

# 2. Get summary statistics
archive-cli logs summary --days 28

# 3. Review all user modifications
archive-cli logs retrieve --event-type role_assignment --limit 100

# 4. Export to reports folder
archive-cli logs export --start-date 2026-02-01 --end-date 2026-02-28 --output ./compliance_reports/february.json
```

---

## Event Types Reference

The following event types are tracked in audit logs:

| Event Type | Description |
|---|---|
| `login` | User authentication |
| `logout` | User session termination |
| `document_upload` | Document file upload |
| `document_download` | Document file download |
| `document_delete` | Document deletion |
| `document_view` | Document access |
| `document_search` | Search query executed |
| `document_share` | Document sharing |
| `encryption_enabled` | Encryption activated |
| `encryption_key_generated` | Encryption key created |
| `user_created` | New user account |
| `user_deleted` | User account deleted |
| `user_updated` | User information modified |
| `role_assignment` | Role assigned to user |
| `permission_change` | Permission modified |
| `audit_log_access` | Audit log retrieved |
| `system_config_change` | System configuration updated |

---

## Error Handling

### Common Errors and Solutions

**Error: "User 'username' already exists"**
```bash
# Solution: Use a different username or delete the existing user first
archive-cli users delete-user existing_user --force
```

**Error: "Invalid start_date format"**
```bash
# Solution: Use YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS format
archive-cli logs retrieve --start-date 2026-02-21  # Correct
```

**Error: "Destination file already exists"**
```bash
# Solution: Use --force flag to overwrite
archive-cli files copy source.txt dest.txt --force
```

**Error: "Cannot delete directory without --recursive"**
```bash
# Solution: Add --recursive flag for directories
archive-cli files delete /path/to/dir --recursive
```

---

## Output Formats

### Success Indicators
- `✅`: Operation completed successfully
- `✓`: Confirmation or validation passed
- `📋`: List or inventory display
- `📊`: Statistics or summary
- `👤`: User-related information
- `📦`: Package or archive operation
- `🔧`: System operations

### Error Indicators
- `❌`: Operation failed
- `⚠️`: Warning message

---

## Environment Variables

The CLI respects the following environment variables:

```bash
# Database connection
DATABASE_URL=sqlite:///./test.db

# JWT settings  
JWT_SECRET_KEY=your-secret-key
JWT_ACCESS_TOKEN_EXPIRES=1800

# Audit settings
AUDIT_ENABLED=true
AUDIT_LOG_FILE=./logs/audit.log
```

---

## Performance Tips

1. **Use pagination for large result sets:**
   ```bash
   archive-cli logs retrieve --limit 1000 --offset 0
   ```

2. **Export instead of displaying very large datasets:**
   ```bash
   archive-cli logs export --start-date 2026-01-01 --end-date 2026-02-28 --output large_export.csv
   ```

3. **Filter before exporting for faster queries:**
   ```bash
   archive-cli logs retrieve --event-type document_upload --status failure
   ```

4. **Use date ranges to narrow results:**
   ```bash
   archive-cli logs retrieve --start-date 2026-02-21T00:00:00 --end-date 2026-02-21T23:59:59
   ```

---

## Security Considerations

1. **Never share passwords in CLI arguments:**
   ```bash
   # Instead of: archive-cli users create --password YourPassword
   # Use interactive mode:
   archive-cli users create
   ```

2. **Protect audit log exports:**
   ```bash
   # Exported files may contain sensitive information
   archive-cli logs export --start-date 2026-02-21 --end-date 2026-02-21 --output audit.csv
   chmod 600 audit.csv  # Restrict file permissions
   ```

3. **Audit log deletions or exports:**
   ```bash
   # All audit operations are themselves logged
   archive-cli logs retrieve --event-type audit_log_access
   ```

---

## Integration with Scripts

### Bash Script Example

```bash
#!/bin/bash
# daily_audit_backup.sh

DATE=$(date +%Y-%m-%d)
BACKUP_DIR="./backups/daily"

# Create directory
mkdir -p $BACKUP_DIR

# Export daily logs
archive-cli logs export \
    --start-date $DATE \
    --end-date $DATE \
    --output "$BACKUP_DIR/audit_$DATE.csv"

# Get summary
echo "Daily Summary for $DATE:"
archive-cli logs summary --days 1

echo "Logs exported to: $BACKUP_DIR/audit_$DATE.csv"
```

### Python Script Example

```python
import subprocess
import json
from datetime import datetime, timedelta

def get_recent_logs(days=7):
    """Retrieve audit logs using CLI."""
    start = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    end = datetime.now().strftime('%Y-%m-%d')
    
    cmd = [
        'archive-cli', 'logs', 'export',
        '--start-date', start,
        '--end-date', end,
        '--output', 'temp_logs.json'
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        with open('temp_logs.json', 'r') as f:
            return json.load(f)
    else:
        print(f"Error: {result.stderr}")
        return None

logs = get_recent_logs(7)
print(f"Retrieved {len(logs)} logs")
```

---

## Troubleshooting

### CLI Command Not Found

```bash
# Ensure Click is installed
pip install click>=8.0.0 tabulate>=0.9.0

# Run with Python module syntax
python -m app.cli --help
```

### Database Connection Issues

```bash
# Check DATABASE_URL environment variable
echo $DATABASE_URL

# Verify database file exists for SQLite
ls -la ./test.db

# Test connection
archive-cli users list
```

### Permission Denied Error

```bash
# On Linux/Mac, make script executable
chmod +x archive-cli

# Run with python explicitly
python archive-cli --help
```

---

## Next Steps

- Set up automated daily audit exports
- Create scheduled backup jobs using archive-cli
- Integrate with monitoring/alerting systems
- Set up role-based access for team members
- Configure audit log retention policies

