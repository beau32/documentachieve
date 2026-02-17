"""Lifecycle service for automatic archival of documents based on age."""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.config import settings, StorageTier, RestoreStatus
from app.database import DocumentMetadata, SessionLocal
from app.storage.factory import get_storage_provider
from app.kafka_producer import get_kafka_producer

logger = logging.getLogger(__name__)


class LifecycleService:
    """Service for managing document lifecycle and automatic archival."""
    
    def __init__(self, db: Session = None):
        """Initialize the lifecycle service."""
        self._db = db
        self._storage = get_storage_provider()
        self._kafka = get_kafka_producer()
    
    @property
    def db(self) -> Session:
        """Get database session, creating one if needed."""
        if self._db is None:
            self._db = SessionLocal()
        return self._db
    
    def close(self):
        """Close database session if we created it."""
        if self._db:
            self._db.close()
            self._db = None
    
    async def get_documents_for_archival(
        self,
        archive_after_days: int = None,
        target_tier: StorageTier = StorageTier.ARCHIVE
    ) -> List[DocumentMetadata]:
        """
        Get documents that should be moved to archive based on their creation date.
        
        Args:
            archive_after_days: Days after creation to archive (default from settings)
            target_tier: Target storage tier
            
        Returns:
            List of documents eligible for archival
        """
        if archive_after_days is None:
            if target_tier == StorageTier.DEEP_ARCHIVE:
                archive_after_days = settings.lifecycle_deep_archive_after_days
            else:
                archive_after_days = settings.lifecycle_archive_after_days
        
        cutoff_date = datetime.utcnow() - timedelta(days=archive_after_days)
        
        # Find documents in standard/lower tier that are older than cutoff
        eligible_tiers = [StorageTier.STANDARD.value]
        if target_tier == StorageTier.DEEP_ARCHIVE:
            eligible_tiers.extend([StorageTier.INFREQUENT.value, StorageTier.ARCHIVE.value])
        elif target_tier == StorageTier.ARCHIVE:
            eligible_tiers.append(StorageTier.INFREQUENT.value)
        
        documents = self.db.query(DocumentMetadata).filter(
            and_(
                DocumentMetadata.created_at <= cutoff_date,
                DocumentMetadata.storage_tier.in_(eligible_tiers)
            )
        ).all()
        
        return documents
    
    async def archive_document(
        self,
        document: DocumentMetadata,
        target_tier: StorageTier = StorageTier.DEEP_ARCHIVE
    ) -> Dict[str, Any]:
        """
        Move a single document to archive storage.
        
        Args:
            document: Document metadata
            target_tier: Target storage tier
            
        Returns:
            Result dictionary with success status and details
        """
        try:
            previous_tier = document.storage_tier or StorageTier.STANDARD.value
            
            # Move in cloud storage
            result = await self._storage.move_to_archive(
                storage_path=document.storage_path,
                storage_tier=target_tier.value
            )
            
            if not result.success:
                return {
                    "success": False,
                    "document_id": document.document_id,
                    "error": result.message
                }
            
            # Update database
            document.storage_tier = target_tier.value
            document.restore_status = RestoreStatus.ARCHIVED.value
            document.archived_at = datetime.utcnow()
            self.db.commit()
            
            # Publish Kafka event
            await self._kafka.publish_moved_to_glacier(
                document_id=document.document_id,
                filename=document.filename,
                previous_tier=previous_tier,
                new_tier=target_tier.value,
                moved_at=datetime.utcnow()
            )
            
            logger.info(
                f"Archived document {document.document_id} from {previous_tier} to {target_tier.value}"
            )
            
            return {
                "success": True,
                "document_id": document.document_id,
                "filename": document.filename,
                "previous_tier": previous_tier,
                "new_tier": target_tier.value,
                "archived_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to archive document {document.document_id}: {str(e)}")
            return {
                "success": False,
                "document_id": document.document_id,
                "error": str(e)
            }
    
    async def run_lifecycle_archival(
        self,
        target_tier: StorageTier = StorageTier.DEEP_ARCHIVE,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Run the lifecycle archival process to move eligible documents to archive.
        
        Args:
            target_tier: Target storage tier
            dry_run: If True, only report what would be archived without making changes
            
        Returns:
            Summary of the archival process
        """
        logger.info(f"Starting lifecycle archival run (target: {target_tier.value}, dry_run: {dry_run})")
        
        documents = await self.get_documents_for_archival(target_tier=target_tier)
        
        results = {
            "started_at": datetime.utcnow().isoformat(),
            "target_tier": target_tier.value,
            "dry_run": dry_run,
            "total_eligible": len(documents),
            "successful": 0,
            "failed": 0,
            "documents": []
        }
        
        if dry_run:
            # Just report what would be archived
            for doc in documents:
                results["documents"].append({
                    "document_id": doc.document_id,
                    "filename": doc.filename,
                    "current_tier": doc.storage_tier,
                    "created_at": doc.created_at.isoformat(),
                    "age_days": (datetime.utcnow() - doc.created_at).days,
                    "action": "would_archive"
                })
            logger.info(f"Dry run complete: {len(documents)} documents eligible for archival")
        else:
            # Actually archive the documents
            for doc in documents:
                result = await self.archive_document(doc, target_tier)
                results["documents"].append(result)
                if result["success"]:
                    results["successful"] += 1
                else:
                    results["failed"] += 1
            
            logger.info(
                f"Archival complete: {results['successful']} succeeded, "
                f"{results['failed']} failed out of {results['total_eligible']}"
            )
        
        results["completed_at"] = datetime.utcnow().isoformat()
        return results
    
    async def check_and_update_restore_status(self) -> Dict[str, Any]:
        """
        Check restore status of documents that are being restored and update accordingly.
        If restore is complete, publish Kafka event.
        
        Returns:
            Summary of status updates
        """
        logger.info("Checking restore status for in-progress documents")
        
        # Find documents with restore in progress
        documents = self.db.query(DocumentMetadata).filter(
            DocumentMetadata.restore_status == RestoreStatus.RESTORE_IN_PROGRESS.value
        ).all()
        
        results = {
            "checked": len(documents),
            "restored": 0,
            "still_in_progress": 0,
            "errors": 0,
            "documents": []
        }
        
        for doc in documents:
            try:
                # Check actual status in cloud storage
                status_result = await self._storage.get_archive_status(doc.storage_path)
                
                if status_result.success:
                    if status_result.is_retrievable and status_result.restore_status == "restored":
                        # Restore complete!
                        doc.restore_status = RestoreStatus.RESTORED.value
                        if status_result.restore_expiry:
                            from dateutil import parser
                            try:
                                doc.restore_expiry = parser.parse(status_result.restore_expiry)
                            except:
                                pass
                        
                        self.db.commit()
                        
                        # Publish Kafka event
                        await self._kafka.publish_restore_ready(
                            document_id=doc.document_id,
                            filename=doc.filename,
                            storage_tier=doc.storage_tier,
                            restore_expiry=doc.restore_expiry
                        )
                        
                        results["restored"] += 1
                        results["documents"].append({
                            "document_id": doc.document_id,
                            "status": "restored",
                            "restore_expiry": doc.restore_expiry.isoformat() if doc.restore_expiry else None
                        })
                        
                        logger.info(f"Document {doc.document_id} restore complete, Kafka event published")
                    else:
                        results["still_in_progress"] += 1
                        results["documents"].append({
                            "document_id": doc.document_id,
                            "status": "in_progress"
                        })
                else:
                    results["errors"] += 1
                    results["documents"].append({
                        "document_id": doc.document_id,
                        "status": "error",
                        "message": status_result.message
                    })
                    
            except Exception as e:
                results["errors"] += 1
                results["documents"].append({
                    "document_id": doc.document_id,
                    "status": "error",
                    "message": str(e)
                })
                logger.error(f"Error checking restore status for {doc.document_id}: {str(e)}")
        
        return results
    
    async def check_expired_restores(self) -> Dict[str, Any]:
        """
        Check for restored documents that have expired and update their status.
        
        Returns:
            Summary of expired documents
        """
        now = datetime.utcnow()
        
        # Find documents with expired restores
        documents = self.db.query(DocumentMetadata).filter(
            and_(
                DocumentMetadata.restore_status == RestoreStatus.RESTORED.value,
                DocumentMetadata.restore_expiry <= now
            )
        ).all()
        
        results = {
            "expired": len(documents),
            "documents": []
        }
        
        for doc in documents:
            doc.restore_status = RestoreStatus.ARCHIVED.value
            doc.restore_expiry = None
            
            results["documents"].append({
                "document_id": doc.document_id,
                "filename": doc.filename
            })
            
            # Publish expiry event
            await self._kafka.publish_restore_expired(
                document_id=doc.document_id,
                filename=doc.filename
            )
        
        if documents:
            self.db.commit()
            logger.info(f"Marked {len(documents)} restored documents as expired")
        
        return results


# Background scheduler for lifecycle tasks
_scheduler = None


def get_lifecycle_scheduler():
    """Get or create the lifecycle scheduler."""
    global _scheduler
    if _scheduler is None and settings.lifecycle_enabled:
        try:
            from apscheduler.schedulers.asyncio import AsyncIOScheduler
            _scheduler = AsyncIOScheduler()
        except ImportError:
            logger.warning("APScheduler not installed, lifecycle scheduling disabled")
    return _scheduler


async def lifecycle_job():
    """Background job for running lifecycle archival."""
    service = LifecycleService()
    try:
        # Run archival for archive tier
        await service.run_lifecycle_archival(
            target_tier=StorageTier.ARCHIVE,
            dry_run=False
        )
        
        # Run archival for deep archive tier
        await service.run_lifecycle_archival(
            target_tier=StorageTier.DEEP_ARCHIVE,
            dry_run=False
        )
        
        # Check restore status
        await service.check_and_update_restore_status()
        
        # Check expired restores
        await service.check_expired_restores()
    finally:
        service.close()


async def start_lifecycle_scheduler():
    """Start the lifecycle scheduler."""
    if not settings.lifecycle_enabled:
        logger.info("Lifecycle scheduling is disabled")
        return
    
    scheduler = get_lifecycle_scheduler()
    if scheduler:
        scheduler.add_job(
            lifecycle_job,
            'interval',
            hours=settings.lifecycle_check_interval_hours,
            id='lifecycle_archival',
            replace_existing=True
        )
        scheduler.start()
        logger.info(
            f"Lifecycle scheduler started (interval: {settings.lifecycle_check_interval_hours} hours)"
        )


async def stop_lifecycle_scheduler():
    """Stop the lifecycle scheduler."""
    global _scheduler
    if _scheduler:
        _scheduler.shutdown()
        _scheduler = None
        logger.info("Lifecycle scheduler stopped")
