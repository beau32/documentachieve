"""
Middleware for authentication, authorization, and audit logging.

Provides:
- AuthMiddleware: JWT token validation and user context injection
- AuditMiddleware: Request/response logging for audit trail
"""

import logging
import json
import time
from typing import Optional, Callable
from datetime import datetime

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response, JSONResponse
from starlette.types import ASGIApp

from app.auth import get_auth_provider
from app.audit_service import get_audit_service, AuditLog, AuditEventType, AuditStatus
from app.user_management import get_user_management_service
from app.config import settings

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware to validate JWT tokens and inject user context into requests.
    
    Validates Authorization header (Bearer token) and makes user info available
    in request.state for downstream handlers.
    
    Skips authentication for:
    - Health check endpoints
    - Login endpoint
    - Swagger/OpenAPI documentation
    """
    
    # Routes that don't require authentication
    EXEMPT_PATHS = {
        "/health",
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/docs",
        "/openapi.json",
        "/redoc",
    }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request to validate JWT tokens.
        
        Args:
            request: The incoming HTTP request
            call_next: The next middleware/handler
            
        Returns:
            The response from the next handler or an error response
        """
        # Skip authentication for exempt paths
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)
        
        # Skip authentication for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # For protected routes, extract and validate token
        if not settings.auth_enabled:
            # Auth disabled, allow all requests
            request.state.user = None
            request.state.user_id = None
            request.state.username = None
            request.state.role = None
            return await call_next(request)
        
        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization", "")
        
        if not auth_header.startswith("Bearer "):
            logger.warning(f"Missing or invalid Authorization header for {request.url.path}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Missing or invalid Authorization header"}
            )
        
        token = auth_header[7:]  # Remove "Bearer " prefix
        
        try:
            # Verify token
            auth_provider = get_auth_provider()
            payload = auth_provider.verify_access_token(token)
            
            user_id = payload.get("user_id")
            username = payload.get("username")
            role = payload.get("role")
            
            if not user_id:
                logger.warning("Invalid token: missing user_id")
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Invalid token"}
                )
            
            # Inject user info into request state
            request.state.user_id = user_id
            request.state.username = username
            request.state.role = role
            request.state.token = token
            
            logger.debug(f"Authenticated user {username} (id={user_id}, role={role})")
        
        except Exception as e:
            logger.warning(f"Token validation failed: {str(e)}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid or expired token"}
            )
        
        # Call next middleware/handler
        response = await call_next(request)
        return response


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all API requests and responses for audit trails.
    
    Captures:
    - HTTP method and endpoint
    - User information (if authenticated)
    - Request/response status codes
    - Client IP address
    - User-Agent
    - Request/response bodies (if configured)
    - Execution time
    
    Automatically determines event type based on endpoint and operation.
    """
    
    # Endpoints that should NOT be audited (too verbose)
    AUDIT_EXEMPT_PATHS = {
        "/health",
        "/docs",
        "/openapi.json",
        "/redoc",
    }
    
    # Map of endpoint patterns to event types
    ENDPOINT_EVENT_TYPES = {
        "/auth/login": AuditEventType.LOGIN,
        "/auth/logout": AuditEventType.LOGOUT,
        "/auth/refresh": AuditEventType.TOKEN_REFRESH,
        "/users": AuditEventType.USER_CREATE,
        "/documents": AuditEventType.DOCUMENT_UPLOAD,
        "/archive": AuditEventType.DOCUMENT_UPLOAD,
        "/retrieve": AuditEventType.DOCUMENT_RETRIEVE,
        "/delete": AuditEventType.DOCUMENT_DELETE,
        "/roles": AuditEventType.ROLE_CREATE,
        "/permissions": AuditEventType.PERMISSION_GRANT,
    }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request to audit it.
        
        Args:
            request: The incoming HTTP request
            call_next: The next middleware/handler
            
        Returns:
            The response from the next handler with audit logging
        """
        # Skip auditing for exempt paths
        if request.url.path in self.AUDIT_EXEMPT_PATHS:
            return await call_next(request)
        
        # Skip OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)
        
        if not settings.audit_enabled:
            return await call_next(request)
        
        # Record start time
        start_time = time.time()
        
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Get User-Agent
        user_agent = request.headers.get("User-Agent", "unknown")
        
        # Get user info (if authenticated)
        user_id = getattr(request.state, "user_id", None)
        username = getattr(request.state, "username", "anonymous")
        
        # Capture request body (if configured and applicable)
        request_body = None
        if settings.audit_include_request_body and request.method in ["POST", "PUT", "PATCH"]:
            try:
                request_body = await request.body()
                # Re-wrap the body so it can be read again by the handler
                async def receive():
                    return {"type": "http.request", "body": request_body}
                request._receive = receive
            except Exception as e:
                logger.debug(f"Could not capture request body: {e}")
        
        # Call next middleware/handler
        try:
            response = await call_next(request)
            http_status = response.status_code
        except Exception as e:
            logger.error(f"Exception during request handling: {e}")
            http_status = status.HTTP_500_INTERNAL_SERVER_ERROR
            raise
        finally:
            # Calculate execution time
            execution_time = time.time() - start_time
            
            # Determine event type
            event_type = self._get_event_type(request.url.path, request.method)
            
            # Determine status
            audit_status = "success" if 200 <= http_status < 300 else "failure"
            if 300 <= http_status < 400:
                audit_status = "partial"
            
            # Log the event
            try:
                audit_service = get_audit_service()
                # Convert string event_type to AuditEventType enum
                try:
                    if isinstance(event_type, str):
                        # Try to match the string to an enum value
                        event_enum = None
                        for evt in AuditEventType:
                            if evt.value == event_type:
                                event_enum = evt
                                break
                        if event_enum:
                            event_type = event_enum
                        else:
                            # Default to a generic event type
                            event_type = AuditEventType.DOCUMENT_UPLOAD
                except:
                    event_type = AuditEventType.DOCUMENT_UPLOAD
                
                # Create AuditLog object
                audit_log = AuditLog(
                    event_type=event_type if isinstance(event_type, AuditEventType) else AuditEventType.DOCUMENT_UPLOAD,
                    user_id=user_id,
                    username=username,
                    resource_type=self._get_resource_type(request.url.path),
                    resource_id=self._get_resource_id(request),
                    action=request.method,
                    status=AuditStatus.SUCCESS if 200 <= http_status < 300 else (AuditStatus.PARTIAL if 300 <= http_status < 400 else AuditStatus.FAILURE),
                    details={
                        "execution_time_ms": round(execution_time * 1000, 2),
                        "query_params": dict(request.query_params),
                        "http_status": http_status,
                        "http_endpoint": str(request.url.path),
                    },
                    ip_address=client_ip,
                    user_agent=user_agent
                )
                # Log without await (it's not async)
                audit_service.log_event(audit_log)
            except Exception as e:
                logger.error(f"Failed to log audit event: {e}")
        
        return response
    
    def _get_event_type(self, endpoint: str, method: str) -> str:
        """
        Determine the event type based on endpoint and HTTP method.
        
        Args:
            endpoint: The API endpoint path
            method: The HTTP method
            
        Returns:
            Event type string
        """
        # Check for direct endpoint matches
        for pattern, event in self.ENDPOINT_EVENT_TYPES.items():
            if pattern in endpoint:
                return event
        
        # Default event types by method
        if method == "POST":
            return AuditEventType.DOCUMENT_UPLOAD
        elif method == "GET":
            return AuditEventType.DOCUMENT_VIEW
        elif method == "PUT" or method == "PATCH":
            return AuditEventType.DOCUMENT_UPLOAD
        elif method == "DELETE":
            return AuditEventType.DOCUMENT_DELETE
        
        return "api_call"
    
    def _get_resource_type(self, endpoint: str) -> str:
        """
        Determine the resource type based on endpoint.
        
        Args:
            endpoint: The API endpoint path
            
        Returns:
            Resource type string
        """
        if "/users" in endpoint:
            return "user"
        elif "/roles" in endpoint:
            return "role"
        elif "/audit" in endpoint:
            return "audit_log"
        elif "/documents" in endpoint or "/archive" in endpoint:
            return "document"
        else:
            return "unknown"
    
    def _get_resource_id(self, request: Request) -> Optional[str]:
        """
        Extract resource ID from request (path parameter or query string).
        
        Args:
            request: The HTTP request
            
        Returns:
            Resource ID or None
        """
        # Try to extract ID from path parameters
        path_parts = request.url.path.split("/")
        for part in path_parts:
            if part.isdigit():
                return part
        
        # Try to get from query parameters
        if "id" in request.query_params:
            return request.query_params["id"]
        
        if "document_id" in request.query_params:
            return request.query_params["document_id"]
        
        if "user_id" in request.query_params:
            return request.query_params["user_id"]
        
        return None


