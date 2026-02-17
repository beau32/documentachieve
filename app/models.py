"""Pydantic models for API requests and responses."""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


# Request Models
class ArchiveRequest(BaseModel):
    """Request model for archiving a document."""
    document_base64: str = Field(..., description="Base64 encoded document content")
    filename: str = Field(..., description="Original filename of the document")
    content_type: str = Field(default="application/octet-stream", description="MIME type of the document")
    tags: Dict[str, str] = Field(default_factory=dict, description="Key-value pairs for document tagging")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata for the document")
    
    class Config:
        json_schema_extra = {
            "example": {
                "document_base64": "SGVsbG8gV29ybGQh",
                "filename": "report.pdf",
                "content_type": "application/pdf",
                "tags": {
                    "department": "finance",
                    "year": "2026",
                    "category": "quarterly-report"
                },
                "metadata": {
                    "author": "John Doe",
                    "version": "1.0"
                }
            }
        }


class RetrieveRequest(BaseModel):
    """Request model for retrieving a document."""
    document_id: str = Field(..., description="Unique hashed identifier of the document")
    
    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "a1b2c3d4e5f6..."
            }
        }


class ReportRequest(BaseModel):
    """Request model for generating a report."""
    start_date: datetime = Field(..., description="Start date for the report period")
    end_date: datetime = Field(..., description="End date for the report period")
    group_by: Optional[str] = Field(default=None, description="Group metrics by tag key (e.g., 'department')")
    
    class Config:
        json_schema_extra = {
            "example": {
                "start_date": "2026-01-01T00:00:00",
                "end_date": "2026-02-17T23:59:59",
                "group_by": "department"
            }
        }


# Response Models
class ArchiveResponse(BaseModel):
    """Response model for archive operation."""
    success: bool
    document_id: str = Field(..., description="Unique hashed identifier for the archived document")
    message: str
    storage_provider: str
    archived_at: datetime
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "document_id": "a1b2c3d4e5f6abcd1234567890abcdef",
                "message": "Document archived successfully",
                "storage_provider": "aws_s3",
                "archived_at": "2026-02-17T10:30:00"
            }
        }


class RetrieveResponse(BaseModel):
    """Response model for retrieve operation."""
    success: bool
    document_id: str
    document_base64: str = Field(..., description="Base64 encoded document content")
    filename: str
    content_type: str
    tags: Dict[str, str]
    metadata: Dict[str, Any]
    archived_at: datetime
    retrieved_at: datetime
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "document_id": "a1b2c3d4e5f6abcd1234567890abcdef",
                "document_base64": "SGVsbG8gV29ybGQh",
                "filename": "report.pdf",
                "content_type": "application/pdf",
                "tags": {"department": "finance"},
                "metadata": {"author": "John Doe"},
                "archived_at": "2026-02-17T10:30:00",
                "retrieved_at": "2026-02-17T11:00:00"
            }
        }


class MetricsSummary(BaseModel):
    """Summary metrics for documents."""
    total_documents: int
    total_size_bytes: int
    total_size_mb: float
    documents_by_content_type: Dict[str, int]
    documents_by_tag: Dict[str, Dict[str, int]]
    storage_provider: str


class ReportResponse(BaseModel):
    """Response model for report operation."""
    success: bool
    start_date: datetime
    end_date: datetime
    metrics: MetricsSummary
    daily_uploads: List[Dict[str, Any]]
    top_tags: List[Dict[str, Any]]
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "start_date": "2026-01-01T00:00:00",
                "end_date": "2026-02-17T23:59:59",
                "metrics": {
                    "total_documents": 150,
                    "total_size_bytes": 52428800,
                    "total_size_mb": 50.0,
                    "documents_by_content_type": {
                        "application/pdf": 100,
                        "image/png": 50
                    },
                    "documents_by_tag": {
                        "department": {"finance": 80, "hr": 70}
                    },
                    "storage_provider": "aws_s3"
                },
                "daily_uploads": [
                    {"date": "2026-02-16", "count": 25, "size_bytes": 5242880}
                ],
                "top_tags": [
                    {"tag_key": "department", "tag_value": "finance", "count": 80}
                ]
            }
        }


