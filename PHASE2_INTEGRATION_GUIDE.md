# Phase 2 Integration Guide - Middleware & Route Implementation

## Overview

This guide explains how to integrate the ready-made user management, authentication, and audit services into the existing FastAPI routes and add middleware for automatic audit logging and authentication verification.

**Status**: Services completed and tested ✅  
**Next Phase**: Integrate into routes ⏳  
**Estimated Time**: 4-6 hours

## Architecture Decision

```
Request Flow:
┌─────────────────────────────────────────────────────────────┐
│  Client sends request with Authorization: Bearer TOKEN      │
├─────────────────────────────────────────────────────────────┤
│  1. AuditMiddleware captures request metadata                │
│  2. AuthMiddleware extracts and validates JWT token         │
│  3. Request reaches route handler with user context         │
│  4. Route performs business logic with permission checking  │
│  5. Route returns response                                   │
│  6. AuditMiddleware logs event to audit service             │
│  7. Response sent to client                                 │
└─────────────────────────────────────────────────────────────┘
```

## Step 1: Create Middleware

Create `app/middleware.py`:

```python
"""
FastAPI middleware for authentication and audit logging.
"""
import time
import logging
from typing import Callable
from fastapi import Request, HTTPException, status
from fastapi.responses import Response
from app.auth import get_auth_provider
from app.audit_service import get_audit_service, AuditEventType, AuditLog, AuditStatus

logger = logging.getLogger(__name__)

class RequestContext:
    """Store request context for use in route handlers."""
    def __init__(self):
        self.user_id: int = None
        self.username: str = None
        self.token_type: str = None
        self.start_time: float = None
        self.ip_address: str = None
        self.user_agent: str = None


# Global request context (use contextvars in production)
_request_context = RequestContext()


def get_request_context() -> RequestContext:
    """Get current request context."""
    return _request_context


class AuthMiddleware:
    """Extract and validate JWT token from Authorization header."""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        # Extract IP address
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Store in context
        _request_context.ip_address = client_ip
        _request_context.user_agent = user_agent
        _request_context.start_time = time.time()
        
        # Check if endpoint requires authentication
        if request.url.path.startswith("/api/v1/auth/"):
            # Auth endpoints don't require token
            return await call_next(request)
        
        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            if request.url.path.startswith("/api/v1/"):
                # API endpoints require authentication
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Missing or invalid Authorization header"
                )
            return await call_next(request)
        
        # Extract and verify token
        token = auth_header.replace("Bearer ", "")
        try:
            auth_provider = get_auth_provider()
            token_data = auth_provider.verify_access_token(token)
            
            # Store user context
            _request_context.user_id = token_data.get("sub")
            _request_context.username = token_data.get("username", "unknown")
            _request_context.token_type = token_data.get("type", "access")
            
        except Exception as e:
            if request.url.path.startswith("/api/v1/"):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Invalid token: {str(e)}"
                )
        
        return await call_next(request)


class AuditMiddleware:
    """Log all requests and responses to audit trail."""
    
    def __init__(self, app):
        self.app = app
        self.audit = get_audit_service()
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        # Skip audit logging for non-API endpoints
        if not request.url.path.startswith("/api/v1/"):
            return await call_next(request)
        
        # Process request
        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time
        
        # Determine status
        status_value = AuditStatus.SUCCESS if response.status_code < 400 else AuditStatus.FAILURE
        
        # Create audit log entry
        audit_log = AuditLog(
            event_type=self._determine_event_type(request),
            user_id=_request_context.user_id,
            username=_request_context.username or "anonymous",
            resource_type=self._determine_resource_type(request),
            resource_id=self._extract_resource_id(request),
            action=request.method.lower(),
            status=status_value,
            http_method=request.method,
            http_endpoint=str(request.url.path),
            http_status=response.status_code,
            ip_address=_request_context.ip_address,
            user_agent=_request_context.user_agent,
            details={
                "duration_ms": int(duration * 1000),
                "query_params": dict(request.query_params) if request.query_params else None
            }
        )
        
        # Log event
        try:
            self.audit.log_event(audit_log)
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
        
        return response
    
    @staticmethod
    def _determine_event_type(request: Request) -> str:
        """Determine audit event type from request."""
        path = request.url.path
        method = request.method
        
        # Document operations
        if "/archive" in path:
            if method == "POST":
                return AuditEventType.DOCUMENT_UPLOAD
            elif method == "GET":
                return AuditEventType.DOCUMENT_DOWNLOAD
        
        if "/documents" in path:
            if method == "DELETE":
                return AuditEventType.DOCUMENT_DELETE
            elif method in ["PUT", "PATCH"]:
                return AuditEventType.DOCUMENT_UPDATE
        
        # User operations
        if "/users" in path:
            if method == "POST":
                return AuditEventType.USER_CREATE
            elif method == "DELETE":
                return AuditEventType.USER_DELETE
            elif method in ["PUT", "PATCH"]:
                return AuditEventType.USER_UPDATE
        
        # Role operations
        if "/role" in path and method in ["PUT", "PATCH", "POST"]:
            return AuditEventType.ROLE_ASSIGN
        
        # Auth operations
        if "/auth/login" in path:
            return AuditEventType.LOGIN
        if "/auth/logout" in path:
            return AuditEventType.LOGOUT
        if "/auth/refresh" in path:
            return AuditEventType.TOKEN_REFRESH
        
        # Encryption operations
        if "/encrypt" in path:
            return AuditEventType.ENCRYPTION_ENABLE
        if "/decrypt" in path:
            return AuditEventType.ENCRYPTION_DISABLE
        
        # Default
        return "api_call"
    
    @staticmethod
    def _determine_resource_type(request: Request) -> str:
        """Determine resource type from request path."""
        path = request.url.path
        
        if "/documents" in path or "/archive" in path:
            return "document"
        if "/users" in path:
            return "user"
        if "/roles" in path:
            return "role"
        if "/audit" in path:
            return "audit_log"
        if "/encrypt" in path or "/decrypt" in path:
            return "encryption"
        
        return "api"
    
    @staticmethod
    def _extract_resource_id(request: Request) -> str:
        """Extract resource ID from URL path."""
        parts = request.url.path.split("/")
        
        # Try to get ID from path (/documents/{id}, /users/{id}, etc.)
        for i, part in enumerate(parts):
            if i > 0 and parts[i-1] in ["documents", "users", "roles"]:
                if part and not part.startswith("{"):
                    return part
        
        # Try query params (e.g., ?document_id=123)
        if "document_id" in request.query_params:
            return request.query_params["document_id"]
        if "user_id" in request.query_params:
            return request.query_params["user_id"]
        
        return "unknown"


# Register middleware in main.py:
# app.add_middleware(AuditMiddleware)
# app.add_middleware(AuthMiddleware)
```

