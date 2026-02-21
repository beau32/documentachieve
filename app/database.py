"""Database models and session management for document metadata."""

import json
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from app.config import settings, StorageTier, RestoreStatus

# Create database engine
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {}
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


class DocumentMetadata(Base):
    """Database model for storing document metadata."""
    
    __tablename__ = "document_metadata"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(String(64), unique=True, index=True, nullable=False)
    filename = Column(String(255), nullable=False)
    content_type = Column(String(100), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    storage_provider = Column(String(50), nullable=False)
    storage_path = Column(String(500), nullable=False)
    storage_tier = Column(String(20), default=StorageTier.STANDARD.value, nullable=False)
    restore_status = Column(String(20), default=RestoreStatus.NOT_ARCHIVED.value, nullable=True)
    restore_expiry = Column(DateTime, nullable=True)  # When restored copy expires
    archived_at = Column(DateTime, nullable=True)  # When moved to deep archive
    tags_json = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=True)
    embedding = Column(Text, nullable=True)  # JSON array of embedding vector
    embedding_text = Column(Text, nullable=True)  # Text used for embedding
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Encryption fields
    is_encrypted = Column(String(5), default="false", nullable=False)  # "true" or "false" for compatibility
    encryption_algorithm = Column(String(50), nullable=True)  # e.g., "RSA", "AES-256-GCM"
    encryption_iv_or_key = Column(Text, nullable=True)  # Hex-encoded IV (AES) or encrypted key (RSA)
    encryption_tag = Column(Text, nullable=True)  # Hex-encoded authentication tag
    metadata_encrypted = Column(String(5), default="false", nullable=False)  # "true" or "false"
    
    # Add indexes for common queries
    __table_args__ = (
        Index('idx_created_at_provider', 'created_at', 'storage_provider'),
        Index('idx_is_encrypted', 'is_encrypted'),
    )
    
    @property
    def tags(self) -> Dict[str, str]:
        """Parse tags from JSON."""
        if self.tags_json:
            return json.loads(self.tags_json)
        return {}
    
    @tags.setter
    def tags(self, value: Dict[str, str]):
        """Serialize tags to JSON."""
        self.tags_json = json.dumps(value) if value else None
    
    @property
    def meta(self) -> Dict[str, Any]:
        """Parse metadata from JSON."""
        if self.metadata_json:
            return json.loads(self.metadata_json)
        return {}
    
    @meta.setter
    def meta(self, value: Dict[str, Any]):
        """Serialize metadata to JSON."""
        self.metadata_json = json.dumps(value) if value else None
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get metadata (method for compatibility)."""
        return self.meta
    
    def set_metadata(self, value: Dict[str, Any]):
        """Set metadata (method for compatibility)."""
        self.meta = value
    
    @property
    def embedding_vector(self) -> Optional[list]:
        """Parse embedding vector from JSON."""
        if self.embedding:
            return json.loads(self.embedding)
        return None
    
    @embedding_vector.setter
    def embedding_vector(self, value: Optional[list]):
        """Serialize embedding vector to JSON."""
        if value:
            self.embedding = json.dumps(value)
        else:
            self.embedding = None


class DocumentTag(Base):
    """Database model for document tags (for efficient querying)."""
    
    __tablename__ = "document_tags"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(String(64), index=True, nullable=False)
    tag_key = Column(String(100), index=True, nullable=False)
    tag_value = Column(String(255), index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_tag_key_value', 'tag_key', 'tag_value'),
    )


class User(Base):
    """Database model for users."""
    
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=True)
    role = Column(String(50), default="user", nullable=False)  # admin, archive_manager, auditor, user, viewer
    is_active = Column(String(5), default="true", nullable=False)  # "true" or "false" for compatibility
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_username', 'username'),
        Index('idx_role', 'role'),
        Index('idx_is_active', 'is_active'),
    )


class AuditLogEntry(Base):
    """Database model for audit log entries."""
    
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(50), index=True, nullable=False)
    user_id = Column(Integer, nullable=True)
    username = Column(String(50), nullable=True)
    resource_type = Column(String(50), nullable=True)
    resource_id = Column(String(255), nullable=True)
    action = Column(String(255), nullable=True)
    status = Column(String(20), nullable=False)  # success, failure, partial
    details = Column(Text, nullable=True)  # JSON details
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        Index('idx_event_type', 'event_type'),
        Index('idx_user_id', 'user_id'),
        Index('idx_resource_type', 'resource_type'),
        Index('idx_timestamp', 'timestamp'),
    )


def init_db():
    """Initialize the database tables and create default admin user."""
    Base.metadata.create_all(bind=engine)
    
    # Create default admin user if it doesn't exist
    db = SessionLocal()
    try:
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            # Create default admin user
            from app.user_management import UserManagementService
            password_hash = UserManagementService.hash_password("password")
            admin = User(
                username="admin",
                email="admin@example.com",
                full_name="Administrator",
                password_hash=password_hash,
                role="admin",
                is_active=True
            )
            db.add(admin)
            db.commit()
            print("Default admin user created (username: admin, password: password)")
    except Exception as e:
        print(f"Could not create default admin user: {e}")
        db.rollback()
    finally:
        db.close()


def get_db() -> Session:
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
