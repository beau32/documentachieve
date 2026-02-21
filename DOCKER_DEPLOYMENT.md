# Docker Deployment Guide

## Docker Image Refresh - v2.0.0

The Docker image has been successfully rebuilt with all Phase 5 updates:

✅ **Latest image**: `cloud-document-archive:latest`  
✅ **Version tags**: `cloud-document-archive:v2.0.0`  
✅ **Image ID**: `5d98998d2bfd`  
✅ **Size**: 4.47GB (compressed), 12.8GB (disk usage)  

### What's Included in v2.0.0

**Phase 1: Encryption (✅ Complete)**
- RSA+AES-256-GCM hybrid encryption
- X.509 certificate support
- Encryption service and key management

**Phase 2: User Management & Audit Trail (✅ Complete)**
- JWT authentication with token refresh
- 5 built-in roles: Admin, Archive Manager, Auditor, User, Viewer
- 20+ granular permissions
- Comprehensive audit logging (17 event types)
- Database and file-based dual logging

**Phase 3: Audit Log Retrieval API (✅ Complete)**
- GET `/api/v1/audit/logs` endpoint
- Period filtering with ISO format dates
- Multi-parameter filtering (event type, user, resource, status)
- Pagination support

**Phase 4: CLI Module (✅ Complete)**
- File operations (copy, delete, overwrite)
- User management commands
- Audit log retrieval and export
- System initialization

**Phase 5: Authentication & Audit Middleware (✅ Complete)**
- AuthMiddleware for JWT token validation
- AuditMiddleware for automatic request/response logging
- Route protection with permission checks
- Exempt paths for health checks and login

## Quick Start with Docker

### 1. Deploy with Docker Compose

```bash
cd documentachieve
docker-compose up -d
```

This will start:
- **API Server** on http://localhost:8000
- **Kafka** on localhost:9092
- **Zookeeper** on localhost:2181

### 2. Access the Application

**Swagger UI**: http://localhost:8000/docs  
**API Base URL**: http://localhost:8000/api/v1  
**Health Check**: http://localhost:8000/health  

### 3. Initialize the System

```bash
# CLI initialization
archive-cli init

# Or via Docker
docker-compose exec api archive-cli init
```

This will:
- Create database tables
- Create initial admin user (prompted)
- Set up directories

### 4. Login and Get Token

```bash
# Login with admin credentials
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "your-password"
  }'
```

Response:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### 5. Use Token for Authenticated Requests

```bash
# Archive a document
curl -X POST http://localhost:8000/api/v1/archive \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "test.pdf",
    "document_base64": "JVBERi0xLjQKJeLjz9M...",
    "content_type": "application/pdf",
    "tags": {"category": "invoice", "year": "2026"}
  }'

# Retrieve audit logs
curl -X GET "http://localhost:8000/api/v1/audit/logs?limit=50&event_type=document_upload" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Configuration

### Environment Variables (set in docker-compose.yml)

```yaml
# Authentication (Phase 2)
AUTH_ENABLED: "true"              # Enable JWT auth
JWT_SECRET_KEY: "change-me"       # Strong random key
JWT_ACCESS_TOKEN_EXPIRES: "30"    # minutes
JWT_REFRESH_TOKEN_EXPIRES: "7"    # days

# Audit Trail (Phase 2)
AUDIT_ENABLED: "true"             # Enable audit logging
AUDIT_LOG_FILE: "./data/audit.log"
AUDIT_INCLUDE_REQUEST_BODY: "false"  # Security: don't log passwords
AUDIT_INCLUDE_RESPONSE_BODY: "false"

# Storage
STORAGE_PROVIDER: "local"         # local, aws_s3, azure_blob, gcp_storage

# Kafka
KAFKA_ENABLED: "true"
KAFKA_BOOTSTRAP_SERVERS: "kafka:29092"

