# 🔐 Authentication & User Management Setup

## Overview

The manager dashboard now has a complete user authentication system with:
- ✅ **Database-backed users** (no more JSON files!)
- ✅ **Secure password hashing** (bcrypt)
- ✅ **JWT token authentication**
- ✅ **Role-based access** (Admin vs Manager)
- ✅ **Session persistence**
- ✅ **Multi-tenant support** (managers tied to specific tenants)

---

## Setup Steps

### 1. Database Setup (if not done yet)
```bash
# Setup PostgreSQL
./scripts/setup_postgres.sh

# Copy environment file
cp .env.example .env

# Migrate to PostgreSQL
source venv/bin/activate
python scripts/migrate_to_postgres.py
```

### 2. Create Initial Users
```bash
# Activate venv
source venv/bin/activate

# Create admin and demo users
python scripts/create_users.py
```

This creates:
- **Admin** user with full access
- **Demo** manager user tied to `demo-agency` tenant

### 3. Test Authentication
```bash
# Start backend
./run_backend.sh

# Test login endpoint
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

You should get back a JWT token:
```json
{
  "token": "eyJ...",
  "user": {
    "id": 1,
    "username": "admin",
    "email": "admin@acesurvey.local",
    "role": "admin",
    "tenant_id": null
  }
}
```

---

## User Roles

### **Admin Role**
- Full system access
- Can see all tenants/clients
- Can create/manage users
- `tenant_id` is `NULL`

### **Manager Role**
- Restricted to specific tenant
- Can only see leads for their tenant
- Cannot create users
- Has `tenant_id` linking them to a Client

---

## API Endpoints

### `POST /api/auth/login`
Login and get JWT token.

**Request:**
```json
{
  "username": "admin",
  "password": "admin123"
}
```

**Response:**
```json
{
  "token": "eyJ...",
  "user": {
    "id": 1,
    "username": "admin",
    "email": "admin@acesurvey.local",
    "role": "admin",
    "tenant_id": null,
    "tenant_slug": null
  }
}
```

### `GET /api/auth/me`
Get current user info from token.

**Headers:**
```
Authorization: Bearer eyJ...
```

**Response:**
```json
{
  "user": {
    "username": "admin",
    "role": "admin",
    "tenant_slug": null
  }
}
```

---

## Frontend Integration (Next Steps)

The manager dashboard needs a login page. Here's what needs to be built:

###1. Login Component
```typescript
// frontend/manager-dashboard/src/app/login/login.component.ts
- Username/password form
- Call POST /api/auth/login
- Store JWT in localStorage
- Redirect to dashboard
```

### 2. Auth Guard
```typescript
// Protect dashboard routes
- Check if JWT exists in localStorage
- Verify token with GET /api/auth/me
- Redirect to login if invalid
```

### 3. HTTP Interceptor
```typescript
// Add Authorization header to all requests
- Read JWT from localStorage
- Add "Authorization: Bearer {token}" header
```

### 4. Logout Function
```typescript
- Clear localStorage
- Redirect to login page
```

---

## Creating New Users

### Option 1: Via Python Script (for now)
```python
from app.core.db import SessionLocal
from app.models.orm import User
from app.auth.security import hash_password

db = SessionLocal()

new_user = User(
    username="john",
    email="john@agency.com",
    hashed_password=hash_password("securePassword123"),
    role="manager",
    tenant_id=1,  # Link to specific client
    is_active=True
)

db.add(new_user)
db.commit()
```

### Option 2: Admin API Endpoint (TODO)
Create `POST /api/admin/users` endpoint for admins to create users via UI.

---

## Security Best Practices

✅ **Implemented:**
- Passwords hashed with bcrypt
- JWT tokens with expiration (24 hours default)
- SQL injection protection (SQLAlchemy ORM)
- Role-based access control

⚠️ **TODO for Production:**
- [ ] Change default passwords!
- [ ] Use strong `ACE_SECRET` environment variable
- [ ] Add rate limiting on login endpoint
- [ ] Add password complexity requirements
- [ ] Add email verification for new users
- [ ] Add password reset functionality
- [ ] Use HTTPS only

---

## Troubleshooting

### "Invalid credentials" error
- Check username/password are correct
- Verify user exists: `SELECT * FROM users WHERE username='admin';`
- Check user is active: `is_active = true`

### Token expired
- JWT tokens expire after 24 hours (default)
- User needs to log in again
- Adjust `ACE_JWT_EXPIRE_MIN` env var if needed

### "Module 'bcrypt' not found"
```bash
pip install bcrypt
```

---

## Database Schema

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    email VARCHAR(160) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'manager',
    tenant_id INTEGER REFERENCES clients(id) ON DELETE SET NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP,
    
    CONSTRAINT chk_users_role CHECK (role IN ('admin', 'manager'))
);
```

---

## Next Steps

1. **Build Login Page** for manager dashboard (Angular component)
2. **Add Auth Guard** to protect dashboard routes
3. **Add Admin Panel** for user management (create/edit/delete users)
4. **Deploy** with proper secret keys

Want me to build the login page for the manager dashboard next?
