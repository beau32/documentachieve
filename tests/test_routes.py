"""Tests for API routes."""

import pytest


class TestAuthRoutes:
    """Test authentication API routes."""
    
    def test_login_success(self, test_client):
        """Test successful login returns tokens."""
        response = test_client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "password"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
    
    def test_login_invalid_credentials(self, test_client):
        """Test login with invalid credentials."""
        response = test_client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "wrongpassword"}
        )
        
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
    
    def test_login_nonexistent_user(self, test_client):
        """Test login with nonexistent user."""
        response = test_client.post(
            "/api/v1/auth/login",
            json={"username": "nonexistent", "password": "password"}
        )
        
        assert response.status_code == 401
    
    def test_login_missing_username(self, test_client):
        """Test login without username."""
        response = test_client.post(
            "/api/v1/auth/login",
            json={"password": "password"}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_login_missing_password(self, test_client):
        """Test login without password."""
        response = test_client.post(
            "/api/v1/auth/login",
            json={"username": "admin"}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_refresh_token_success(self, test_client, admin_token):
        """Test successful token refresh."""
        # First get refresh token
        login_response = test_client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "password"}
        )
        refresh_token = login_response.json()["refresh_token"]
        
        # Use refresh token
        response = test_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
    
    def test_refresh_token_invalid(self, test_client):
        """Test refresh with invalid token."""
        response = test_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid.token.here"}
        )
        
        assert response.status_code == 401
    
    def test_logout_success(self, test_client, admin_token):
        """Test successful logout."""
        response = test_client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
    
    def test_logout_missing_token(self, test_client):
        """Test logout without token."""
        response = test_client.post("/api/v1/auth/logout")
        
        assert response.status_code == 401
    
    def test_logout_invalid_token(self, test_client):
        """Test logout with invalid token."""
        response = test_client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": "Bearer invalid.token.here"}
        )
        
        assert response.status_code == 401


class TestAuthorizationHeader:
    """Test Authorization header handling."""
    
    def test_valid_bearer_token(self, test_client, admin_token):
        """Test request with valid Bearer token."""
        response = test_client.get(
            "/health",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        # Health check should work with or without token
        assert response.status_code == 200
    
    def test_missing_bearer_prefix(self, test_client, admin_token):
        """Test request with token but missing Bearer prefix."""
        response = test_client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": admin_token}
        )
        
        assert response.status_code == 401
    
    def test_malformed_authorization_header(self, test_client):
        """Test request with malformed Authorization header."""
        response = test_client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": "InvalidFormat token"}
        )
        
        assert response.status_code == 401


class TestHealthEndpoint:
    """Test health check endpoints."""
    
    def test_root_endpoint(self, test_client):
        """Test root endpoint."""
        response = test_client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
    
    def test_health_endpoint(self, test_client):
        """Test health check endpoint."""
        response = test_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
        assert "application" in data
        assert "version" in data


class TestLoginFlow:
    """Test complete login flow."""
    
    def test_complete_auth_flow(self, test_client):
        """Test complete authentication flow: login -> use token -> refresh -> logout."""
        # Step 1: Login
        login_response = test_client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "testpass123"}
        )
        assert login_response.status_code == 200
        login_data = login_response.json()
        access_token = login_data["access_token"]
        refresh_token = login_data["refresh_token"]
        
        # Step 2: Use token
        response = test_client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert response.status_code == 200
        
        # Step 3: Refresh token
        refresh_response = test_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        assert refresh_response.status_code == 200
        new_access_token = refresh_response.json()["access_token"]
        
        # Step 4: Use new token
        logout_response = test_client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {new_access_token}"}
        )
        assert logout_response.status_code == 200
    
    def test_multiple_logins(self, test_client):
        """Test multiple logins generate different tokens."""
        response1 = test_client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "password"}
        )
        token1 = response1.json()["access_token"]
        
        response2 = test_client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "password"}
        )
        token2 = response2.json()["access_token"]
        
        # Tokens should be different
        assert token1 != token2
        # But both should be valid
        assert token1 != ""
        assert token2 != ""
