# Middleware System Documentation

## Overview

The middleware system provides two key functions for the Cloud Document Archive:

1. **AuthMiddleware** - Validates JWT tokens and injects user context
2. **AuditMiddleware** - Logs all API requests and responses for compliance

Both middleware are automatically integrated into the FastAPI application when `AUTH_ENABLED` or `AUDIT_ENABLED` are set to true in the configuration.

## Architecture

```
Client Request
    ↓
[CORS Middleware]
    ↓
[AuthMiddleware] ← Validates JWT tokens, injects user context
    ↓
[AuditMiddleware] ← Logs requests/responses with audittrail
    ↓
[Route Handler] ← Protected route with permission checks
    ↓
Response
```

---

## AuthMiddleware

### Purpose

Validates JWT bearer tokens from the `Authorization` header and injects authenticated user information into the request context for downstream handlers.

### Configuration

Enable via environment variables:

```bash
AUTH_ENABLED=true
JWT_SECRET_KEY="your-secret-key"
JWT_ACCESS_TOKEN_EXPIRES=30      # minutes
JWT_REFRESH_TOKEN_EXPIRES=7      # days
```

### Exempt Paths

The following paths do NOT require authentication:
- `/health` - Health check endpoint
- `/api/v1/auth/login` - User login
- `/api/v1/auth/register` - User registration (if implemented)
- `/docs` - Swagger UI
- `/openapi.json` - OpenAPI schema
- `/redoc` - ReDoc documentation

### How It Works

1. **Token Extraction**: Reads `Authorization: Bearer <token>` from request headers
2. **Token Validation**: Verifies token signature and expiration using JWT_SECRET_KEY
3. **User Injection**: Extracts user info and injects into `request.state`:
   - `user_id`: Numeric user identifier
   - `username`: User login name
   - `role`: Assigned role (admin, archive_manager, auditor, user, viewer)
4. **Error Handling**: Returns 401 Unauthorized if token is invalid or missing

### Usage in Routes

```python
from fastapi import Depends, Request
from app.middleware import get_current_user

@app.get("/api/v1/documents")
async def list_documents(
    request: Request,
    user: dict = Depends(get_current_user)
):
    """Get documents for current user."""
    return {
        "user_id": user["user_id"],
        "username": user["username"],
        "role": user["role"]
    }
```

### Implementation Details

**File**: `app/middleware.py`

**Key Methods**:
- `AuthMiddleware.dispatch()` - Main middleware handler
- `get_current_user()` - Dependency to retrieve authenticated user

**Error Responses**:
```json
{
  "detail": "Missing or invalid Authorization header"
}
```

```json
{
  "detail": "Invalid or expired token"
}
```

---

## AuditMiddleware

### Purpose

Automatically logs all API requests and responses to the audit trail for compliance and debugging. Captures comprehensive information about each API call including user, IP, method, status, and execution time.

### Configuration

Enable via environment variables:

```bash
AUDIT_ENABLED=true
AUDIT_LOG_FILE=./logs/audit.log        # File path for audit logs
AUDIT_INCLUDE_REQUEST_BODY=false       # Log request bodies (security concern for passwords)
AUDIT_INCLUDE_RESPONSE_BODY=false      # Log response bodies
```

### Exempt Paths

The following paths are NOT audited (too verbose):
- `/health` - Health check (frequent)
- `/docs` - Swagger UI
- `/openapi.json` - OpenAPI schema
- `/redoc` - ReDoc documentation

### Captured Information

For each request/response, the middleware logs:

| Field | Description |
|-------|-------------|
| `event_type` | Type of event (login, document_upload, etc.) |
| `timestamp` | When the request was made |
| `user_id` | ID of authenticated user (if applicable) |
| `username` | Name of authenticated user |
| `ip_address` | Client IP address |
| `user_agent` | Client User-Agent string |
| `http_method` | HTTP method (GET, POST, DELETE, etc.) |
| `http_endpoint` | API endpoint path |
| `http_status` | Response HTTP status code |
| `status` | Audit status (success, failure, partial) |
| `resource_type` | Type of resource affected (document, user, etc.) |
| `resource_id` | ID of resource affected |
| `execution_time_ms` | Time to execute request (milliseconds) |
| `query_params` | Query string parameters |