class DeleteResponse(BaseModel):
    """Response model for delete operation."""
    success: bool
    document_id: str
    message: str
    deleted_at: datetime
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "document_id": "a1b2c3d4e5f6abcd1234567890abcdef",
                "message": "Document deleted successfully",
                "deleted_at": "2026-02-17T10:30:00"
            }
        }


# Vector Search Models
class VectorSearchRequest(BaseModel):
    """Request model for vector semantic search."""
    query: str = Field(..., description="Search query text")
    top_k: int = Field(default=10, ge=1, le=100, description="Number of results to return")
    min_similarity: float = Field(default=0.0, ge=0.0, le=1.0, description="Minimum similarity score (0-1)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "quarterly financial report",
                "top_k": 5,
                "min_similarity": 0.5
            }
        }


class VectorSearchResult(BaseModel):
    """Single result from vector search."""
    document_id: str
    filename: str
    content_type: str
    similarity_score: float
    tags: Dict[str, str]
    created_at: datetime
    storage_tier: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "a1b2c3d4e5f6abcd1234567890abcdef",
                "filename": "quarterly_report.pdf",
                "content_type": "application/pdf",
                "similarity_score": 0.92,
                "tags": {"department": "finance"},
                "created_at": "2026-02-17T10:30:00",
                "storage_tier": "standard"
            }
        }


class VectorSearchResponse(BaseModel):
    """Response model for vector search operation."""
    success: bool
    query: str
    results: List[VectorSearchResult]
    total_results: int
    search_time_ms: float
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "query": "quarterly financial report",
                "results": [
                    {
                        "document_id": "a1b2c3d4e5f6abcd1234567890abcdef",
                        "filename": "q4_2025_report.pdf",
                        "content_type": "application/pdf",
                        "similarity_score": 0.95,
                        "tags": {"department": "finance"},
                        "created_at": "2026-02-17T10:30:00",
                        "storage_tier": "standard"
                    }
                ],
                "total_results": 1,
                "search_time_ms": 145.23
            }
        }


class ErrorResponse(BaseModel):
    """Error response model."""
    success: bool = False
    error: str
    detail: Optional[str] = None


# Deep Archive Models
class DeepArchiveRequest(BaseModel):
    """Request model for moving a document to deep archive."""
    document_id: str = Field(..., description="Unique hashed identifier of the document")
    storage_tier: str = Field(
        default="deep_archive",
        description="Target storage tier: archive, deep_archive"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "a1b2c3d4e5f6abcd1234567890abcdef",
                "storage_tier": "deep_archive"
            }
        }


class DeepArchiveResponse(BaseModel):
    """Response model for deep archive operation."""
    success: bool
    document_id: str
    message: str
    previous_tier: str
    new_tier: str
    archived_at: datetime
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "document_id": "a1b2c3d4e5f6abcd1234567890abcdef",
                "message": "Document moved to deep archive successfully",
                "previous_tier": "standard",
                "new_tier": "deep_archive",
                "archived_at": "2026-02-17T10:30:00"
            }
        }


class RestoreRequest(BaseModel):
    """Request model for restoring a document from deep archive."""
    document_id: str = Field(..., description="Unique hashed identifier of the document")
    restore_days: Optional[int] = Field(
        default=7,
        description="Number of days to keep the restored copy available"
    )
    restore_tier: Optional[str] = Field(
        default="Standard",
        description="Restore speed: Expedited (1-5 min), Standard (3-5 hrs), Bulk (5-12 hrs)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "a1b2c3d4e5f6abcd1234567890abcdef",
                "restore_days": 7,
                "restore_tier": "Standard"
            }
        }


class RestoreResponse(BaseModel):
    """Response model for restore operation."""
    success: bool
    document_id: str
    message: str
    restore_status: str
    estimated_completion: Optional[str] = None
    restore_expiry: Optional[datetime] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "document_id": "a1b2c3d4e5f6abcd1234567890abcdef",
                "message": "Restore initiated successfully",
                "restore_status": "in_progress",
                "estimated_completion": "3-5 hours for Standard tier",
                "restore_expiry": None
            }
        }


