"""Azure Blob Storage provider implementation."""

import logging
from typing import Dict, Any

from azure.storage.blob import BlobServiceClient, ContentSettings, StandardBlobTier
from azure.core.exceptions import ResourceNotFoundError, AzureError

from app.config import settings
from app.storage.base import BaseStorageProvider, StorageResult, RetrieveResult, ArchiveResult, RestoreResult

logger = logging.getLogger(__name__)

# Mapping of storage tiers to Azure Blob tiers
STORAGE_TIER_MAP = {
    "standard": StandardBlobTier.HOT,
    "infrequent": StandardBlobTier.COOL,
    "archive": StandardBlobTier.COLD,
    "deep_archive": StandardBlobTier.ARCHIVE,
}

# Reverse mapping for display
BLOB_TIER_TO_STORAGE = {
    "Hot": "standard",
    "Cool": "infrequent",
    "Cold": "archive",
    "Archive": "deep_archive",
}


class AzureBlobProvider(BaseStorageProvider):
    """Azure Blob Storage provider for document archiving."""
    
    def __init__(self):
        """Initialize the Azure Blob client."""
        self._client = None
        self._container_name = settings.azure_container_name
    
    @property
    def provider_name(self) -> str:
        return "azure_blob"
    
    @property
    def client(self) -> BlobServiceClient:
        """Lazy initialization of Azure Blob client."""
        if self._client is None:
            if not settings.azure_connection_string:
                raise ValueError("Azure connection string not configured")
            self._client = BlobServiceClient.from_connection_string(
                settings.azure_connection_string
            )
        return self._client
    
    @property
    def container_client(self):
        """Get the container client."""
        return self.client.get_container_client(self._container_name)
    
    async def upload(
        self,
        document_id: str,
        data: bytes,
        filename: str,
        content_type: str,
        tags: Dict[str, str],
        metadata: Dict[str, Any]
    ) -> StorageResult:
        """Upload a document to Azure Blob Storage."""
        storage_path = self._generate_storage_path(document_id, filename)
        
        try:
            # Get blob client
            blob_client = self.container_client.get_blob_client(storage_path)
            
            # Prepare metadata (Azure metadata must be string values)
            azure_metadata = {k: str(v) for k, v in metadata.items()}
            azure_metadata['original_filename'] = filename
            azure_metadata['document_id'] = document_id
            
            # Set content settings
            content_settings = ContentSettings(content_type=content_type)
            
            # Upload blob
            blob_client.upload_blob(
                data,
                overwrite=True,
                metadata=azure_metadata,
                tags=tags,
                content_settings=content_settings
            )
            
            logger.info(f"Successfully uploaded document {document_id} to Azure Blob: {storage_path}")
            
            return StorageResult(
                success=True,
                storage_path=storage_path,
                message="Document uploaded successfully to Azure Blob Storage",
                metadata={"container": self._container_name, "blob": storage_path}
            )
            
        except ValueError as e:
            logger.error(f"Configuration error: {str(e)}")
            return StorageResult(
                success=False,
                storage_path="",
                message=f"Configuration error: {str(e)}"
            )
        except AzureError as e:
            logger.error(f"Failed to upload to Azure Blob: {str(e)}")
            return StorageResult(
                success=False,
                storage_path="",
                message=f"Failed to upload to Azure Blob: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error uploading to Azure Blob: {str(e)}")
            return StorageResult(
                success=False,
                storage_path="",
                message=f"Unexpected error: {str(e)}"
            )
    
    async def download(self, storage_path: str) -> RetrieveResult:
        """Download a document from Azure Blob Storage."""
        try:
            blob_client = self.container_client.get_blob_client(storage_path)
            
            # Download blob
            download_stream = blob_client.download_blob()
            data = download_stream.readall()
            
            # Get metadata
            properties = blob_client.get_blob_properties()
            metadata = dict(properties.metadata) if properties.metadata else {}
            
            logger.info(f"Successfully downloaded document from Azure Blob: {storage_path}")
            
            return RetrieveResult(
                success=True,
                data=data,
                message="Document retrieved successfully from Azure Blob Storage",
                metadata=metadata
            )
            
        except ResourceNotFoundError:
            return RetrieveResult(
                success=False,
                data=b'',
                message="Document not found in Azure Blob Storage"
            )
        except AzureError as e:
            logger.error(f"Failed to download from Azure Blob: {str(e)}")
            return RetrieveResult(
                success=False,
                data=b'',
                message=f"Failed to download from Azure Blob: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error downloading from Azure Blob: {str(e)}")
            return RetrieveResult(
                success=False,
                data=b'',
                message=f"Unexpected error: {str(e)}"
            )
    
    async def delete(self, storage_path: str) -> bool:
        """Delete a document from Azure Blob Storage."""
        try:
            blob_client = self.container_client.get_blob_client(storage_path)
            blob_client.delete_blob()
            logger.info(f"Successfully deleted document from Azure Blob: {storage_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete from Azure Blob: {str(e)}")
            return False
    
    async def exists(self, storage_path: str) -> bool:
        """Check if a document exists in Azure Blob Storage."""
        try:
            blob_client = self.container_client.get_blob_client(storage_path)
            blob_client.get_blob_properties()
            return True
        except ResourceNotFoundError:
            return False
        except Exception:
            return False
    
    async def move_to_archive(
        self,
        storage_path: str,
        storage_tier: str
    ) -> ArchiveResult:
        """Move a document to archive storage tier."""
        try:
            blob_client = self.container_client.get_blob_client(storage_path)
            
            # Get current tier
            properties = blob_client.get_blob_properties()
            current_tier = properties.blob_tier
            current_tier_name = BLOB_TIER_TO_STORAGE.get(current_tier, 'standard')
            
            # Get target tier
            target_tier = STORAGE_TIER_MAP.get(storage_tier, StandardBlobTier.ARCHIVE)
            
            if current_tier == target_tier.value if hasattr(target_tier, 'value') else target_tier:
                return ArchiveResult(
                    success=True,
                    message=f"Document is already in {storage_tier} storage",
                    previous_tier=current_tier_name,
                    new_tier=storage_tier
                )
            
            # Set the new tier
            blob_client.set_standard_blob_tier(target_tier)
            
            logger.info(f"Successfully moved document to {storage_tier}: {storage_path}")
            
            return ArchiveResult(
                success=True,
                message=f"Document moved to {storage_tier} successfully",
                previous_tier=current_tier_name,
                new_tier=storage_tier,
                metadata={"blob_tier": str(target_tier)}
            )
            
        except ResourceNotFoundError:
            return ArchiveResult(
                success=False,
                message="Document not found"
            )
        except AzureError as e:
            logger.error(f"Failed to move to archive: {str(e)}")
            return ArchiveResult(
                success=False,
                message=f"Failed to move to archive: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error moving to archive: {str(e)}")
            return ArchiveResult(
                success=False,
                message=f"Unexpected error: {str(e)}"
            )
    
    async def restore_from_archive(
        self,
        storage_path: str,
        restore_days: int = 7,
        restore_tier: str = "Standard"
    ) -> RestoreResult:
        """Initiate restore of a document from archive tier."""
        try:
            blob_client = self.container_client.get_blob_client(storage_path)
            properties = blob_client.get_blob_properties()
            current_tier = properties.blob_tier
            
            # Check if already in accessible tier
            if current_tier in ['Hot', 'Cool', 'Cold']:
                return RestoreResult(
                    success=True,
                    message="Document is already in an accessible storage tier",
                    restore_status="not_archived",
                    is_retrievable=True
                )
            
            # Check archive status
            archive_status = properties.archive_status
            
            if archive_status == 'rehydrate-pending-to-hot' or archive_status == 'rehydrate-pending-to-cool':
                return RestoreResult(
                    success=True,
                    message="Rehydration is already in progress",
                    restore_status="in_progress",
                    estimated_completion="Up to 15 hours for standard priority",
                    is_retrievable=False
                )
            
            # Map restore tier to rehydrate priority
            priority = 'Standard'
            if restore_tier.lower() == 'expedited':
                priority = 'High'
            
            # Initiate rehydration by setting tier to Hot
            blob_client.set_standard_blob_tier(
                StandardBlobTier.HOT,
                rehydrate_priority=priority
            )
            
            logger.info(f"Initiated rehydration for document: {storage_path}")
            
            return RestoreResult(
                success=True,
                message=f"Rehydration initiated with {priority} priority",
                restore_status="in_progress",
                estimated_completion="Up to 15 hours for standard, or within hours for high priority",
                is_retrievable=False
            )
            
        except ResourceNotFoundError:
            return RestoreResult(
                success=False,
                message="Document not found"
            )
        except AzureError as e:
            logger.error(f"Failed to initiate rehydration: {str(e)}")
            return RestoreResult(
                success=False,
                message=f"Failed to initiate rehydration: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error initiating rehydration: {str(e)}")
            return RestoreResult(
                success=False,
                message=f"Unexpected error: {str(e)}"
            )
    
    async def get_archive_status(self, storage_path: str) -> RestoreResult:
        """Get the archive/restore status of a document."""
        try:
            blob_client = self.container_client.get_blob_client(storage_path)
            properties = blob_client.get_blob_properties()
            
            current_tier = properties.blob_tier
            archive_status = properties.archive_status
            
            # Hot, Cool, Cold are immediately accessible
            if current_tier in ['Hot', 'Cool', 'Cold']:
                return RestoreResult(
                    success=True,
                    message=f"Document is in {current_tier} tier and immediately accessible",
                    restore_status="not_archived" if current_tier == 'Hot' else "archived",
                    is_retrievable=True
                )
            
            # Archive tier
            if current_tier == 'Archive':
                if archive_status and 'rehydrate-pending' in archive_status:
                    return RestoreResult(
                        success=True,
                        message="Rehydration is in progress",
                        restore_status="in_progress",
                        is_retrievable=False
                    )
                else:
                    return RestoreResult(
                        success=True,
                        message="Document is in Archive tier and requires rehydration",
                        restore_status="archived",
                        is_retrievable=False
                    )
            
            return RestoreResult(
                success=True,
                message=f"Document is in {current_tier} tier",
                restore_status="archived",
                is_retrievable=current_tier not in ['Archive']
            )
            
        except ResourceNotFoundError:
            return RestoreResult(
                success=False,
                message="Document not found"
            )
        except Exception as e:
            return RestoreResult(
                success=False,
                message=f"Unexpected error: {str(e)}"
            )