### Event Type Detection

The middleware automatically determines event type based on endpoint:

| Endpoint Pattern | Event Type |
|---|---|
| `/auth/login` | LOGIN |
| `/auth/logout` | LOGOUT |
| `/documents` | DOCUMENT_UPLOAD (POST) or DOCUMENT_VIEW (GET) |
| `/archive` | DOCUMENT_UPLOAD |
| `/retrieve` | DOCUMENT_DOWNLOAD |
| `/delete` | DOCUMENT_DELETE |
| `/search` | DOCUMENT_SEARCH |
| `/audit/logs` | AUDIT_LOG_ACCESS |
| `/users` | USER_CREATED |
| `/roles` | ROLE_ASSIGNMENT |

### Status Determination

Response HTTP status determines audit status:

- **2xx (200-299)**: `success`
- **3xx (300-399)**: `partial`
- **4xx, 5xx**: `failure`

### Usage Example

```bash
# Make authenticated request
curl -X POST http://localhost:8000/api/v1/archive \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"filename": "test.pdf", "tags": ""}'

# Audit log will be created showing:
# - User who made the request
# - Document uploaded successfully (2xx status)
# - Execution time
# - IP address and user agent
```

### Implementation Details

**File**: `app/middleware.py`

**Key Methods**:
- `AuditMiddleware.dispatch()` - Main middleware handler
- `_get_event_type()` - Determine event type from endpoint
- `_get_resource_type()` - Extract resource type from endpoint
- `_get_resource_id()` - Extract resource ID from path or query

### Log Entry Structure

Audit logs are stored in both file and database in this format:

```python
{
    "id": 1,
    "timestamp": "2026-02-21T14:30:45.123456",
    "event_type": "document_upload",
    "user_id": 1,
    "username": "john",
    "resource_type": "document",
    "resource_id": "doc-abc123",
    "action": "POST",
    "status": "success",
    "http_method": "POST",
    "http_endpoint": "/api/v1/archive",
    "http_status": 200,
    "ip_address": "192.168.1.100",
    "user_agent": "curl/7.68.0",
    "execution_time_ms": 145.32,
    "details": {
        "query_params": {},
        "execution_time_ms": 145.32
    }
}
```

---

## Permission and Role Dependencies

### Require Role

Restrict access to specific roles:

```python
from fastapi import Depends
from app.middleware import require_role

@app.delete("/api/v1/users/{user_id}")
async def delete_user(
    user_id: int,
    role: str = Depends(require_role("admin"))
):
    """Only admins can delete users."""
    return {"deleted": user_id}
```

**Allowed in roles**: Pass one or more role names
```python
# Require any of these roles
role: str = Depends(require_role("admin", "archive_manager"))
```

### Require Permission

Restrict access based on fine-grained permissions:

```python
from fastapi import Depends
from app.middleware import require_permission

@app.post("/api/v1/archive")
async def archive_document(
    request: ArchiveRequest,
    permission: str = Depends(require_permission("document_upload"))
):
    """Only users with document_upload permission can upload."""
    return {"archived": True}
```

**Available Permissions**:
- `document_upload` - Upload documents
- `document_download` - Download documents
- `document_delete` - Delete documents
- `document_view` - View documents
- `document_search` - Search documents
- `document_share` - Share documents
- `audit_read` - Read audit logs
- `user_create` - Create users
- `user_delete` - Delete users
- `user_update` - Update users
- `role_assign` - Assign roles
- `role_create` - Create roles
- `permission_manage` - Manage permissions
- `system_config` - Manage system configuration

### Error Responses

**Missing Authorization Header (401)**:
```json
{
  "detail": "Missing or invalid Authorization header"
}
```

**Invalid Token (401)**:
```json
{
  "detail": "Invalid or expired token"
}
```

**Insufficient Permissions (403)**:
```json
{
  "detail": "This operation requires one of: admin, archive_manager"
}
```

```json
{
  "detail": "Missing required permission: document_upload"
}
```

---

## Integration with Routes

### Protected Route Example

