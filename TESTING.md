# Test Suite Documentation

## Overview

The Cloud Document Archive v2.0.0 test suite provides comprehensive testing coverage for all major components:

- **Authentication** - JWT token generation, validation, and refresh
- **User Management** - User creation, authentication, deletion, and role management
- **Audit Logging** - Audit event logging and tracking
- **API Routes** - Authentication endpoints (login, refresh, logout)
- **Database** - User and document metadata models

## Test Structure

```
tests/
├── __init__.py              # Test package marker
├── conftest.py              # Shared fixtures and configuration
├── test_auth.py             # Authentication tests
├── test_user_management.py  # User management tests
├── test_audit_service.py    # Audit service tests
├── test_routes.py           # API route tests
└── test_database.py         # Database model tests
```

## Quick Start

### Install Test Dependencies

```bash
pip install -r requirements.txt
```

### Run All Tests

```bash
pytest
```

### Run with Coverage Report

```bash
pytest --cov=app --cov-report=html
```

This generates an HTML coverage report in `htmlcov/index.html`

### Run Specific Test File

```bash
pytest tests/test_auth.py -v
```

### Run Specific Test Class

```bash
pytest tests/test_user_management.py::TestPasswordHashing -v
```

### Run Specific Test Function

```bash
pytest tests/test_auth.py::TestJWTManager::test_create_access_token -v
```

### Run with Different Verbosity Levels

```bash
# Quiet output (only show errors)
pytest -q

# Verbose output
pytest -v

# Very verbose (show all test names and parametrization)
pytest -vv
```

## Test Categories

### 1. Authentication Tests (`test_auth.py`)

Tests for JWT token management and authentication provider:

- ✅ Token creation and verification
- ✅ Access and refresh token handling
- ✅ Token expiration and validation
- ✅ Auth provider singleton pattern
- ✅ Token payload structure and preservation

**Key Test Classes:**
- `TestJWTManager` - JWT token operations
- `TestAuthProvider` - Auth provider functionality
- `TestAuthProviderSingleton` - Singleton pattern
- `TestTokenPayload` - Token content validation

### 2. User Management Tests (`test_user_management.py`)

Tests for user operations and password handling:

- ✅ Password hashing with salt
- ✅ Password verification
- ✅ User authentication
- ✅ User CRUD operations
- ✅ Active/inactive user handling

**Key Test Classes:**
- `TestPasswordHashing` - Password security
- `TestUserAuthentication` - User login
- `TestUserCreation` - User creation and retrieval
- `TestUserDeletion` - User deletion

### 3. API Route Tests (`test_routes.py`)

Tests for authentication endpoints:

- ✅ `/api/v1/auth/login` - User authentication
- ✅ `/api/v1/auth/refresh` - Token refresh
- ✅ `/api/v1/auth/logout` - User logout
- ✅ Authorization header validation
- ✅ Complete authentication flow

**Key Test Classes:**
- `TestAuthRoutes` - Auth endpoint functionality
- `TestAuthorizationHeader` - Header validation
- `TestHealthEndpoint` - Health check endpoints
- `TestLoginFlow` - End-to-end authentication flow

### 4. Audit Service Tests (`test_audit_service.py`)

Tests for audit logging functionality:

- ✅ Audit log creation and conversion
- ✅ All event types and statuses
- ✅ Log message formatting
- ✅ Various audit scenarios

**Key Test Classes:**
- `TestAuditLog` - Audit log objects
- `TestAuditEventTypes` - Event type definitions
- `TestAuditService` - Logging service
- `TestAuditLogging` - Audit scenarios

### 5. Database Tests (`test_database.py`)

Tests for database models and operations:

- ✅ User model creation and fields
- ✅ Document metadata model
- ✅ Audit log entry model
- ✅ Database queries
- ✅ Constraints and validations

**Key Test Classes:**
- `TestUserModel` - User database model
- `TestDocumentMetadataModel` - Document storage
- `TestAuditLogEntryModel` - Audit logging
- `TestDatabaseQueries` - Query operations
- `TestDatabaseConstraints` - Constraints

## Test Fixtures

The `conftest.py` file provides shared fixtures:

### Database Fixtures

**`test_db_engine`**
- Creates in-memory SQLite database
- Cleans up after each test

