# User Management & Access Control Guide

## Overview

The Cloud Document Archive includes a comprehensive user management and permission system with audit trail logging for all API calls.

## Features

✅ **User Management**
- Create, read, update, and delete users
- Role-based access control (RBAC)
- User status management (active/inactive)
- Password hashing with PBKDF2

✅ **Role-Based Permissions**
- 5 built-in roles with default permissions
- Granular permission model
- Easy to extend with custom roles

✅ **Authentication**
- JWT token-based authentication
- Access token and refresh token support
- Token expiration and validation
- Secure password storage

✅ **Audit Logging**
- Log every API call with detailed information
- Track document operations
- User management events
- Access control events
- System changes
- Query audit logs with filters

✅ **IP Address & User Agent Tracking**
- Capture client IP address
- Track user agent/browser information
- Enable forensic analysis

## Built-in Roles

### 1. **Admin**
- Full system access
- All permissions
- Can manage all users and roles

### 2. **Archive Manager**
- Complete document management
- Can upload, retrieve, update, delete documents
- Can archive to different tiers
- Can view reports and audit logs
- Can view user information

### 3. **Auditor**
- Read-only access
- Can view audit logs
- Can generate reports
- Can view documents
- Cannot modify or delete anything

### 4. **User** (default)
- Standard document operations
- Can upload and retrieve documents
- Can view reports
- Can update own documents
- Cannot delete

### 5. **Viewer**
- Read-only access
- Can view documents
- Can view reports
- Cannot upload or modify

## Permission Matrix

| Permission | Admin | Archive Manager | Auditor | User | Viewer |
|-----------|-------|-----------------|---------|------|--------|
| document:create | ✓ | ✓ | ✗ | ✓ | ✗ |
| document:read | ✓ | ✓ | ✓ | ✓ | ✓ |
| document:update | ✓ | ✓ | ✗ | ✓ | ✗ |
| document:delete | ✓ | ✓ | ✗ | ✗ | ✗ |
| document:archive | ✓ | ✓ | ✗ | ✗ | ✗ |
| document:restore | ✓ | ✓ | ✗ | ✗ | ✗ |
| user:create | ✓ | ✗ | ✗ | ✗ | ✗ |
| user:read | ✓ | ✓ | ✓ | ✗ | ✗ |
| user:update | ✓ | ✗ | ✗ | ✗ | ✗ |
| user:delete | ✓ | ✗ | ✗ | ✗ | ✗ |
| user:manage_roles | ✓ | ✗ | ✗ | ✗ | ✗ |
| role:create | ✓ | ✗ | ✗ | ✗ | ✗ |
| role:read | ✓ | ✗ | ✗ | ✗ | ✗ |
| role:update | ✓ | ✗ | ✗ | ✗ | ✗ |
| role:delete | ✓ | ✗ | ✗ | ✗ | ✗ |
| permission:manage | ✓ | ✗ | ✗ | ✗ | ✗ |
| audit:read | ✓ | ✓ | ✓ | ✗ | ✗ |
| report:read | ✓ | ✓ | ✓ | ✓ | ✓ |
| system:config | ✓ | ✗ | ✗ | ✗ | ✗ |
| system:admin | ✓ | ✗ | ✗ | ✗ | ✗ |

## Setting Up User Management

### 1. Enable Authentication

Edit `config.yaml`:
```yaml
auth:
  enabled: true
  jwt_secret_key: "your-secret-key-change-in-production"
  jwt_access_token_expires: 30  # minutes
  jwt_refresh_token_expires: 7  # days
  
audit:
  enabled: true
  log_file: audit.log
  include_request_body: false
  include_response_body: false
```

Or set environment variables:
```bash
export AUTH_ENABLED=true
export JWT_SECRET_KEY="your-secret-key"
export AUDIT_ENABLED=true
```

### 2. Create Initial Admin User

```python
from app.user_management import UserManagementService, UserRole
from app.database import SessionLocal

db = SessionLocal()
user_service = UserManagementService(db)

result = user_service.create_user(
    username="admin",
    email="admin@example.com",
    password="secure-password-123",
    full_name="Administrator",
    role=UserRole.ADMIN
)

print(f"Admin user created: {result}")
```

