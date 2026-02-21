"""Tests for database models and operations."""

import pytest
from app.database import User, DocumentMetadata, AuditLogEntry
from app.user_management import UserManagementService


class TestUserModel:
    """Test User database model."""
    
    def test_user_creation(self, test_db_session):
        """Test creating a user in database."""
        user = User(
            username="newuser",
            email="new@example.com",
            full_name="New User",
            password_hash="hash123",
            role="user",
            is_active=True
        )
        
        test_db_session.add(user)
        test_db_session.commit()
        
        assert user.id is not None
        assert user.username == "newuser"
        assert user.email == "new@example.com"
    
    def test_user_fields(self, test_db_session):
        """Test user model fields."""
        user = test_db_session.query(User).filter(User.username == "admin").first()
        
        assert user.id is not None
        assert user.username == "admin"
        assert user.email == "admin@example.com"
        assert user.full_name is not None
        assert user.password_hash is not None
        assert user.role == "admin"
        assert user.is_active is True
    
    def test_user_created_at(self, test_db_session):
        """Test user created_at timestamp."""
        user = test_db_session.query(User).filter(User.username == "admin").first()
        
        assert user.created_at is not None
    
    def test_user_updated_at(self, test_db_session):
        """Test user updated_at timestamp."""
        user = test_db_session.query(User).filter(User.username == "admin").first()
        
        assert user.updated_at is not None
    
    def test_user_roles(self, test_db_session):
        """Test different user roles."""
        roles = ["admin", "archive_manager", "auditor", "user", "viewer"]
        
        for i, role in enumerate(roles):
            user = User(
                username=f"user_{i}",
                email=f"user{i}@example.com",
                password_hash="hash",
                role=role
            )
            test_db_session.add(user)
        
        test_db_session.commit()
        
        for i, role in enumerate(roles):
            user = test_db_session.query(User).filter(User.username == f"user_{i}").first()
            assert user.role == role
    
    def test_user_is_active_flag(self, test_db_session):
        """Test user is_active flag."""
        # Active user
        active_user = User(
            username="active",
            email="active@example.com",
            password_hash="hash",
            is_active=True
        )
        test_db_session.add(active_user)
        
        # Inactive user
        inactive_user = User(
            username="inactive",
            email="inactive@example.com",
            password_hash="hash",
            is_active=False
        )
        test_db_session.add(inactive_user)
        test_db_session.commit()
        
        active = test_db_session.query(User).filter(User.username == "active").first()
        inactive = test_db_session.query(User).filter(User.username == "inactive").first()
        
        assert active.is_active is True
        assert inactive.is_active is False


class TestDocumentMetadataModel:
    """Test DocumentMetadata model."""
    
    def test_document_metadata_creation(self, test_db_session, test_client, admin_token):
        """Test creating document metadata."""
        doc = DocumentMetadata(
            document_id="doc_123",
            file_name="test.pdf",
            content_type="application/pdf",
            size_bytes=1024,
            storage_provider="local",
            stored_path="/data/documents/doc_123.pdf",
            storage_tier="standard",
            user_id=1
        )
        
        test_db_session.add(doc)
        test_db_session.commit()
        
        assert doc.id is not None
        assert doc.document_id == "doc_123"
        assert doc.file_name == "test.pdf"
    
    def test_document_metadata_fields(self, test_db_session):
        """Test document metadata fields."""
        doc = DocumentMetadata(
            document_id="doc_456",
            file_name="data.xlsx",
            content_type="application/vnd.ms-excel",
            size_bytes=2048,
            storage_provider="aws_s3",
            stored_path="s3://bucket/doc_456.xlsx",
            storage_tier="archive",
            user_id=1,
            metadata_json='{"key": "value"}',
            tags="important,sensitive"
        )
        
        test_db_session.add(doc)
        test_db_session.commit()
        
        retrieved = test_db_session.query(DocumentMetadata).filter(
            DocumentMetadata.document_id == "doc_456"
        ).first()
        
        assert retrieved.file_name == "data.xlsx"
        assert retrieved.size_bytes == 2048
        assert retrieved.storage_provider == "aws_s3"
        assert retrieved.storage_tier == "archive"
    
    def test_document_restore_status(self, test_db_session):
        """Test document restore status field."""
        statuses = ["not_archived", "restoring", "restored", "archived"]
        
        for i, status in enumerate(statuses):
            doc = DocumentMetadata(
                document_id=f"doc_{i}",
                file_name=f"file_{i}.txt",
                content_type="text/plain",
                size_bytes=100,
                storage_provider="local",
                stored_path=f"/data/doc_{i}.txt",
                restore_status=status,
                user_id=1
            )
            test_db_session.add(doc)
        
        test_db_session.commit()
        
        for i, status in enumerate(statuses):
            doc = test_db_session.query(DocumentMetadata).filter(
                DocumentMetadata.document_id == f"doc_{i}"
            ).first()
            assert doc.restore_status == status
    
    def test_document_timestamps(self, test_db_session):
        """Test document created_at and updated_at."""
        doc = DocumentMetadata(
            document_id="doc_789",
            file_name="timestamp_test.txt",
            content_type="text/plain",
            size_bytes=50,
            storage_provider="local",
            stored_path="/data/timestamp_test.txt",
            user_id=1
        )
        
        test_db_session.add(doc)
        test_db_session.commit()
        
        assert doc.created_at is not None
        assert doc.updated_at is not None


