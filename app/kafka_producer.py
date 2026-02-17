"""Kafka producer service for publishing document events."""

import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum

from app.config import settings

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Types of events published to Kafka."""
    DOCUMENT_ARCHIVED = "document_archived"
    DOCUMENT_DELETED = "document_deleted"
    DOCUMENT_MOVED_TO_GLACIER = "document_moved_to_glacier"
    DOCUMENT_RESTORE_INITIATED = "document_restore_initiated"
    DOCUMENT_RESTORE_READY = "document_restore_ready"
    DOCUMENT_RESTORE_EXPIRED = "document_restore_expired"


class KafkaProducerService:
    """Service for publishing events to Kafka."""
    
    def __init__(self):
        """Initialize the Kafka producer."""
        self._producer = None
        self._enabled = settings.kafka_enabled
    
    @property
    def producer(self):
        """Lazy initialization of Kafka producer."""
        if self._producer is None and self._enabled:
            try:
                from aiokafka import AIOKafkaProducer
                import asyncio
                
                self._producer = AIOKafkaProducer(
                    bootstrap_servers=settings.kafka_bootstrap_servers,
                    value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
                    key_serializer=lambda k: k.encode('utf-8') if k else None
                )
            except ImportError:
                logger.warning("aiokafka not installed, Kafka publishing disabled")
                self._enabled = False
            except Exception as e:
                logger.error(f"Failed to create Kafka producer: {str(e)}")
                self._enabled = False
        return self._producer
    
    async def start(self):
        """Start the Kafka producer."""
        if self._enabled and self.producer:
            try:
                await self.producer.start()
                logger.info("Kafka producer started successfully")
            except Exception as e:
                logger.error(f"Failed to start Kafka producer: {str(e)}")
                self._enabled = False
    
    async def stop(self):
        """Stop the Kafka producer."""
        if self._producer:
            try:
                await self._producer.stop()
                logger.info("Kafka producer stopped")
            except Exception as e:
                logger.error(f"Error stopping Kafka producer: {str(e)}")
    
    async def publish_event(
        self,
        topic: str,
        event_type: EventType,
        document_id: str,
        data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Publish an event to Kafka.
        
        Args:
            topic: Kafka topic to publish to
            event_type: Type of event
            document_id: Document identifier (used as message key)
            data: Additional event data
            
        Returns:
            True if published successfully, False otherwise
        """
        if not self._enabled:
            logger.debug(f"Kafka disabled, skipping event: {event_type.value}")
            return False
        
        try:
            event = {
                "event_type": event_type.value,
                "document_id": document_id,
                "timestamp": datetime.utcnow().isoformat(),
                "data": data or {}
            }
            
            if self.producer:
                await self.producer.send_and_wait(
                    topic=topic,
                    key=document_id,
                    value=event
                )
                logger.info(f"Published event {event_type.value} for document {document_id}")
                return True
            else:
                logger.warning("Kafka producer not available")
                return False
                
        except Exception as e:
            logger.error(f"Failed to publish event: {str(e)}")
            return False
    
    async def publish_document_archived(
        self,
        document_id: str,
        filename: str,
        storage_tier: str,
        storage_provider: str
    ) -> bool:
        """Publish event when a document is archived."""
        return await self.publish_event(
            topic=settings.kafka_topic_archived,
            event_type=EventType.DOCUMENT_ARCHIVED,
            document_id=document_id,
            data={
                "filename": filename,
                "storage_tier": storage_tier,
                "storage_provider": storage_provider
            }
        )
    
    async def publish_moved_to_glacier(
        self,
        document_id: str,
        filename: str,
        previous_tier: str,
        new_tier: str,
        moved_at: datetime
    ) -> bool:
        """Publish event when a document is moved to Glacier."""
        return await self.publish_event(
            topic=settings.kafka_topic_archived,
            event_type=EventType.DOCUMENT_MOVED_TO_GLACIER,
            document_id=document_id,
            data={
                "filename": filename,
                "previous_tier": previous_tier,
                "new_tier": new_tier,
                "moved_at": moved_at.isoformat()
            }
        )
    
    async def publish_restore_initiated(
        self,
        document_id: str,
        filename: str,
        restore_tier: str,
        estimated_completion: Optional[str] = None
    ) -> bool:
        """Publish event when restore is initiated."""
        return await self.publish_event(
            topic=settings.kafka_topic_restore_ready,
            event_type=EventType.DOCUMENT_RESTORE_INITIATED,
            document_id=document_id,
            data={
                "filename": filename,
                "restore_tier": restore_tier,
                "estimated_completion": estimated_completion
            }
        )
    
    async def publish_restore_ready(
        self,
        document_id: str,
        filename: str,
        storage_tier: str,
        restore_expiry: Optional[datetime] = None,
        download_url: Optional[str] = None
    ) -> bool:
        """Publish event when a document restore is complete and ready for download."""
        return await self.publish_event(
            topic=settings.kafka_topic_restore_ready,
            event_type=EventType.DOCUMENT_RESTORE_READY,
            document_id=document_id,
            data={
                "filename": filename,
                "storage_tier": storage_tier,
                "restore_expiry": restore_expiry.isoformat() if restore_expiry else None,
                "download_url": download_url,
                "message": "Document is now available for download"
            }
        )
    
    async def publish_restore_expired(
        self,
        document_id: str,
        filename: str
    ) -> bool:
        """Publish event when a restored document expires."""
        return await self.publish_event(
            topic=settings.kafka_topic_restore_ready,
            event_type=EventType.DOCUMENT_RESTORE_EXPIRED,
            document_id=document_id,
            data={
                "filename": filename,
                "message": "Restored document copy has expired"
            }
        )

    async def publish_document_deleted(
        self,
        document_id: str,
        filename: str,
        storage_provider: str,
        deleted_by: Optional[str] = None
    ) -> bool:
        """Publish event when a document is deleted."""
        return await self.publish_event(
            topic=settings.kafka_topic_archived,
            event_type=EventType.DOCUMENT_DELETED,
            document_id=document_id,
            data={
                "filename": filename,
                "storage_provider": storage_provider,
                "deleted_by": deleted_by,
                "message": "Document permanently deleted"
            }
        )


# Singleton instance
_kafka_producer: Optional[KafkaProducerService] = None


def get_kafka_producer() -> KafkaProducerService:
    """Get the Kafka producer singleton instance."""
    global _kafka_producer
    if _kafka_producer is None:
        _kafka_producer = KafkaProducerService()
    return _kafka_producer
