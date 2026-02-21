"""Shared test fixtures and configuration."""

import pytest
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import app
from app.user_management import UserManagementService


# Create in-memory SQLite database for testing
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def test_db_engine():
    """Create a test database engine."""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def test_db_session(test_db_engine):
    """Create a test database session."""
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_db_engine
    )
    
    session = TestingSessionLocal()
    
    # Create default admin user for testing
    from app.database import User
    admin_user = User(
        username="admin",
        email="admin@example.com",
        full_name="Test Admin",
        password_hash=UserManagementService.hash_password("password"),
        role="admin",
        is_active=True
    )
    session.add(admin_user)
    
    # Create test user
    test_user = User(
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        password_hash=UserManagementService.hash_password("testpass123"),
        role="user",
        is_active=True
    )
    session.add(test_user)
    
    session.commit()
    
    yield session
    
    session.close()


@pytest.fixture(scope="function")
def test_client(test_db_session):
    """Create a test client with dependency override."""
    def override_get_db():
        try:
            yield test_db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    client = TestClient(app)
    yield client
    
    app.dependency_overrides.clear()


@pytest.fixture
def admin_token(test_client):
    """Get JWT token for admin user."""
    response = test_client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "password"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def user_token(test_client):
    """Get JWT token for test user."""
    response = test_client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "testpass123"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]
