# Phase 2 Integration Checklist

Use this checklist to track progress as you integrate the user management and audit services into the FastAPI routes.

## Pre-Integration Setup ✓

- [ ] Read [PHASE2_INTEGRATION_GUIDE.md](PHASE2_INTEGRATION_GUIDE.md) - Complete guide
- [ ] Read [PHASE2_GETTING_STARTED.md](PHASE2_GETTING_STARTED.md) - Getting started
- [ ] Review [USER_MANAGEMENT.md](USER_MANAGEMENT.md) - Complete documentation
- [ ] Verify Phase 2 files exist:
  - [ ] `app/auth.py` exists (226 lines)
  - [ ] `app/user_management.py` exists (312 lines)
  - [ ] `app/audit_service.py` exists (184 lines)
- [ ] Verify Phase 2 database changes in `app/database.py`:
  - [ ] User table exists with proper columns
  - [ ] AuditLogEntry table exists with proper columns
  - [ ] Both tables have indexes
- [ ] Verify Phase 2 config in `app/config.py`:
  - [ ] 8 auth/audit settings exist
  - [ ] Settings are in _flatten_yaml_config mapping
- [ ] Verify Phase 2 models in `app/models.py`:
  - [ ] 11 new Pydantic models added
  - [ ] All models have proper validation
- [ ] Verify `requirements.txt` has `pyjwt>=2.8.0`

## Step 1: Create Middleware ⏳