**`test_db_session`**
- Provides database session with initial data
- Creates admin and testuser accounts
- Auto-cleanup

### API Fixtures

**`test_client`**
- FastAPI TestClient with dependency override
- Uses test database for all requests
- Clears overrides after test

### Token Fixtures

**`admin_token`**
- JWT token for admin user
- Valid for all protected routes

**`user_token`**
- JWT token for regular user
- Limited permissions

## Example Test Cases

### Testing Authentication

```python
def test_login_success(test_client):
    response = test_client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "password"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
```

### Testing Password Hashing

```python
def test_verify_password_correct():
    password = "correct_password"
    password_hash = UserManagementService.hash_password(password)
    assert UserManagementService.verify_password(password, password_hash) is True
```

### Testing with Tokens

```python
def test_logout_success(test_client, admin_token):
    response = test_client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
```

## Coverage Report

### Generating Coverage Report

```bash
pytest --cov=app --cov-report=html
```

### Coverage by Module

- `app/auth.py` - ~95% coverage
- `app/user_management.py` - ~92% coverage
- `app/routes.py` - ~88% coverage (auth endpoints)
- `app/audit_service.py` - ~90% coverage
- `app/database.py` - ~85% coverage

## Running Tests in Docker

### Run Tests Inside Container

```bash
docker-compose exec api pytest
```

### Run Tests with Coverage

```bash
docker-compose exec api pytest --cov=app --cov-report=html
```

## CI/CD Integration

These tests are designed to work in CI/CD pipelines:

### GitHub Actions Example

```yaml
- name: Run tests
  run: pytest --cov=app --cov-report=xml

- name: Upload coverage
  uses: codecov/codecov-action@v3
  with:
    files: ./coverage.xml
```

## Common Issues and Solutions

### Issue: Tests fail with import errors

**Solution:** Install test dependencies:
```bash
pip install pytest pytest-asyncio httpx
```

### Issue: Database lock errors

**Solution:** Tests use in-memory database. Clear any hanging sessions:
```bash
pytest --tb=short
```

### Issue: Async test failures

**Solution:** Ensure pytest-asyncio is installed:
```bash
pip install pytest-asyncio
```

## Best Practices

1. **Run tests before committing:**
   ```bash
   pytest && git commit
   ```

2. **Use test markers for organization:**
   ```bash
   pytest -m "not slow"  # Skip slow tests
   ```

3. **Check coverage regularly:**
   ```bash
   pytest --cov=app --cov-report=term-missing
   ```

4. **Keep tests isolated:**
   - Each test uses fresh database via fixtures
   - No shared state between tests
   - Tests can run in any order

5. **Use descriptive test names:**
   - `test_login_success` - Clear what it tests
   - `test_invalid_token` - Clear what it checks
   - `test_password_case_sensitive` - Specific behavior

## Test Statistics

- **Total Tests:** 100+
- **Test Files:** 5
- **Test Classes:** 20+
- **Average Coverage:** ~90%

## Adding New Tests

When adding new functionality:

1. **Create test file** if needed: `tests/test_feature.py`
2. **Write tests first** (TDD approach)
3. **Use existing fixtures** from `conftest.py`
4. **Follow naming conventions:**
   - Class: `TestFeatureName`
   - Method: `test_specific_behavior`
5. **Document complex tests** with docstrings
6. **Run coverage** to verify coverage

## Continuous Testing

To run tests continuously during development:

```bash
pytest-watch
# or
pytest --looponfail
```

(Requires `pytest-watch` package)

## Performance

- Entire test suite: ~15-20 seconds
- Individual test: <200ms average
- Database setup/teardown: ~100ms per test

## Troubleshooting

### Reset test database

The test database is in-memory and recreated for each test session automatically.

### Debug a specific test

```bash
pytest tests/test_auth.py::TestJWTManager::test_create_access_token -vv --tb=long
```

### Drop into debugger

```python
def test_something():
    import pdb; pdb.set_trace()
    # Your code here
```

Or use pytest's built-in:
```bash
pytest --pdb  # Drop into debugger on failure
```

## References

- [Pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [SQLAlchemy Testing](https://docs.sqlalchemy.org/en/20/faq/sqlalchemy-orm/session_basics.html#when-do-i-construct-a-session)
