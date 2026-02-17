"""API routes for the document archive application."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
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
    ErrorResponse
)
from app.services import DocumentArchiveService
from app.lifecycle_service import LifecycleService

router = APIRouter(prefix="/api/v1", tags=["Document Archive"])


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
    db: Session = Depends(get_db)
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
    db: Session = Depends(get_db)
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
    db: Session = Depends(get_db)
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

