"""
Command-line interface for Cloud Document Archive.

Provides commands for:
- File operations (copy, delete, overwrite)
- User management (create, list, delete, assign role)
- Audit log retrieval
"""

import click
import shutil
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
from tabulate import tabulate
from sqlalchemy.orm import Session

from app.database import SessionLocal, User
from app.user_management import UserManagementService, UserRole, Permission
from app.audit_service import get_audit_service, AuditEventType


@click.group()
@click.version_option()
def cli():
    """Cloud Document Archive CLI - Manage files, users, and audit logs."""
    pass


# ============================================================================
# FILE OPERATIONS
# ============================================================================

@cli.group()
def files():
    """File operations: copy, delete, overwrite."""
    pass


@files.command()
@click.argument('source', type=click.Path(exists=True))
@click.argument('destination', type=click.Path())
@click.option('--force', is_flag=True, help='Overwrite destination if it exists')
def copy(source: str, destination: str, force: bool):
    """Copy a file to a new location."""
    try:
        src_path = Path(source)
        dst_path = Path(destination)
        
        if dst_path.exists() and not force:
            click.echo(f"❌ Error: Destination '{destination}' already exists.", err=True)
            click.echo("Use --force to overwrite.", err=True)
            raise SystemExit(1)
        
        # Create destination directory if needed
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        
        if src_path.is_file():
            shutil.copy2(src_path, dst_path)
            click.echo(f"✅ File copied successfully:")
            click.echo(f"   From: {source}")
            click.echo(f"   To:   {destination}")
        elif src_path.is_dir():
            if dst_path.exists():
                shutil.rmtree(dst_path)
            shutil.copytree(src_path, dst_path)
            click.echo(f"✅ Directory copied successfully:")
            click.echo(f"   From: {source}")
            click.echo(f"   To:   {destination}")
    except Exception as e:
        click.echo(f"❌ Error copying file: {str(e)}", err=True)
        raise SystemExit(1)


@files.command()
@click.argument('path', type=click.Path(exists=True))
@click.option('--recursive', '-r', is_flag=True, help='Delete directory recursively')
@click.option('--force', '-f', is_flag=True, help='Skip confirmation')
def delete(path: str, recursive: bool, force: bool):
    """Delete a file or directory."""
    try:
        file_path = Path(path)
        
        if not force:
            click.confirm(f"Are you sure you want to delete '{path}'?", abort=True)
        
        if file_path.is_file():
            file_path.unlink()
            click.echo(f"✅ File deleted: {path}")
        elif file_path.is_dir():
            if not recursive:
                click.echo(f"❌ Error: '{path}' is a directory. Use --recursive to delete.", err=True)
                raise SystemExit(1)
            shutil.rmtree(file_path)
            click.echo(f"✅ Directory deleted: {path}")
    except Exception as e:
        click.echo(f"❌ Error deleting file: {str(e)}", err=True)
        raise SystemExit(1)


@files.command()
@click.argument('source', type=click.Path(exists=True))
@click.argument('destination', type=click.Path())
@click.option('--backup', is_flag=True, help='Backup destination if it exists')
def overwrite(source: str, destination: str, backup: bool):
    """Overwrite a file at destination with source file."""
    try:
        src_path = Path(source)
        dst_path = Path(destination)
        
        if not src_path.is_file():
            click.echo(f"❌ Error: Source '{source}' is not a file.", err=True)
            raise SystemExit(1)
        
        # Backup existing file if requested
        if dst_path.exists() and backup:
            backup_path = Path(f"{destination}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            shutil.copy2(dst_path, backup_path)
            click.echo(f"📦 Backup created: {backup_path}")
        
        # Create destination directory if needed
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Overwrite the file
        shutil.copy2(src_path, dst_path)
        click.echo(f"✅ File overwritten successfully:")
        click.echo(f"   Source:      {source}")
        click.echo(f"   Destination: {destination}")
    except Exception as e:
        click.echo(f"❌ Error overwriting file: {str(e)}", err=True)
        raise SystemExit(1)


# ============================================================================
# USER MANAGEMENT
# ============================================================================

@cli.group()
def users():
    """User management: create, list, delete, assign role."""
    pass


@users.command()
@click.option('--username', prompt='Username', help='User login name')
@click.option('--email', prompt='Email', help='User email address')
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True, help='User password')
@click.option('--role', type=click.Choice(['admin', 'archive_manager', 'auditor', 'user', 'viewer']),
              default='user', help='User role')
