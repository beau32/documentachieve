"""Google Cloud Storage provider implementation."""

import logging
from typing import Dict, Any

from google.cloud import storage
from google.cloud.exceptions import NotFound, GoogleCloudError

from app.config import settings
from app.storage.base import BaseStorageProvider, StorageResult, RetrieveResult, ArchiveResult, RestoreResult

logger = logging.getLogger(__name__)

# Mapping of storage tiers to GCP storage classes
STORAGE_TIER_MAP = {
    "standard": "STANDARD",
    "infrequent": "NEARLINE",
    "archive": "COLDLINE",
    "deep_archive": "ARCHIVE",
}

# Reverse mapping for display
STORAGE_CLASS_TO_TIER = {v: k for k, v in STORAGE_TIER_MAP.items()}


class GCPStorageProvider(BaseStorageProvider):
    """Google Cloud Storage provider for document archiving."""
    
    def __init__(self):
        """Initialize the GCP Storage client."""
        self._client = None
        self._bucket_name = settings.gcp_bucket_name
    
    @property
    def provider_name(self) -> str:
        return "gcp_storage"
    
    @property
    def client(self) -> storage.Client:
        """Lazy initialization of GCP Storage client."""
        if self._client is None:
            if settings.gcp_credentials_path:
                self._client = storage.Client.from_service_account_json(
                    settings.gcp_credentials_path,
                    project=settings.gcp_project_id
                )
            else:
                # Use default credentials (e.g., from environment)
                self._client = storage.Client(project=settings.gcp_project_id)
        return self._client
    
    @property
    def bucket(self):
        """Get the storage bucket."""
        return self.client.bucket(self._bucket_name)
    
    async def upload(
        self,
        document_id: str,
        data: bytes,
        filename: str,
        content_type: str,
        tags: Dict[str, str],
        metadata: Dict[str, Any]
    ) -> StorageResult:
        """Upload a document to Google Cloud Storage."""
        storage_path = self._generate_storage_path(document_id, filename)
        
        try:
            # Get blob
            blob = self.bucket.blob(storage_path)
            
            # Prepare metadata (GCP metadata must be string values)
            gcp_metadata = {k: str(v) for k, v in metadata.items()}
            gcp_metadata['original_filename'] = filename
            gcp_metadata['document_id'] = document_id
            
            # Add tags to metadata (GCP doesn't have native tagging like AWS/Azure)
            for tag_key, tag_value in tags.items():
                gcp_metadata[f'tag_{tag_key}'] = tag_value
            
            blob.metadata = gcp_metadata
            
            # Upload blob
            blob.upload_from_string(
                data,
                content_type=content_type
            )
            
            logger.info(f"Successfully uploaded document {document_id} to GCP Storage: {storage_path}")
            
            return StorageResult(
                success=True,
                storage_path=storage_path,
                message="Document uploaded successfully to Google Cloud Storage",
                metadata={"bucket": self._bucket_name, "blob": storage_path}
            )
            
        except GoogleCloudError as e:
            logger.error(f"Failed to upload to GCP Storage: {str(e)}")
            return StorageResult(
                success=False,
                storage_path="",
                message=f"Failed to upload to GCP Storage: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error uploading to GCP Storage: {str(e)}")
            return StorageResult(
                success=False,
                storage_path="",
                message=f"Unexpected error: {str(e)}"
            )
    
    async def download(self, storage_path: str) -> RetrieveResult:
        """Download a document from Google Cloud Storage."""
        try:
            blob = self.bucket.blob(storage_path)
            
            # Check if blob exists
            if not blob.exists():
                return RetrieveResult(
                    success=False,
                    data=b'',
                    message="Document not found in Google Cloud Storage"
                )
            
            # Download blob
            data = blob.download_as_bytes()
            
            # Get metadata
            blob.reload()
            metadata = dict(blob.metadata) if blob.metadata else {}
            
            logger.info(f"Successfully downloaded document from GCP Storage: {storage_path}")
            
            return RetrieveResult(
                success=True,
                data=data,
                message="Document retrieved successfully from Google Cloud Storage",
                metadata=metadata
            )
            
        except NotFound:
            return RetrieveResult(
                success=False,
                data=b'',
                message="Document not found in Google Cloud Storage"
            )
        except GoogleCloudError as e:
            logger.error(f"Failed to download from GCP Storage: {str(e)}")
            return RetrieveResult(
                success=False,
                data=b'',
                message=f"Failed to download from GCP Storage: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error downloading from GCP Storage: {str(e)}")
            return RetrieveResult(
                success=False,
                data=b'',
                message=f"Unexpected error: {str(e)}"
            )
    
    async def delete(self, storage_path: str) -> bool:
        """Delete a document from Google Cloud Storage."""
        try:
            blob = self.bucket.blob(storage_path)
            blob.delete()
            logger.info(f"Successfully deleted document from GCP Storage: {storage_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete from GCP Storage: {str(e)}")
            return False
    
    async def exists(self, storage_path: str) -> bool:
        """Check if a document exists in Google Cloud Storage."""
        try:
            blob = self.bucket.blob(storage_path)
            return blob.exists()
        except Exception:
            return False
    
    async def move_to_archive(
        self,
        storage_path: str,
        storage_tier: str
    ) -> ArchiveResult:
        """Move a document to archive storage class."""
        try:
            blob = self.bucket.blob(storage_path)
            
            # Get current storage class
            blob.reload()
            current_class = blob.storage_class or 'STANDARD'
            current_tier = STORAGE_CLASS_TO_TIER.get(current_class, 'standard')
            
            # Get target storage class
            target_class = STORAGE_TIER_MAP.get(storage_tier, 'ARCHIVE')
            
            if current_class == target_class:
                return ArchiveResult(
                    success=True,
                    message=f"Document is already in {storage_tier} storage",
                    previous_tier=current_tier,
                    new_tier=storage_tier
                )
            
            # Update storage class by rewriting the blob
            blob.update_storage_class(target_class)
            
            logger.info(f"Successfully moved document to {storage_tier}: {storage_path}")
            
            return ArchiveResult(
                success=True,
                message=f"Document moved to {storage_tier} successfully",
                previous_tier=current_tier,
                new_tier=storage_tier,
                metadata={"storage_class": target_class}
            )
            
        except NotFound:
            return ArchiveResult(
                success=False,
                message="Document not found"
            )
        except GoogleCloudError as e:
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
        """Restore a document from archive by changing storage class.
        
        Note: GCP doesn't have a restore process like AWS Glacier.
        Archive class objects are immediately accessible but with higher
        retrieval costs and minimum storage duration requirements.
        To 'restore', we change the storage class to STANDARD.
        """
        try:
            blob = self.bucket.blob(storage_path)
            blob.reload()
            
            current_class = blob.storage_class or 'STANDARD'
            
            # GCP Archive is immediately accessible, but we can move to standard
            if current_class == 'STANDARD':
                return RestoreResult(
                    success=True,
                    message="Document is already in standard storage",
                    restore_status="not_archived",
                    is_retrievable=True
                )
            
            # Unlike AWS Glacier, GCP Archive objects are immediately accessible
            # But we can offer to move them back to standard for lower access costs
            if current_class in ['ARCHIVE', 'COLDLINE', 'NEARLINE']:
                # Move to standard storage class
                blob.update_storage_class('STANDARD')
                
                return RestoreResult(
                    success=True,
                    message=f"Document moved from {current_class} to STANDARD storage class",
                    restore_status="restored",
                    is_retrievable=True
                )
            
            return RestoreResult(
                success=True,
                message="Document is accessible",
                restore_status="not_archived",
                is_retrievable=True
            )
            
        except NotFound:
            return RestoreResult(
                success=False,
                message="Document not found"
            )
        except GoogleCloudError as e:
            logger.error(f"Failed to restore: {str(e)}")
            return RestoreResult(
                success=False,
                message=f"Failed to restore: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error restoring: {str(e)}")
            return RestoreResult(
                success=False,
                message=f"Unexpected error: {str(e)}"
            )
    
    async def get_archive_status(self, storage_path: str) -> RestoreResult:
        """Get the archive status of a document.
        
        Note: GCP Archive class objects are always immediately accessible,
        unlike AWS Glacier. The status reflects the storage class.
        """
        try:
            blob = self.bucket.blob(storage_path)
            
            if not blob.exists():
                return RestoreResult(
                    success=False,
                    message="Document not found"
                )
            
            blob.reload()
            current_class = blob.storage_class or 'STANDARD'
            storage_tier = STORAGE_CLASS_TO_TIER.get(current_class, 'standard')
            
            # GCP objects are always immediately accessible regardless of storage class
            is_archived = current_class in ['ARCHIVE', 'COLDLINE']
            
            return RestoreResult(
                success=True,
                message=f"Document is in {current_class} storage class (immediately accessible)",
                restore_status="archived" if is_archived else "not_archived",
                is_retrievable=True  # GCP archive objects are always retrievable
            )
            
        except NotFound:
            return RestoreResult(
                success=False,
                message="Document not found"
            )
        except Exception as e:
            return RestoreResult(
                success=False,
                message=f"Unexpected error: {str(e)}"
            )