def get_current_user(request: Request) -> dict:
    """
    Helper function to get current authenticated user from request.
    
    Can be used in route handlers via dependency injection.
    
    Args:
        request: The HTTP request
        
    Returns:
        Dictionary with user info (user_id, username, role)
        
    Raises:
        HTTPException: If user is not authenticated
    """
    user_id = getattr(request.state, "user_id", None)
    username = getattr(request.state, "username", None)
    role = getattr(request.state, "role", None)
    
    if not user_id and settings.auth_enabled:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    return {
        "user_id": user_id,
        "username": username,
        "role": role,
    }


def require_role(*roles: str):
    """
    Dependency to require specific roles for a route.
    
    Usage in route:
        @app.get("/admin")
        async def admin_route(request: Request = Depends(require_role("admin"))):
            return {"message": "admin only"}
    
    Args:
        roles: One or more role names required to access the route
        
    Returns:
        Dependency function that validates the user's role
    """
    async def verify_role(request: Request):
        user_role = getattr(request.state, "role", None)
        
        if not user_role and settings.auth_enabled:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated"
            )
        
        if settings.auth_enabled and user_role not in roles:
            logger.warning(f"Access denied: user role '{user_role}' not in {roles}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This operation requires one of: {', '.join(roles)}"
            )
        
        return user_role
    
    return verify_role


def require_permission(permission: str):
    """
    Dependency to require a specific permission for a route.
    
    Usage in route:
        @app.post("/documents")
        async def upload_document(
            request: Request,
            permission: str = Depends(require_permission("document_upload"))
        ):
            return {"message": "document uploaded"}
    
    Args:
        permission: The permission name required
        
    Returns:
        Dependency function that validates the user's permission
    """
    async def verify_permission(request: Request):
        user_id = getattr(request.state, "user_id", None)
        
        if not user_id and settings.auth_enabled:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated"
            )
        
        if settings.auth_enabled:
            user_mgmt = get_user_management_service()
            has_permission = user_mgmt.check_permission(user_id, permission)
            
            if not has_permission:
                logger.warning(f"Access denied: user {user_id} missing permission '{permission}'")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing required permission: {permission}"
                )
        
        return permission
    
    return verify_permission
