"""Iceberg table support for storing document metadata on AWS S3."""

import logging
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

import pyarrow as pa
from pyiceberg.catalog import load_catalog
from pyiceberg.exceptions import IcebergError
from pyiceberg.schema import (
    Schema,
    NestedField,
    StructType,
)
from pyiceberg.types import (
    IntegerType,
    StringType,
    BinaryType,
    TimestampType,
    NestedField as Field,
)

from app.config import settings, StorageTier, RestoreStatus

logger = logging.getLogger(__name__)


@dataclass
class DocumentMetadataRecord:
    """Iceberg record for document metadata."""
    document_id: str
    filename: str
    content_type: str
    size_bytes: int
    storage_provider: str
    storage_path: str
    storage_tier: str
    restore_status: Optional[str]
    restore_expiry: Optional[int]  # Unix timestamp
    archived_at: Optional[int]  # Unix timestamp
    tags_json: Optional[str]
    metadata_json: Optional[str]
    embedding: Optional[str]  # JSON array
    embedding_text: Optional[str]
    created_at: int  # Unix timestamp
    updated_at: int  # Unix timestamp


class IcebergDatabase:
    """Iceberg table manager for document metadata storage on S3."""
    
    CATALOG_NAME = "s3"
    NAMESPACE = "document_archive"
    TABLE_NAME = "document_metadata"
    TABLE_FULL_NAME = f"{NAMESPACE}.{TABLE_NAME}"
    
    def __init__(self):
        """Initialize Iceberg catalog and table."""
        self.catalog = None
        self.table = None
        self._connect()
    
    def _connect(self):
        """Connect to Iceberg catalog."""
        try:
            # Configure Iceberg catalog for S3
            catalog_config = {
                "type": "rest",
                "uri": settings.iceberg_catalog_uri or "http://localhost:8181",
                "s3.endpoint": settings.iceberg_s3_endpoint,
                "s3.access-key-id": settings.aws_access_key_id,
                "s3.secret-access-key": settings.aws_secret_access_key,
                "s3.region": settings.aws_region,
            }
            
            self.catalog = load_catalog(self.CATALOG_NAME, **catalog_config)
            logger.info("Connected to Iceberg catalog")
            
            # Create namespace if it doesn't exist
            try:
                self.catalog.create_namespace(self.NAMESPACE)
            except IcebergError:
                pass  # Namespace already exists
            
            # Get or create table
            self._ensure_table_exists()
            
        except Exception as e:
            logger.error(f"Failed to connect to Iceberg catalog: {e}")
            raise
    
    def _ensure_table_exists(self):
        """Create table if it doesn't exist."""
        try:
            self.table = self.catalog.load_table(self.TABLE_FULL_NAME)
            logger.info("Loaded existing Iceberg table")
        except IcebergError:
            # Table doesn't exist, create it
            schema = self._get_table_schema()
            self.table = self.catalog.create_table(
                self.TABLE_FULL_NAME,
                schema=schema,
                partitions=[["created_at"]],  # Partition by date
            )
            logger.info("Created new Iceberg table")
    
    @staticmethod
    def _get_table_schema() -> Schema:
        """Define Iceberg table schema."""
        return Schema(
            NestedField(1, "document_id", StringType(), required=True),
            NestedField(2, "filename", StringType(), required=True),
            NestedField(3, "content_type", StringType(), required=True),
            NestedField(4, "size_bytes", IntegerType(), required=True),
            NestedField(5, "storage_provider", StringType(), required=True),
            NestedField(6, "storage_path", StringType(), required=True),
            NestedField(7, "storage_tier", StringType(), required=False),
            NestedField(8, "restore_status", StringType(), required=False),
            NestedField(9, "restore_expiry", TimestampType(), required=False),
            NestedField(10, "archived_at", TimestampType(), required=False),
            NestedField(11, "tags_json", StringType(), required=False),
            NestedField(12, "metadata_json", StringType(), required=False),
            NestedField(13, "embedding", StringType(), required=False),
            NestedField(14, "embedding_text", StringType(), required=False),
            NestedField(15, "created_at", TimestampType(), required=True),
            NestedField(16, "updated_at", TimestampType(), required=True),
        )
    
    def insert_metadata(self, record: DocumentMetadataRecord) -> bool:
        """
        Insert document metadata into Iceberg table.
        
        Args:
            record: Document metadata record
            
        Returns:
            True if successful
        """
        try:
            record_dict = asdict(record)
            df = pa.Table.from_pydict({
                k: [v] for k, v in record_dict.items()
            })
            self.table.append(df)
            logger.info(f"Inserted metadata for document {record.document_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to insert metadata: {e}")
            raise
    
    def update_metadata(self, document_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update document metadata using Iceberg's time travel capabilities.
        
        Args:
            document_id: Document identifier
            updates: Dictionary of updates
            
        Returns:
            True if successful
        """
        try:
            updates["updated_at"] = int(datetime.utcnow().timestamp() * 1000)
            self.table.update().set(updates).where(
                f"document_id = '{document_id}'"
            ).commit()
            logger.info(f"Updated metadata for document {document_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update metadata: {e}")
            raise
    
    def get_metadata(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve document metadata.
        
        Args:
            document_id: Document identifier
            
        Returns:
            Metadata dictionary or None
        """
        try:
            records = self.table.scan().filter(f"document_id = '{document_id}'").to_arrow()
            if len(records) == 0:
                return None
            
            return records[0].to_pydict()
        except Exception as e:
            logger.error(f"Failed to retrieve metadata: {e}")
            raise
    
    def list_metadata(
        self,
        provider: Optional[str] = None,
        storage_tier: Optional[str] = None,
        start_date: Optional[int] = None,
        end_date: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        List document metadata with optional filters.
        
        Args:
            provider: Storage provider filter
            storage_tier: Storage tier filter
            start_date: Start date (Unix timestamp)
            end_date: End date (Unix timestamp)
            
        Returns:
            List of metadata records
        """
        try:
            scan = self.table.scan()
            
            # Apply filters
            filters = []
            if provider:
                filters.append(f"storage_provider = '{provider}'")
            if storage_tier:
                filters.append(f"storage_tier = '{storage_tier}'")
            if start_date:
                filters.append(f"created_at >= {start_date}")
            if end_date:
                filters.append(f"created_at <= {end_date}")
            
            if filters:
                where_clause = " AND ".join(filters)
                scan = scan.filter(where_clause)
            
            records = scan.to_arrow()
            return [dict(zip(records.column_names, values)) 
                    for values in zip(*records.to_pydict().values())]
        except Exception as e:
            logger.error(f"Failed to list metadata: {e}")
            raise
    
    def delete_metadata(self, document_id: str) -> bool:
        """
        Delete document metadata.
        
        Args:
            document_id: Document identifier
            
        Returns:
            True if successful
        """
        try:
            self.table.delete().where(f"document_id = '{document_id}'").commit()
            logger.info(f"Deleted metadata for document {document_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete metadata: {e}")
            raise
    
    def get_time_travel_snapshot(
        self,
        document_id: str,
        timestamp: int,
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve document metadata from specific point in time (Time Travel).
        
        Args:
            document_id: Document identifier
            timestamp: Unix timestamp
            
        Returns:
            Metadata at that point in time or None
        """
        try:
            scan = self.table.scan(snapshot_id=timestamp)
            records = scan.filter(f"document_id = '{document_id}'").to_arrow()
            
            if len(records) == 0:
                return None
            
            return records[0].to_pydict()
        except Exception as e:
            logger.error(f"Failed to retrieve time travel snapshot: {e}")
            raise
    
    def get_statistics(
        self,
        start_date: Optional[int] = None,
        end_date: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Get statistics about stored documents.
        
        Args:
            start_date: Start date (Unix timestamp)
            end_date: End date (Unix timestamp)
            
        Returns:
            Statistics dictionary
        """
        try:
            scan = self.table.scan()
            
            if start_date or end_date:
                filters = []
                if start_date:
                    filters.append(f"created_at >= {start_date}")
                if end_date:
                    filters.append(f"created_at <= {end_date}")
                
                if filters:
                    scan = scan.filter(" AND ".join(filters))
            
            records = scan.to_arrow()
            
            # Calculate statistics
            total_size = sum(row["size_bytes"].as_py() if row["size_bytes"].as_py() else 0 
                             for row in records)
            
            stats = {
                "total_documents": len(records),
                "total_size_bytes": total_size,
                "by_provider": {},
                "by_tier": {},
                "by_restore_status": {},
            }
            
            # Group by provider
            for record in records:
                provider = record["storage_provider"].as_py()
                stats["by_provider"][provider] = stats["by_provider"].get(provider, 0) + 1
                
                tier = record["storage_tier"].as_py()
                stats["by_tier"][tier] = stats["by_tier"].get(tier, 0) + 1
                
                status = record["restore_status"].as_py()
                stats["by_restore_status"][status] = stats["by_restore_status"].get(status, 0) + 1
            
            return stats
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            raise


# Global instance
_iceberg_db: Optional[IcebergDatabase] = None


def get_iceberg_db() -> IcebergDatabase:
    """Get or create Iceberg database instance."""
    global _iceberg_db
    if _iceberg_db is None:
        _iceberg_db = IcebergDatabase()
    return _iceberg_db
