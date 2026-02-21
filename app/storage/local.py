"""Local filesystem storage provider for development and testing."""

import logging
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional

from app.config import settings, StorageTier, RestoreStatus
from app.storage.base import BaseStorageProvider, StorageResult, RetrieveResult, ArchiveResult, RestoreResult

logger = logging.getLogger(__name__)


class LocalStorageProvider(BaseStorageProvider):
    """Local filesystem storage provider for development."""
    
    def __init__(self):
        """Initialize local storage provider."""
        self.base_path = Path(settings.local_storage_path or "./documents")
        self.archive_path = Path(settings.local_archive_path or "./documents_archive")
        self.deep_archive_path = Path(settings.local_deep_archive_path or "./documents_deep_archive")
        
        # Create directories if they don't exist
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.archive_path.mkdir(parents=True, exist_ok=True)
        self.deep_archive_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Local storage initialized at {self.base_path}")
    
    @property
    def provider_name(self) -> str:
        return "local"
    
    def _get_storage_path(self, document_id: str, tier: str = StorageTier.STANDARD.value) -> Path:
        """Get the storage path for a document based on its tier."""
        if tier == StorageTier.STANDARD.value:
            base = self.base_path
        elif tier in [StorageTier.INFREQUENT.value, StorageTier.ARCHIVE.value]:
            base = self.archive_path
        elif tier == StorageTier.DEEP_ARCHIVE.value:
            base = self.deep_archive_path
        else:
            base = self.base_path
        
        # Create subdirectories by date for organization
        today = datetime.utcnow().strftime("%Y/%m/%d")
        return base / today / document_id
    
    def _get_metadata_path(self, storage_path: Path) -> Path:
        """Get the metadata file path for a document."""
        return storage_path.parent / f"{storage_path.name}.meta.json"
    
    async def upload(
        self,
        document_id: str,
        data: bytes,
        filename: str,
        content_type: str,
        tags: Dict[str, str],
        metadata: Dict[str, Any]
    ) -> StorageResult:
        """
        Upload a document to local storage.
        
        Args:
            document_id: Unique identifier for the document
            data: Binary content of the document
            filename: Original filename
            content_type: MIME type
            tags: Key-value tags
            metadata: Additional metadata
            
        Returns:
            StorageResult with storage path
        """
        try:
            # Get storage path
            storage_path = self._get_storage_path(document_id, StorageTier.STANDARD.value)
            storage_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write document
            with open(storage_path, 'wb') as f:
                f.write(data)
            
            # Create metadata file
            meta_file = self._get_metadata_path(storage_path)
            meta_data = {
                "document_id": document_id,
                "filename": filename,
                "content_type": content_type,
                "size_bytes": len(data),
                "tags": tags,
                "metadata": metadata,
                "uploaded_at": datetime.utcnow().isoformat(),
                "storage_tier": StorageTier.STANDARD.value,
                "content_hash": hashlib.sha256(data).hexdigest(),
            }
            
            with open(meta_file, 'w') as f:
                json.dump(meta_data, f, indent=2)
            
            logger.info(f"Uploaded {filename} ({len(data)} bytes) to {storage_path}")
            
            return StorageResult(
                success=True,
                storage_path=str(storage_path),
                message=f"Document uploaded successfully to {storage_path}",
                metadata=meta_data
            )
        
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            return StorageResult(
                success=False,
                storage_path="",
                message=f"Upload failed: {str(e)}"
            )
    
    async def download(self, storage_path: str) -> RetrieveResult:
        """
        Download a document from local storage.
        
        Args:
            storage_path: Path to the document
            
        Returns:
            RetrieveResult with document data
        """
        try:
            path = Path(storage_path)
            
            if not path.exists():
                return RetrieveResult(
                    success=False,
                    data=b"",
                    message=f"Document not found at {storage_path}"
                )
            
            with open(path, 'rb') as f:
                data = f.read()
            
            logger.info(f"Downloaded {len(data)} bytes from {storage_path}")
            
            return RetrieveResult(
                success=True,
                data=data,
                message="Document retrieved successfully"
            )
        
        except Exception as e:
            logger.error(f"Download failed: {e}")
            return RetrieveResult(
                success=False,
                data=b"",
                message=f"Download failed: {str(e)}"
            )
    
    async def delete(self, storage_path: str) -> bool:
        """
        Delete a document from local storage.
        
        Args:
            storage_path: Path to the document
            
        Returns:
            True if successful
        """
        try:
            path = Path(storage_path)
            meta_path = self._get_metadata_path(path)
            
            if path.exists():
                path.unlink()
            if meta_path.exists():
                meta_path.unlink()
            
            logger.info(f"Deleted document at {storage_path}")
            return True
        
        except Exception as e:
            logger.error(f"Delete failed: {e}")
            return False
    
    async def archive_to_tier(
        self,
        storage_path: str,
        target_tier: str
    ) -> ArchiveResult:
        """
        Move a document to a colder storage tier (simulate archiving).
        
        Args:
            storage_path: Current storage path
            target_tier: Target storage tier
            
        Returns:
            ArchiveResult with operation status
        """
        try:
            current_path = Path(storage_path)
            
            if not current_path.exists():
                return ArchiveResult(
                    success=False,
                    message=f"Document not found at {storage_path}"
                )
            
            # Determine target directory
            if target_tier == StorageTier.INFREQUENT.value or target_tier == StorageTier.ARCHIVE.value:
                target_base = self.archive_path
            elif target_tier == StorageTier.DEEP_ARCHIVE.value:
                target_base = self.deep_archive_path
            else:
                target_base = self.base_path
            
            # Create target path maintaining date structure
            today = datetime.utcnow().strftime("%Y/%m/%d")
            target_path = target_base / today / current_path.name
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Move document
            with open(current_path, 'rb') as src:
                with open(target_path, 'wb') as dst:
                    dst.write(src.read())
            
            # Move metadata
            current_meta = self._get_metadata_path(current_path)
            target_meta = self._get_metadata_path(target_path)
            
            if current_meta.exists():
                with open(current_meta, 'r') as f:
                    meta_data = json.load(f)
                meta_data["storage_tier"] = target_tier
                meta_data["archived_at"] = datetime.utcnow().isoformat()
                with open(target_meta, 'w') as f:
                    json.dump(meta_data, f, indent=2)
            
            # Remove original
            current_path.unlink()
            if current_meta.exists():
                current_meta.unlink()
            
            logger.info(f"Archived {current_path} to tier {target_tier} at {target_path}")
            
            return ArchiveResult(
                success=True,
                message=f"Document archived to {target_tier}",
                previous_tier=StorageTier.STANDARD.value,
                new_tier=target_tier
            )
        
        except Exception as e:
            logger.error(f"Archive failed: {e}")
            return ArchiveResult(
                success=False,
                message=f"Archive failed: {str(e)}"
            )
    
    async def restore_from_archive(
        self,
        storage_path: str,
        restore_days: int = 7
    ) -> RestoreResult:
        """
        Restore a document from archive (move back to standard tier for limited time).
        
        Args:
            storage_path: Current archive path
            restore_days: Days to keep restored
            
        Returns:
            RestoreResult with restoration status
        """
        try:
            archive_path = Path(storage_path)
            
            if not archive_path.exists():
                return RestoreResult(
                    success=False,
                    message=f"Document not found at {storage_path}",
                    is_retrievable=False
                )
            
            # Create restored copy in standard storage
            today = datetime.utcnow().strftime("%Y/%m/%d")
            restore_path = self.base_path / today / f"restored_{archive_path.name}"
            restore_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(archive_path, 'rb') as src:
                with open(restore_path, 'wb') as dst:
                    dst.write(src.read())
            
            # Update metadata
            restore_meta = self._get_metadata_path(restore_path)
            archive_meta = self._get_metadata_path(archive_path)
            
            if archive_meta.exists():
                with open(archive_meta, 'r') as f:
                    meta_data = json.load(f)
            else:
                meta_data = {}
            
            expiry = datetime.utcnow() + timedelta(days=restore_days)
            meta_data.update({
                "restore_status": RestoreStatus.RESTORED.value,
                "restore_expiry": expiry.isoformat(),
                "restored_at": datetime.utcnow().isoformat(),
            })
            
            with open(restore_meta, 'w') as f:
                json.dump(meta_data, f, indent=2)
            
            logger.info(f"Restored {archive_path} to {restore_path} for {restore_days} days")
            
            return RestoreResult(
                success=True,
                message=f"Document restored for {restore_days} days",
                restore_status=RestoreStatus.RESTORED.value,
                restore_expiry=expiry.isoformat(),
                is_retrievable=True
            )
        
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return RestoreResult(
                success=False,
                message=f"Restore failed: {str(e)}",
                is_retrievable=False
            )
    
    async def get_object_metadata(self, storage_path: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a stored object.
        
        Args:
            storage_path: Path to the document
            
        Returns:
            Metadata dictionary or None
        """
        try:
            meta_path = self._get_metadata_path(Path(storage_path))
            
            if meta_path.exists():
                with open(meta_path, 'r') as f:
                    return json.load(f)
            
            return None
        
        except Exception as e:
            logger.error(f"Failed to get metadata: {e}")
            return None
