"""User management service for handling users, roles, and permissions."""

import hashlib
import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class UserRole(str, Enum):
    """Built-in user roles."""
    ADMIN = "admin"               # Full system access
    ARCHIVE_MANAGER = "archive_manager"  # Can manage documents
    AUDITOR = "auditor"          # Can view audit logs, reports
    USER = "user"                # Can upload/retrieve documents
    VIEWER = "viewer"            # Read-only access


class Permission(str, Enum):
    """Permission types."""
    # Document permissions
    DOCUMENT_CREATE = "document:create"
    DOCUMENT_READ = "document:read"
    DOCUMENT_UPDATE = "document:update"
    DOCUMENT_DELETE = "document:delete"
    DOCUMENT_ARCHIVE = "document:archive"
    DOCUMENT_RESTORE = "document:restore"
    
    # User management permissions
    USER_CREATE = "user:create"
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    USER_MANAGE_ROLES = "user:manage_roles"
    
    # Role/Permission management
    ROLE_CREATE = "role:create"
    ROLE_READ = "role:read"
    ROLE_UPDATE = "role:update"
    ROLE_DELETE = "role:delete"
    PERMISSION_MANAGE = "permission:manage"
    
    # Audit and reporting
    AUDIT_READ = "audit:read"
    REPORT_READ = "report:read"
    
    # System administration
    SYSTEM_CONFIG = "system:config"
    SYSTEM_ADMIN = "system:admin"


# Default role permissions
DEFAULT_ROLE_PERMISSIONS = {
    UserRole.ADMIN: [p.value for p in Permission],  # All permissions
    UserRole.ARCHIVE_MANAGER: [
        Permission.DOCUMENT_CREATE.value,
        Permission.DOCUMENT_READ.value,
        Permission.DOCUMENT_UPDATE.value,
        Permission.DOCUMENT_DELETE.value,
        Permission.DOCUMENT_ARCHIVE.value,
        Permission.DOCUMENT_RESTORE.value,
        Permission.REPORT_READ.value,
        Permission.USER_READ.value,
        Permission.AUDIT_READ.value,
    ],
    UserRole.AUDITOR: [
        Permission.DOCUMENT_READ.value,
        Permission.AUDIT_READ.value,
        Permission.REPORT_READ.value,
        Permission.USER_READ.value,
    ],
    UserRole.USER: [
        Permission.DOCUMENT_CREATE.value,
        Permission.DOCUMENT_READ.value,
        Permission.DOCUMENT_UPDATE.value,
        Permission.REPORT_READ.value,
    ],
    UserRole.VIEWER: [
        Permission.DOCUMENT_READ.value,
        Permission.REPORT_READ.value,
    ],
}


