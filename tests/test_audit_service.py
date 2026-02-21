"""Tests for audit service functionality."""

import pytest
from datetime import datetime
from app.audit_service import (
    AuditService, AuditLog, AuditEventType, AuditStatus
)


class TestAuditLog:
    """Test AuditLog class."""
    
    def test_create_audit_log(self):
        """Test creating an audit log entry."""
        audit_log = AuditLog(
            event_type=AuditEventType.LOGIN,
            user_id="user_123",
            username="testuser",
            resource_type="authentication",
            resource_id="",
            action="login",
            status=AuditStatus.SUCCESS,
            details={"ip": "127.0.0.1"},
            ip_address="127.0.0.1",
            user_agent="Mozilla/5.0"
        )
        
        assert audit_log.event_type == AuditEventType.LOGIN
        assert audit_log.user_id == "user_123"
        assert audit_log.username == "testuser"
        assert audit_log.status == AuditStatus.SUCCESS
    
    def test_audit_log_to_dict(self):
        """Test converting audit log to dictionary."""
        audit_log = AuditLog(
            event_type=AuditEventType.DOCUMENT_UPLOAD,
            user_id="user_123",
            username="testuser",
            resource_type="document",
            resource_id="doc_456",
            action="upload",
            status=AuditStatus.SUCCESS,
            details={"size": 1024}
        )
        
        log_dict = audit_log.to_dict()
        
        assert log_dict["event_type"] == "document_upload"
        assert log_dict["user_id"] == "user_123"
        assert log_dict["username"] == "testuser"
        assert log_dict["status"] == "success"
        assert "details" in log_dict
    
    def test_audit_log_to_json(self):
        """Test converting audit log to JSON."""
        audit_log = AuditLog(
            event_type=AuditEventType.USER_CREATE,
            user_id="admin_123",
            username="admin",
            resource_type="user",
            resource_id="user_789",
            action="create",
            status=AuditStatus.SUCCESS
        )
        
        json_str = audit_log.to_json()
        
        assert isinstance(json_str, str)
        assert "event_type" in json_str
        assert "user_create" in json_str
        assert "admin" in json_str


class TestAuditEventTypes:
    """Test audit event types."""
    
    def test_all_event_types_exist(self):
        """Test all expected event types are defined."""
        expected_types = [
            "LOGIN", "LOGOUT", "LOGIN_FAILED", "TOKEN_REFRESH",
            "DOCUMENT_UPLOAD", "DOCUMENT_RETRIEVE", "DOCUMENT_DELETE",
            "DOCUMENT_ARCHIVE", "DOCUMENT_RESTORE",
            "USER_CREATE", "USER_UPDATE", "USER_DELETE",
            "USER_ROLE_ASSIGN", "USER_ROLE_REVOKE",
            "ROLE_CREATE", "ROLE_UPDATE", "ROLE_DELETE",
            "PERMISSION_GRANT", "PERMISSION_REVOKE",
            "ACCESS_DENIED", "UNAUTHORIZED_ACCESS",
            "CONFIGURATION_CHANGE", "SYSTEM_ERROR", "ENCRYPTION_KEY_ACCESS"
        ]
        
        for event_name in expected_types:
            assert hasattr(AuditEventType, event_name)
    
    def test_event_type_values(self):
        """Test event type values are correct strings."""
        assert AuditEventType.LOGIN.value == "login"
        assert AuditEventType.LOGOUT.value == "logout"
        assert AuditEventType.DOCUMENT_UPLOAD.value == "document_upload"
        assert AuditEventType.USER_CREATE.value == "user_create"
    
    def test_event_type_enum_iteration(self):
        """Test iterating through event types."""
        event_types = list(AuditEventType)
        
        assert len(event_types) > 0
        assert all(isinstance(e, AuditEventType) for e in event_types)


class TestAuditStatus:
    """Test audit status types."""
    
    def test_status_values(self):
        """Test audit status values."""
        assert AuditStatus.SUCCESS.value == "success"
        assert AuditStatus.FAILURE.value == "failure"
        assert AuditStatus.PARTIAL.value == "partial"
    
    def test_status_enum(self):
        """Test status enum."""
        statuses = [AuditStatus.SUCCESS, AuditStatus.FAILURE, AuditStatus.PARTIAL]
        assert len(statuses) == 3


