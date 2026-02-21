"""Authentication and JWT token handling."""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from enum import Enum

try:
    import jwt
except ImportError:
    jwt = None

logger = logging.getLogger(__name__)


class TokenType(str, Enum):
    """Types of JWT tokens."""
    ACCESS = "access"
    REFRESH = "refresh"


class AuthenticationError(Exception):
    """Authentication error."""
    pass


class TokenError(Exception):
    """Token error."""
    pass


class JWTManager:
    """Manages JWT token creation and validation."""
    
    def __init__(
        self,
        secret_key: str,
        access_token_expires_minutes: int = 30,
        refresh_token_expires_days: int = 7,
        algorithm: str = "HS256",
    ):
        """
        Initialize JWT manager.
        
        Args:
            secret_key: Secret key for signing tokens
            access_token_expires_minutes: Access token expiration in minutes
            refresh_token_expires_days: Refresh token expiration in days
            algorithm: Algorithm to use for signing (HS256, RS256, etc.)
        """
        if not jwt:
            raise ImportError("pyjwt library required for JWT support")
        
        self.secret_key = secret_key
        self.access_token_expires = timedelta(minutes=access_token_expires_minutes)
        self.refresh_token_expires = timedelta(days=refresh_token_expires_days)
        self.algorithm = algorithm
    
    def create_token(
        self,
        data: Dict[str, Any],
        token_type: TokenType = TokenType.ACCESS,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """
        Create a JWT token.
        
        Args:
            data: Data to encode in token
            token_type: Type of token (access or refresh)
            expires_delta: Custom expiration time
            
        Returns:
            JWT token string
        """
        try:
            to_encode = data.copy()
            
            # Set expiration
            if expires_delta:
                expire = datetime.utcnow() + expires_delta
            elif token_type == TokenType.ACCESS:
                expire = datetime.utcnow() + self.access_token_expires
            else:
                expire = datetime.utcnow() + self.refresh_token_expires
            
            to_encode.update({
                "exp": expire,
                "type": token_type.value,
                "iat": datetime.utcnow(),
            })
            
            token = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
            
            logger.debug(f"Created {token_type.value} token for user {data.get('sub')}")
            
            return token
        
        except Exception as e:
            logger.error(f"Failed to create token: {e}")
            raise TokenError(f"Failed to create token: {e}")
    
    def verify_token(self, token: str, token_type: TokenType = TokenType.ACCESS) -> Dict[str, Any]:
        """
        Verify and decode a JWT token.
        
        Args:
            token: JWT token to verify
            token_type: Expected token type
            
        Returns:
            Decoded token data
            
        Raises:
            TokenError: If token is invalid
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check token type
            if payload.get("type") != token_type.value:
                raise TokenError(f"Invalid token type. Expected {token_type.value}")
            
            return payload
        
        except jwt.ExpiredSignatureError:
            raise TokenError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise TokenError(f"Invalid token: {e}")
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            raise TokenError(f"Token verification failed: {e}")
    
    def refresh_token(self, refresh_token: str) -> str:
        """
        Create a new access token from a refresh token.
        
        Args:
            refresh_token: Refresh token
            
        Returns:
            New access token
            
        Raises:
            TokenError: If refresh token is invalid
        """
        try:
            payload = self.verify_token(refresh_token, TokenType.REFRESH)
            
            # Remove old claims that shouldn't be refreshed
            payload.pop("exp", None)
            payload.pop("iat", None)
            
            new_token = self.create_token(payload, TokenType.ACCESS)
            
            logger.info(f"Refreshed token for user {payload.get('sub')}")
            
            return new_token
        
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            raise TokenError(f"Token refresh failed: {e}")


class AuthProvider:
    """Handles authentication operations."""
    
    def __init__(self, jwt_manager: JWTManager):
        """
        Initialize auth provider.
        
        Args:
            jwt_manager: JWT manager instance
        """
        self.jwt = jwt_manager
    
    def create_tokens(self, user_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Create access and refresh tokens for a user.
        
        Args:
            user_data: User data (should include 'id' and 'username')
            
        Returns:
            Dict with access_token and refresh_token
        """
        token_data = {
            "sub": str(user_data["id"]),
            "user_id": str(user_data["id"]),
            "username": user_data["username"],
            "email": user_data.get("email", ""),
            "role": user_data.get("role", "user"),
        }
        
        access_token = self.jwt.create_token(token_data, TokenType.ACCESS)
        refresh_token = self.jwt.create_token(token_data, TokenType.REFRESH)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }
    
    def verify_access_token(self, token: str) -> Dict[str, Any]:
        """
        Verify access token and return user data.
        
        Args:
            token: Access token
            
        Returns:
            User data from token
            
        Raises:
            TokenError: If token is invalid
        """
        return self.jwt.verify_token(token, TokenType.ACCESS)
    
    def refresh_access_token(self, refresh_token: str) -> str:
        """
        Create new access token from refresh token.
        
        Args:
            refresh_token: Refresh token
            
        Returns:
            New access token
        """
        return self.jwt.refresh_token(refresh_token)


# Global JWT manager and auth provider
_jwt_manager: Optional[JWTManager] = None
_auth_provider: Optional[AuthProvider] = None


def get_jwt_manager() -> JWTManager:
    """Get or create the global JWT manager."""
    global _jwt_manager
    
    if _jwt_manager is None:
        from app.config import settings
        
        _jwt_manager = JWTManager(
            secret_key=settings.jwt_secret_key,
            access_token_expires_minutes=settings.jwt_access_token_expires,
            refresh_token_expires_days=settings.jwt_refresh_token_expires,
        )
    
    return _jwt_manager


def get_auth_provider() -> AuthProvider:
    """Get or create the global auth provider."""
    global _auth_provider
    
    if _auth_provider is None:
        jwt_manager = get_jwt_manager()
        _auth_provider = AuthProvider(jwt_manager)
    
    return _auth_provider


def reset_auth():
    """Reset auth services (for testing)."""
    global _jwt_manager, _auth_provider
    _jwt_manager = None
    _auth_provider = None