### 3. Start the Application

```bash
python -m uvicorn app.main:app --reload
```

## API Endpoints

### Authentication

#### Login
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "john.doe",
  "password": "password123"
}
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

#### Refresh Token
```http
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### User Management

#### Create User (Admin only)
```http
POST /api/v1/users
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "username": "jane.smith",
  "email": "jane@example.com",
  "password": "secure-password-123",
  "full_name": "Jane Smith",
  "role": "archive_manager"
}
```

#### Get Users (Admin/Archive Manager)
```http
GET /api/v1/users?skip=0&limit=10
Authorization: Bearer <access_token>
```

#### Get User (Own user or Admin)
```http
GET /api/v1/users/{user_id}
Authorization: Bearer <access_token>
```

#### Update User (Own user or Admin)
```http
PUT /api/v1/users/{user_id}
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "email": "newemail@example.com",
  "full_name": "Updated Name",
  "is_active": true
}
```

#### Assign Role (Admin only)
```http
POST /api/v1/users/{user_id}/role
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "role": "auditor"
}
```

#### Delete User (Admin only)
```http
DELETE /api/v1/users/{user_id}
Authorization: Bearer <access_token>
```

### Audit Trail

#### Get Audit Logs (Admin/Archive Manager/Auditor)
```http
GET /api/v1/audit/logs?user_id=1&event_type=document_upload&limit=100
Authorization: Bearer <access_token>
```

Query Parameters:
- `user_id` - Filter by user ID
- `event_type` - Filter by event type (login, document_upload, user_create, etc.)
- `resource_type` - Filter by resource type (document, user, role)
- `start_date` - Filter by start date (ISO format)
- `end_date` - Filter by end date (ISO format)
- `skip` - Number of results to skip
- `limit` - Maximum number of results

Response:
```json
{
  "success": true,
  "total": 42,
  "logs": [
    {
      "id": 1,
      "event_type": "document_upload",
      "user_id": 1,
      "username": "john.doe",
      "resource_type": "document",
      "resource_id": "abc123xyz",
      "action": "upload",
      "status": "success",
      "ip_address": "192.168.1.1",
      "user_agent": "Mozilla/5.0...",
      "timestamp": "2026-02-21T10:30:00",
      "details": {
        "filename": "report.pdf",
        "size_bytes": 1024,
        "storage_provider": "aws_s3"
      }
    }
  ]
}
```

## Audit Events

### Event Types

#### Authentication Events
- `login` - User login
- `logout` - User logout
- `login_failed` - Failed login attempt
- `token_refresh` - Token refresh

#### Document Operations
- `document_upload` - Document uploaded
- `document_retrieve` - Document retrieved/downloaded
- `document_delete` - Document deleted
- `document_archive` - Document moved to archive tier
- `document_restore` - Document restored from archive

#### User Management
- `user_create` - User created
- `user_update` - User information updated
- `user_delete` - User deleted
- `user_role_assign` - Role assigned to user
- `user_role_revoke` - Role removed from user

#### Role/Permission Management
- `role_create` - Role created
- `role_update` - Role updated
- `role_delete` - Role deleted
- `permission_grant` - Permission granted
- `permission_revoke` - Permission revoked

#### Access Control
- `access_denied` - Access denied due to insufficient permissions
- `unauthorized_access` - Attempted access without authentication

#### System
- `configuration_change` - System configuration changed
- `system_error` - System error occurred
- `encryption_key_access` - Private encryption key accessed

## Working with Authenticated APIs

### Using Tokens in Requests

All protected endpoints require the `Authorization` header with a Bearer token:

```bash
curl -X GET http://localhost:8000/api/v1/users \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Python Example

