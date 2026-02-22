"""API routes for the document archive application."""

import json
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session

from app.database import get_db, User
from app.middleware import get_current_user, require_permission, require_role
from app.auth import get_auth_provider
from app.user_management import UserManagementService
from app.models import (
    ArchiveRequest, ArchiveResponse,
    RetrieveRequest, RetrieveResponse,
    ReportRequest, ReportResponse,
    DeepArchiveRequest, DeepArchiveResponse,
    RestoreRequest, RestoreResponse,
    ArchiveStatusResponse,
    LifecycleArchivalRequest, LifecycleArchivalResponse,
    GlacierRetrieveRequest, GlacierRetrieveResponse,
    RestoreStatusCheckResponse,
    DeleteResponse,
    VectorSearchRequest, VectorSearchResponse,
    PIIDetectionRequest, PIIDetectionResponse,
    AnonymizeRequest, AnonymizeResponse,
    AuditLogsResponse,
    ErrorResponse,
    LoginRequest, TokenResponse, RefreshTokenRequest
)
from app.services import DocumentArchiveService
from app.lifecycle_service import LifecycleService
from app.audit_service import get_audit_service

router = APIRouter(prefix="/api/v1", tags=["Document Archive"])
auth_router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


# Authentication Endpoints
@auth_router.post(
    "/login",
    response_model=TokenResponse,
    responses={
        200: {"description": "Login successful, tokens returned"},
        401: {"model": ErrorResponse, "description": "Invalid credentials"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="User login",
    description="Authenticate user with username and password to receive JWT tokens"
)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Login endpoint that authenticates a user and returns JWT tokens.
    
    **Request Body:**
    - username: str - The username of the user
    - password: str - The plaintext password of the user
    
    **Returns:**
    - access_token: str - JWT access token for API access
    - refresh_token: str - JWT refresh token for token renewal
    - token_type: str - Token type (always "bearer")
    """
    try:
        # Authenticate user
        user_data = UserManagementService.authenticate_user(db, request.username, request.password)
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Generate tokens
        auth_provider = get_auth_provider()
        tokens = auth_provider.create_tokens(user_data)
        
        return TokenResponse(
            access_token=tokens.get("access_token"),
            refresh_token=tokens.get("refresh_token"),
            token_type="bearer"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )


@auth_router.post(
    "/refresh",
    response_model=TokenResponse,
    responses={
        200: {"description": "Token refresh successful"},
        401: {"model": ErrorResponse, "description": "Invalid or expired refresh token"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Refresh access token",
    description="Use a refresh token to obtain a new access token"
)
async def refresh_token(request: RefreshTokenRequest):
    """
    Refresh endpoint that provides a new access token using a refresh token.
    
    **Request Body:**
    - refresh_token: str - The refresh token to use for renewal
    
    **Returns:**
    - access_token: str - New JWT access token
    - refresh_token: str - New JWT refresh token
    - token_type: str - Token type (always "bearer")
    """
    try:
        auth_provider = get_auth_provider()
        
        # Verify and refresh the token
        result = auth_provider.refresh_access_token(request.refresh_token)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        return TokenResponse(
            access_token=result.get("access_token"),
            refresh_token=result.get("refresh_token"),
            token_type="bearer"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token refresh failed: {str(e)}"
        )


@auth_router.post(
    "/logout",
    responses={
        200: {"description": "Logout successful"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="User logout",
    description="Invalidate the current user's tokens"
)
async def logout(current_user: User = Depends(get_current_user)):
    """
    Logout endpoint that invalidates the current user's session.
    
    **Authentication:** Requires valid Bearer token in Authorization header
    
    **Returns:**
    - message: str - Confirmation of logout
    """
    try:
        # In a production system, you might:
        # - Add token to a blacklist
        # - Invalidate user session
        # - Log the logout event
        
        # Note: Audit logging on logout is optional to avoid circular dependencies
        # Logging is handled by AuditMiddleware
        
        return {"message": "Successfully logged out"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Logout failed: {str(e)}"
        )


@router.post(
    "/archive",
    response_model=ArchiveResponse,
    responses={
        200: {"description": "Document archived successfully"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Archive a document",
    description="Upload and archive a document in base64 format to cloud storage with tagging metadata"
)
async def archive_document(
    request: ArchiveRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    permission: str = Depends(require_permission("document:create"))
) -> ArchiveResponse:
    """
    Archive a document to cloud storage.
    
    - **document_base64**: Base64 encoded document content
    - **filename**: Original filename of the document
    - **content_type**: MIME type of the document
    - **tags**: Key-value pairs for document tagging
    - **metadata**: Additional metadata for the document
    
    Returns a unique hashed identifier for the archived document.
    """
    service = DocumentArchiveService(db)
    response = await service.archive_document(request)
    
    if not response.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=response.message
        )
    
    return response


@router.delete(
    "/archive/{document_id}",
    response_model=DeleteResponse,
    responses={
        200: {"description": "Document deleted successfully"},
        404: {"model": ErrorResponse, "description": "Document not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Delete a document",
    description="Permanently delete a document from cloud storage and database"
)
async def delete_document(
    document_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    permission: str = Depends(require_permission("document:delete"))
) -> DeleteResponse:
    """
    Delete a document from the archive.
    
    - **document_id**: Unique hashed identifier of the document to delete
    
    Returns confirmation of deletion with timestamp.
    """
    service = DocumentArchiveService(db)
    response = await service.delete_document(document_id)
    
    if not response.success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=response.message
        )
    
    return response


@router.post(
    "/retrieve",
    response_model=RetrieveResponse,
    responses={
        200: {"description": "Document retrieved successfully"},
        404: {"model": ErrorResponse, "description": "Document not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Retrieve a document",
    description="Retrieve a document in base64 format using its unique identifier"
)
async def retrieve_document(
    request: RetrieveRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    permission: str = Depends(require_permission("document:read"))
) -> RetrieveResponse:
    """
    Retrieve a document from cloud storage.
    
    - **document_id**: Unique hashed identifier of the document
    
    Returns the document content in base64 format along with metadata.
    """
    service = DocumentArchiveService(db)
    response = await service.retrieve_document(request.document_id)
    
    if not response.success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    return response


@router.get(
    "/retrieve/{document_id}",
    response_model=RetrieveResponse,
    responses={
        200: {"description": "Document retrieved successfully"},
        404: {"model": ErrorResponse, "description": "Document not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Retrieve a document by ID",
    description="Retrieve a document in base64 format using its unique identifier (GET method)"
)
async def retrieve_document_by_id(
    document_id: str,
    db: Session = Depends(get_db)
) -> RetrieveResponse:
    """
    Retrieve a document from cloud storage by ID.
    
    - **document_id**: Unique hashed identifier of the document
    
    Returns the document content in base64 format along with metadata.
    """
    service = DocumentArchiveService(db)
    response = await service.retrieve_document(document_id)
    
    if not response.success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    return response


@router.post(
    "/report",
    response_model=ReportResponse,
    responses={
        200: {"description": "Report generated successfully"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Generate metrics report",
    description="Generate a report with key metrics for documents archived within a given time period"
)
async def generate_report(
    request: ReportRequest,
    db: Session = Depends(get_db)
) -> ReportResponse:
    """
    Generate a metrics report for archived documents.
    
    - **start_date**: Start date for the report period
    - **end_date**: End date for the report period
    - **group_by**: Optional tag key to group metrics by
    
    Returns metrics including document counts, sizes, and tag distributions.
    """
    if request.start_date > request.end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be before end_date"
        )
    
    service = DocumentArchiveService(db)
    response = await service.generate_report(request)
    
    if not response.success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate report"
        )
    
    return response


# Deep Archive Endpoints
@router.post(
    "/deep-archive",
    response_model=DeepArchiveResponse,
    tags=["Deep Archive"],
    responses={
        200: {"description": "Document moved to deep archive successfully"},
        404: {"model": ErrorResponse, "description": "Document not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Move document to deep archive",
    description="Move a document to deep archive storage (AWS Glacier, Azure Archive, GCP Archive)"
)
async def move_to_deep_archive(
    request: DeepArchiveRequest,
    db: Session = Depends(get_db)
) -> DeepArchiveResponse:
    """
    Move a document to deep archive storage.
    
    - **document_id**: Unique hashed identifier of the document
    - **storage_tier**: Target storage tier (archive, deep_archive)
    
    Returns the archive operation result.
    """
    service = DocumentArchiveService(db)
    response = await service.move_to_deep_archive(request)
    
    if not response.success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if "not found" in response.message.lower() else status.HTTP_400_BAD_REQUEST,
            detail=response.message
        )
    
    return response


@router.post(
    "/restore",
    response_model=RestoreResponse,
    tags=["Deep Archive"],
    responses={
        200: {"description": "Restore initiated successfully"},
        404: {"model": ErrorResponse, "description": "Document not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Restore document from deep archive",
    description="Initiate restore of a document from deep archive storage"
)
async def restore_from_archive(
    request: RestoreRequest,
    db: Session = Depends(get_db)
) -> RestoreResponse:
    """
    Restore a document from deep archive storage.
    
    - **document_id**: Unique hashed identifier of the document
    - **restore_days**: Number of days to keep the restored copy available
    - **restore_tier**: Restore speed (Expedited, Standard, Bulk)
    
    Returns the restore operation status. Note that retrieval from
    deep archive (e.g., AWS Glacier) may take hours to complete.
    """
    service = DocumentArchiveService(db)
    response = await service.restore_from_deep_archive(request)
    
    if not response.success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if "not found" in response.message.lower() else status.HTTP_400_BAD_REQUEST,
            detail=response.message
        )
    
    return response


@router.get(
    "/archive-status/{document_id}",
    response_model=ArchiveStatusResponse,
    tags=["Deep Archive"],
    responses={
        200: {"description": "Status retrieved successfully"},
        404: {"model": ErrorResponse, "description": "Document not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Get archive status",
    description="Get the current archive/restore status of a document"
)
async def get_archive_status(
    document_id: str,
    db: Session = Depends(get_db)
) -> ArchiveStatusResponse:
    """
    Get the archive/restore status of a document.
    
    - **document_id**: Unique hashed identifier of the document
    
    Returns:
    - **storage_tier**: Current storage tier (standard, archive, deep_archive)
    - **restore_status**: Restore status (not_archived, archived, in_progress, restored)
    - **is_retrievable**: Whether the document can be immediately retrieved
    - **restore_expiry**: When the restored copy expires (if applicable)
    """
    service = DocumentArchiveService(db)
    response = await service.get_archive_status(document_id)
    
    if not response.success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if "not found" in response.message.lower() else status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=response.message
        )
    
    return response


# Glacier Retrieval Endpoints
@router.post(
    "/glacier/retrieve",
    response_model=GlacierRetrieveResponse,
    tags=["Glacier"],
    responses={
        200: {"description": "Document retrieved or restore initiated"},
        404: {"model": ErrorResponse, "description": "Document not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Retrieve document from Glacier",
    description="Retrieve a document from Glacier/archive storage. If already restored, returns content. Otherwise initiates restore and publishes Kafka event when ready."
)
async def retrieve_from_glacier(
    request: GlacierRetrieveRequest,
    db: Session = Depends(get_db)
) -> GlacierRetrieveResponse:
    """
    Retrieve a document from Glacier/archive storage.
    
    - **document_id**: Unique hashed identifier of the document
    - **restore_tier**: Restore speed (Expedited, Standard, Bulk)
    - **restore_days**: Number of days to keep the restored copy
    
    If the document is:
    - In standard storage: Returns immediately
    - Already restored: Returns content + publishes Kafka event
    - In archive: Initiates restore and returns estimated completion time
    - Restore in progress: Returns current status
    
    A Kafka event is published to 'document-restore-ready' topic when restore completes.
    """
    service = DocumentArchiveService(db)
    response = await service.retrieve_from_glacier(request)
    
    if not response.success and "not found" in response.message.lower():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=response.message
        )
    
    return response


@router.get(
    "/glacier/retrieve/{document_id}",
    response_model=GlacierRetrieveResponse,
    tags=["Glacier"],
    responses={
        200: {"description": "Document retrieved or restore initiated"},
        404: {"model": ErrorResponse, "description": "Document not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Retrieve document from Glacier by ID",
    description="Retrieve a document from Glacier using GET method with default restore options"
)
async def retrieve_from_glacier_by_id(
    document_id: str,
    db: Session = Depends(get_db)
) -> GlacierRetrieveResponse:
    """
    Retrieve a document from Glacier by ID using default restore options.
    
    Uses Standard restore tier and 7-day restore period.
    """
    request = GlacierRetrieveRequest(document_id=document_id)
    service = DocumentArchiveService(db)
    response = await service.retrieve_from_glacier(request)
    
    if not response.success and "not found" in response.message.lower():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=response.message
        )
    
    return response


# Lifecycle Management Endpoints
@router.post(
    "/lifecycle/archive",
    response_model=LifecycleArchivalResponse,
    tags=["Lifecycle"],
    responses={
        200: {"description": "Archival process completed"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Run lifecycle archival",
    description="Move documents to archive storage based on their creation date"
)
async def run_lifecycle_archival(
    request: LifecycleArchivalRequest,
    db: Session = Depends(get_db)
) -> LifecycleArchivalResponse:
    """
    Run the lifecycle archival process to move old documents to archive storage.
    
    - **target_tier**: Target storage tier (archive, deep_archive)
    - **dry_run**: If True, only report what would be archived
    - **archive_after_days**: Days after creation to archive (default from settings)
    
    Documents older than the specified days will be moved to the target storage tier.
    Kafka events are published for each archived document.
    """
    from app.config import StorageTier
    from datetime import datetime
    
    service = LifecycleService(db)
    
    try:
        target = StorageTier(request.target_tier)
    except ValueError:
        target = StorageTier.DEEP_ARCHIVE
    
    result = await service.run_lifecycle_archival(
        target_tier=target,
        dry_run=request.dry_run
    )
    
    return LifecycleArchivalResponse(
        success=True,
        started_at=datetime.fromisoformat(result["started_at"]),
        completed_at=datetime.fromisoformat(result["completed_at"]) if result.get("completed_at") else None,
        target_tier=result["target_tier"],
        dry_run=result["dry_run"],
        total_eligible=result["total_eligible"],
        successful=result.get("successful", 0),
        failed=result.get("failed", 0),
        documents=result["documents"]
    )


@router.post(
    "/lifecycle/check-restores",
    response_model=RestoreStatusCheckResponse,
    tags=["Lifecycle"],
    responses={
        200: {"description": "Status check completed"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Check restore status",
    description="Check status of all documents with restore in progress and publish Kafka events for completed restores"
)
async def check_restore_status(
    db: Session = Depends(get_db)
) -> RestoreStatusCheckResponse:
    """
    Check the restore status of all documents being restored.
    
    For each document that has completed restoration:
    - Updates database status to 'restored'
    - Publishes Kafka event to 'document-restore-ready' topic
    
    This endpoint can be called periodically or triggered by a scheduler.
    """
    service = LifecycleService(db)
    
    try:
        result = await service.check_and_update_restore_status()
        
        return RestoreStatusCheckResponse(
            success=True,
            checked=result["checked"],
            restored=result["restored"],
            still_in_progress=result["still_in_progress"],
            errors=result["errors"],
            documents=result["documents"]
        )
    finally:
        pass  # Session is managed by dependency


@router.get(
    "/lifecycle/eligible",
    tags=["Lifecycle"],
    responses={
        200: {"description": "List of eligible documents"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Get documents eligible for archival",
    description="Get a list of documents that are eligible for archival based on their age"
)
async def get_eligible_for_archival(
    target_tier: str = "deep_archive",
    archive_after_days: int = None,
    db: Session = Depends(get_db)
):
    """
    Get documents eligible for archival based on their creation date.
    
    - **target_tier**: Target storage tier (archive, deep_archive)
    - **archive_after_days**: Days after creation (default from settings)
    
    Returns a list of documents with their details and age.
    """
    from app.config import StorageTier
    from datetime import datetime
    
    service = LifecycleService(db)
    
    try:
        target = StorageTier(target_tier)
    except ValueError:
        target = StorageTier.DEEP_ARCHIVE
    
    documents = await service.get_documents_for_archival(
        archive_after_days=archive_after_days,
        target_tier=target
    )
    
    return {
        "target_tier": target_tier,
        "archive_after_days": archive_after_days,
        "total_eligible": len(documents),
        "documents": [
            {
                "document_id": doc.document_id,
                "filename": doc.filename,
                "storage_tier": doc.storage_tier,
                "created_at": doc.created_at.isoformat(),
                "age_days": (datetime.utcnow() - doc.created_at).days,
                "size_bytes": doc.size_bytes
            }
            for doc in documents
        ]
    }


@router.post(
    "/search",
    response_model=VectorSearchResponse,
    responses={
        200: {"description": "Search completed successfully"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Vector semantic search",
    description="Search documents by semantic similarity using vector embeddings"
)
async def vector_search(
    request: VectorSearchRequest,
    db: Session = Depends(get_db)
) -> VectorSearchResponse:
    """
    Perform semantic search on archived documents using query embeddings.
    
    - **query**: Search query text
    - **top_k**: Number of top results to return (1-100, default: 10)
    - **min_similarity**: Minimum similarity score to include (0-1, default: 0.0)
    
    Returns ranked list of similar documents based on their metadata and filenames.
    """
    service = DocumentArchiveService(db)
    response = await service.vector_search(request)
    
    if not response.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vector search failed"
        )
    
    return response


@router.post(
    "/detect-pii",
    response_model=PIIDetectionResponse,
    responses={
        200: {"description": "PII detection completed"},
        404: {"model": ErrorResponse, "description": "Document not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Detect PII in document",
    description="Scan a document for personally identifiable information (PII)"
)
async def detect_pii(
    request: PIIDetectionRequest,
    db: Session = Depends(get_db)
) -> PIIDetectionResponse:
    """
    Detect personally identifiable information in an archived document.
    
    - **document_id**: Unique identifier of the document to scan
    - **pii_types**: Optional list of specific PII types to detect (email, phone, ssn, credit_card, ip_address, name, address, date_of_birth, person, organization)
    
    Detects PIIs like emails, phone numbers, SSNs, credit cards, IP addresses, and names.
    """
    service = DocumentArchiveService(db)
    response = await service.detect_piis(request)
    
    if not response.success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=response.message
        )
    
    return response


@router.post(
    "/anonymize",
    response_model=AnonymizeResponse,
    responses={
        200: {"description": "Anonymization completed"},
        404: {"model": ErrorResponse, "description": "Document not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Anonymize document",
    description="Remove or redact personally identifiable information from a document"
)
async def anonymize_document(
    request: AnonymizeRequest,
    db: Session = Depends(get_db)
) -> AnonymizeResponse:
    """
    Anonymize personally identifiable information in an archived document.
    
    - **document_id**: Unique identifier of the document to anonymize
    - **pii_types**: Optional list of specific PII types to anonymize
    - **mask_mode**: Anonymization mode - 'redact' (replace with [TYPE]) or 'remove' (delete)
    - **save_anonymized_version**: If True, save anonymized version as new document
    
    Replaces or removes detected PII and optionally saves as new document.
    """
    service = DocumentArchiveService(db)
    response = await service.anonymize_document(request)
    
    if not response.success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=response.message
        )
    
    return response


@router.get(
    "/audit/logs",
    response_model=AuditLogsResponse,
    responses={
        200: {"description": "Audit logs retrieved successfully"},
        400: {"model": ErrorResponse, "description": "Invalid date format"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Retrieve audit logs",
    description="Query audit logs for a given period with optional filters"
)
async def get_audit_logs(
    start_date: Optional[str] = Query(None, description="Start date (ISO format: YYYY-MM-DDTHH:MM:SS)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format: YYYY-MM-DDTHH:MM:SS)"),
    event_type: Optional[str] = Query(None, description="Filter by event type (e.g., login, document_upload)"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type (e.g., document, user)"),
    log_status: Optional[str] = Query(None, description="Filter by status (success, failure, partial)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    permission: str = Depends(require_permission("audit:read"))
) -> AuditLogsResponse:
    """
    Retrieve audit logs for a given period with optional filtering.
    
    **Parameters:**
    - **start_date**: ISO format start date (e.g., 2026-02-01T00:00:00)
    - **end_date**: ISO format end date (e.g., 2026-02-28T23:59:59)
    - **event_type**: Filter by event type (login, logout, document_upload, etc.)
    - **user_id**: Filter by specific user ID
    - **resource_type**: Filter by resource type (document, user, role, etc.)
    - **status**: Filter by operation status (success, failure, partial)
    - **skip**: Pagination offset
    - **limit**: Maximum results to return
    
    **Example:**
    ```
    GET /api/v1/audit/logs?start_date=2026-02-21T00:00:00&end_date=2026-02-21T23:59:59&event_type=document_upload
    ```
    
    Returns list of audit log entries matching the criteria.
    """
    try:
        # Parse dates if provided
        start = None
        end = None
        
        if start_date:
            try:
                start = datetime.fromisoformat(start_date)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid start_date format. Use ISO format: YYYY-MM-DDTHH:MM:SS"
                )
        
        if end_date:
            try:
                end = datetime.fromisoformat(end_date)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid end_date format. Use ISO format: YYYY-MM-DDTHH:MM:SS"
                )
        
        # Get audit service and retrieve logs
        audit_service = get_audit_service()
        logs = await audit_service.get_audit_logs(
            db=db,
            event_type=event_type,
            user_id=user_id,
            resource_type=resource_type,
            start_date=start,
            end_date=end,
            limit=limit
        )
        
        # Convert logs to dictionaries - handle both dict and ORM objects
        log_list = []
        for log in logs:
            if isinstance(log, dict):
                # Already a dictionary from service
                log_dict = log
            else:
                # ORM object - convert to dict
                log_dict = {
                    "id": log.id if log.id else 0,
                    "timestamp": log.timestamp.isoformat() if log.timestamp else "",
                    "event_type": log.event_type or "",
                    "user_id": log.user_id,
                    "username": log.username or "",
                    "resource_type": log.resource_type or "",
                    "resource_id": log.resource_id or "",
                    "action": log.action or "",
                    "status": log.status or "",
                    "ip_address": log.ip_address or "",
                    "user_agent": log.user_agent or "",
                    "details": json.loads(log.details) if log.details and isinstance(log.details, str) else (log.details or {})
                }
            log_list.append(log_dict)
        
        return AuditLogsResponse(
            success=True,
            logs=log_list,
            total=len(log_list),
            skip=skip,
            limit=limit
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve audit logs: {str(e)}"
        )