def create(username: str, email: str, password: str, role: str):
    """Create a new user."""
    try:
        db = SessionLocal()
        service = UserManagementService(db)
        
        # Check if user exists
        existing = service.get_user_by_username(username)
        if existing:
            click.echo(f"❌ Error: User '{username}' already exists.", err=True)
            db.close()
            raise SystemExit(1)
        
        # Create user
        result = service.create_user(
            username=username,
            email=email,
            password=password,
            role=UserRole[role.upper()]
        )
        
        if "error" in result:
            click.echo(f"❌ Error: {result['error']}", err=True)
            db.close()
            raise SystemExit(1)
        
        click.echo(f"✅ User created successfully:")
        click.echo(f"   User ID:  {result['id']}")
        click.echo(f"   Username: {result['username']}")
        click.echo(f"   Email:    {result['email']}")
        click.echo(f"   Role:     {result['role']}")
        db.close()
    except Exception as e:
        click.echo(f"❌ Error creating user: {str(e)}", err=True)
        raise SystemExit(1)


@users.command()
@click.option('--limit', default=10, help='Number of users to display')
def list(limit: int):
    """List all users."""
    try:
        db = SessionLocal()
        users_list = db.query(User).limit(limit).all()
        
        if not users_list:
            click.echo("No users found.")
            db.close()
            return
        
        table_data = [
            [u.id, u.username, u.email, u.role, "✓" if u.is_active else "✗", u.created_at]
            for u in users_list
        ]
        
        click.echo(f"\n📋 Users (showing {len(users_list)} of {db.query(User).count()}):\n")
        click.echo(tabulate(table_data, headers=["ID", "Username", "Email", "Role", "Active", "Created"],
                           tablefmt="grid"))
        click.echo()
        db.close()
    except Exception as e:
        click.echo(f"❌ Error listing users: {str(e)}", err=True)
        raise SystemExit(1)


@users.command()
@click.argument('username')
@click.option('--force', '-f', is_flag=True, help='Skip confirmation')
def delete_user(username: str, force: bool):
    """Delete a user by username."""
    try:
        db = SessionLocal()
        service = UserManagementService(db)
        
        user = service.get_user_by_username(username)
        if not user:
            click.echo(f"❌ Error: User '{username}' not found.", err=True)
            db.close()
            raise SystemExit(1)
        
        if not force:
            click.confirm(f"Are you sure you want to delete user '{username}'?", abort=True)
        
        result = service.delete_user(user.id)
        
        if "error" in result:
            click.echo(f"❌ Error: {result['error']}", err=True)
            db.close()
            raise SystemExit(1)
        
        click.echo(f"✅ User '{username}' deleted successfully.")
        db.close()
    except Exception as e:
        click.echo(f"❌ Error deleting user: {str(e)}", err=True)
        raise SystemExit(1)


@users.command()
@click.argument('username')
@click.option('--role', type=click.Choice(['admin', 'archive_manager', 'auditor', 'user', 'viewer']),
              required=True, help='New role')
def assign_role(username: str, role: str):
    """Assign a role to a user."""
    try:
        db = SessionLocal()
        service = UserManagementService(db)
        
        user = service.get_user_by_username(username)
        if not user:
            click.echo(f"❌ Error: User '{username}' not found.", err=True)
            db.close()
            raise SystemExit(1)
        
        result = service.assign_role(user.id, UserRole[role.upper()])
        
        if "error" in result:
            click.echo(f"❌ Error: {result['error']}", err=True)
            db.close()
            raise SystemExit(1)
        
        click.echo(f"✅ Role assigned successfully:")
        click.echo(f"   Username: {result['username']}")
        click.echo(f"   New Role: {result['role']}")
        db.close()
    except Exception as e:
        click.echo(f"❌ Error assigning role: {str(e)}", err=True)
        raise SystemExit(1)


@users.command()
@click.argument('username')
def info(username: str):
    """Get detailed information about a user."""
    try:
        db = SessionLocal()
        service = UserManagementService(db)
        
        user = service.get_user_by_username(username)
        if not user:
            click.echo(f"❌ Error: User '{username}' not found.", err=True)
            db.close()
            raise SystemExit(1)
        
        permissions = service.get_user_permissions(user.id)
        
        click.echo(f"\n👤 User Information:\n")
        click.echo(f"  ID:        {user.id}")
        click.echo(f"  Username:  {user.username}")
        click.echo(f"  Email:     {user.email}")
        click.echo(f"  Role:      {user.role}")
        click.echo(f"  Active:    {'Yes' if user.is_active else 'No'}")
        click.echo(f"  Created:   {user.created_at}")
        click.echo(f"  Updated:   {user.updated_at}")
        
        if permissions:
            click.echo(f"\n  Permissions ({len(permissions)}):")
            for perm in sorted(permissions):
                click.echo(f"    • {perm}")
        click.echo()
        db.close()
    except Exception as e:
        click.echo(f"❌ Error retrieving user info: {str(e)}", err=True)
        raise SystemExit(1)


