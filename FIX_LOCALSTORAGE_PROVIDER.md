# Fix: LocalStorageProvider Abstract Methods Implementation

## Issue

The application was throwing a `TypeError` when trying to instantiate `LocalStorageProvider`:

```
TypeError: Can't instantiate abstract class LocalStorageProvider with abstract methods exists, get_archive_status, move_to_archive
```

## Root Cause

The `LocalStorageProvider` class in `app/storage/local.py` was missing implementations for three abstract methods defined in the `BaseStorageProvider` abstract base class:

1. **`exists(storage_path: str) -> bool`** - Check if a document exists in storage
2. **`move_to_archive(storage_path: str, storage_tier: str) -> ArchiveResult`** - Move document to archive tier
3. **`get_archive_status(storage_path: str) -> RestoreResult`** - Get archive/restore status of a document

## Solution

### 1. Added `exists()` Method

```python
async def exists(self, storage_path: str) -> bool:
    """
    Check if a document exists in local storage.
    
    Args:
        storage_path: Path to the document
        
    Returns:
        True if document exists
    """
    try:
        path = Path(storage_path)
        return path.exists()
    except Exception as e:
        logger.error(f"Exists check failed: {e}")
        return False
```

**Purpose:** Verifies the existence of a document at a given storage path.

### 2. Added `move_to_archive()` Method

```python
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
    return await self.archive_to_tier(storage_path, storage_tier)
```

**Purpose:** Moves a document to archive or deep archive storage tiers (delegates to existing `archive_to_tier()` method).

### 3. Added `get_archive_status()` Method

```python
async def get_archive_status(self, storage_path: str) -> RestoreResult:
    """
    Get the archive/restore status of a document.
    
    Args:
        storage_path: Path to the document in storage
        
    Returns:
        RestoreResult with current status
    """
    try:
        path = Path(storage_path)
        
        if not path.exists():
            return RestoreResult(
                success=False,
                message=f"Document not found at {storage_path}",
                restore_status="not_found",
                is_retrievable=False
            )
        
        # Check metadata for archive/restore status
        meta_path = self._get_metadata_path(path)
        
        if meta_path.exists():
            with open(meta_path, 'r') as f:
                meta_data = json.load(f)
            
            restore_status = meta_data.get("restore_status", RestoreStatus.AVAILABLE.value)
            restore_expiry = meta_data.get("restore_expiry")
            storage_tier = meta_data.get("storage_tier", StorageTier.STANDARD.value)
            
            # Check if restore is expired
            is_retrievable = True
            if restore_expiry:
                expiry_dt = datetime.fromisoformat(restore_expiry)
                if expiry_dt < datetime.utcnow():
                    restore_status = RestoreStatus.EXPIRED.value
                    is_retrievable = False
            
            return RestoreResult(
                success=True,
                message=f"Document status: {restore_status} (tier: {storage_tier})",
                restore_status=restore_status,
                restore_expiry=restore_expiry,
                is_retrievable=is_retrievable
            )
        else:
            # No metadata, assume available
            return RestoreResult(
                success=True,
                message="Document is available",
                restore_status=RestoreStatus.AVAILABLE.value,
                is_retrievable=True
            )
    
    except Exception as e:
        logger.error(f"Failed to get archive status: {e}")
        return RestoreResult(
            success=False,
            message=f"Failed to get archive status: {str(e)}",
            is_retrievable=False
        )
```

**Purpose:** Checks if a document is in archive/deep archive and returns its restore status.

## Testing

After implementing the abstract methods, the `LocalStorageProvider` can now be successfully instantiated:

```bash
$ python -c "from app.storage.local import LocalStorageProvider; provider = LocalStorageProvider(); print(f'✅ LocalStorageProvider instantiated successfully: {provider.provider_name}')"
✅ LocalStorageProvider instantiated successfully: local
```

## Impact

- ✅ Fixes `TypeError` when initializing storage provider
- ✅ Enables local storage backend for document archiving
- ✅ Maintains consistency with other storage providers (AWS S3, Azure Blob, GCP)
- ✅ All abstract methods now properly implemented in `LocalStorageProvider`

## Files Modified

- `app/storage/local.py` - Added 3 abstract method implementations

## Related Files

The following storage providers already had all abstract methods implemented:
- `app/storage/aws_s3.py`
- `app/storage/azure_blob.py`
- `app/storage/gcp_storage.py`

## Commit

```
Fix: Implement missing abstract methods in LocalStorageProvider (exists, move_to_archive, get_archive_status)
Commit: 88cc0b8
```

