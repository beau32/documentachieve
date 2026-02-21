# User Management & Audit Trail - Quick Start

## 5-Minute Setup

### 1. Enable Authentication

Edit or create `config.yaml`:
```yaml
auth:
  enabled: true
  jwt_secret_key: "change-this-to-a-random-key"
  jwt_access_token_expires: 30
  jwt_refresh_token_expires: 7

audit:
  enabled: true
  log_file: audit.log
```

Or use environment variables:
```bash
export AUTH_ENABLED=true
export JWT_SECRET_KEY="change-this-to-a-random-key"  
export AUDIT_ENABLED=true
```

### 2. Create Admin User

```python
python -c "
from app.user_management import UserManagementService, UserRole
from app.database import SessionLocal

db = SessionLocal()
service = UserManagementService(db)
result = service.create_user(
    username='admin',
    email='admin@example.com',
    password='admin123456',
    role=UserRole.ADMIN
)
print('Created:', result)
"
```

### 3. Get Access Token

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123456"}'
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

### 4. Use Token in Requests

```bash
# Archive a document
curl -X POST http://localhost:8000/api/v1/archive \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{...}'
```

### 5. View Audit Logs

```bash
curl -X GET "http://localhost:8000/api/v1/audit/logs?limit=10" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Common Tasks

### Create a User

```bash
curl -X POST http://localhost:8000/api/v1/users \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john.doe",
    "email": "john@example.com",
    "password": "secure-password-123",
    "full_name": "John Doe",
    "role": "user"
  }'
```

### List All Users

```bash
curl -X GET "http://localhost:8000/api/v1/users?limit=20" \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

### Assign Role

```bash
curl -X POST http://localhost:8000/api/v1/users/2/role \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"role": "archive_manager"}'
```

### Filter Audit Logs

By event type:
```bash
curl -X GET "http://localhost:8000/api/v1/audit/logs?event_type=document_upload&limit=50" \
  -H "Authorization: Bearer TOKEN"
```

By user:
```bash
curl -X GET "http://localhost:8000/api/v1/audit/logs?user_id=1&limit=50" \
  -H "Authorization: Bearer TOKEN"
```

By date range:
```bash
curl -X GET "http://localhost:8000/api/v1/audit/logs?start_date=2026-02-01T00:00:00&end_date=2026-02-21T23:59:59&limit=100" \
  -H "Authorization: Bearer TOKEN"
```

## Roles Quick Reference

| Role | Best For | Key Permissions |
|------|----------|-----------------|
| **admin** | System administrators | All permissions |
| **archive_manager** | Document managers | Full document operations + logs |
| **auditor** | Compliance officers | Read-only + audit logs |
| **user** | Regular users | Upload, retrieve, update documents |
| **viewer** | External stakeholders | View documents and reports only |

## Token Management

### Get New Access Token Using Refresh Token

```bash
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "YOUR_REFRESH_TOKEN"}'
```

### Access Token Lifetime

- **Default**: 30 minutes
- **Configure**: Set `JWT_ACCESS_TOKEN_EXPIRES` in config
- **Refresh**: Use refresh token before expiration

## Audit Trail Examples

### Document Upload Event
```json
{
  "event_type": "document_upload",
  "user_id": 1,
  "username": "john.doe",
  "resource_type": "document",
  "resource_id": "abc123xyz",
  "action": "upload",
  "status": "success",
  "timestamp": "2026-02-21T10:30:00",
  "details": {
    "filename": "report.pdf",
    "size_bytes": 2048,
    "storage_provider": "aws_s3"
  }
}
```

### Access Denied Event
```json
{
  "event_type": "access_denied",
  "user_id": 2,
  "username": "jane.smith",
  "resource_type": "user",
  "resource_id": "1",
  "action": "delete",
  "status": "failure",
  "timestamp": "2026-02-21T11:00:00",
  "details": {
    "reason": "Insufficient permissions",
    "required_permission": "user:delete"
  }
}
```

## Configuration Reference

### config.yaml

```yaml
app:
  name: Cloud Document Archive
  debug: false

storage:
  provider: local
  # ... storage configuration ...

database:
  url: sqlite:///./document_archive.db

# User Authentication & Authorization
auth:
  enabled: true
  jwt_secret_key: "your-secret-key-change-in-production"
  jwt_access_token_expires: 30  # minutes
  jwt_refresh_token_expires: 7  # days

# Audit Trail Logging
audit:
  enabled: true
  log_file: audit.log
  include_request_body: false  # Security: Don't log passwords
  include_response_body: false # For productivity
```

## Environment Variables

```bash
AUTH_ENABLED=true
JWT_SECRET_KEY="strong-random-key"
JWT_ACCESS_TOKEN_EXPIRES=30
JWT_REFRESH_TOKEN_EXPIRES=7

AUDIT_ENABLED=true
AUDIT_LOG_FILE=audit.log
AUDIT_INCLUDE_REQUEST_BODY=false
AUDIT_INCLUDE_RESPONSE_BODY=false
```

## Python API Usage

```python
from app.database import SessionLocal
from app.user_management import UserManagementService, UserRole, Permission
from app.auth import get_auth_provider
from app.audit_service import get_audit_service, AuditEventType, AuditLog, AuditStatus

db = SessionLocal()

# Create user
users = UserManagementService(db)
result = users.create_user(
    username="jane.smith",
    email="jane@example.com",
    password="secure-pass-123",
    role=UserRole.ARCHIVE_MANAGER
)

# Check permission
has_permission = users.check_permission(
    user_id=1,
    permission=Permission.DOCUMENT_DELETE
)

# Authenticate user
user_data = UserManagementService.authenticate_user(
    db,
    "jane.smith",
    "secure-pass-123"
)

# Create tokens
auth = get_auth_provider()
tokens = auth.create_tokens(user_data)

# Log audit event
audit = get_audit_service()
log = AuditLog(
    event_type=AuditEventType.DOCUMENT_UPLOAD,
    user_id=1,
    username="jane.smith",
    resource_type="document",
    resource_id="doc123",
    status=AuditStatus.SUCCESS,
    details={"filename": "report.pdf"}
)
audit.log_event(log)
```

## Troubleshooting

### "User already exists"
- Username must be unique
- Check existing users with GET /users

### "Invalid credentials"
- Verify username and password
- Check user is active (`is_active=true`)

### "Token expired"
- Use refresh token to get new access token
- Re-authenticate if needed

### "Access denied"
- Check user role and permissions
- Try with admin account
- Review audit logs for details

## Next Steps

1. Read [USER_MANAGEMENT.md](USER_MANAGEMENT.md) for complete documentation
2. Set strong JWT secret key for production
3. Configure HTTPS for all endpoints
4. Set up audit log rotation
5. Implement custom roles if needed
6. Enable MFA for admin accounts

## Support Docs

- Complete guide: [USER_MANAGEMENT.md](USER_MANAGEMENT.md)
- API endpoints: [USER_MANAGEMENT.md#api-endpoints](USER_MANAGEMENT.md#api-endpoints)
- Audit events: [USER_MANAGEMENT.md#audit-events](USER_MANAGEMENT.md#audit-events)
- Security: [USER_MANAGEMENT.md#security-best-practices](USER_MANAGEMENT.md#security-best-practices)
