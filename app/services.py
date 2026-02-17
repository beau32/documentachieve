"""Document archive service containing business logic."""

import base64
import hashlib
import logging
import time
from datetime import datetime
from typing import Optional, Dict, Any, List
from collections import defaultdict

from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.config import settings, StorageTier, RestoreStatus
from app.database import DocumentMetadata, DocumentTag
from app.models import (
    ArchiveRequest, ArchiveResponse,
    RetrieveRequest, RetrieveResponse,
    ReportRequest, ReportResponse, MetricsSummary,
    DeepArchiveRequest, DeepArchiveResponse,
    RestoreRequest, RestoreResponse,
    ArchiveStatusResponse,
    GlacierRetrieveRequest, GlacierRetrieveResponse,
    DeleteResponse,
    VectorSearchRequest, VectorSearchResponse, VectorSearchResult,
    PIIDetectionRequest, PIIDetectionResponse, PII,
    AnonymizeRequest, AnonymizeResponse, AnonymizationOperation
)
from app.storage.factory import get_storage_provider
from app.kafka_producer import get_kafka_producer
from app.embedding_service import get_embedding_service
from app.anonymization_service import get_anonymization_service, PIIType

logger = logging.getLogger(__name__)


class DocumentArchiveService:
    """Service class for document archive operations."""
    
    def __init__(self, db: Session):
        """Initialize the service with a database session."""
        self.db = db
        self.storage = get_storage_provider()
        self.kafka = get_kafka_producer()
        self.embeddings = get_embedding_service()
        self.anonymizer = get_anonymization_service()
    
    def _generate_document_id(self, data: bytes, filename: str, timestamp: datetime) -> str:
        """
        Generate a unique hashed identifier for a document.
        
        Args:
            data: Binary content of the document
            filename: Original filename
            timestamp: Archive timestamp
            
        Returns:
            A unique SHA-256 hash string
        """
        # Create hash from content + filename + timestamp
        hash_input = (
            data + 
            filename.encode('utf-8') + 
            timestamp.isoformat().encode('utf-8')
        )
        return hashlib.sha256(hash_input).hexdigest()
    
    async def archive_document(self, request: ArchiveRequest) -> ArchiveResponse:
        """
        Archive a document to cloud storage.
        
        Args:
            request: Archive request containing document data and metadata
            
        Returns:
            ArchiveResponse with document ID and status
        """
        try:
            # Decode base64 document
            try:
                document_data = base64.b64decode(request.document_base64)
            except Exception as e:
                logger.error(f"Failed to decode base64 document: {str(e)}")
                return ArchiveResponse(
                    success=False,
                    document_id="",
                    message=f"Invalid base64 encoding: {str(e)}",
                    storage_provider=self.storage.provider_name,
                    archived_at=datetime.utcnow()
                )
            
            # Generate unique document ID
            timestamp = datetime.utcnow()
            document_id = self._generate_document_id(
                document_data, 
                request.filename, 
                timestamp
            )
            
            # Check if document already exists
            existing = self.db.query(DocumentMetadata).filter(
                DocumentMetadata.document_id == document_id
            ).first()
            
            if existing:
                return ArchiveResponse(
                    success=True,
                    document_id=document_id,
                    message="Document already archived with this ID",
                    storage_provider=self.storage.provider_name,
                    archived_at=existing.created_at
                )
            
            # Upload to cloud storage
            result = await self.storage.upload(
                document_id=document_id,
                data=document_data,
                filename=request.filename,
                content_type=request.content_type,
                tags=request.tags,
                metadata=request.metadata
            )
            
            if not result.success:
                return ArchiveResponse(
                    success=False,
                    document_id="",
                    message=result.message,
                    storage_provider=self.storage.provider_name,
                    archived_at=timestamp
                )
            
            # Store metadata in database
            doc_metadata = DocumentMetadata(
                document_id=document_id,
                filename=request.filename,
                content_type=request.content_type,
                size_bytes=len(document_data),
                storage_provider=self.storage.provider_name,
                storage_path=result.storage_path
            )
            doc_metadata.tags = request.tags
            doc_metadata.meta = request.metadata
            
            # Generate and store embedding for semantic search
            embedding_text = self._prepare_embedding_text(
                request.filename,
                request.tags,
                request.metadata
            )
            if embedding_text:
                embedding_vector = self.embeddings.generate_embedding(embedding_text)
                if embedding_vector:
                    doc_metadata.embedding_vector = embedding_vector
                    doc_metadata.embedding_text = embedding_text
                    logger.debug(f"Generated embedding for document: {document_id}")
            
            self.db.add(doc_metadata)
            
            # Store tags for efficient querying
            for tag_key, tag_value in request.tags.items():
                doc_tag = DocumentTag(
                    document_id=document_id,
                    tag_key=tag_key,
                    tag_value=tag_value
                )
                self.db.add(doc_tag)
            
            self.db.commit()
            
            logger.info(f"Successfully archived document: {document_id}")
            
            # Publish Kafka event for document archived
            await self.kafka.publish_document_archived(
                document_id=document_id,
                filename=request.filename,
                storage_tier="standard",
                storage_provider=self.storage.provider_name
            )
            
            return ArchiveResponse(
                success=True,
                document_id=document_id,
                message="Document archived successfully",
                storage_provider=self.storage.provider_name,
                archived_at=timestamp
            )
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error archiving document: {str(e)}")
            return ArchiveResponse(
                success=False,
                document_id="",
                message=f"Error archiving document: {str(e)}",
                storage_provider=self.storage.provider_name,
                archived_at=datetime.utcnow()
            )
    
    async def retrieve_document(self, document_id: str) -> RetrieveResponse:
        """
        Retrieve a document from cloud storage.
        
        Args:
            document_id: Unique document identifier
            
        Returns:
            RetrieveResponse with document data and metadata
        """
        try:
            # Get document metadata from database
            doc_metadata = self.db.query(DocumentMetadata).filter(
                DocumentMetadata.document_id == document_id
            ).first()
            
            if not doc_metadata:
                return RetrieveResponse(
                    success=False,
                    document_id=document_id,
                    document_base64="",
                    filename="",
                    content_type="",
                    tags={},
                    metadata={},
                    archived_at=datetime.utcnow(),
                    retrieved_at=datetime.utcnow()
                )
            
            # Download from cloud storage
            result = await self.storage.download(doc_metadata.storage_path)
            
            if not result.success:
                return RetrieveResponse(
                    success=False,
                    document_id=document_id,
                    document_base64="",
                    filename=doc_metadata.filename,
                    content_type=doc_metadata.content_type,
                    tags=doc_metadata.tags,
                    metadata=doc_metadata.meta,
                    archived_at=doc_metadata.created_at,
                    retrieved_at=datetime.utcnow()
                )
            
            # Encode document data to base64
            document_base64 = base64.b64encode(result.data).decode('utf-8')
            
            logger.info(f"Successfully retrieved document: {document_id}")
            
            return RetrieveResponse(
                success=True,
                document_id=document_id,
                document_base64=document_base64,
                filename=doc_metadata.filename,
                content_type=doc_metadata.content_type,
                tags=doc_metadata.tags,
                metadata=doc_metadata.meta,
                archived_at=doc_metadata.created_at,
                retrieved_at=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Error retrieving document: {str(e)}")
            return RetrieveResponse(
                success=False,
                document_id=document_id,
                document_base64="",
                filename="",
                content_type="",
                tags={},
                metadata={},
                archived_at=datetime.utcnow(),
                retrieved_at=datetime.utcnow()
            )
    
    async def delete_document(self, document_id: str) -> DeleteResponse:
        """
        Delete a document from cloud storage and database.
        
        Args:
            document_id: Unique document identifier
            
        Returns:
            DeleteResponse with status and message
        """
        try:
            # Get document metadata from database
            doc_metadata = self.db.query(DocumentMetadata).filter(
                DocumentMetadata.document_id == document_id
            ).first()
            
            if not doc_metadata:
                return DeleteResponse(
                    success=False,
                    document_id=document_id,
                    message="Document not found",
                    deleted_at=datetime.utcnow()
                )
            
            filename = doc_metadata.filename
            storage_path = doc_metadata.storage_path
            
            # Delete from cloud storage
            storage_deleted = await self.storage.delete(storage_path)
            
            if not storage_deleted:
                logger.warning(f"Failed to delete document from storage: {document_id}")
            
            # Delete tags from database
            self.db.query(DocumentTag).filter(
                DocumentTag.document_id == document_id
            ).delete()
            
            # Delete metadata from database
            self.db.delete(doc_metadata)
            self.db.commit()
            
            logger.info(f"Successfully deleted document: {document_id}")
            
            # Publish Kafka event for document deleted
            await self.kafka.publish_document_deleted(
                document_id=document_id,
                filename=filename,
                storage_provider=self.storage.provider_name
            )
            
            return DeleteResponse(
                success=True,
                document_id=document_id,
                message="Document deleted successfully",
                deleted_at=datetime.utcnow()
            )
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting document: {str(e)}")
            return DeleteResponse(
                success=False,
                document_id=document_id,
                message=f"Error deleting document: {str(e)}",
                deleted_at=datetime.utcnow()
            )
    
    async def generate_report(self, request: ReportRequest) -> ReportResponse:
        """
        Generate a report with metrics for the specified time period.
        
        Args:
            request: Report request with date range and grouping options
            
        Returns:
            ReportResponse with metrics and statistics
        """
        try:
            # Query documents within the date range
            documents = self.db.query(DocumentMetadata).filter(
                and_(
                    DocumentMetadata.created_at >= request.start_date,
                    DocumentMetadata.created_at <= request.end_date
                )
            ).all()
            
            # Calculate basic metrics
            total_documents = len(documents)
            total_size_bytes = sum(doc.size_bytes for doc in documents)
            
            # Group by content type
            documents_by_content_type: Dict[str, int] = defaultdict(int)
            for doc in documents:
                documents_by_content_type[doc.content_type] += 1
            
            # Group by tags
            documents_by_tag: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
            
            # Query tags for documents in range
            doc_ids = [doc.document_id for doc in documents]
            if doc_ids:
                tags = self.db.query(DocumentTag).filter(
                    DocumentTag.document_id.in_(doc_ids)
                ).all()
                
                for tag in tags:
                    documents_by_tag[tag.tag_key][tag.tag_value] += 1
            
            # Calculate daily uploads
            daily_uploads: Dict[str, Dict[str, Any]] = defaultdict(
                lambda: {"count": 0, "size_bytes": 0}
            )
            for doc in documents:
                date_key = doc.created_at.strftime("%Y-%m-%d")
                daily_uploads[date_key]["count"] += 1
                daily_uploads[date_key]["size_bytes"] += doc.size_bytes
            
            daily_uploads_list = [
                {"date": date, "count": data["count"], "size_bytes": data["size_bytes"]}
                for date, data in sorted(daily_uploads.items())
            ]
            
            # Calculate top tags
            top_tags: List[Dict[str, Any]] = []
            for tag_key, tag_values in documents_by_tag.items():
                for tag_value, count in tag_values.items():
                    top_tags.append({
                        "tag_key": tag_key,
                        "tag_value": tag_value,
                        "count": count
                    })
            top_tags = sorted(top_tags, key=lambda x: x["count"], reverse=True)[:10]
            
            # Build metrics summary
            metrics = MetricsSummary(
                total_documents=total_documents,
                total_size_bytes=total_size_bytes,
                total_size_mb=round(total_size_bytes / (1024 * 1024), 2),
                documents_by_content_type=dict(documents_by_content_type),
                documents_by_tag={k: dict(v) for k, v in documents_by_tag.items()},
                storage_provider=self.storage.provider_name
            )
            
            logger.info(
                f"Generated report for period {request.start_date} to {request.end_date}: "
                f"{total_documents} documents"
            )
            
            return ReportResponse(
                success=True,
                start_date=request.start_date,
                end_date=request.end_date,
                metrics=metrics,
                daily_uploads=daily_uploads_list,
                top_tags=top_tags
            )
            
        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")
            return ReportResponse(
                success=False,
                start_date=request.start_date,
                end_date=request.end_date,
                metrics=MetricsSummary(
                    total_documents=0,
                    total_size_bytes=0,
                    total_size_mb=0,
                    documents_by_content_type={},
                    documents_by_tag={},
                    storage_provider=self.storage.provider_name
                ),
                daily_uploads=[],
                top_tags=[]
            )
    
    async def move_to_deep_archive(
        self,
        request: DeepArchiveRequest
    ) -> DeepArchiveResponse:
        """
        Move a document to deep archive storage.
        
        Args:
            request: Deep archive request with document ID and target tier
            
        Returns:
            DeepArchiveResponse with operation status
        """
        try:
            # Get document metadata
            doc_metadata = self.db.query(DocumentMetadata).filter(
                DocumentMetadata.document_id == request.document_id
            ).first()
            
            if not doc_metadata:
                return DeepArchiveResponse(
                    success=False,
                    document_id=request.document_id,
                    message="Document not found",
                    previous_tier="",
                    new_tier="",
                    archived_at=datetime.utcnow()
                )
            
            previous_tier = doc_metadata.storage_tier or StorageTier.STANDARD.value
            
            # Move to archive in cloud storage
            result = await self.storage.move_to_archive(
                storage_path=doc_metadata.storage_path,
                storage_tier=request.storage_tier
            )
            
            if not result.success:
                return DeepArchiveResponse(
                    success=False,
                    document_id=request.document_id,
                    message=result.message,
                    previous_tier=previous_tier,
                    new_tier="",
                    archived_at=datetime.utcnow()
                )
            
            # Update database
            doc_metadata.storage_tier = request.storage_tier
            doc_metadata.restore_status = RestoreStatus.ARCHIVED.value
            doc_metadata.archived_at = datetime.utcnow()
            self.db.commit()
            
            logger.info(f"Moved document {request.document_id} to {request.storage_tier}")
            
            return DeepArchiveResponse(
                success=True,
                document_id=request.document_id,
                message=result.message,
                previous_tier=previous_tier,
                new_tier=request.storage_tier,
                archived_at=datetime.utcnow()
            )
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error moving to deep archive: {str(e)}")
            return DeepArchiveResponse(
                success=False,
                document_id=request.document_id,
                message=f"Error: {str(e)}",
                previous_tier="",
                new_tier="",
                archived_at=datetime.utcnow()
            )
    
    async def restore_from_deep_archive(
        self,
        request: RestoreRequest
    ) -> RestoreResponse:
        """
        Initiate restore of a document from deep archive.
        
        Args:
            request: Restore request with document ID and restore options
            
        Returns:
            RestoreResponse with restore status
        """
        try:
            # Get document metadata
            doc_metadata = self.db.query(DocumentMetadata).filter(
                DocumentMetadata.document_id == request.document_id
            ).first()
            
            if not doc_metadata:
                return RestoreResponse(
                    success=False,
                    document_id=request.document_id,
                    message="Document not found",
                    restore_status=""
                )
            
            # Check if already restored or not archived
            if doc_metadata.storage_tier == StorageTier.STANDARD.value:
                return RestoreResponse(
                    success=True,
                    document_id=request.document_id,
                    message="Document is in standard storage and immediately retrievable",
                    restore_status=RestoreStatus.NOT_ARCHIVED.value
                )
            
            # Initiate restore in cloud storage
            result = await self.storage.restore_from_archive(
                storage_path=doc_metadata.storage_path,
                restore_days=request.restore_days or 7,
                restore_tier=request.restore_tier or "Standard"
            )
            
            if not result.success:
                return RestoreResponse(
                    success=False,
                    document_id=request.document_id,
                    message=result.message,
                    restore_status=""
                )
            
            # Update database with restore status
            doc_metadata.restore_status = result.restore_status
            if result.restore_expiry:
                from dateutil import parser
                try:
                    doc_metadata.restore_expiry = parser.parse(result.restore_expiry)
                except:
                    pass
            self.db.commit()
            
            logger.info(f"Initiated restore for document {request.document_id}")
            
            return RestoreResponse(
                success=True,
                document_id=request.document_id,
                message=result.message,
                restore_status=result.restore_status,
                estimated_completion=result.estimated_completion,
                restore_expiry=doc_metadata.restore_expiry
            )
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error restoring from deep archive: {str(e)}")
            return RestoreResponse(
                success=False,
                document_id=request.document_id,
                message=f"Error: {str(e)}",
                restore_status=""
            )
    
    async def get_archive_status(self, document_id: str) -> ArchiveStatusResponse:
        """
        Get the archive/restore status of a document.
        
        Args:
            document_id: Document identifier
            
        Returns:
            ArchiveStatusResponse with current status
        """
        try:
            # Get document metadata
            doc_metadata = self.db.query(DocumentMetadata).filter(
                DocumentMetadata.document_id == document_id
            ).first()
            
            if not doc_metadata:
                return ArchiveStatusResponse(
                    success=False,
                    document_id=document_id,
                    storage_tier="",
                    restore_status="",
                    is_retrievable=False,
                    message="Document not found"
                )
            
            # Get real-time status from cloud storage
            result = await self.storage.get_archive_status(
                storage_path=doc_metadata.storage_path
            )
            
            # Update database with latest status
            if result.success:
                doc_metadata.restore_status = result.restore_status
                if result.restore_expiry:
                    from dateutil import parser
                    try:
                        doc_metadata.restore_expiry = parser.parse(result.restore_expiry)
                    except:
                        pass
                self.db.commit()
            
            return ArchiveStatusResponse(
                success=True,
                document_id=document_id,
                storage_tier=doc_metadata.storage_tier or StorageTier.STANDARD.value,
                restore_status=result.restore_status if result.success else doc_metadata.restore_status or "",
                restore_expiry=doc_metadata.restore_expiry,
                is_retrievable=result.is_retrievable if result.success else False,
                message=result.message
            )
            
        except Exception as e:
            logger.error(f"Error getting archive status: {str(e)}")
            return ArchiveStatusResponse(
                success=False,
                document_id=document_id,
                storage_tier="",
                restore_status="",
                is_retrievable=False,
                message=f"Error: {str(e)}"
            )
    
    async def retrieve_from_glacier(
        self,
        request: GlacierRetrieveRequest
    ) -> GlacierRetrieveResponse:
        """
        Retrieve a document from Glacier/archive storage.
        
        If the document is already restored, returns the document content.
        If restoration is needed, initiates restore and returns status.
        When restore completes, publishes Kafka event.
        
        Args:
            request: Glacier retrieve request with document ID and options
            
        Returns:
            GlacierRetrieveResponse with document content or restore status
        """
        try:
            # Get document metadata
            doc_metadata = self.db.query(DocumentMetadata).filter(
                DocumentMetadata.document_id == request.document_id
            ).first()
            
            if not doc_metadata:
                return GlacierRetrieveResponse(
                    success=False,
                    document_id=request.document_id,
                    filename="",
                    storage_tier="",
                    restore_status="",
                    is_retrievable=False,
                    message="Document not found"
                )
            
            # Check if document is in archive storage
            storage_tier = doc_metadata.storage_tier or StorageTier.STANDARD.value
            
            # If in standard storage, retrieve directly
            if storage_tier == StorageTier.STANDARD.value:
                result = await self.storage.download(doc_metadata.storage_path)
                
                if result.success:
                    document_base64 = base64.b64encode(result.data).decode('utf-8')
                    return GlacierRetrieveResponse(
                        success=True,
                        document_id=request.document_id,
                        filename=doc_metadata.filename,
                        storage_tier=storage_tier,
                        restore_status=RestoreStatus.NOT_ARCHIVED.value,
                        is_retrievable=True,
                        document_base64=document_base64,
                        message="Document retrieved successfully (standard storage)"
                    )
                else:
                    return GlacierRetrieveResponse(
                        success=False,
                        document_id=request.document_id,
                        filename=doc_metadata.filename,
                        storage_tier=storage_tier,
                        restore_status="",
                        is_retrievable=False,
                        message=result.message
                    )
            
            # Document is in archive storage - check restore status
            archive_status = await self.storage.get_archive_status(doc_metadata.storage_path)
            
            if archive_status.success and archive_status.is_retrievable:
                # Document is restored and available!
                result = await self.storage.download(doc_metadata.storage_path)
                
                if result.success:
                    document_base64 = base64.b64encode(result.data).decode('utf-8')
                    
                    # Update database
                    doc_metadata.restore_status = RestoreStatus.RESTORED.value
                    if archive_status.restore_expiry:
                        from dateutil import parser
                        try:
                            doc_metadata.restore_expiry = parser.parse(archive_status.restore_expiry)
                        except:
                            pass
                    self.db.commit()
                    
                    # Publish Kafka event - document is ready
                    kafka_published = await self.kafka.publish_restore_ready(
                        document_id=request.document_id,
                        filename=doc_metadata.filename,
                        storage_tier=storage_tier,
                        restore_expiry=doc_metadata.restore_expiry
                    )
                    
                    logger.info(f"Retrieved document {request.document_id} from Glacier")
                    
                    return GlacierRetrieveResponse(
                        success=True,
                        document_id=request.document_id,
                        filename=doc_metadata.filename,
                        storage_tier=storage_tier,
                        restore_status=RestoreStatus.RESTORED.value,
                        is_retrievable=True,
                        document_base64=document_base64,
                        restore_expiry=doc_metadata.restore_expiry,
                        message="Document retrieved successfully from Glacier",
                        kafka_event_published=kafka_published
                    )
                else:
                    return GlacierRetrieveResponse(
                        success=False,
                        document_id=request.document_id,
                        filename=doc_metadata.filename,
                        storage_tier=storage_tier,
                        restore_status=archive_status.restore_status,
                        is_retrievable=False,
                        message=f"Restore complete but download failed: {result.message}"
                    )
            
            # Check if restore is in progress
            if archive_status.restore_status == "in_progress":
                return GlacierRetrieveResponse(
                    success=True,
                    document_id=request.document_id,
                    filename=doc_metadata.filename,
                    storage_tier=storage_tier,
                    restore_status=RestoreStatus.RESTORE_IN_PROGRESS.value,
                    is_retrievable=False,
                    estimated_completion=archive_status.estimated_completion,
                    message="Restore is in progress. Please check back later."
                )
            
            # Need to initiate restore
            restore_result = await self.storage.restore_from_archive(
                storage_path=doc_metadata.storage_path,
                restore_days=request.restore_days or 7,
                restore_tier=request.restore_tier or "Standard"
            )
            
            if restore_result.success:
                # Update database
                doc_metadata.restore_status = RestoreStatus.RESTORE_IN_PROGRESS.value
                self.db.commit()
                
                # Publish Kafka event - restore initiated
                await self.kafka.publish_restore_initiated(
                    document_id=request.document_id,
                    filename=doc_metadata.filename,
                    restore_tier=request.restore_tier or "Standard",
                    estimated_completion=restore_result.estimated_completion
                )
                
                return GlacierRetrieveResponse(
                    success=True,
                    document_id=request.document_id,
                    filename=doc_metadata.filename,
                    storage_tier=storage_tier,
                    restore_status=RestoreStatus.RESTORE_IN_PROGRESS.value,
                    is_retrievable=False,
                    estimated_completion=restore_result.estimated_completion,
                    message=f"Restore initiated. {restore_result.message}"
                )
            else:
                return GlacierRetrieveResponse(
                    success=False,
                    document_id=request.document_id,
                    filename=doc_metadata.filename,
                    storage_tier=storage_tier,
                    restore_status="",
                    is_retrievable=False,
                    message=f"Failed to initiate restore: {restore_result.message}"
                )
                
        except Exception as e:
            logger.error(f"Error retrieving from Glacier: {str(e)}")
            return GlacierRetrieveResponse(
                success=False,
                document_id=request.document_id,
                filename="",
                storage_tier="",
                restore_status="",
                is_retrievable=False,
                message=f"Error: {str(e)}"
            )
    
    def _prepare_embedding_text(
        self,
        filename: str,
        tags: Dict[str, str],
        metadata: Dict[str, Any]
    ) -> str:
        """
        Prepare text for embedding from document metadata.
        
        Args:
            filename: Document filename
            tags: Document tags
            metadata: Document metadata
            
        Returns:
            Combined text for embedding
        """
        text_parts = [filename]
        
        # Add tags
        for key, value in tags.items():
            text_parts.append(f"{key}: {value}")
        
        # Add metadata
        for key, value in metadata.items():
            if isinstance(value, (str, int, float)):
                text_parts.append(f"{key}: {value}")
        
        return " ".join(text_parts)
    
    async def vector_search(self, request: VectorSearchRequest) -> VectorSearchResponse:
        """
        Perform semantic search on documents using vector embeddings.
        
        Args:
            request: Vector search request with query and parameters
            
        Returns:
            Vector search response with ranked results
        """
        search_start = time.time()
        
        try:
            # Generate embedding for the query
            query_embedding = self.embeddings.generate_embedding(request.query)
            
            if not query_embedding:
                return VectorSearchResponse(
                    success=False,
                    query=request.query,
                    results=[],
                    total_results=0,
                    search_time_ms=0.0
                )
            
            # Get all documents with embeddings
            docs_with_embeddings = self.db.query(DocumentMetadata).filter(
                DocumentMetadata.embedding.isnot(None)
            ).all()
            
            if not docs_with_embeddings:
                search_time_ms = (time.time() - search_start) * 1000
                return VectorSearchResponse(
                    success=True,
                    query=request.query,
                    results=[],
                    total_results=0,
                    search_time_ms=search_time_ms
                )
            
            # Calculate similarities
            results = []
            for doc in docs_with_embeddings:
                similarity = self.embeddings.cosine_similarity(
                    query_embedding,
                    doc.embedding_vector
                )
                
                # Only include results above threshold
                if similarity >= request.min_similarity:
                    results.append({
                        "document_id": doc.document_id,
                        "filename": doc.filename,
                        "content_type": doc.content_type,
                        "similarity_score": similarity,
                        "tags": doc.tags,
                        "created_at": doc.created_at,
                        "storage_tier": doc.storage_tier,
                        "doc_object": doc
                    })
            
            # Sort by similarity (descending)
            results.sort(key=lambda x: x["similarity_score"], reverse=True)
            
            # Limit to top_k
            results = results[:request.top_k]
            
            # Build response
            search_results = [
                VectorSearchResult(
                    document_id=r["document_id"],
                    filename=r["filename"],
                    content_type=r["content_type"],
                    similarity_score=r["similarity_score"],
                    tags=r["tags"],
                    created_at=r["created_at"],
                    storage_tier=r["storage_tier"]
                )
                for r in results
            ]
            
            search_time_ms = (time.time() - search_start) * 1000
            
            logger.info(f"Vector search completed: '{request.query}' -> {len(search_results)} results in {search_time_ms:.2f}ms")
            
            return VectorSearchResponse(
                success=True,
                query=request.query,
                results=search_results,
                total_results=len(search_results),
                search_time_ms=search_time_ms
            )
            
        except Exception as e:
            logger.error(f"Error in vector search: {str(e)}")
            search_time_ms = (time.time() - search_start) * 1000
            return VectorSearchResponse(
                success=False,
                query=request.query,
                results=[],
                total_results=0,
                search_time_ms=search_time_ms
            )

    async def detect_piis(self, request: PIIDetectionRequest) -> PIIDetectionResponse:
        """
        Detect personally identifiable information in a document.
        
        Args:
            request: PII detection request with document ID and PII types
            
        Returns:
            PIIDetectionResponse with detected PIIs
        """
        try:
            # Retrieve document
            doc = self.db.query(DocumentMetadata).filter(
                DocumentMetadata.document_id == request.document_id
            ).first()
            
            if not doc:
                return PIIDetectionResponse(
                    success=False,
                    document_id=request.document_id,
                    filename="unknown",
                    pii_found=False,
                    total_piis=0,
                    pii_summary={},
                    detected_piis=[],
                    message="Document not found"
                )
            
            # Retrieve document content from storage
            try:
                content_base64 = self.storage.retrieve(request.document_id)
                content_bytes = base64.b64decode(content_base64)
                # Try to decode as text; fallback to hex representation if binary
                try:
                    document_text = content_bytes.decode('utf-8', errors='ignore')
                except:
                    document_text = content_bytes.hex()
            except Exception as e:
                logger.warning(f"Could not retrieve document content: {str(e)}")
                document_text = f"Unable to extract text: {str(e)}"
            
            # Convert PII types from strings to enum
            pii_enum_types = None
            if request.pii_types:
                try:
                    pii_enum_types = [PIIType(ptype) for ptype in request.pii_types]
                except ValueError as e:
                    logger.warning(f"Invalid PII type: {str(e)}")
            
            # Detect PIIs
            detected_entities = self.anonymizer.detect_piis(document_text, pii_enum_types)
            
            # Get summary
            summary = self.anonymizer.get_summary(detected_entities)
            
            # Build response
            detected_piis = [
                PII(
                    type=entity.entity_type.value,
                    detected_value=entity.text[:50] + "..." if len(entity.text) > 50 else entity.text,
                    confidence=entity.confidence,
                    position={"start": entity.start, "end": entity.end}
                )
                for entity in detected_entities
            ]
            
            message = f"PII detection completed. Found {len(detected_entities)} PII." if detected_entities else "No PII detected."
            
            logger.info(f"PII detection for {request.document_id}: {len(detected_entities)} PIIs found")
            
            return PIIDetectionResponse(
                success=True,
                document_id=request.document_id,
                filename=doc.filename,
                pii_found=len(detected_entities) > 0,
                total_piis=len(detected_entities),
                pii_summary=summary,
                detected_piis=detected_piis,
                message=message
            )
            
        except Exception as e:
            logger.error(f"Error in PII detection: {str(e)}")
            return PIIDetectionResponse(
                success=False,
                document_id=request.document_id,
                filename="unknown",
                pii_found=False,
                total_piis=0,
                pii_summary={},
                detected_piis=[],
                message=f"Error during PII detection: {str(e)}"
            )

    async def anonymize_document(self, request: AnonymizeRequest) -> AnonymizeResponse:
        """
        Anonymize personally identifiable information in a document.
        
        Args:
            request: Anonymization request with document ID, PII types, and options
            
        Returns:
            AnonymizeResponse with anonymization results
        """
        try:
            # Retrieve document metadata
            doc = self.db.query(DocumentMetadata).filter(
                DocumentMetadata.document_id == request.document_id
            ).first()
            
            if not doc:
                return AnonymizeResponse(
                    success=False,
                    document_id=request.document_id,
                    original_filename="unknown",
                    total_piis_anonymized=0,
                    message="Document not found"
                )
            
            # Retrieve document content
            try:
                content_base64 = self.storage.retrieve(request.document_id)
                content_bytes = base64.b64decode(content_base64)
                # Try to decode as text; fallback to hex representation if binary
                try:
                    document_text = content_bytes.decode('utf-8', errors='ignore')
                except:
                    document_text = content_bytes.hex()
            except Exception as e:
                logger.warning(f"Could not retrieve document content: {str(e)}")
                return AnonymizeResponse(
                    success=False,
                    document_id=request.document_id,
                    original_filename=doc.filename,
                    total_piis_anonymized=0,
                    message=f"Could not retrieve document: {str(e)}"
                )
            
            # Convert PII types
            pii_enum_types = None
            if request.pii_types:
                try:
                    pii_enum_types = [PIIType(ptype) for ptype in request.pii_types]
                except ValueError as e:
                    logger.warning(f"Invalid PII type: {str(e)}")
            
            # Anonymize
            anonymized_text, operations = self.anonymizer.anonymize(
                document_text,
                pii_enum_types,
                request.mask_mode
            )
            
            # Prepare response
            anonymization_ops = [
                AnonymizationOperation(
                    type=op["type"].value if isinstance(op["type"], PIIType) else op["type"],
                    original_text=op["original_text"][:50] + "..." if len(op["original_text"]) > 50 else op["original_text"],
                    replacement=op["replacement"],
                    confidence=op["confidence"]
                )
                for op in operations
            ]
            
            # Generate preview (first 500 chars)
            preview = anonymized_text[:500] + "..." if len(anonymized_text) > 500 else anonymized_text
            
            new_document_id = None
            anonymized_filename = None
            
            # Optionally save anonymized version as new document
            if request.save_anonymized_version and operations:
                try:
                    # Convert anonymized text back to base64
                    anonymized_bytes = anonymized_text.encode('utf-8')
                    anonymized_base64 = base64.b64encode(anonymized_bytes).decode('utf-8')
                    
                    # Create archive request for anonymized version
                    name_parts = doc.filename.rsplit('.', 1)
                    if len(name_parts) == 2:
                        anonymized_filename = f"{name_parts[0]}-anonymized.{name_parts[1]}"
                    else:
                        anonymized_filename = f"{doc.filename}-anonymized"
                    
                    archive_request = ArchiveRequest(
                        document_base64=anonymized_base64,
                        filename=anonymized_filename,
                        content_type=doc.content_type,
                        tags={"anonymized": "true", "original_id": request.document_id},
                        metadata={"original_filename": doc.filename, "source_document_id": request.document_id}
                    )
                    
                    archive_response = await self.archive_document(archive_request)
                    if archive_response.success:
                        new_document_id = archive_response.document_id
                        logger.info(f"Anonymized version saved: {new_document_id}")
                
                except Exception as e:
                    logger.warning(f"Could not save anonymized version: {str(e)}")
            
            message = f"Document anonymized successfully. {len(operations)} PII anonymized with '{request.mask_mode}' mode."
            
            logger.info(f"Anonymization for {request.document_id}: {len(operations)} PIIs anonymized")
            
            return AnonymizeResponse(
                success=True,
                document_id=request.document_id,
                original_filename=doc.filename,
                anonymized_filename=anonymized_filename,
                total_piis_anonymized=len(operations),
                anonymization_operations=anonymization_ops,
                preview_anonymized_content=preview,
                new_document_id=new_document_id,
                mask_mode_used=request.mask_mode,
                message=message
            )
            
        except Exception as e:
            logger.error(f"Error in anonymization: {str(e)}")
            return AnonymizeResponse(
                success=False,
                document_id=request.document_id,
                original_filename="unknown",
                total_piis_anonymized=0,
                message=f"Error during anonymization: {str(e)}"
            )