```python
from fastapi import APIRouter, Depends, Request
from app.middleware import (
    get_current_user,
    require_role,
    require_permission
)

router = APIRouter()

@router.post("/api/v1/archive")
async def archive_document(
    request: ArchiveRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    permission: str = Depends(require_permission("document_upload"))
):
    """
    Archive a document.
    
    Requires:
    - Valid JWT token (AuthMiddleware)
    - document_upload permission (require_permission)
    
    Also:
    - Automatic request/response logging (AuditMiddleware)
    - User info available in 'user' parameter
    """
    # user = {"user_id": 1, "username": "john", "role": "user"}
    # permission = "document_upload"
    
    service = DocumentArchiveService(db)
    return await service.archive_document(request)
```

### Admin-Only Route Example

```python
@router.delete("/api/v1/users/{user_id}")
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    role: str = Depends(require_role("admin"))
):
    """Delete a user - admin only."""
    # This endpoint is only accessible to admin users
    service = UserManagementService(db)
    return service.delete_user(user_id)
```

---

## Troubleshooting

### Issue: "Missing or invalid Authorization header"

**Cause**: Request was missing the `Authorization` header

**Fix**: Include Authorization header in request:
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/v1/archive
```

### Issue: "Invalid or expired token"

**Cause**: Token is invalid or has expired

**Fix**:
1. Get a new token via login endpoint
2. Check JWT_SECRET_KEY matches in config
3. Check token hasn't expired (default 30 minutes)

```bash
# Login to get new token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "john", "password": "password"}'

# Use new token
curl -H "Authorization: Bearer NEW_TOKEN" http://localhost:8000/api/v1/archive
```

### Issue: "Missing required permission: document_upload"

**Cause**: User's role doesn't have the required permission

**Fix**: Assign the required role to the user:
```bash
archive-cli users assign-role john --role archive_manager
```

Or check user's current permissions:
```bash
archive-cli users info john
```

### Issue: Audit logs not being created

**Cause**: `AUDIT_ENABLED` is set to false or middleware initialization failed

**Fix**:
1. Set `AUDIT_ENABLED=true` in environment
2. Verify `AUDIT_LOG_FILE` path is writable
3. Check logs for initialization errors:
   ```bash
   tail -f ./logs/audit.log
   ```

---

## Security Considerations

### JWT Tokens

1. **Secret Key**: Use a strong, random secret key
   ```bash
   # Generate a secure key
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **Token Expiration**: Keep token expiration short (30 minutes default)

3. **Refresh Tokens**: Use refresh tokens for longer sessions (7 days default)

4. **HTTPS**: Always use HTTPS in production to prevent token interception

### Audit Logging

1. **Request Bodies**: Don't log request bodies (may contain passwords)
   ```bash
   AUDIT_INCLUDE_REQUEST_BODY=false
   ```

2. **Sensitive Data**: Avoid logging response bodies containing sensitive data
   ```bash
   AUDIT_INCLUDE_RESPONSE_BODY=false
   ```

3. **Log Retention**: Implement log retention policies
   - Rotate logs periodically
   - Archive old logs securely
   - Consider regulatory requirements (GDPR 30 days, HIPAA 6 years)

---

## Performance Tuning

### Audit Middleware Impact

- **Minimal Overhead**: ~1-5ms per request for logging
- **Async**: Non-blocking logging operation
- **Database**: Uses connection pooling to minimize impact

### Optimization Tips

1. **Reduce Logged Data**: Disable REQUEST/RESPONSE body logging if not needed
2. **Event Sampling**: Sample high-volume events (if needed)
3. **Async Audit Service**: Uses async database writes

---

## Deployment Checklist

- [ ] Set `AUTH_ENABLED=true` in production
- [ ] Set `AUDIT_ENABLED=true` for compliance
- [ ] Generate strong `JWT_SECRET_KEY`
- [ ] Configure short token expiration (30 min)
- [ ] Enable HTTPS/TLS
- [ ] Set up audit log rotation
- [ ] Configure firewall for authentication endpoints
- [ ] Monitor failed authentication attempts
- [ ] Document role/permission assignments
- [ ] Test authentication flow before production

