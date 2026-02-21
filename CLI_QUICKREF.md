# CLI Quick Reference

## Installation

```bash
pip install click>=8.0.0 tabulate>=0.9.0
python -m app.cli --help
```

## File Operations

```bash
# Copy file
archive-cli files copy <source> <destination> [--force]

# Delete file
archive-cli files delete <path> [--recursive] [--force]

# Overwrite file
archive-cli files overwrite <source> <destination> [--backup]
```

## User Management

```bash
# Create user
archive-cli users create [--username] [--email] [--password] [--role]

# List users
archive-cli users list [--limit 10]

# Delete user
archive-cli users delete-user <username> [--force]

# Assign role
archive-cli users assign-role <username> --role <role>

# Get user info
archive-cli users info <username>
```

**Available Roles:** `admin`, `archive_manager`, `auditor`, `user`, `viewer`

## Audit Logs

```bash
# Retrieve logs
archive-cli logs retrieve [--start-date] [--end-date] [--event-type] 
                          [--user-id] [--resource-type] [--status] 
                          [--limit 50] [--offset 0]

# Log summary
archive-cli logs summary [--days 7] [--event-type]

# Export logs
archive-cli logs export --start-date <date> --end-date <date> --output <file>
```

**Date Format:** `YYYY-MM-DD` or `YYYY-MM-DDTHH:MM:SS`  
**Output Formats:** `.json` or `.csv`

## System

```bash
# Initialize application
archive-cli init

# Show version
archive-cli version
```

## Common Examples

### User Setup
```bash
# Create admin
archive-cli users create --username admin --role admin

# Create manager
archive-cli users create --username manager --role archive_manager

# List all users
archive-cli users list
```

### File Management
```bash
# Backup directory
archive-cli files copy /archive/docs ./backup --force

# Clean old files
archive-cli files delete /temp/old --recursive --force

# Archive with backup
archive-cli files overwrite new_docs.tar old_docs.tar --backup
```

### Audit Reports
```bash
# Today's summary
archive-cli logs summary --days 1

# Failed operations
archive-cli logs retrieve --status failure

# User activity
archive-cli logs retrieve --user-id 1 --limit 100

# Export month
archive-cli logs export --start-date 2026-02-01 --end-date 2026-02-28 --output february.csv
```

## Help

```bash
# General help
archive-cli --help

# Command group help
archive-cli files --help
archive-cli users --help
archive-cli logs --help

# Specific command help
archive-cli files copy --help
archive-cli users create --help
archive-cli logs retrieve --help
```

## Status Indicators

- `✅` - Success
- `❌` - Error  
- `📋` - List
- `📊` - Statistics
- `👤` - User info
- `📦` - Archive/backup

