"""Abstract base class for cloud storage providers."""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class StorageResult:
    """Result of a storage operation."""
    success: bool
    storage_path: str
    message: str
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class RetrieveResult:
    """Result of a retrieve operation."""
    success: bool
    data: bytes
    message: str
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ArchiveResult:
    """Result of an archive tier change operation."""
    success: bool
    message: str
    previous_tier: str = ""
    new_tier: str = ""
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class RestoreResult:
    """Result of a restore operation from archive."""
    success: bool
    message: str
    restore_status: str = ""
    estimated_completion: Optional[str] = None
    restore_expiry: Optional[str] = None
    is_retrievable: bool = False


class BaseStorageProvider(ABC):
    """Abstract base class for cloud storage providers."""
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name."""
        pass
    
    @abstractmethod
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
        Upload a document to cloud storage.
        
        Args:
            document_id: Unique identifier for the document
            data: Binary content of the document
            filename: Original filename
            content_type: MIME type of the document
            tags: Key-value pairs for tagging
            metadata: Additional metadata
            
        Returns:
            StorageResult with operation status and storage path
        """
        pass
    
    @abstractmethod
    async def download(self, storage_path: str) -> RetrieveResult:
        """
        Download a document from cloud storage.
        
        Args:
            storage_path: Path to the document in storage
            
        Returns:
            RetrieveResult with document data
        """
        pass
    
    @abstractmethod
    async def delete(self, storage_path: str) -> bool:
        """
        Delete a document from cloud storage.
        
        Args:
            storage_path: Path to the document in storage
            
        Returns:
            True if deletion was successful
        """
        pass
    
    @abstractmethod
    async def exists(self, storage_path: str) -> bool:
        """
        Check if a document exists in storage.
        
        Args:
            storage_path: Path to the document in storage
            
        Returns:
            True if document exists
        """
        pass
    
    @abstractmethod
    async def move_to_archive(
        self,
        storage_path: str,
        storage_tier: str
    ) -> ArchiveResult:
        """
        Move a document to archive/deep archive storage tier.
        
        Args:
            storage_path: Path to the document in storage
            storage_tier: Target storage tier (archive, deep_archive)
            
        Returns:
            ArchiveResult with operation status
        """
        pass
    
    @abstractmethod
    async def restore_from_archive(
        self,
        storage_path: str,
        restore_days: int = 7,
        restore_tier: str = "Standard"
    ) -> RestoreResult:
        """
        Initiate restore of a document from archive storage.
        
        Args:
            storage_path: Path to the document in storage
            restore_days: Number of days to keep restored copy
            restore_tier: Restore speed tier (Expedited, Standard, Bulk)
            
        Returns:
            RestoreResult with restore status
        """
        pass
    
    @abstractmethod
    async def get_archive_status(self, storage_path: str) -> RestoreResult:
        """
        Get the archive/restore status of a document.
        
        Args:
            storage_path: Path to the document in storage
            
        Returns:
            RestoreResult with current status
        """
        pass

    def _generate_storage_path(self, document_id: str, filename: str) -> str:
        """
        Generate a storage path for a document.
        
        Args:
            document_id: Unique document identifier
            filename: Original filename
            
        Returns:
            Storage path string
        """
        from datetime import datetime
        date_prefix = datetime.utcnow().strftime("%Y/%m/%d")
        return f"archives/{date_prefix}/{document_id}/{filename}"