class ArchiveStatusResponse(BaseModel):
    """Response model for checking archive/restore status."""
    success: bool
    document_id: str
    storage_tier: str
    restore_status: str
    restore_expiry: Optional[datetime] = None
    is_retrievable: bool = Field(
        description="Whether the document can be immediately retrieved"
    )
    message: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "document_id": "a1b2c3d4e5f6abcd1234567890abcdef",
                "storage_tier": "deep_archive",
                "restore_status": "restored",
                "restore_expiry": "2026-02-24T10:30:00",
                "is_retrievable": True,
                "message": "Document is restored and available until 2026-02-24"
            }
        }


# Lifecycle Management Models
class LifecycleArchivalRequest(BaseModel):
    """Request model for running lifecycle archival."""
    target_tier: str = Field(
        default="deep_archive",
        description="Target storage tier: archive, deep_archive"
    )
    dry_run: bool = Field(
        default=True,
        description="If True, only report what would be archived without making changes"
    )
    archive_after_days: Optional[int] = Field(
        default=None,
        description="Override days after creation to archive (default from settings)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "target_tier": "deep_archive",
                "dry_run": True,
                "archive_after_days": 90
            }
        }


class LifecycleArchivalResponse(BaseModel):
    """Response model for lifecycle archival operation."""
    success: bool
    started_at: datetime
    completed_at: Optional[datetime] = None
    target_tier: str
    dry_run: bool
    total_eligible: int
    successful: int = 0
    failed: int = 0
    documents: List[Dict[str, Any]]
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "started_at": "2026-02-17T10:00:00",
                "completed_at": "2026-02-17T10:05:00",
                "target_tier": "deep_archive",
                "dry_run": False,
                "total_eligible": 10,
                "successful": 9,
                "failed": 1,
                "documents": [
                    {
                        "document_id": "a1b2c3d4...",
                        "filename": "report.pdf",
                        "previous_tier": "standard",
                        "new_tier": "deep_archive"
                    }
                ]
            }
        }


class GlacierRetrieveRequest(BaseModel):
    """Request model for retrieving a document from Glacier."""
    document_id: str = Field(..., description="Unique hashed identifier of the document")
    restore_tier: Optional[str] = Field(
        default="Standard",
        description="Restore speed: Expedited (1-5 min), Standard (3-5 hrs), Bulk (5-12 hrs)"
    )
    restore_days: Optional[int] = Field(
        default=7,
        description="Number of days to keep the restored copy available"
    )
    wait_for_restore: bool = Field(
        default=False,
        description="If True and document is available, return it immediately"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "a1b2c3d4e5f6abcd1234567890abcdef",
                "restore_tier": "Standard",
                "restore_days": 7,
                "wait_for_restore": False
            }
        }


class GlacierRetrieveResponse(BaseModel):
    """Response model for Glacier retrieval operation."""
    success: bool
    document_id: str
    filename: str
    storage_tier: str
    restore_status: str
    is_retrievable: bool
    document_base64: Optional[str] = Field(
        default=None,
        description="Base64 encoded document content (only if is_retrievable=True)"
    )
    restore_expiry: Optional[datetime] = None
    estimated_completion: Optional[str] = None
    message: str
    kafka_event_published: bool = False
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "document_id": "a1b2c3d4e5f6abcd1234567890abcdef",
                "filename": "report.pdf",
                "storage_tier": "deep_archive",
                "restore_status": "restored",
                "is_retrievable": True,
                "document_base64": "SGVsbG8gV29ybGQh",
                "restore_expiry": "2026-02-24T10:30:00",
                "estimated_completion": None,
                "message": "Document retrieved successfully from Glacier",
                "kafka_event_published": True
            }
        }


class RestoreStatusCheckResponse(BaseModel):
    """Response model for checking restore status of multiple documents."""
    success: bool
    checked: int
    restored: int
    still_in_progress: int
    errors: int
    documents: List[Dict[str, Any]]


