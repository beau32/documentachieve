"""Local file-based Iceberg table storage for development and testing."""

import logging
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import asdict
from pathlib import Path

from app.config import settings
from app.iceberg_database import DocumentMetadataRecord

logger = logging.getLogger(__name__)


class LocalIcebergDatabase:
    """
    Local file-based Iceberg table implementation for development/testing.
    Stores metadata as JSONL (JSON Lines) files for simplicity.
    """
    
    def __init__(self):
        """Initialize local Iceberg database."""
        self.warehouse_path = Path(settings.local_iceberg_warehouse or "./iceberg_warehouse")
        self.namespace = "document_archive"
        self.table_name = "document_metadata"
        
        # Create warehouse structure
        self.table_path = self.warehouse_path / self.namespace / self.table_name
        self.metadata_path = self.table_path / "metadata"
        self.data_path = self.table_path / "data"
        
        self.metadata_path.mkdir(parents=True, exist_ok=True)
        self.data_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Local Iceberg database initialized at {self.warehouse_path}")
    
    def _get_data_file(self) -> Path:
        """Get the current data file."""
        return self.data_path / "metadata.jsonl"
    
    def _get_metadata_file(self) -> Path:
        """Get the metadata manifest file."""
        return self.metadata_path / "manifest.json"
    
    def _record_to_dict(self, record: DocumentMetadataRecord) -> Dict[str, Any]:
        """Convert record to dictionary."""
        d = asdict(record)
        d["_timestamp"] = datetime.utcnow().isoformat()
        return d
    
    def _dict_to_record(self, d: Dict[str, Any]) -> DocumentMetadataRecord:
        """Convert dictionary to record."""
        d.pop("_timestamp", None)
        return DocumentMetadataRecord(**d)
    
    def insert_metadata(self, record: DocumentMetadataRecord) -> bool:
        """
        Insert document metadata.
        
        Args:
            record: Document metadata record
            
        Returns:
            True if successful
        """
        try:
            data_file = self._get_data_file()
            
            with open(data_file, 'a') as f:
                json.dump(self._record_to_dict(record), f)
                f.write('\n')
            
            logger.info(f"Inserted metadata for document {record.document_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to insert metadata: {e}")
            raise
    
    def update_metadata(self, document_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update document metadata.
        
        Args:
            document_id: Document identifier
            updates: Dictionary of updates
            
        Returns:
            True if successful
        """
        try:
            data_file = self._get_data_file()
            records = []
            found = False
            
            # Read all records
            if data_file.exists():
                with open(data_file, 'r') as f:
                    for line in f:
                        if line.strip():
                            records.append(json.loads(line))
            
            # Update record
            for record in records:
                if record.get("document_id") == document_id:
                    record.update(updates)
                    record["_timestamp"] = datetime.utcnow().isoformat()
                    found = True
                    break
            
            if not found:
                return False
            
            # Write back
            with open(data_file, 'w') as f:
                for record in records:
                    json.dump(record, f)
                    f.write('\n')
            
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
            data_file = self._get_data_file()
            
            if not data_file.exists():
                return None
            
            with open(data_file, 'r') as f:
                for line in f:
                    if line.strip():
                        record = json.loads(line)
                        if record.get("document_id") == document_id:
                            return record
            
            return None
        
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
            data_file = self._get_data_file()
            results = []
            
            if not data_file.exists():
                return results
            
            with open(data_file, 'r') as f:
                for line in f:
                    if line.strip():
                        record = json.loads(line)
                        
                        # Apply filters
                        if provider and record.get("storage_provider") != provider:
                            continue
                        if storage_tier and record.get("storage_tier") != storage_tier:
                            continue
                        if start_date and record.get("created_at", 0) < start_date:
                            continue
                        if end_date and record.get("created_at", 0) > end_date:
                            continue
                        
                        results.append(record)
            
            return results
        
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
            data_file = self._get_data_file()
            records = []
            found = False
            
            # Read all records
            if data_file.exists():
                with open(data_file, 'r') as f:
                    for line in f:
                        if line.strip():
                            record = json.loads(line)
                            if record.get("document_id") != document_id:
                                records.append(record)
                            else:
                                found = True
            
            if not found:
                return False
            
            # Write back
            with open(data_file, 'w') as f:
                for record in records:
                    json.dump(record, f)
                    f.write('\n')
            
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
        Retrieve document metadata from specific point in time.
        Note: Local implementation keeps all historical records.
        
        Args:
            document_id: Document identifier
            timestamp: Unix timestamp
            
        Returns:
            Metadata at that point in time or None
        """
        try:
            data_file = self._get_data_file()
            
            if not data_file.exists():
                return None
            
            # Get most recent version before timestamp
            latest = None
            with open(data_file, 'r') as f:
                for line in f:
                    if line.strip():
                        record = json.loads(line)
                        if record.get("document_id") == document_id:
                            record_ts = record.get("_timestamp")
                            if record_ts:
                                # Simple comparison (would need proper parsing in production)
                                if record_ts <= datetime.fromtimestamp(timestamp).isoformat():
                                    latest = record
            
            return latest
        
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
            data_file = self._get_data_file()
            
            stats = {
                "total_documents": 0,
                "total_size_bytes": 0,
                "by_provider": {},
                "by_tier": {},
                "by_restore_status": {},
            }
            
            if not data_file.exists():
                return stats
            
            with open(data_file, 'r') as f:
                for line in f:
                    if line.strip():
                        record = json.loads(line)
                        
                        # Apply date filters
                        if start_date and record.get("created_at", 0) < start_date:
                            continue
                        if end_date and record.get("created_at", 0) > end_date:
                            continue
                        
                        stats["total_documents"] += 1
                        stats["total_size_bytes"] += record.get("size_bytes", 0)
                        
                        provider = record.get("storage_provider")
                        if provider:
                            stats["by_provider"][provider] = stats["by_provider"].get(provider, 0) + 1
                        
                        tier = record.get("storage_tier")
                        if tier:
                            stats["by_tier"][tier] = stats["by_tier"].get(tier, 0) + 1
                        
                        status = record.get("restore_status")
                        if status:
                            stats["by_restore_status"][status] = stats["by_restore_status"].get(status, 0) + 1
            
            return stats
        
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            raise


# Global instance
_local_iceberg_db: Optional[LocalIcebergDatabase] = None


def get_local_iceberg_db() -> LocalIcebergDatabase:
    """Get or create local Iceberg database instance."""
    global _local_iceberg_db
    if _local_iceberg_db is None:
        _local_iceberg_db = LocalIcebergDatabase()
    return _local_iceberg_db