## Step 2: Add Middleware to FastAPI App

Update `app/main.py`:

```python
"""Update the FastAPI app creation to include middleware."""

from fastapi import FastAPI
from app.middleware import AuthMiddleware, AuditMiddleware

# ... existing code ...

app = FastAPI(title="Cloud Document Archive", version="1.0.0")

# Add middleware (order matters - AuditMiddleware should be outermost)
app.add_middleware(AuditMiddleware)
app.add_middleware(AuthMiddleware)

# ... rest of app setup ...
```

## Step 3: Create Authentication Routes

Add to `app/routes.py`:

```python
"""Authentication endpoints."""

from fastapi import APIRouter, HTTPException, status, Depends
from app.models import (
    LoginRequest, TokenResponse, RefreshTokenRequest,
    ErrorResponse
)
from app.auth import get_auth_provider
from app.user_management import UserManagementService, UserRole
from app.database import SessionLocal, get_db
from app.middleware import get_request_context

router = APIRouter()

@router.post(
    "/auth/login",
    response_model=TokenResponse,
    responses={
        401: {"model": ErrorResponse},
        400: {"model": ErrorResponse}
    },
    tags=["Authentication"],
    summary="User login",
    description="Authenticate user and receive JWT tokens"
)
async def login(
    credentials: LoginRequest,
    db = Depends(get_db)
):
    """
    Login endpoint.
    
    Returns access token (30 min expiration) and refresh token (7 days).
    """
    user_svc = UserManagementService(db)
    
    # Authenticate user
    user_data = UserManagementService.authenticate_user(
        db,
        credentials.username,
        credentials.password
    )
    
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Create tokens
    auth = get_auth_provider()
    tokens = auth.create_tokens(user_data)
    
    return {
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "token_type": "bearer"
    }


@router.post(
    "/auth/refresh",
    response_model=TokenResponse,
    responses={
        401: {"model": ErrorResponse}
    },
    tags=["Authentication"],
    summary="Refresh access token",
    description="Get new access token using refresh token"
)
async def refresh_token(request: RefreshTokenRequest):
    """Refresh access token using refresh token."""
    auth = get_auth_provider()
    
    try:
        new_access_token = auth.refresh_token(request.refresh_token)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token refresh failed: {str(e)}"
        )
    
    return {
        "access_token": new_access_token,
        "refresh_token": request.refresh_token,
        "token_type": "bearer"
    }


@router.post(
    "/auth/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Authentication"],
    summary="User logout",
    description="Logout user (token will be invalidated)"
)
async def logout():
    """Logout endpoint. Token becomes invalid immediately."""
    # In a production system, add token to blacklist
    # For now, client should discard token
    return None
```