```python
import requests
import json

# Login
login_response = requests.post(
    "http://localhost:8000/api/v1/auth/login",
    json={"username": "john.doe", "password": "password123"}
)

tokens = login_response.json()
access_token = tokens["access_token"]

# Use token in subsequent requests
headers = {"Authorization": f"Bearer {access_token}"}

# Archive a document
archive_response = requests.post(
    "http://localhost:8000/api/v1/archive",
    headers=headers,
    json={
        "document_base64": "...",
        "filename": "document.pdf",
        "content_type": "application/pdf"
    }
)

print(archive_response.json())
```

## Security Best Practices

### 1. JWT Secret Key
- Use a strong, random secret key in production
- Change the default value before deployment
- Store securely using environment variables or secrets manager
- Never commit to version control

```bash
# Generate a strong secret key
openssl rand -hex 32
```

### 2. Token Expiration
- Set appropriate token expiration times
- Access tokens: 15-30 minutes (short-lived)
- Refresh tokens: 7-30 days (long-lived)
- Users must re-authenticate when refresh token expires

### 3. HTTPS Only
- Always use HTTPS in production
- Enable secure cookie flags
- Use SameSite cookie policy

### 4. Password Requirements
- Minimum 8 characters
- Enforce strong passwords on creation
- Regularly prompt for password changes
- Implement account lockout after failed attempts

### 5. Audit Log Protection
- Store audit logs securely
- Implement log retention policies
- Regularly archive and backup
- Encrypt sensitive audit data

### 6. Role-Based Access Control
- Assign minimum necessary permissions
- Regularly review and update roles
- Remove unused accounts
- Monitor privilege escalation

## Compliance

### HIPAA
- Audit trail logging meets HIPAA requirements
- User authentication and access control
- Account monitoring and reporting

### GDPR
- User data deletion (Right to be Forgotten)
- Audit trail retention policies
- Data access logging

### PCI-DSS
- Strong access control mechanisms
- User role segregation
- Comprehensive audit trail

### SOC 2
- User authentication
- Access control logging
- Audit trail for all access

## Troubleshooting

### Invalid Token
**Error**: `Invalid token: Signature verification failed`

**Solution**:
- Ensure JWT_SECRET_KEY is the same across requests
- Token may have expired - refresh using refresh token
- Check token format (Bearer token)

### Permission Denied
**Error**: `Access denied: Insufficient permissions`

**Solution**:
- Verify user role has required permission
- Check audit logs for access denial events
- Request admin to assign appropriate role

### User Not Found
**Error**: `User not found`

**Solution**:
- Verify username spelling
- Check if user has been deleted
- Ensure user is active (`is_active = true`)

### Token Expired
**Error**: `Token has expired`

**Solution**:
- Use refresh token to get new access token
- Re-authenticate if refresh token also expired
- Check token expiration settings

## Migration Guide

### Existing System Without User Management

1. **Enable authentication in config.yaml**
2. **Run database migrations** to create user and audit tables
3. **Create initial admin user** (see section 2 above)
4. **Update client applications** to use authentication
5. **Gradually assign roles** to existing users
6. **Review audit logs** for security events

## Performance Tuning

### JWT Verification
- Tokens are verified locally (no database lookup)
- Use caching for permission checks
- Consider token blacklist for revocation

### Audit Logging
- Log to file asynchronously
- Implement log rotation
- Archive old logs
- Use batching for database writes

### User Queries
- Index username and email columns
- Cache frequently used user roles
- Use pagination for large result sets

## Advanced Topics

### Custom Roles
Create custom roles with specific permissions:

```python
CUSTOM_ROLE_PERMISSIONS = {
    "senior_auditor": [
        Permission.DOCUMENT_READ.value,
        Permission.AUDIT_READ.value,
        Permission.REPORT_READ.value,
        Permission.USER_READ.value,
        # Add more as needed
    ]
}
```

### OAuth/SSO Integration
Integrate with external identity providers:
- Azure AD
- AWS IAM
- Okta
- Google Workspace

### Multi-Factor Authentication (MFA)
Add MFA for enhanced security:
- TOTP (Time-based One-Time Password)
- SMS verification
- Hardware security keys

## Support

For issues or questions, refer to:
- [Authentication API Reference](#api-endpoints)
- [Audit Events](#audit-events)
- [Security Best Practices](#security-best-practices)