class PIIDetectionRequest(BaseModel):
    """Request model for PII detection in a document."""
    document_id: str = Field(..., description="Unique hashed identifier of the document")
    pii_types: Optional[List[str]] = Field(
        default=None,
        description="Specific PII types to detect: name, email, phone, ssn, credit_card, ip_address, address, date_of_birth, person, organization"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "a1b2c3d4e5f6abcd1234567890abcdef",
                "pii_types": ["email", "phone", "ssn"]
            }
        }


class PII(BaseModel):
    """Detected PII entity."""
    type: str = Field(..., description="PII entity type")
    detected_value: str = Field(..., description="The detected PII value (showing from document)")
    confidence: float = Field(..., description="Confidence score 0-1")
    position: Dict[str, int] = Field(..., description="Start and end position in text")


class PIIDetectionResponse(BaseModel):
    """Response model for PII detection."""
    success: bool
    document_id: str
    filename: str
    pii_found: bool
    total_piis: int
    pii_summary: Dict[str, int] = Field(..., description="Count of each PII type found")
    detected_piis: List[PII] = Field(default_factory=list, description="List of detected PII entities")
    message: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "document_id": "a1b2c3d4e5f6abcd1234567890abcdef",
                "filename": "report.pdf",
                "pii_found": True,
                "total_piis": 3,
                "pii_summary": {
                    "email": 2,
                    "phone": 1
                },
                "detected_piis": [
                    {
                        "type": "email",
                        "detected_value": "john@example.com",
                        "confidence": 0.95,
                        "position": {"start": 145, "end": 162}
                    }
                ],
                "message": "PII detection completed. Found 3 potential PII."
            }
        }


class AnonymizeRequest(BaseModel):
    """Request model for anonymizing a document."""
    document_id: str = Field(..., description="Unique hashed identifier of the document")
    pii_types: Optional[List[str]] = Field(
        default=None,
        description="Specific PII types to anonymize: name, email, phone, ssn, credit_card, ip_address, address, date_of_birth, person, organization"
    )
    mask_mode: str = Field(
        default="redact",
        description="Anonymization mode: 'redact' (replace with [TYPE]) or 'remove' (delete)"
    )
    save_anonymized_version: bool = Field(
        default=True,
        description="If True, save anonymized version as new document with '-anonymized' suffix"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "a1b2c3d4e5f6abcd1234567890abcdef",
                "pii_types": None,
                "mask_mode": "redact",
                "save_anonymized_version": True
            }
        }


class AnonymizationOperation(BaseModel):
    """Record of a single anonymization operation."""
    type: str = Field(..., description="PII type that was anonymized")
    original_text: str = Field(..., description="Original text before anonymization")
    replacement: str = Field(..., description="Text used as replacement")
    confidence: float = Field(..., description="Confidence score of detection")


class AnonymizeResponse(BaseModel):
    """Response model for anonymization operation."""
    success: bool
    document_id: str
    original_filename: str
    anonymized_filename: Optional[str] = None
    total_piis_anonymized: int
    anonymization_operations: List[AnonymizationOperation] = Field(default_factory=list)
    preview_anonymized_content: Optional[str] = Field(
        default=None,
        description="First 500 characters of anonymized content for preview"
    )
    new_document_id: Optional[str] = Field(
        default=None,
        description="Document ID of saved anonymized version (if save_anonymized_version=True)"
    )
    mask_mode_used: str
    message: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "document_id": "a1b2c3d4e5f6abcd1234567890abcdef",
                "original_filename": "report.pdf",
                "anonymized_filename": "report-anonymized.pdf",
                "total_piis_anonymized": 5,
                "anonymization_operations": [
                    {
                        "type": "email",
                        "original_text": "john@example.com",
                        "replacement": "[EMAIL]",
                        "confidence": 0.95
                    }
                ],
                "preview_anonymized_content": "Report prepared by [NAME] on [DATE]. Contact: [EMAIL]...",
                "new_document_id": "b2c3d4e5f6abcd1234567890abcdefg1",
                "mask_mode_used": "redact",
                "message": "Document anonymized successfully. 5 PII removed."
            }
        }