# Lifecycle
LIFECYCLE_ENABLED: "true"
LIFECYCLE_ARCHIVE_AFTER_DAYS: "90"
LIFECYCLE_DEEP_ARCHIVE_AFTER_DAYS: "365"
```

### Production Checklist

- [ ] Generate strong `JWT_SECRET_KEY` (at least 32 characters)
- [ ] Change `STORAGE_PROVIDER` from `local` to `aws_s3`, `azure_blob`, or `gcp_storage`
- [ ] Configure cloud provider credentials
- [ ] Enable HTTPS/TLS termination (use nginx reverse proxy)
- [ ] Set up database backups
- [ ] Configure firewall rules
- [ ] Use strong admin password
- [ ] Enable audit log rotation
- [ ] Set up monitoring and alerts
- [ ] Document role/permission assignments

## Docker Compose Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f api

# View logs for specific service
docker-compose logs -f kafka

# Restart service
docker-compose restart api

# Remove volumes (DELETE DATA!)
docker-compose down -v

# Rebuild image
docker-compose build --no-cache

# Execute command in container
docker-compose exec api archive-cli users list

# Enter container shell
docker-compose exec api /bin/bash
```

## Troubleshooting

### API fails to start

Check logs:
```bash
docker-compose logs api
```

Common issues:
- **Port 8000 already in use**: Change port in docker-compose.yml
- **Database locked**: Remove `./data/document_archive.db` and restart
- **Import error**: Rebuild image with `docker-compose build --no-cache`

### Cannot connect to API

```bash
# Check if container is running
docker ps | grep cloud-document-archive

# Check container status
docker-compose ps

# View logs
docker-compose logs api

# Test health endpoint
curl http://localhost:8000/health
```

### Authentication not working

```bash
# Check JWT_SECRET_KEY is set
docker-compose exec api env | grep JWT

# Try logging in
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password"}'
```

### Audit logs not being created

Check audit is enabled:
```bash
docker-compose exec api env | grep AUDIT_ENABLED

# View audit log file
docker-compose exec api cat ./data/audit.log
```

## Performance Tuning

### Memory

For large deployments, increase memory in docker-compose.yml:

```yaml
services:
  api:
    mem_limit: 4g
    memswap_limit: 4g
```

### CPU

Limit CPU usage:

```yaml
services:
  api:
    cpus: '2.0'
```

## Updating to Latest Version

### 1. Stop current container

```bash
docker-compose down
```

### 2. Pull latest code

```bash
git pull origin main
```

### 3. Rebuild image

```bash
docker-compose build --no-cache
```

### 4. Start with new image

```bash
docker-compose up -d
```

### 5. Verify services

```bash
docker-compose ps
curl http://localhost:8000/health
```

## Image Details

**Base Image**: `python:3.11-slim`  
**Multi-stage Build**: Yes (optimized for size)  
**Healthcheck**: Enabled (30s interval, 10s timeout)  
**Entrypoint**: `uvicorn app.main:app --host 0.0.0.0 --port 8000`  

### Layers

1. **Builder Stage**
   - Python 3.11 base
   - System dependencies (gcc)
   - Python packages from requirements.txt

2. **Runtime Stage**
   - Python 3.11 runtime
   - Runtime dependencies (curl for healthcheck)
   - Application code
   - Data directory

### Volumes

- `./data:/app/data` - Persistent storage for SQLite database, audit logs, and documents

## Security Best Practices

1. **Secret Management**
   - Don't commit `.env` file with secrets
   - Use production-grade secret management (Vault, AWS Secrets Manager)
   - Rotate JWT_SECRET_KEY periodically

2. **Network Security**
   - Use HTTPS in production (nginx reverse proxy)
   - Restrict API access to authorized clients
   - Use network policies for Kafka access

3. **Authentication**
   - Change default admin password
   - Require strong passwords for all users
   - Implement session timeouts
   - Monitor failed login attempts

4. **Audit Logging**
   - Regularly review audit logs
   - Archive old logs for compliance
   - Set up monitoring for suspicious activities
   - Don't log sensitive data (passwords, tokens)

5. **Data Protection**
   - Enable encryption for sensitive documents
   - Use cloud provider encryption at rest
   - Use TLS for data in transit
   - Implement database backups

## Support

For issues or questions:
- Check documentation in `MIDDLEWARE_GUIDE.md`, `CLI_GUIDE.md`, `USER_MANAGEMENT.md`
- Review audit logs for debugging
- Check container logs with `docker-compose logs`