### Implementation
- [ ] Create file: `app/middleware.py`
- [ ] Copy AuthMiddleware class from [PHASE2_INTEGRATION_GUIDE.md](PHASE2_INTEGRATION_GUIDE.md#step-1-create-middleware)
- [ ] Copy AuditMiddleware class from integration guide
- [ ] Verify imports work correctly
- [ ] Test middleware locally:
  ```bash
  python -c "from app.middleware import AuthMiddleware, AuditMiddleware; print('OK')"
  ```

### Validation
- [ ] AuthMiddleware correctly extracts JWT token
- [ ] AuthMiddleware validates token format
- [ ] AuditMiddleware logs requests to audit.log
- [ ] AuditMiddleware logs to SQLite database
- [ ] Request context is properly propagated

---

## Step 2: Register Middleware in FastAPI ⏳

### Implementation
- [ ] Edit `app/main.py`
- [ ] Import middleware:
  ```python
  from app.middleware import AuthMiddleware, AuditMiddleware
  ```
- [ ] Add middleware to app (order matters):
  ```python
  app.add_middleware(AuditMiddleware)
  app.add_middleware(AuthMiddleware)
  ```
- [ ] Verify no import errors:
  ```bash
  python -c "from app.main import app; print('OK')"
  ```

### Validation
- [ ] Application starts without errors
- [ ] Middleware loads before any routes
- [ ] Request context accessible in routes

---

## Step 3: Create Authentication Routes ⏳

### Implementation
- [ ] Create file: `app/routes/auth.py` (or add to existing routes.py)
- [ ] Copy code from [PHASE2_INTEGRATION_GUIDE.md#step-3-create-authentication-routes](PHASE2_INTEGRATION_GUIDE.md#step-3-create-authentication-routes)
- [ ] Implement endpoints:
  - [ ] `POST /api/v1/auth/login` - User login
  - [ ] `POST /api/v1/auth/refresh` - Token refresh
  - [ ] `POST /api/v1/auth/logout` - Logout

### Testing
- [ ] Create test user:
  ```bash
  python -c "
  from app.user_management import UserManagementService, UserRole
  from app.database import SessionLocal
  db = SessionLocal()
  svc = UserManagementService(db)
  result = svc.create_user('testuser', 'test@example.com', 'password123', UserRole.USER)
  print('User created:', result)
  "
  ```

- [ ] Test login endpoint:
  ```bash
  curl -X POST http://localhost:8000/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username":"testuser","password":"password123"}'
  ```
  - [ ] Returns 200 with access_token
  - [ ] Returns refresh_token
  - [ ] Tokens are valid JWT format

- [ ] Test refresh endpoint:
  ```bash
  curl -X POST http://localhost:8000/api/v1/auth/refresh \
    -H "Content-Type: application/json" \
    -d '{"refresh_token":"YOUR_REFRESH_TOKEN"}'
  ```
  - [ ] Returns new access_token
  - [ ] New token is valid

- [ ] Test invalid credentials:
  ```bash
  curl -X POST http://localhost:8000/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username":"testuser","password":"wrongpassword"}'
  ```
  - [ ] Returns 401 Unauthorized

---

## Step 4: Create User Management Routes ⏳

### Implementation
- [ ] Create file: `app/routes/users.py` (or add to existing)
- [ ] Copy code from [PHASE2_INTEGRATION_GUIDE.md#step-4-create-user-management-routes](PHASE2_INTEGRATION_GUIDE.md#step-4-create-user-management-routes)
- [ ] Implement endpoints:
  - [ ] `POST /api/v1/users` - Create user (admin only)
  - [ ] `GET /api/v1/users` - List users (admin only)
  - [ ] `GET /api/v1/users/{id}` - Get user (admin only)
  - [ ] `POST /api/v1/users/{id}/role` - Assign role (admin only)

### Testing
- [ ] Create admin user:
  ```bash
  python -c "
  from app.user_management import UserManagementService, UserRole
  from app.database import SessionLocal
  db = SessionLocal()
  svc = UserManagementService(db)
  result = svc.create_user('admin', 'admin@example.com', 'admin123', UserRole.ADMIN)
  print('Admin created:', result)
  "
  ```

- [ ] Login as admin:
  ```bash
  curl -X POST http://localhost:8000/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"admin123"}' > token.json
  
  export ADMIN_TOKEN=$(cat token.json | jq -r '.access_token')
  ```

- [ ] Create user via API:
  ```bash
  curl -X POST http://localhost:8000/api/v1/users \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
      "username":"john.doe",
      "email":"john@example.com",
      "password":"password123",
      "role":"user"
    }'
  ```
  - [ ] Returns 201 Created with user_id

- [ ] List users:
  ```bash
  curl -X GET http://localhost:8000/api/v1/users \
    -H "Authorization: Bearer $ADMIN_TOKEN"
  ```
  - [ ] Returns list of users
  - [ ] Non-admin gets 403 Forbidden

- [ ] Assign role:
  ```bash
  curl -X POST http://localhost:8000/api/v1/users/2/role \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"role":"archive_manager"}'
  ```
  - [ ] User role is updated

---

## Step 5: Create Audit Log Routes ⏳

### Implementation
- [ ] Create file: `app/routes/audit.py` (or add to existing)
- [ ] Copy code from [PHASE2_INTEGRATION_GUIDE.md#step-5-create-audit-log-routes](PHASE2_INTEGRATION_GUIDE.md#step-5-create-audit-log-routes)
- [ ] Implement endpoints:
  - [ ] `GET /api/v1/audit/logs` - Query audit logs
  - [ ] Optional: `GET /api/v1/audit/events` - List event types

### Testing
- [ ] Query audit logs:
  ```bash
  curl -X GET "http://localhost:8000/api/v1/audit/logs?limit=10" \
    -H "Authorization: Bearer $ADMIN_TOKEN"
  ```
  - [ ] Returns list of audit entries
  - [ ] Contains login events from authentication

- [ ] Filter by event type:
  ```bash
  curl -X GET "http://localhost:8000/api/v1/audit/logs?event_type=login&limit=10" \
    -H "Authorization: Bearer $ADMIN_TOKEN"
  ```
  - [ ] Returns only login events

- [ ] Filter by date:
  ```bash
  curl -X GET "http://localhost:8000/api/v1/audit/logs?start_date=2026-02-21T00:00:00&end_date=2026-02-21T23:59:59" \
    -H "Authorization: Bearer $ADMIN_TOKEN"
  ```
  - [ ] Returns events from that date

- [ ] Non-auditor cannot access:
  ```bash
  curl -X GET "http://localhost:8000/api/v1/audit/logs" \
    -H "Authorization: Bearer $USER_TOKEN"
  ```
  - [ ] Returns 403 Forbidden

---

## Step 6: Update Existing Routes with Permission Checks ⏳

### Implementation
- [ ] Identify all protected document endpoints
- [ ] Add permission checking dependency from guide:
  ```python
  def check_permission(required_permission: Permission):
      """Dependency to check permission."""
  ```
- [ ] Add to each route:
  - [ ] `POST /archive` - requires DOCUMENT_UPLOAD
  - [ ] `GET /documents/{id}` - requires DOCUMENT_READ
  - [ ] `DELETE /documents/{id}` - requires DOCUMENT_DELETE
  - [ ] etc.

### Testing
- [ ] Non-authenticated fails:
  ```bash
  curl -X POST http://localhost:8000/api/v1/archive \
    -H "Content-Type: application/json" \
    -d '{...}'
  ```
  - [ ] Returns 401 Unauthorized

- [ ] Insufficient permissions fails:
  ```bash
  # User has no DOCUMENT_UPLOAD permission
  curl -X POST http://localhost:8000/api/v1/archive \
    -H "Authorization: Bearer $USER_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{...}'
  ```
  - [ ] Returns 403 Forbidden
  - [ ] Event logged to audit trail as access_denied

- [ ] Proper permissions succeed:
  ```bash
  # Admin has DOCUMENT_UPLOAD permission
  curl -X POST http://localhost:8000/api/v1/archive \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{...}'
  ```
  - [ ] Operation succeeds
  - [ ] Event logged to audit trail as success

---

## Step 7: Register All Routes in FastAPI ⏳

### Implementation
- [ ] Update `app/main.py`:
  ```python
  from app.routes import auth, users, audit, documents
  
  app.include_router(auth.router, prefix="/api/v1", tags=["Auth"])
  app.include_router(users.router, prefix="/api/v1", tags=["Users"])
  app.include_router(audit.router, prefix="/api/v1", tags=["Audit"])
  app.include_router(documents.router, prefix="/api/v1", tags=["Documents"])
  ```

### Validation
- [ ] Application starts without errors
- [ ] Swagger docs show all endpoints at http://localhost:8000/docs
- [ ] All auth endpoints present
- [ ] All user management endpoints present
- [ ] All audit endpoints present

---

## Comprehensive Integration Testing ⏳

### Full Authentication Flow
- [ ] Admin can create users
- [ ] Users can login with username/password
- [ ] Login returns valid JWT tokens
- [ ] Access token works for API calls
- [ ] Refresh token generates new access token
- [ ] Expired token is rejected
- [ ] Invalid token is rejected

### Full Authorization Flow
- [ ] Admin can do everything
- [ ] Archive Manager can manage documents + audit
- [ ] Auditor can only read audit logs
- [ ] User can upload/download documents
- [ ] Viewer can only view
- [ ] Access denied events are logged
- [ ] Permissions are checked correctly

### Full Audit Trail Flow
- [ ] Login events logged
- [ ] Document operations logged
- [ ] User creation/deletion logged
- [ ] Permission denials logged
- [ ] Logs include IP address
- [ ] Logs include User-Agent
- [ ] Logs can be filtered by event type
- [ ] Logs can be filtered by date range
- [ ] Logs can be filtered by user

### Configuration
- [ ] AUTH_ENABLED=true enables authentication
- [ ] AUTH_ENABLED=false disables authentication
- [ ] AUDIT_ENABLED=true logs events
- [ ] AUDIT_ENABLED=false skips logging
- [ ] JWT_SECRET_KEY can be set
- [ ] Token expiration can be configured
- [ ] Audit log file location can be configured

---

## Security Verification ✓

### Before Deployment
- [ ] JWT_SECRET_KEY is strong and secure
- [ ] JWT_SECRET_KEY is NOT in version control
- [ ] HTTPS is enabled on all endpoints
- [ ] Password hashing is verified (PBKDF2)
- [ ] Token expiration times are reasonable
- [ ] Admin credentials are secure
- [ ] Default users are removed except admin
- [ ] Audit logs are being written
- [ ] Sensitive endpoints require authentication
- [ ] Sensitive endpoints check permissions

### Compliance
- [ ] HIPAA: User identity logged, timestamp present
- [ ] GDPR: Data access logged, modifications tracked
- [ ] PCI-DSS: Authentication enforced, access logged
- [ ] SOC 2: Logical access implemented, monitoring active

---

## Performance Testing ⏳

- [ ] No memory leaks in middleware
- [ ] Database queries are fast
- [ ] Token verification is fast < 1ms
- [ ] Audit logging doesn't slow down requests
- [ ] Can handle 100+ concurrent users
- [ ] Can query 1000+ audit logs quickly

### Load Testing
```bash
ab -n 1000 -c 10 -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/users
```

---

## Documentation Updates ✓

- [ ] Update README.md with API endpoints
- [ ] Update deployment guide for JWT setup
- [ ] Update troubleshooting with auth issues
- [ ] Add configuration examples
- [ ] Document custom permissions if added
- [ ] Update API documentation (Swagger)

---

## Deployment Readiness ✓

### Development Environment
- [ ] All tests passing
- [ ] No debug code left
- [ ] No hardcoded secrets
- [ ] Error handling complete
- [ ] Logging comprehensive

### Staging Environment
- [ ] Deploy and run tests
- [ ] Security audit performed
- [ ] Penetration testing completed
- [ ] Performance testing passed
- [ ] Documentation reviewed
- [ ] Team sign-off obtained

### Production Deployment
- [ ] Backup database before deploying
- [ ] Plan rollback procedure
- [ ] Monitor audit logs during deployment
- [ ] Have admin credentials ready
- [ ] Test all endpoints in production
- [ ] Monitor performance metrics
- [ ] Watch error logs for issues

---

## Ongoing Maintenance ⏳

### Weekly
- [ ] Review audit logs for anomalies
- [ ] Check JWT secret key hasn't been exposed
- [ ] Monitor performance metrics

### Monthly
- [ ] Rotate JWT secret key if needed
- [ ] Review and update admin permissions
- [ ] Audit log rotation/archival
- [ ] Database maintenance

### Quarterly
- [ ] Security review
- [ ] Dependency updates (pyjwt, sqlalchemy, etc.)
- [ ] Penetration testing
- [ ] Compliance audit

---

## Sign-Off

**Project Manager**: _________________ Date: _____________

**Lead Developer**: _________________ Date: _____________

**Security Lead**: _________________ Date: _____________

**QA Lead**: _________________ Date: _____________

---

## Notes & Issues

### During Integration
(Record any issues found and resolutions)

| Issue | Resolution | Date |
|-------|-----------|------|
| | | |
| | | |

---

**Integration Checklist Version**: 1.0  
**Last Updated**: 2026-02-21  
**Estimated Time to Complete**: 4-6 hours  
**Status**: Not Started
