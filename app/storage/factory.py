"""Storage provider factory for selecting the appropriate cloud storage."""

from typing import Dict, Type

from app.config import settings, StorageProvider
from app.storage.base import BaseStorageProvider
from app.storage.aws_s3 import AWSS3Provider
from app.storage.azure_blob import AzureBlobProvider
from app.storage.gcp_storage import GCPStorageProvider


# Registry of available storage providers
_PROVIDERS: Dict[StorageProvider, Type[BaseStorageProvider]] = {
    StorageProvider.AWS_S3: AWSS3Provider,
    StorageProvider.AZURE_BLOB: AzureBlobProvider,
    StorageProvider.GCP_STORAGE: GCPStorageProvider,
}

# Singleton instance cache
_provider_instances: Dict[StorageProvider, BaseStorageProvider] = {}


def get_storage_provider(provider: StorageProvider = None) -> BaseStorageProvider:
    """
    Get the storage provider instance.
    
    Args:
        provider: Optional specific provider to use. If not provided,
                  uses the configured default provider.
                  
    Returns:
        An instance of the appropriate storage provider.
        
    Raises:
        ValueError: If the requested provider is not supported.
    """
    if provider is None:
        provider = settings.storage_provider
    
    if provider not in _PROVIDERS:
        raise ValueError(f"Unsupported storage provider: {provider}")
    
    # Return cached instance if available
    if provider not in _provider_instances:
        _provider_instances[provider] = _PROVIDERS[provider]()
    
    return _provider_instances[provider]


def get_all_providers() -> Dict[StorageProvider, BaseStorageProvider]:
    """
    Get all available storage provider instances.
    
    Returns:
        Dictionary mapping provider enum to provider instance.
    """
    for provider in _PROVIDERS:
        if provider not in _provider_instances:
            _provider_instances[provider] = _PROVIDERS[provider]()
    
    return _provider_instances.copy()


def clear_provider_cache():
    """Clear the provider instance cache. Useful for testing."""
    _provider_instances.clear()