class TestAuditService:
    """Test audit service."""
    
    def test_create_audit_service(self):
        """Test creating audit service."""
        service = AuditService()
        
        assert service is not None
        assert service.logger is not None
    
    def test_log_event(self):
        """Test logging an audit event."""
        service = AuditService()
        
        audit_log = AuditLog(
            event_type=AuditEventType.LOGIN,
            user_id="user_123",
            username="testuser",
            action="login",
            status=AuditStatus.SUCCESS
        )
        
        # Should not raise an exception
        service.log_event(audit_log)
    
    def test_format_log_message(self):
        """Test formatting log message."""
        service = AuditService()
        
        audit_log = AuditLog(
            event_type=AuditEventType.LOGIN,
            user_id="user_123",
            username="testuser",
            resource_type="authentication",
            resource_id="",
            action="login",
            status=AuditStatus.SUCCESS,
            ip_address="192.168.1.1"
        )
        
        message = service._format_log_message(audit_log)
        
        assert "login" in message.lower()
        assert "testuser" in message
        assert "success" in message.lower()
        assert "192.168.1.1" in message
    
    def test_log_message_with_details(self):
        """Test log message includes details."""
        service = AuditService()
        
        audit_log = AuditLog(
            event_type=AuditEventType.DOCUMENT_UPLOAD,
            user_id="user_123",
            username="testuser",
            action="upload",
            status=AuditStatus.SUCCESS,
            details={"file_size": 1024, "format": "pdf"}
        )
        
        message = service._format_log_message(audit_log)
        
        assert "file_size" in message


class TestAuditLogging:
    """Test audit logging scenarios."""
    
    def test_login_audit_log(self):
        """Test login audit log."""
        audit_log = AuditLog(
            event_type=AuditEventType.LOGIN,
            user_id="user_123",
            username="john_doe",
            resource_type="authentication",
            action="login",
            status=AuditStatus.SUCCESS,
            ip_address="10.0.0.1",
            details={"mfa_used": True}
        )
        
        assert audit_log.event_type == AuditEventType.LOGIN
        assert audit_log.username == "john_doe"
        assert audit_log.details["mfa_used"] is True
    
    def test_failed_login_audit_log(self):
        """Test failed login audit log."""
        audit_log = AuditLog(
            event_type=AuditEventType.LOGIN_FAILED,
            username="john_doe",
            resource_type="authentication",
            action="login",
            status=AuditStatus.FAILURE,
            ip_address="10.0.0.1",
            details={"reason": "invalid_credentials"}
        )
        
        assert audit_log.event_type == AuditEventType.LOGIN_FAILED
        assert audit_log.status == AuditStatus.FAILURE
        assert audit_log.details["reason"] == "invalid_credentials"
    
    def test_document_operations_audit_log(self):
        """Test document operation audit logs."""
        operations = [
            (AuditEventType.DOCUMENT_UPLOAD, "upload"),
            (AuditEventType.DOCUMENT_RETRIEVE, "retrieve"),
            (AuditEventType.DOCUMENT_DELETE, "delete"),
            (AuditEventType.DOCUMENT_ARCHIVE, "archive"),
        ]
        
        for event_type, action in operations:
            audit_log = AuditLog(
                event_type=event_type,
                user_id="user_123",
                username="testuser",
                resource_type="document",
                resource_id="doc_456",
                action=action,
                status=AuditStatus.SUCCESS
            )
            
            assert audit_log.event_type == event_type
            assert audit_log.resource_id == "doc_456"
    
    def test_user_management_audit_log(self):
        """Test user management audit logs."""
        operations = [
            (AuditEventType.USER_CREATE, "create"),
            (AuditEventType.USER_UPDATE, "update"),
            (AuditEventType.USER_DELETE, "delete"),
            (AuditEventType.USER_ROLE_ASSIGN, "assign_role"),
        ]
        
        for event_type, action in operations:
            audit_log = AuditLog(
                event_type=event_type,
                user_id="admin_123",
                username="admin",
                resource_type="user",
                resource_id="user_789",
                action=action,
                status=AuditStatus.SUCCESS
            )
            
            assert audit_log.event_type == event_type
            assert audit_log.resource_type == "user"


class TestAuditLogTimestamp:
    """Test audit log timestamps."""
    
    def test_default_timestamp(self):
        """Test audit log has default timestamp."""
        before = datetime.utcnow()
        audit_log = AuditLog(
            event_type=AuditEventType.LOGIN,
            user_id="user_123",
            username="testuser"
        )
        after = datetime.utcnow()
        
        assert audit_log.timestamp is not None
        assert before <= audit_log.timestamp <= after
    
    def test_custom_timestamp(self):
        """Test audit log accepts custom timestamp."""
        custom_time = datetime(2026, 2, 21, 10, 30, 0)
        audit_log = AuditLog(
            event_type=AuditEventType.LOGIN,
            user_id="user_123",
            username="testuser",
            timestamp=custom_time
        )
        
        assert audit_log.timestamp == custom_time
