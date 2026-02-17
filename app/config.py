"""Configuration management for the cloud document archive application."""

import os
import yaml
from enum import Enum
from typing import Optional, Dict, Any
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field


class StorageProvider(str, Enum):
    """Supported cloud storage providers."""
    AWS_S3 = "aws_s3"
    AZURE_BLOB = "azure_blob"
    GCP_STORAGE = "gcp_storage"


class StorageTier(str, Enum):
    """Storage tiers for document archiving."""
    STANDARD = "standard"           # Regular storage (S3 Standard, Azure Hot, GCP Standard)
    INFREQUENT = "infrequent"       # Infrequent access (S3 IA, Azure Cool, GCP Nearline)
    ARCHIVE = "archive"             # Archive tier (S3 Glacier IR, Azure Cold, GCP Coldline)
    DEEP_ARCHIVE = "deep_archive"   # Deep archive (S3 Glacier Deep, Azure Archive, GCP Archive)


class RestoreStatus(str, Enum):
    """Restore status for archived documents."""
    NOT_ARCHIVED = "not_archived"       # Document is in standard storage
    ARCHIVED = "archived"               # Document is in archive, not being restored
    RESTORE_IN_PROGRESS = "in_progress" # Restore is in progress
    RESTORED = "restored"               # Document is temporarily restored


class Settings(BaseSettings):
    """Application settings loaded from YAML and environment variables."""
    
    # Application settings
    app_name: str = "Cloud Document Archive"
    debug: bool = False
    
    # Active storage provider
    storage_provider: StorageProvider = StorageProvider.AWS_S3
    
    # AWS S3 Configuration
    aws_access_key_id: Optional[str] = Field(default=None)
    aws_secret_access_key: Optional[str] = Field(default=None)
    aws_region: str = "us-east-1"
    aws_s3_bucket: str = "document-archive"
    
    # AWS Glacier Configuration
    aws_glacier_restore_days: int = 7  # Days to keep restored objects
    aws_glacier_restore_tier: str = "Standard"  # Expedited, Standard, or Bulk
    
    # Azure Blob Storage Configuration
    azure_connection_string: Optional[str] = Field(default=None)
    azure_container_name: str = "document-archive"
    
    # GCP Storage Configuration
    gcp_project_id: Optional[str] = Field(default=None)
    gcp_credentials_path: Optional[str] = Field(default=None)
    gcp_bucket_name: str = "document-archive"
    
    # Database for metadata (using SQLite for simplicity)
    database_url: str = "sqlite:///./document_archive.db"
    
    # Kafka Configuration
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic_restore_ready: str = "document-restore-ready"
    kafka_topic_archived: str = "document-archived"
    kafka_enabled: bool = False  # Set to True to enable Kafka publishing
    
    # Lifecycle/Archival Configuration
    lifecycle_enabled: bool = False  # Enable automatic archival based on age
    lifecycle_archive_after_days: int = 90  # Days after creation to move to archive
    lifecycle_deep_archive_after_days: int = 365  # Days after creation to move to deep archive
    lifecycle_check_interval_hours: int = 24  # How often to check for files to archive
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
    
    @classmethod
    def from_yaml(cls, yaml_path: str = "config.yaml") -> "Settings":
        """
        Load settings from YAML file.
        Environment variables take precedence over YAML values.
        
        Args:
            yaml_path: Path to the YAML configuration file
            
        Returns:
            Settings instance with values loaded from YAML and environment
        """
        config_data = {}
        
        # Load YAML file if it exists
        yaml_file = Path(yaml_path)
        if yaml_file.exists():
            with open(yaml_file, 'r') as f:
                yaml_data = yaml.safe_load(f) or {}
                _flatten_yaml_config(yaml_data, config_data)
        
        # Create settings instance - environment variables override YAML
        return cls(**config_data)


def _flatten_yaml_config(data: Dict[str, Any], flat: Dict[str, Any], prefix: str = "") -> None:
    """
    Flatten nested YAML configuration to flat dictionary.
    Converts nested keys to environment variable format (e.g., 'app.debug' -> 'APP_DEBUG').
    
    Args:
        data: Nested YAML configuration
        flat: Flat dictionary to populate
        prefix: Current prefix for nested keys
    """
    for key, value in data.items():
        if isinstance(value, dict):
            new_prefix = f"{prefix}_{key}" if prefix else key
            _flatten_yaml_config(value, flat, new_prefix)
        else:
            env_key = f"{prefix}_{key}".upper() if prefix else key.upper()
            
            # Map YAML keys to Python attribute names
            if env_key == "APP_NAME":
                flat['app_name'] = value
            elif env_key == "APP_DEBUG":
                flat['debug'] = value
            elif env_key == "STORAGE_PROVIDER":
                flat['storage_provider'] = value
            elif env_key == "AWS_ACCESS_KEY_ID":
                flat['aws_access_key_id'] = value
            elif env_key == "AWS_SECRET_ACCESS_KEY":
                flat['aws_secret_access_key'] = value
            elif env_key == "AWS_REGION":
                flat['aws_region'] = value
            elif env_key == "AWS_BUCKET":
                flat['aws_s3_bucket'] = value
            elif env_key == "AWS_GLACIER_RESTORE_DAYS":
                flat['aws_glacier_restore_days'] = value
            elif env_key == "AWS_GLACIER_RESTORE_TIER":
                flat['aws_glacier_restore_tier'] = value
            elif env_key == "AZURE_CONNECTION_STRING":
                flat['azure_connection_string'] = value
            elif env_key == "AZURE_CONTAINER_NAME":
                flat['azure_container_name'] = value
            elif env_key == "GCP_PROJECT_ID":
                flat['gcp_project_id'] = value
            elif env_key == "GCP_CREDENTIALS_PATH":
                flat['gcp_credentials_path'] = value
            elif env_key == "GCP_BUCKET_NAME":
                flat['gcp_bucket_name'] = value
            elif env_key == "DATABASE_URL":
                flat['database_url'] = value
            elif env_key == "KAFKA_ENABLED":
                flat['kafka_enabled'] = value
            elif env_key == "KAFKA_BOOTSTRAP_SERVERS":
                flat['kafka_bootstrap_servers'] = value
            elif env_key == "KAFKA_TOPICS_RESTORE_READY":
                flat['kafka_topic_restore_ready'] = value
            elif env_key == "KAFKA_TOPICS_ARCHIVED":
                flat['kafka_topic_archived'] = value
            elif env_key == "LIFECYCLE_ENABLED":
                flat['lifecycle_enabled'] = value
            elif env_key == "LIFECYCLE_ARCHIVE_AFTER_DAYS":
                flat['lifecycle_archive_after_days'] = value
            elif env_key == "LIFECYCLE_DEEP_ARCHIVE_AFTER_DAYS":
                flat['lifecycle_deep_archive_after_days'] = value
            elif env_key == "LIFECYCLE_CHECK_INTERVAL_HOURS":
                flat['lifecycle_check_interval_hours'] = value


# Load settings, preferring YAML if available, falling back to environment variables
_config_yaml_path = os.getenv("CONFIG_YAML_PATH", "config.yaml")
if Path(_config_yaml_path).exists():
    settings = Settings.from_yaml(_config_yaml_path)
else:
    settings = Settings()