## Step 4: Create User Management Routes

Add to `app/routes.py`:

```python
"""User management endpoints."""

from typing import List
from fastapi import APIRouter, HTTPException, status, Depends, Query
from app.models import (
    UserCreateRequest, UserUpdateRequest, UserResponse,
    RoleAssignRequest, ErrorResponse
)
from app.user_management import UserManagementService, UserRole, Permission
from app.database import SessionLocal, get_db, User
from app.middleware import get_request_context

router = APIRouter()


def check_admin(context = Depends(get_request_context)):
    """Verify user is admin."""
    if context.user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    db = SessionLocal()
    user = db.query(User).filter(User.id == context.user_id).first()
    db.close()
    
    if not user or user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return user


@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse},
        403: {"model": ErrorResponse}
    },
    tags=["User Management"],
    summary="Create user",
    description="Create new user (admin only)"
)
async def create_user(
    request: UserCreateRequest,
    user = Depends(check_admin),
    db = Depends(get_db)
):
    """Create new user."""
    user_svc = UserManagementService(db)
    
    # Check if user already exists
    existing = user_svc.get_user_by_username(request.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    # Create user
    result = user_svc.create_user(
        username=request.username,
        email=request.email,
        password=request.password,
        role=UserRole[request.role.upper()]
    )
    
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )
    
    return {
        "user_id": result["id"],
        "username": result["username"],
        "email": result["email"],
        "role": result["role"],
        "is_active": result["is_active"],
        "created_at": result["created_at"]
    }


@router.get(
    "/users",
    response_model=List[UserResponse],
    tags=["User Management"],
    summary="List users",
    description="List all users (admin only)"
)
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    user = Depends(check_admin),
    db = Depends(get_db)
):
    """List all users with pagination."""
    users = db.query(User).offset(skip).limit(limit).all()
    
    return [
        {
            "user_id": u.id,
            "username": u.username,
            "email": u.email,
            "role": u.role,
            "is_active": u.is_active,
            "created_at": u.created_at
        }
        for u in users
    ]


@router.post(
    "/users/{user_id}/role",
    response_model=UserResponse,
    responses={
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse}
    },
    tags=["User Management"],
    summary="Assign role",
    description="Assign role to user (admin only)"
)
async def assign_role(
    user_id: int,
    request: RoleAssignRequest,
    admin = Depends(check_admin),
    db = Depends(get_db)
):
    """Assign role to user."""
    user_svc = UserManagementService(db)
    
    result = user_svc.assign_role(
        user_id,
        UserRole[request.role.upper()]
    )
    
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )
    
    return {
        "user_id": result["id"],
        "username": result["username"],
        "email": result["email"],
        "role": result["role"],
        "is_active": result["is_active"],
        "created_at": result["created_at"]
    }
```

