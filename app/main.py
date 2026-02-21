"""Main FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, text

from app.config import settings
from app.database import init_db, SessionLocal, DocumentMetadata
from app.routes import router
from app.kafka_producer import get_kafka_producer
from app.lifecycle_service import start_lifecycle_scheduler, stop_lifecycle_scheduler
from app.middleware import AuthMiddleware, AuditMiddleware

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Cloud Document Archive application...")
    init_db()
    logger.info(f"Using storage provider: {settings.storage_provider.value}")
    
    # Start Kafka producer
    if settings.kafka_enabled:
        kafka_producer = get_kafka_producer()
        await kafka_producer.start()
        logger.info("Kafka producer started")
    
    # Start lifecycle scheduler
    if settings.lifecycle_enabled:
        await start_lifecycle_scheduler()
        logger.info("Lifecycle scheduler started")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Cloud Document Archive application...")
    
    # Stop lifecycle scheduler
    await stop_lifecycle_scheduler()
    
    # Stop Kafka producer
    if settings.kafka_enabled:
        kafka_producer = get_kafka_producer()
        await kafka_producer.stop()


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="""
    Cloud Document Archive API
    
    A multi-cloud document archiving service supporting AWS S3, Azure Blob Storage, 
    and Google Cloud Storage. Archive documents with metadata and tags, retrieve them 
    by unique identifiers, and generate analytics reports.
    
    ## Features
    
    * **Archive**: Upload documents in base64 format with custom tags and metadata
    * **Retrieve**: Download documents using unique hashed identifiers
    * **Report**: Generate metrics and analytics for archived documents
    * **Deep Archive**: Move documents to Glacier/Archive storage tiers
    * **Glacier Retrieval**: Retrieve documents from Glacier with automatic restore
    * **Lifecycle Management**: Automatic archival based on document age
    * **Kafka Events**: Publish events when documents are archived or restored
    
    ## Supported Cloud Providers
    
    * AWS S3 (with Glacier Deep Archive)
    * Azure Blob Storage (with Archive tier)
    * Google Cloud Storage (with Archive class)
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add authentication middleware (validates JWT tokens)
if settings.auth_enabled:
    app.add_middleware(AuthMiddleware)
    logger.info("Authentication middleware enabled")

# Add audit middleware (logs all requests/responses)
if settings.audit_enabled:
    app.add_middleware(AuditMiddleware)
    logger.info("Audit middleware enabled")

# Include API routes
app.include_router(router)


@app.get("/", tags=["Health"])
async def root():
    """Root endpoint - health check."""
    return {
        "status": "healthy",
        "application": settings.app_name,
        "version": "1.0.0",
        "storage_provider": settings.storage_provider.value
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint with key application statistics."""
    try:
        db = SessionLocal()
        
        # Get document statistics
        total_docs = db.query(func.count(DocumentMetadata.id)).scalar() or 0
        total_size = db.query(func.sum(DocumentMetadata.size_bytes)).scalar() or 0
        total_size_mb = round(total_size / (1024 * 1024), 2) if total_size else 0
        
        # Get storage tier distribution
        tier_dist = {}
        tier_results = db.query(
            DocumentMetadata.storage_tier,
            func.count(DocumentMetadata.id).label('count')
        ).group_by(DocumentMetadata.storage_tier).all()
        
        for tier, count in tier_results:
            tier_dist[tier or "unknown"] = count
        
        # Get restore status distribution
        restore_dist = {}
        restore_results = db.query(
            DocumentMetadata.restore_status,
            func.count(DocumentMetadata.id).label('count')
        ).group_by(DocumentMetadata.restore_status).all()
        
        for status, count in restore_results:
            restore_dist[status or "unknown"] = count
        
        # Get content type distribution
        content_types = {}
        ct_results = db.query(
            DocumentMetadata.content_type,
            func.count(DocumentMetadata.id).label('count')
        ).group_by(DocumentMetadata.content_type).all()
        
        for content_type, count in ct_results:
            content_types[content_type or "unknown"] = count
        
        # Get recent uploads (last 24 hours)
        from sqlalchemy import and_
        from datetime import timedelta
        recent_count = db.query(func.count(DocumentMetadata.id)).filter(
            DocumentMetadata.created_at >= datetime.utcnow() - timedelta(days=1)
        ).scalar() or 0
        
        db.close()
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "application": settings.app_name,
            "version": "1.0.0",
            "configuration": {
                "storage_provider": settings.storage_provider.value,
                "kafka_enabled": settings.kafka_enabled,
                "lifecycle_enabled": settings.lifecycle_enabled,
                "database_type": "sqlite" if "sqlite" in settings.database_url else "postgres"
            },
            "statistics": {
                "total_documents": total_docs,
                "total_size_mb": total_size_mb,
                "documents_24h": recent_count,
                "storage_tier_distribution": tier_dist,
                "restore_status_distribution": restore_dist,
                "content_types_distribution": content_types,
                "avg_document_size_kb": round((total_size / total_docs) / 1024, 2) if total_docs > 0 else 0
            },
            "uptime_info": "Monitor with your infrastructure tools"
        }
    except Exception as e:
        logger.error(f"Error in health check: {str(e)}")
        return {
            "status": "degraded",
            "error": str(e),
            "storage_provider": settings.storage_provider.value,
            "kafka_enabled": settings.kafka_enabled,
            "lifecycle_enabled": settings.lifecycle_enabled
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
