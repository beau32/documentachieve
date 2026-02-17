"""AWS S3 storage provider implementation."""

import logging
from typing import Dict, Any

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from app.config import settings
from app.storage.base import BaseStorageProvider, StorageResult, RetrieveResult, ArchiveResult, RestoreResult

logger = logging.getLogger(__name__)

# Mapping of storage tiers to S3 storage classes
STORAGE_TIER_MAP = {
    "standard": "STANDARD",
    "infrequent": "STANDARD_IA",
    "archive": "GLACIER_IR",  # Glacier Instant Retrieval
    "deep_archive": "DEEP_ARCHIVE",  # Glacier Deep Archive
}

# Reverse mapping for display
STORAGE_CLASS_TO_TIER = {v: k for k, v in STORAGE_TIER_MAP.items()}
STORAGE_CLASS_TO_TIER["GLACIER"] = "archive"


class AWSS3Provider(BaseStorageProvider):
    """AWS S3 storage provider for document archiving."""
    
    def __init__(self):
        """Initialize the S3 client."""
        self._client = None
        self._bucket = settings.aws_s3_bucket
    
    @property
    def provider_name(self) -> str:
        return "aws_s3"
    
    @property
    def client(self):
        """Lazy initialization of S3 client."""
        if self._client is None:
            self._client = boto3.client(
                's3',
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                region_name=settings.aws_region
            )
        return self._client
    
    async def upload(
        self,
        document_id: str,
        data: bytes,
        filename: str,
        content_type: str,
        tags: Dict[str, str],
        metadata: Dict[str, Any]
    ) -> StorageResult:
        """Upload a document to AWS S3."""
        storage_path = self._generate_storage_path(document_id, filename)
        
        try:
            # Prepare S3 metadata (must be string values)
            s3_metadata = {k: str(v) for k, v in metadata.items()}
            s3_metadata['original_filename'] = filename
            s3_metadata['document_id'] = document_id
            
            # Prepare tags as URL-encoded string
            tag_string = "&".join([f"{k}={v}" for k, v in tags.items()])
            
            # Upload to S3
            extra_args = {
                'ContentType': content_type,
                'Metadata': s3_metadata
            }
            
            if tag_string:
                extra_args['Tagging'] = tag_string
            
            self.client.put_object(
                Bucket=self._bucket,
                Key=storage_path,
                Body=data,
                **extra_args
            )
            
            logger.info(f"Successfully uploaded document {document_id} to S3: {storage_path}")
            
            return StorageResult(
                success=True,
                storage_path=storage_path,
                message="Document uploaded successfully to AWS S3",
                metadata={"bucket": self._bucket, "key": storage_path}
            )
            
        except NoCredentialsError:
            logger.error("AWS credentials not configured")
            return StorageResult(
                success=False,
                storage_path="",
                message="AWS credentials not configured"
            )
        except ClientError as e:
            error_msg = e.response.get('Error', {}).get('Message', str(e))
            logger.error(f"Failed to upload to S3: {error_msg}")
            return StorageResult(
                success=False,
                storage_path="",
                message=f"Failed to upload to S3: {error_msg}"
            )
        except Exception as e:
            logger.error(f"Unexpected error uploading to S3: {str(e)}")
            return StorageResult(
                success=False,
                storage_path="",
                message=f"Unexpected error: {str(e)}"
            )
    
    async def download(self, storage_path: str) -> RetrieveResult:
        """Download a document from AWS S3."""
        try:
            # First check if the object is in Glacier and needs restore
            head_response = self.client.head_object(
                Bucket=self._bucket,
                Key=storage_path
            )
            
            storage_class = head_response.get('StorageClass', 'STANDARD')
            
            # Check if object is in Glacier
            if storage_class in ['GLACIER', 'DEEP_ARCHIVE', 'GLACIER_IR']:
                restore_status = head_response.get('Restore', '')
                
                # Check if restore is in progress or not started
                if not restore_status:
                    return RetrieveResult(
                        success=False,
                        data=b'',
                        message=f"Document is in {storage_class} and must be restored before retrieval. Use the restore endpoint first."
                    )
                elif 'ongoing-request="true"' in restore_status:
                    return RetrieveResult(
                        success=False,
                        data=b'',
                        message="Document restore is in progress. Please try again later."
                    )
                # If restore is complete, we can proceed with download
            
            response = self.client.get_object(
                Bucket=self._bucket,
                Key=storage_path
            )
            
            data = response['Body'].read()
            metadata = response.get('Metadata', {})
            
            logger.info(f"Successfully downloaded document from S3: {storage_path}")
            
            return RetrieveResult(
                success=True,
                data=data,
                message="Document retrieved successfully from AWS S3",
                metadata=metadata
            )
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == '404' or error_code == 'NoSuchKey':
                return RetrieveResult(
                    success=False,
                    data=b'',
                    message="Document not found in S3"
                )
            error_msg = e.response.get('Error', {}).get('Message', str(e))
            logger.error(f"Failed to download from S3: {error_msg}")
            return RetrieveResult(
                success=False,
                data=b'',
                message=f"Failed to download from S3: {error_msg}"
            )
        except Exception as e:
            logger.error(f"Unexpected error downloading from S3: {str(e)}")
            return RetrieveResult(
                success=False,
                data=b'',
                message=f"Unexpected error: {str(e)}"
            )
    
    async def delete(self, storage_path: str) -> bool:
        """Delete a document from AWS S3."""
        try:
            self.client.delete_object(
                Bucket=self._bucket,
                Key=storage_path
            )
            logger.info(f"Successfully deleted document from S3: {storage_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete from S3: {str(e)}")
            return False
    
    async def exists(self, storage_path: str) -> bool:
        """Check if a document exists in AWS S3."""
        try:
            self.client.head_object(
                Bucket=self._bucket,
                Key=storage_path
            )
            return True
        except ClientError:
            return False
    
    async def move_to_archive(
        self,
        storage_path: str,
        storage_tier: str
    ) -> ArchiveResult:
        """Move a document to Glacier archive storage."""
        try:
            # Get current storage class
            head_response = self.client.head_object(
                Bucket=self._bucket,
                Key=storage_path
            )
            current_class = head_response.get('StorageClass', 'STANDARD')
            current_tier = STORAGE_CLASS_TO_TIER.get(current_class, 'standard')
            
            # Get target storage class
            target_class = STORAGE_TIER_MAP.get(storage_tier, 'DEEP_ARCHIVE')
            
            if current_class == target_class:
                return ArchiveResult(
                    success=True,
                    message=f"Document is already in {storage_tier} storage",
                    previous_tier=current_tier,
                    new_tier=storage_tier
                )
            
            # Copy object to itself with new storage class
            self.client.copy_object(
                Bucket=self._bucket,
                Key=storage_path,
                CopySource={'Bucket': self._bucket, 'Key': storage_path},
                StorageClass=target_class,
                MetadataDirective='COPY'
            )
            
            logger.info(f"Successfully moved document to {storage_tier}: {storage_path}")
            
            return ArchiveResult(
                success=True,
                message=f"Document moved to {storage_tier} successfully",
                previous_tier=current_tier,
                new_tier=storage_tier,
                metadata={"storage_class": target_class}
            )
            
        except ClientError as e:
            error_msg = e.response.get('Error', {}).get('Message', str(e))
            logger.error(f"Failed to move to archive: {error_msg}")
            return ArchiveResult(
                success=False,
                message=f"Failed to move to archive: {error_msg}"
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
        """Initiate restore of a document from Glacier."""
        try:
            # Check current storage class
            head_response = self.client.head_object(
                Bucket=self._bucket,
                Key=storage_path
            )
            
            storage_class = head_response.get('StorageClass', 'STANDARD')
            
            # Check if already in standard storage
            if storage_class == 'STANDARD':
                return RestoreResult(
                    success=True,
                    message="Document is already in standard storage and immediately retrievable",
                    restore_status="not_archived",
                    is_retrievable=True
                )
            
            # Check if restore is already in progress or complete
            restore_status = head_response.get('Restore', '')
            
            if restore_status:
                if 'ongoing-request="true"' in restore_status:
                    return RestoreResult(
                        success=True,
                        message="Restore is already in progress",
                        restore_status="in_progress",
                        estimated_completion=self._get_restore_estimate(restore_tier),
                        is_retrievable=False
                    )
                elif 'ongoing-request="false"' in restore_status:
                    # Parse expiry date from restore status
                    import re
                    expiry_match = re.search(r'expiry-date="([^"]+)"', restore_status)
                    expiry = expiry_match.group(1) if expiry_match else None
                    
                    return RestoreResult(
                        success=True,
                        message="Document is already restored and available",
                        restore_status="restored",
                        restore_expiry=expiry,
                        is_retrievable=True
                    )
            
            # Initiate restore
            self.client.restore_object(
                Bucket=self._bucket,
                Key=storage_path,
                RestoreRequest={
                    'Days': restore_days,
                    'GlacierJobParameters': {
                        'Tier': restore_tier
                    }
                }
            )
            
            logger.info(f"Initiated restore for document: {storage_path}")
            
            return RestoreResult(
                success=True,
                message=f"Restore initiated successfully with {restore_tier} tier",
                restore_status="in_progress",
                estimated_completion=self._get_restore_estimate(restore_tier),
                is_retrievable=False
            )
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == 'RestoreAlreadyInProgress':
                return RestoreResult(
                    success=True,
                    message="Restore is already in progress",
                    restore_status="in_progress",
                    is_retrievable=False
                )
            error_msg = e.response.get('Error', {}).get('Message', str(e))
            logger.error(f"Failed to initiate restore: {error_msg}")
            return RestoreResult(
                success=False,
                message=f"Failed to initiate restore: {error_msg}"
            )
        except Exception as e:
            logger.error(f"Unexpected error initiating restore: {str(e)}")
            return RestoreResult(
                success=False,
                message=f"Unexpected error: {str(e)}"
            )
    
    async def get_archive_status(self, storage_path: str) -> RestoreResult:
        """Get the archive/restore status of a document."""
        try:
            head_response = self.client.head_object(
                Bucket=self._bucket,
                Key=storage_path
            )
            
            storage_class = head_response.get('StorageClass', 'STANDARD')
            storage_tier = STORAGE_CLASS_TO_TIER.get(storage_class, 'standard')
            
            # Standard storage - immediately retrievable
            if storage_class == 'STANDARD':
                return RestoreResult(
                    success=True,
                    message="Document is in standard storage",
                    restore_status="not_archived",
                    is_retrievable=True
                )
            
            # Check restore status
            restore_status = head_response.get('Restore', '')
            
            if not restore_status:
                return RestoreResult(
                    success=True,
                    message=f"Document is in {storage_tier} storage and requires restore",
                    restore_status="archived",
                    is_retrievable=False
                )
            
            if 'ongoing-request="true"' in restore_status:
                return RestoreResult(
                    success=True,
                    message="Restore is in progress",
                    restore_status="in_progress",
                    is_retrievable=False
                )
            
            if 'ongoing-request="false"' in restore_status:
                import re
                expiry_match = re.search(r'expiry-date="([^"]+)"', restore_status)
                expiry = expiry_match.group(1) if expiry_match else None
                
                return RestoreResult(
                    success=True,
                    message=f"Document is restored and available (expires: {expiry})",
                    restore_status="restored",
                    restore_expiry=expiry,
                    is_retrievable=True
                )
            
            return RestoreResult(
                success=True,
                message=f"Document is in {storage_tier} storage",
                restore_status="archived",
                is_retrievable=False
            )
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == '404' or error_code == 'NoSuchKey':
                return RestoreResult(
                    success=False,
                    message="Document not found"
                )
            error_msg = e.response.get('Error', {}).get('Message', str(e))
            return RestoreResult(
                success=False,
                message=f"Failed to get status: {error_msg}"
            )
        except Exception as e:
            return RestoreResult(
                success=False,
                message=f"Unexpected error: {str(e)}"
            )
    
    def _get_restore_estimate(self, restore_tier: str) -> str:
        """Get estimated restore completion time based on tier."""
        estimates = {
            "Expedited": "1-5 minutes",
            "Standard": "3-5 hours",
            "Bulk": "5-12 hours"
        }
        return estimates.get(restore_tier, "Unknown")