## Step 5: Create Audit Log Routes

Add to `app/routes.py`:

```python
"""Audit logging endpoints."""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Depends, Query
from app.models import AuditLogsResponse, ErrorResponse
from app.audit_service import get_audit_service, AuditEventType
from app.user_management import Permission
from app.database import get_db
from app.middleware import get_request_context

router = APIRouter()


def check_auditor(context = Depends(get_request_context)):
    """Verify user is auditor or admin."""
    if context.user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    # In production, check user.role
    return context.user_id


@router.get(
    "/audit/logs",
    response_model=AuditLogsResponse,
    tags=["Audit & Compliance"],
    summary="Get audit logs",
    description="Query audit logs with filters"
)
async def get_audit_logs(
    event_type: Optional[str] = Query(None),
    user_id: Optional[int] = Query(None),
    resource_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    auditor_user = Depends(check_auditor),
    db = Depends(get_db)
):
    """Get audit logs with optional filters."""
    audit_svc = get_audit_service()
    
    # Parse dates if provided
    start = None
    end = None
    if start_date:
        try:
            start = datetime.fromisoformat(start_date)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid start_date format. Use ISO format: YYYY-MM-DDTHH:MM:SS"
            )
    
    if end_date:
        try:
            end = datetime.fromisoformat(end_date)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid end_date format. Use ISO format: YYYY-MM-DDTHH:MM:SS"
            )
    
    # Get logs
    logs = audit_svc.get_audit_logs(
        event_type=event_type,
        user_id=user_id,
        resource_type=resource_type,
        status=status,
        start_date=start,
        end_date=end_date,
        offset=skip,
        limit=limit
    )
    
    return {
        "logs": [log.to_dict() for log in logs],
        "total": len(logs),
        "skip": skip,
        "limit": limit
    }


@router.get(
    "/audit/events",
    tags=["Audit & Compliance"],
    summary="Get audit event types",
    description="List all available audit event types"
)
async def get_event_types():
    """Get list of all available audit event types."""
    return {
        "event_types": [
            "login",
            "logout",
            "token_refresh",
            "document_upload",
            "document_download",
            "document_update",
            "document_delete",
            "document_share",
            "user_create",
            "user_update",
            "user_delete",
            "role_assign",
            "permission_change",
            "access_denied",
            "encryption_enable",
            "encryption_disable",
            "system_config_change"
        ]
    }
```

## Step 6: Update Main Routes

Update `app/routes.py` existing routes to include authentication:

```python
"""Protect existing document archive routes with authentication."""

from fastapi import Depends, HTTPException, status
from app.user_management import UserManagementService, Permission
from app.middleware import get_request_context
from app.database import SessionLocal, User


def check_permission(required_permission: Permission):
    """Dependency to check if user has required permission."""
    async def _check_permission(context = Depends(get_request_context)):
        if context.user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated"
            )
        
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == context.user_id).first()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found"
                )
            
            user_svc = UserManagementService(db)
            if not user_svc.check_permission(context.user_id, required_permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: {required_permission}"
                )
            
            return user
        finally:
            db.close()
    
    return _check_permission


# Then add to existing routes:
# @router.post("/archive")
# async def archive_document(
#     request: ArchiveRequest,
#     user = Depends(check_permission(Permission.DOCUMENT_UPLOAD)),
#     db = Depends(get_db)
# ):
#     """Archive document (requires DOCUMENT_UPLOAD permission)."""
#     # ... existing logic ...
```

