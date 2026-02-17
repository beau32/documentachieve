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
    
    # Add indexes for common queries
    __table_args__ = (
        Index('idx_created_at_provider', 'created_at', 'storage_provider'),
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


def init_db():
    """Initialize the database tables."""
    Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