class UserManagementService:
    """Service for managing users, roles, and permissions."""
    
    def __init__(self, db: Session):
        """Initialize user management service."""
        self.db = db
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password using PBKDF2.
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password with salt
        """
        salt = secrets.token_hex(32)
        pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return f"{salt}${pwd_hash.hex()}"
    
    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """
        Verify a password against a hash.
        
        Args:
            password: Plain text password
            hashed: Hashed password from database
            
        Returns:
            True if password matches, False otherwise
        """
        try:
            salt, pwd_hash = hashed.split('$')
            new_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
            return new_hash.hex() == pwd_hash
        except Exception:
            return False
    
    def create_user(
        self,
        username: str,
        email: str,
        password: str,
        full_name: Optional[str] = None,
        role: UserRole = UserRole.USER,
        is_active: bool = True,
    ) -> Dict[str, Any]:
        """
        Create a new user.
        
        Args:
            username: Username (must be unique)
            email: Email address
            password: Password (will be hashed)
            full_name: Full name of user
            role: Initial role
            is_active: Whether user is active
            
        Returns:
            Dict with user info or error
        """
        from app.database import User
        
        # Check if user exists
        existing = self.db.query(User).filter(User.username == username).first()
        if existing:
            return {"success": False, "error": "Username already exists"}
        
        try:
            # Create user
            user = User(
                username=username,
                email=email,
                password_hash=self.hash_password(password),
                full_name=full_name,
                role=role.value,
                is_active=is_active,
                created_at=datetime.utcnow(),
            )
            
            self.db.add(user)
            self.db.commit()
            
            logger.info(f"User created: {username} with role {role}")
            
            return {
                "success": True,
                "user_id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
            }
        
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create user: {e}")
            return {"success": False, "error": str(e)}
    
    def update_user(
        self,
        user_id: int,
        email: Optional[str] = None,
        full_name: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Update user information."""
        from app.database import User
        
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return {"success": False, "error": "User not found"}
            
            if email:
                user.email = email
            if full_name:
                user.full_name = full_name
            if is_active is not None:
                user.is_active = is_active
            
            user.updated_at = datetime.utcnow()
            self.db.commit()
            
            logger.info(f"User updated: {user.username}")
            
            return {"success": True, "message": "User updated"}
        
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update user: {e}")
            return {"success": False, "error": str(e)}
    
    def assign_role(self, user_id: int, role: UserRole) -> Dict[str, Any]:
        """Assign a role to a user."""
        from app.database import User
        
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return {"success": False, "error": "User not found"}
            
            user.role = role.value
            user.updated_at = datetime.utcnow()
            self.db.commit()
            
            logger.info(f"Role assigned to {user.username}: {role}")
            
            return {"success": True, "message": f"Role {role} assigned to {user.username}"}
        
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to assign role: {e}")
            return {"success": False, "error": str(e)}
    
    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        from app.database import User
        
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat(),
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
        }
    
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username."""
        from app.database import User
        
        user = self.db.query(User).filter(User.username == username).first()
        if not user:
            return None
        
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat(),
        }
    
    def list_users(self, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """List all users."""
        from app.database import User
        
        users = self.db.query(User).offset(skip).limit(limit).all()
        
        return [
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role,
                "is_active": user.is_active,
            }
            for user in users
        ]
    
    def delete_user(self, user_id: int) -> Dict[str, Any]:
        """Delete a user."""
        from app.database import User
        
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return {"success": False, "error": "User not found"}
            
            username = user.username
            self.db.delete(user)
            self.db.commit()
            
            logger.info(f"User deleted: {username}")
            
            return {"success": True, "message": f"User {username} deleted"}
        
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete user: {e}")
            return {"success": False, "error": str(e)}
    
    def check_permission(
        self,
        user_id: int,
        permission: Permission,
    ) -> bool:
        """
        Check if user has permission.
        
        Args:
            user_id: User ID
            permission: Permission to check
            
        Returns:
            True if user has permission, False otherwise
        """
        from app.database import User
        
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            return False
        
        # Get role permissions
        role = UserRole(user.role)
        permissions = DEFAULT_ROLE_PERMISSIONS.get(role, [])
        
        # Handle both string and enum permission values
        permission_str = permission.value if hasattr(permission, 'value') else permission
        return permission_str in permissions
    
    def get_user_permissions(self, user_id: int) -> List[str]:
        """Get all permissions for a user."""
        from app.database import User
        
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return []
        
        role = UserRole(user.role)
        return DEFAULT_ROLE_PERMISSIONS.get(role, [])
    
    @staticmethod
    def authenticate_user(db: Session, username: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Authenticate user with username and password.
        
        Args:
            db: Database session
            username: Username
            password: Password
            
        Returns:
            User dict if authenticated, None otherwise
        """
        from app.database import User
        
        user = db.query(User).filter(User.username == username).first()
        if not user or not user.is_active:
            return None
        
        if not UserManagementService.verify_password(password, user.password_hash):
            return None
        
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
        }


# Global instance for singleton pattern
_user_management_service: Optional[UserManagementService] = None


def get_user_management_service() -> UserManagementService:
    """Get or create the global user management service."""
    global _user_management_service
    
    if _user_management_service is None:
        from app.database import SessionLocal
        db = SessionLocal()
        _user_management_service = UserManagementService(db)
    
    return _user_management_service