# ============================================================================
# AUDIT LOG RETRIEVAL
# ============================================================================

@cli.group()
def logs():
    """Audit log retrieval and filtering."""
    pass


@logs.command()
@click.option('--start-date', type=str, help='Start date (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)')
@click.option('--end-date', type=str, help='End date (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)')
@click.option('--event-type', type=str, help='Filter by event type')
@click.option('--user-id', type=int, help='Filter by user ID')
@click.option('--resource-type', type=str, help='Filter by resource type')
@click.option('--status', type=click.Choice(['success', 'failure', 'partial']), help='Filter by status')
@click.option('--limit', default=50, help='Number of logs to display')
@click.option('--offset', default=0, help='Number of logs to skip')
def retrieve(start_date: Optional[str], end_date: Optional[str], event_type: Optional[str],
             user_id: Optional[int], resource_type: Optional[str], status: Optional[str],
             limit: int, offset: int):
    """Retrieve audit logs with optional filtering."""
    try:
        # Parse dates
        start = None
        end = None
        
        if start_date:
            try:
                # Support both YYYY-MM-DD and YYYY-MM-DDTHH:MM:SS formats
                if 'T' in start_date:
                    start = datetime.fromisoformat(start_date)
                else:
                    start = datetime.fromisoformat(f"{start_date}T00:00:00")
            except ValueError:
                click.echo(f"❌ Error: Invalid start_date format. Use YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS", err=True)
                raise SystemExit(1)
        
        if end_date:
            try:
                if 'T' in end_date:
                    end = datetime.fromisoformat(end_date)
                else:
                    end = datetime.fromisoformat(f"{end_date}T23:59:59")
            except ValueError:
                click.echo(f"❌ Error: Invalid end_date format. Use YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS", err=True)
                raise SystemExit(1)
        
        # Get logs
        audit_service = get_audit_service()
        logs_list = audit_service.get_audit_logs(
            event_type=event_type,
            user_id=user_id,
            resource_type=resource_type,
            status=status,
            start_date=start,
            end_date=end,
            offset=offset,
            limit=limit
        )
        
        if not logs_list:
            click.echo("📭 No audit logs found matching the criteria.")
            return
        
        # Format table data
        table_data = []
        for log in logs_list:
            timestamp = str(getattr(log, 'created_at', getattr(log, 'timestamp', '')))
            # Truncate timestamp for display
            if len(timestamp) > 19:
                timestamp = timestamp[:19]
            
            table_data.append([
                log.id,
                timestamp,
                log.event_type,
                log.username or 'N/A',
                log.status,
                log.resource_type,
                log.action
            ])
        
        click.echo(f"\n📊 Audit Logs (showing {len(logs_list)} logs):\n")
        click.echo(tabulate(table_data, 
                           headers=["ID", "Timestamp", "Event Type", "User", "Status", "Resource", "Action"],
                           tablefmt="grid"))
        
        click.echo(f"\n✓ Total records retrieved: {len(logs_list)}")
        if offset > 0:
            click.echo(f"  (Offset: {offset})")
        click.echo()
    except Exception as e:
        click.echo(f"❌ Error retrieving logs: {str(e)}", err=True)
        raise SystemExit(1)


@logs.command()
@click.option('--days', default=7, help='Number of days to look back')
@click.option('--event-type', type=str, help='Filter by event type')
def summary(days: int, event_type: Optional[str]):
    """Display a summary of recent audit logs."""
    try:
        start_date = datetime.now() - timedelta(days=days)
        
        audit_service = get_audit_service()
        logs_list = audit_service.get_audit_logs(
            start_date=start_date,
            event_type=event_type,
            limit=1000
        )
        
        if not logs_list:
            click.echo(f"No audit logs found for the last {days} days.")
            return
        
        # Count by event type
        event_counts = {}
        status_counts = {'success': 0, 'failure': 0, 'partial': 0}
        user_counts = {}
        
        for log in logs_list:
            event_counts[log.event_type] = event_counts.get(log.event_type, 0) + 1
            status_counts[log.status] = status_counts.get(log.status, 0) + 1
            user_counts[log.username] = user_counts.get(log.username, 0) + 1
        
        click.echo(f"\n📈 Audit Log Summary (Last {days} days):\n")
        
        # Event types
        click.echo("Event Types:")
        for event, count in sorted(event_counts.items(), key=lambda x: x[1], reverse=True):
            click.echo(f"  • {event}: {count}")
        
        # Status summary
        click.echo("\nStatus Summary:")
        for status, count in status_counts.items():
            if count > 0:
                click.echo(f"  • {status}: {count}")
        
        # Top users
        click.echo("\nTop Users:")
        for user, count in sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
            click.echo(f"  • {user}: {count} actions")
        
        click.echo(f"\nTotal Events: {len(logs_list)}\n")
    except Exception as e:
        click.echo(f"❌ Error generating summary: {str(e)}", err=True)
        raise SystemExit(1)