class TestAuditLogEntryModel:
    """Test AuditLogEntry model."""
    
    def test_audit_log_entry_creation(self, test_db_session):
        """Test creating audit log entry."""
        entry = AuditLogEntry(
            event_type="login",
            user_id=1,
            username="admin",
            resource_type="authentication",
            resource_id="",
            action="login",
            status="success",
            ip_address="127.0.0.1",
            user_agent="Mozilla/5.0"
        )
        
        test_db_session.add(entry)
        test_db_session.commit()
        
        assert entry.id is not None
        assert entry.event_type == "login"
        assert entry.username == "admin"
    
    def test_audit_log_entry_fields(self, test_db_session):
        """Test audit log entry fields."""
        entry = AuditLogEntry(
            event_type="document_upload",
            user_id=1,
            username="admin",
            resource_type="document",
            resource_id="doc_123",
            action="upload",
            status="success",
            details='{"size": 1024}',
            ip_address="192.168.1.1",
            user_agent="Chrome/120.0"
        )
        
        test_db_session.add(entry)
        test_db_session.commit()
        
        retrieved = test_db_session.query(AuditLogEntry).filter(
            AuditLogEntry.event_type == "document_upload"
        ).first()
        
        assert retrieved.resource_type == "document"
        assert retrieved.resource_id == "doc_123"
        assert retrieved.status == "success"
    
    def test_audit_log_timestamp(self, test_db_session):
        """Test audit log entry timestamp."""
        entry = AuditLogEntry(
            event_type="login",
            user_id=1,
            username="admin",
            action="login",
            status="success"
        )
        
        test_db_session.add(entry)
        test_db_session.commit()
        
        assert entry.created_at is not None


class TestDatabaseQueries:
    """Test database query operations."""
    
    def test_query_user_by_username(self, test_db_session):
        """Test querying user by username."""
        user = test_db_session.query(User).filter(User.username == "admin").first()
        
        assert user is not None
        assert user.username == "admin"
    
    def test_query_active_users(self, test_db_session):
        """Test querying active users."""
        active_users = test_db_session.query(User).filter(User.is_active == True).all()
        
        assert len(active_users) >= 2  # admin and testuser
    
    def test_query_users_by_role(self, test_db_session):
        """Test querying users by role."""
        admins = test_db_session.query(User).filter(User.role == "admin").all()
        
        assert len(admins) >= 1
        assert all(u.role == "admin" for u in admins)
    
    def test_count_total_users(self, test_db_session):
        """Test counting total users."""
        from sqlalchemy import func
        
        count = test_db_session.query(func.count(User.id)).scalar()
        
        assert count >= 2
    
    def test_delete_user(self, test_db_session):
        """Test deleting a user."""
        # Create a user to delete
        user = User(
            username="todelete",
            email="delete@example.com",
            password_hash="hash",
            role="user"
        )
        test_db_session.add(user)
        test_db_session.commit()
        user_id = user.id
        
        # Delete it
        test_db_session.query(User).filter(User.id == user_id).delete()
        test_db_session.commit()
        
        # Verify it's deleted
        deleted = test_db_session.query(User).filter(User.id == user_id).first()
        assert deleted is None
    
    def test_update_user(self, test_db_session):
        """Test updating a user."""
        user = test_db_session.query(User).filter(User.username == "testuser").first()
        
        original_email = user.email
        user.email = "newemail@example.com"
        test_db_session.commit()
        
        # Verify update
        updated = test_db_session.query(User).filter(User.username == "testuser").first()
        assert updated.email == "newemail@example.com"
        assert updated.email != original_email


class TestDatabaseConstraints:
    """Test database constraints and validations."""
    
    def test_user_username_uniqueness(self, test_db_session):
        """Test username uniqueness constraint."""
        # Try to create user with duplicate username
        duplicate = User(
            username="admin",
            email="duplicate@example.com",
            password_hash="hash",
            role="user"
        )
        test_db_session.add(duplicate)
        
        with pytest.raises(Exception):  # IntegrityError
            test_db_session.commit()
        
        test_db_session.rollback()
    
    def test_user_email_uniqueness(self, test_db_session):
        """Test email uniqueness constraint."""
        # Try to create user with duplicate email
        duplicate = User(
            username="newuser",
            email="admin@example.com",  # Duplicate
            password_hash="hash",
            role="user"
        )
        test_db_session.add(duplicate)
        
        with pytest.raises(Exception):  # IntegrityError
            test_db_session.commit()
        
        test_db_session.rollback()
    
    def test_user_not_null_constraints(self, test_db_session):
        """Test not null constraints on users."""
        incomplete_user = User(
            email="incomplete@example.com",
            # Missing: username, password_hash, role
        )
        test_db_session.add(incomplete_user)
        
        with pytest.raises(Exception):
            test_db_session.commit()
        
        test_db_session.rollback()
