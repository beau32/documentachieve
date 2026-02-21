"""Tests for JWT authentication functionality."""

import pytest
from datetime import datetime, timedelta
from app.auth import get_auth_provider, reset_auth_provider, JWTManager, AuthProvider
from app.config import settings


class TestJWTManager:
    """Test JWT token management."""
    
    def test_create_access_token(self):
        """Test creating access token."""
        jwt_manager = JWTManager()
        
        user_data = {"user_id": 1, "username": "testuser", "role": "user"}
        token = jwt_manager.create_token(user_data, token_type="access")
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_verify_valid_token(self):
        """Test verifying valid token."""
        jwt_manager = JWTManager()
        
        user_data = {"user_id": 1, "username": "testuser", "role": "user"}
        token = jwt_manager.create_token(user_data, token_type="access")
        
        payload = jwt_manager.verify_token(token, token_type="access")
        
        assert payload is not None
        assert payload["user_id"] == 1
        assert payload["username"] == "testuser"
        assert payload["role"] == "user"
    
    def test_verify_invalid_token(self):
        """Test verifying invalid token fails."""
        jwt_manager = JWTManager()
        
        invalid_token = "invalid.token.here"
        
        with pytest.raises(Exception):
            jwt_manager.verify_token(invalid_token, token_type="access")
    
    def test_verify_wrong_token_type(self):
        """Test verifying token with wrong type fails."""
        jwt_manager = JWTManager()
        
        user_data = {"user_id": 1, "username": "testuser"}
        token = jwt_manager.create_token(user_data, token_type="access")
        
        # Try to verify as refresh token
        with pytest.raises(Exception):
            jwt_manager.verify_token(token, token_type="refresh")
    
    def test_create_refresh_token(self):
        """Test creating refresh token."""
        jwt_manager = JWTManager()
        
        user_data = {"user_id": 1, "username": "testuser"}
        token = jwt_manager.create_token(user_data, token_type="refresh")
        
        assert token is not None
        assert isinstance(token, str)
    
    def test_token_expiration(self):
        """Test token expiration."""
        jwt_manager = JWTManager()
        
        user_data = {"user_id": 1, "username": "testuser"}
        # Create token with very short expiration
        token = jwt_manager.create_token(user_data, token_type="access")
        
        # Token should be valid immediately
        payload = jwt_manager.verify_token(token, token_type="access")
        assert payload is not None


class TestAuthProvider:
    """Test auth provider."""
    
    def test_create_tokens(self):
        """Test creating both access and refresh tokens."""
        auth_provider = AuthProvider(JWTManager())
        
        user_data = {"id": 1, "username": "testuser", "role": "user"}
        tokens = auth_provider.create_tokens(user_data)
        
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert tokens["access_token"] is not None
        assert tokens["refresh_token"] is not None
    
    def test_verify_access_token(self):
        """Test verifying access token."""
        auth_provider = AuthProvider(JWTManager())
        
        user_data = {"id": 1, "username": "testuser", "role": "user"}
        tokens = auth_provider.create_tokens(user_data)
        
        payload = auth_provider.verify_access_token(tokens["access_token"])
        
        assert payload is not None
        assert payload["user_id"] == 1
        assert payload["username"] == "testuser"
    
    def test_refresh_access_token(self):
        """Test refreshing access token."""
        auth_provider = AuthProvider(JWTManager())
        
        user_data = {"id": 1, "username": "testuser", "role": "user"}
        tokens = auth_provider.create_tokens(user_data)
        
        new_tokens = auth_provider.refresh_access_token(tokens["refresh_token"])
        
        assert new_tokens is not None
        assert "access_token" in new_tokens
        assert "refresh_token" in new_tokens
        assert new_tokens["access_token"] != tokens["access_token"]
    
    def test_refresh_with_invalid_token(self):
        """Test refreshing with invalid token."""
        auth_provider = AuthProvider(JWTManager())
        
        result = auth_provider.refresh_access_token("invalid.token.here")
        
        assert result is None


class TestAuthProviderSingleton:
    """Test auth provider singleton pattern."""
    
    def test_get_auth_provider_singleton(self):
        """Test getting auth provider returns same instance."""
        reset_auth_provider()
        
        provider1 = get_auth_provider()
        provider2 = get_auth_provider()
        
        assert provider1 is provider2
    
    def test_reset_auth_provider(self):
        """Test resetting auth provider."""
        reset_auth_provider()
        
        provider1 = get_auth_provider()
        reset_auth_provider()
        provider2 = get_auth_provider()
        
        # Should be different instances after reset
        assert provider1 is not provider2


class TestTokenPayload:
    """Test token payload structure."""
    
    def test_token_contains_required_fields(self):
        """Test token contains all required fields."""
        auth_provider = AuthProvider(JWTManager())
        
        user_data = {"id": 123, "username": "testuser", "role": "admin"}
        tokens = auth_provider.create_tokens(user_data)
        
        payload = auth_provider.verify_access_token(tokens["access_token"])
        
        assert "user_id" in payload
        assert "username" in payload
        assert "role" in payload
        assert "exp" in payload  # expiration time
        assert payload["user_id"] == 123
    
    def test_token_payload_preservation(self):
        """Test user data is preserved in token."""
        auth_provider = AuthProvider(JWTManager())
        
        user_data = {
            "id": 42,
            "username": "johndoe",
            "role": "archive_manager",
            "email": "john@example.com"
        }
        tokens = auth_provider.create_tokens(user_data)
        
        payload = auth_provider.verify_access_token(tokens["access_token"])
        
        assert payload["user_id"] == 42
        assert payload["username"] == "johndoe"
        assert payload["role"] == "archive_manager"