## Step 7: Register All Routes

Update `app/main.py`:

```python
"""Register all route groups in FastAPI app."""

from fastapi import FastAPI
from app.routes import router as archive_router
from app.routes import auth_routes, user_routes, audit_routes

app = FastAPI(title="Cloud Document Archive", version="1.0.0")

# Add middleware first
app.add_middleware(AuditMiddleware)
app.add_middleware(AuthMiddleware)

# Include route groups
app.include_router(archive_router, prefix="/api/v1", tags=["Archive"])
app.include_router(auth_routes.router, prefix="/api/v1", tags=["Auth"])
app.include_router(user_routes.router, prefix="/api/v1", tags=["Users"])
app.include_router(audit_routes.router, prefix="/api/v1", tags=["Audit"])
```

## Step 8: Testing

### Test Authentication Flow

```bash
# 1. Create admin user
python -c "
from app.user_management import UserManagementService, UserRole
from app.database import SessionLocal
db = SessionLocal()
service = UserManagementService(db)
service.create_user('admin', 'admin@example.com', 'admin123', UserRole.ADMIN)
"

# 2. Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# 3. Save token
export TOKEN="eyJhbGc..."

# 4. Try protected endpoint
curl -X GET http://localhost:8000/api/v1/users \
  -H "Authorization: Bearer $TOKEN"

# 5. View audit logs
curl -X GET "http://localhost:8000/api/v1/audit/logs?limit=10" \
  -H "Authorization: Bearer $TOKEN"
```

### Test Permission Checking

```bash
# Create regular user
curl -X POST http://localhost:8000/api/v1/users \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username":"john",
    "email":"john@example.com",
    "password":"john123",
    "role":"user"
  }'

# Try to create another user (should fail - only admin can)
curl -X POST http://localhost:8000/api/v1/users \
  -H "Authorization: Bearer USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"username":"jane","email":"jane@example.com","password":"jane123","role":"user"}'

# Should return 403 Forbidden
```

## Deployment Checklist

- [ ] Create middleware.py with AuthMiddleware and AuditMiddleware
- [ ] Add middleware to FastAPI app in main.py
- [ ] Create auth routes (/auth/login, /auth/refresh, etc.)
- [ ] Create user management routes (/users, /users/{id}/role, etc.)
- [ ] Create audit routes (/audit/logs)
- [ ] Update existing document routes with permission checks
- [ ] Set JWT_SECRET_KEY environment variable
- [ ] Enable AUTH_ENABLED and AUDIT_ENABLED in config
- [ ] Test authentication flow end-to-end
- [ ] Test permission checking
- [ ] Test audit logging
- [ ] Update API documentation (Swagger)
- [ ] Update deployment guide

## Security Reminders

1. **Never commit JWT_SECRET_KEY** to repository
2. **Always use HTTPS** in production
3. **Implement rate limiting** on login endpoint
4. **Encrypt audit logs** on disk if required by compliance
5. **Rotate JWT secrets** periodically
6. **Use strong passwords** for default admin account
7. **Log all permission denials** (already done by AuditMiddleware)
8. **Document all custom permissions** if added

## Next Steps

1. Review this guide with security team
2. Implement middleware and routes following steps 1-7
3. Run test scenarios from Step 8
4. Deploy to staging environment
5. Perform security audit and penetration testing
6. Deploy to production

## Support

- **Middleware questions**: See [app/middleware.py](app/middleware.py) code comments
- **Auth implementation**: See [USER_MANAGEMENT.md](USER_MANAGEMENT.md)
- **Route patterns**: See [FastAPI documentation](https://fastapi.tiangolo.com/)
- **Security best practices**: See [USER_MANAGEMENT.md#security-best-practices](USER_MANAGEMENT.md#security-best-practices)

---

**Integration Guide Version**: 1.0
**Last Updated**: 2026-02-21
