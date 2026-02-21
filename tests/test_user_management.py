"""Tests for user management functionality."""

import pytest
from app.user_management import UserManagementService
from app.database import User


class TestPasswordHashing:
    """Test password hashing and verification."""
    
    def test_hash_password(self):
        """Test password hashing creates different hashes."""
        password = "test_password_123"
        hash1 = UserManagementService.hash_password(password)
        hash2 = UserManagementService.hash_password(password)
        
        # Should create different hashes due to salt
        assert hash1 != hash2
        assert len(hash1) > 0
        assert len(hash2) > 0
    
    def test_verify_password_correct(self):
        """Test password verification succeeds with correct password."""
        password = "correct_password"
        password_hash = UserManagementService.hash_password(password)
        
        assert UserManagementService.verify_password(password, password_hash) is True
    
    def test_verify_password_incorrect(self):
        """Test password verification fails with incorrect password."""
        correct_password = "correct_password"
        wrong_password = "wrong_password"
        password_hash = UserManagementService.hash_password(correct_password)
        
        assert UserManagementService.verify_password(wrong_password, password_hash) is False
    
    def test_verify_password_case_sensitive(self):
        """Test password verification is case sensitive."""
        password = "MyPassword"
        password_hash = UserManagementService.hash_password(password)
        
        assert UserManagementService.verify_password("mypassword", password_hash) is False
        assert UserManagementService.verify_password("MYPASSWORD", password_hash) is False
        assert UserManagementService.verify_password("MyPassword", password_hash) is True


class TestUserAuthentication:
    """Test user authentication."""
    
    def test_authenticate_user_success(self, test_db_session):
        """Test successful user authentication."""
        result = UserManagementService.authenticate_user(
            test_db_session,
            "admin",
            "password"
        )
        
        assert result is not None
        assert result["username"] == "admin"
        assert result["email"] == "admin@example.com"
        assert result["role"] == "admin"
        assert "id" in result
    
    def test_authenticate_user_wrong_password(self, test_db_session):
        """Test authentication fails with wrong password."""
        result = UserManagementService.authenticate_user(
            test_db_session,
            "admin",
            "wrong_password"
        )
        
        assert result is None
    
    def test_authenticate_user_nonexistent(self, test_db_session):
        """Test authentication fails for nonexistent user."""
        result = UserManagementService.authenticate_user(
            test_db_session,
            "nonexistent",
            "password"
        )
        
        assert result is None
    
    def test_authenticate_inactive_user(self, test_db_session):
        """Test authentication fails for inactive users."""
        # Create inactive user
        inactive_user = User(
            username="inactive",
            email="inactive@example.com",
            full_name="Inactive User",
            password_hash=UserManagementService.hash_password("password"),
            role="user",
            is_active=False
        )
        test_db_session.add(inactive_user)
        test_db_session.commit()
        
        result = UserManagementService.authenticate_user(
            test_db_session,
            "inactive",
            "password"
        )
        
        assert result is None


class TestUserCreation:
    """Test user creation and retrieval."""
    
    def test_get_all_users(self, test_db_session):
        """Test getting all users."""
        service = UserManagementService(test_db_session)
        users = service.get_all_users()
        
        assert len(users) >= 2  # admin and testuser
        usernames = [u.username for u in users]
        assert "admin" in usernames
        assert "testuser" in usernames
    
    def test_get_user_by_id(self, test_db_session):
        """Test getting user by ID."""
        service = UserManagementService(test_db_session)
        user = service.get_user_by_id(1)
        
        assert user is not None
        assert user.username == "admin"
    
    def test_get_user_by_username(self, test_db_session):
        """Test getting user by username."""
        service = UserManagementService(test_db_session)
        user = service.get_user_by_username("testuser")
        
        assert user is not None
        assert user.email == "test@example.com"
    
    def test_create_user(self, test_db_session):
        """Test creating a new user."""
        service = UserManagementService(test_db_session)
        
        user = service.create_user(
            username="newuser",
            email="new@example.com",
            full_name="New User",
            password="newpass123",
            role="user"
        )
        
        assert user is not None
        assert user.username == "newuser"
        assert user.email == "new@example.com"
        assert user.role == "user"
        
        # Verify it can be retrieved
        retrieved = service.get_user_by_username("newuser")
        assert retrieved is not None
        assert retrieved.id == user.id
    
    def test_create_duplicate_user(self, test_db_session):
        """Test creating duplicate user fails."""
        service = UserManagementService(test_db_session)
        
        # Try to create user with existing username
        result = service.create_user(
            username="admin",
            email="duplicate@example.com",
            full_name="Duplicate",
            password="password",
            role="user"
        )
        
        assert result is None


class TestUserDeletion:
    """Test user deletion."""
    
    def test_delete_user(self, test_db_session):
        """Test deleting a user."""
        service = UserManagementService(test_db_session)
        
        # Create a user to delete
        user = service.create_user(
            username="todelete",
            email="delete@example.com",
            full_name="To Delete",
            password="password",
            role="user"
        )
        user_id = user.id
        
        # Delete the user
        result = service.delete_user(user_id)
        assert result is True
        
        # Verify it's deleted
        deleted_user = service.get_user_by_id(user_id)
        assert deleted_user is None
    
    def test_delete_nonexistent_user(self, test_db_session):
        """Test deleting nonexistent user."""
        service = UserManagementService(test_db_session)
        
        result = service.delete_user(9999)
        assert result is False
