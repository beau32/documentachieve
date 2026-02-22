"""Audit logging service for tracking API calls and system operations."""

import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

logger = logging.getLogger(__name__)


class AuditEventType(str, Enum):
    """Types of events that can be audited."""
    # Authentication events
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    TOKEN_REFRESH = "token_refresh"
    
    # Document operations
    DOCUMENT_UPLOAD = "document_upload"
    DOCUMENT_RETRIEVE = "document_retrieve"
    DOCUMENT_DELETE = "document_delete"
    DOCUMENT_ARCHIVE = "document_archive"
    DOCUMENT_RESTORE = "document_restore"
    
    # User management
    USER_CREATE = "user_create"
    USER_UPDATE = "user_update"
    USER_DELETE = "user_delete"
    USER_ROLE_ASSIGN = "user_role_assign"
    USER_ROLE_REVOKE = "user_role_revoke"
    
    # Role/Permission management
    ROLE_CREATE = "role_create"
    ROLE_UPDATE = "role_update"
    ROLE_DELETE = "role_delete"
    PERMISSION_GRANT = "permission_grant"
    PERMISSION_REVOKE = "permission_revoke"
    
    # Access control
    ACCESS_DENIED = "access_denied"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    
    # System operations
    CONFIGURATION_CHANGE = "configuration_change"
    SYSTEM_ERROR = "system_error"
    ENCRYPTION_KEY_ACCESS = "encryption_key_access"


class AuditStatus(str, Enum):
    """Status of audit events."""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"


class AuditLog:
    """Represents an audit log entry."""
    
    def __init__(
        self,
        event_type: AuditEventType,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        action: Optional[str] = None,
        status: AuditStatus = AuditStatus.SUCCESS,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ):
        """
        Initialize audit log entry.
        
        Args:
            event_type: Type of event
            user_id: ID of user performing action
            username: Username of user
            resource_type: Type of resource accessed (document, user, role, etc.)
            resource_id: ID of resource accessed
            action: Action performed
            status: Status of action (success, failure, partial)
            details: Additional details about the event
            ip_address: Client IP address
            user_agent: Client user agent
            timestamp: Timestamp of event
        """
        self.event_type = event_type
        self.user_id = user_id
        self.username = username
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.action = action
        self.status = status
        self.details = details or {}
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.timestamp = timestamp or datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            "event_type": self.event_type.value,
            "user_id": self.user_id,
            "username": self.username,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "action": self.action,
            "status": self.status.value,
            "details": json.dumps(self.details),
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "timestamp": self.timestamp,
        }
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        data = self.to_dict()
        data["timestamp"] = self.timestamp.isoformat()
        return json.dumps(data)


class AuditService:
    """Service for logging and retrieving audit events."""
    
    def __init__(self):
        """Initialize audit service."""
        self.logger = logging.getLogger("audit")
        
        # Create audit logger if it doesn't exist
        if not self.logger.handlers:
            handler = logging.FileHandler("audit.log")
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def log_event(self, audit_log: AuditLog) -> None:
        """
        Log an audit event.
        
        Args:
            audit_log: AuditLog instance to log
        """
        try:
            # Log to file
            log_message = self._format_log_message(audit_log)
            self.logger.info(log_message)
            
            # Also log to database (if database session available)
            self._log_to_database(audit_log)
        
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
    
    def _format_log_message(self, audit_log: AuditLog) -> str:
        """Format audit log entry for logging."""
        parts = [
            f"EventType={audit_log.event_type.value}",
            f"User={audit_log.username or audit_log.user_id or 'UNKNOWN'}",
            f"Status={audit_log.status.value}",
            f"Resource={audit_log.resource_type}:{audit_log.resource_id}" if audit_log.resource_type else "",
            f"IP={audit_log.ip_address}" if audit_log.ip_address else "",
        ]
        
        message = " | ".join(str(p) for p in parts if p)
        
        if audit_log.details:
            message += f" | Details={json.dumps(audit_log.details)}"
        
        return message
    
    def _log_to_database(self, audit_log: AuditLog) -> None:
        """Log to database."""
        try:
            from app.database import SessionLocal, AuditLogEntry
            import json
            
            db = SessionLocal()
            try:
                # Create AuditLogEntry from AuditLog
                db_log = AuditLogEntry(
                    event_type=audit_log.event_type.value if hasattr(audit_log.event_type, 'value') else str(audit_log.event_type),
                    user_id=audit_log.user_id,
                    username=audit_log.username,
                    resource_type=audit_log.resource_type,
                    resource_id=audit_log.resource_id,
                    action=audit_log.action,
                    status=audit_log.status.value if hasattr(audit_log.status, 'value') else str(audit_log.status),
                    details=json.dumps(audit_log.details) if audit_log.details else None,
                    ip_address=audit_log.ip_address,
                    user_agent=audit_log.user_agent,
                    timestamp=audit_log.timestamp if hasattr(audit_log, 'timestamp') else datetime.utcnow()
                )
                db.add(db_log)
                db.commit()
            except Exception as e:
                db.rollback()
                logger.error(f"Database error logging audit event: {e}")
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Failed to log to database: {e}")
    
    async def get_audit_logs(
        self,
        db,
        user_id: Optional[str] = None,
        event_type: Optional[str] = None,
        resource_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve audit logs with optional filters.
        
        Args:
            db: Database session
            user_id: Filter by user ID
            event_type: Filter by event type
            resource_type: Filter by resource type
            start_date: Filter by start date
            end_date: Filter by end date
            limit: Maximum number of results
            
        Returns:
            List of audit log entries
        """
        from app.database import AuditLogEntry
        from sqlalchemy import and_
        
        query = db.query(AuditLogEntry)
        
        # Apply filters
        conditions = []
        
        if user_id:
            conditions.append(AuditLogEntry.user_id == user_id)
        
        if event_type:
            conditions.append(AuditLogEntry.event_type == event_type)
        
        if resource_type:
            conditions.append(AuditLogEntry.resource_type == resource_type)
        
        if start_date:
            conditions.append(AuditLogEntry.timestamp >= start_date)
        
        if end_date:
            conditions.append(AuditLogEntry.timestamp <= end_date)
        
        if conditions:
            query = query.filter(and_(*conditions))
        
        # Order by timestamp descending and limit
        logs = query.order_by(AuditLogEntry.timestamp.desc()).limit(limit).all()
        
        return [
            {
                "id": log.id,
                "event_type": log.event_type,
                "user_id": log.user_id,
                "username": log.username,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "action": log.action,
                "status": log.status,
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
                "timestamp": log.timestamp.isoformat(),
                "details": json.loads(log.details) if log.details else {},
            }
            for log in logs
        ]


# Global audit service instance
_audit_service: Optional[AuditService] = None


def get_audit_service() -> AuditService:
    """Get or create the global audit service instance."""
    global _audit_service
    
    if _audit_service is None:
        _audit_service = AuditService()
    
    return _audit_service


def reset_audit_service():
    """Reset the global audit service (for testing)."""
    global _audit_service
    _audit_service = None