@logs.command()
@click.option('--start-date', type=str, required=True, help='Start date (YYYY-MM-DD)')
@click.option('--end-date', type=str, required=True, help='End date (YYYY-MM-DD)')
@click.option('--output', type=click.Path(), required=True, help='Output file path (CSV or JSON)')
def export(start_date: str, end_date: str, output: str):
    """Export audit logs to file (CSV or JSON)."""
    try:
        import json
        import csv
        
        # Parse dates
        try:
            start = datetime.fromisoformat(f"{start_date}T00:00:00")
            end = datetime.fromisoformat(f"{end_date}T23:59:59")
        except ValueError:
            click.echo("❌ Error: Invalid date format. Use YYYY-MM-DD", err=True)
            raise SystemExit(1)
        
        # Get logs
        audit_service = get_audit_service()
        logs_list = audit_service.get_audit_logs(
            start_date=start,
            end_date=end,
            limit=10000
        )
        
        if not logs_list:
            click.echo(f"No audit logs found between {start_date} and {end_date}.")
            return
        
        # Prepare data
        logs_data = []
        for log in logs_list:
            logs_data.append({
                'id': log.id,
                'timestamp': str(getattr(log, 'created_at', getattr(log, 'timestamp', ''))),
                'event_type': log.event_type,
                'user_id': log.user_id,
                'username': log.username,
                'resource_type': log.resource_type,
                'resource_id': log.resource_id,
                'action': log.action,
                'status': log.status,
                'ip_address': log.ip_address,
                'http_method': log.http_method,
                'http_endpoint': log.http_endpoint,
                'http_status': log.http_status,
                'details': str(log.details) if hasattr(log, 'details') else ''
            })
        
        # Export
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if output.endswith('.json'):
            with open(output_path, 'w') as f:
                json.dump(logs_data, f, indent=2)
            click.echo(f"✅ Exported {len(logs_data)} logs to JSON: {output}")
        
        elif output.endswith('.csv'):
            with open(output_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=logs_data[0].keys())
                writer.writeheader()
                writer.writerows(logs_data)
            click.echo(f"✅ Exported {len(logs_data)} logs to CSV: {output}")
        
        else:
            click.echo("❌ Error: Output file must end with .json or .csv", err=True)
            raise SystemExit(1)
    
    except Exception as e:
        click.echo(f"❌ Error exporting logs: {str(e)}", err=True)
        raise SystemExit(1)


# ============================================================================
# HELPER COMMANDS
# ============================================================================

@cli.command()
def init():
    """Initialize the application (create database, tables, admin user)."""
    try:
        from app.database import Base, engine
        
        click.echo("🔧 Initializing Cloud Document Archive...\n")
        
        # Create tables
        click.echo("📦 Creating database tables...")
        Base.metadata.create_all(bind=engine)
        click.echo("✅ Database tables created.")
        
        # Create admin user
        db = SessionLocal()
        admin_exists = db.query(User).filter(User.username == "admin").first()
        
        if not admin_exists:
            click.echo("\n👤 Creating admin user...")
            admin_username = click.prompt("Admin username", default="admin")
            admin_email = click.prompt("Admin email", default="admin@example.com")
            admin_password = click.prompt("Admin password", hide_input=True, confirmation_prompt=True)
            
            service = UserManagementService(db)
            result = service.create_user(
                username=admin_username,
                email=admin_email,
                password=admin_password,
                role=UserRole.ADMIN
            )
            
            click.echo(f"✅ Admin user created: {result['username']}")
        else:
            click.echo("✅ Admin user already exists.")
        
        db.close()
        click.echo("\n✅ Initialization complete!\n")
    except Exception as e:
        click.echo(f"❌ Error during initialization: {str(e)}", err=True)
        raise SystemExit(1)


@cli.command()
def version():
    """Show version information."""
    click.echo("Cloud Document Archive v2.0.0")
    click.echo("with User Management, Authentication, and Audit Trail")


if __name__ == '__main__':
    cli()
