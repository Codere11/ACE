# ACE Multi-Tenant SaaS Platform - Operations Guide

This guide documents all operations for managing the ACE platform.

## Table of Contents
- [Getting Started](#getting-started)
- [Authentication](#authentication)
- [Organization Management](#organization-management)
- [User Management](#user-management)
- [Survey Management](#survey-management)
- [Survey Responses](#survey-responses)
- [Database Operations](#database-operations)
- [Deployment](#deployment)

---

## Getting Started

### Start the Backend

```bash
# Using run script (recommended)
./run_backend.sh

# Or manually
cd /home/maksich/Documents/ACE-RealEstate
source venv/bin/activate  # or create: python3 -m venv venv
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Backend will be available at:** `http://localhost:8000`

**API Documentation:** `http://localhost:8000/docs` (Swagger UI)

### Seed Test Data

```bash
# Create test organization with admin and 2 users
python3 scripts/seed_test_org.py
```

**Test credentials:**
- Admin: `admin@test.com` / `test123` (org_admin)
- User 1: `user1@test.com` / `test123` (org_user)
- User 2: `user2@test.com` / `test123` (org_user)

---

## Authentication

### Login

**Endpoint:** `POST /api/auth/login`

**Request:**
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "test123"
  }'
```

**Response:**
```json
{
  "token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": 1,
    "username": "admin",
    "email": "admin@test.com",
    "role": "org_admin",
    "organization_id": 1,
    "organization_slug": "test-company"
  }
}
```

**Save the token for subsequent requests!**

### Get Current User

**Endpoint:** `GET /api/auth/me`

**Request:**
```bash
curl -X GET http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Organization Management

### List Organizations

**Endpoint:** `GET /api/organizations`

**Requires:** `org_admin` role

**Request:**
```bash
curl -X GET http://localhost:8000/api/organizations \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Create Organization

**Endpoint:** `POST /api/organizations`

**Note:** Currently unprotected for initial setup. In production, should require super admin.

**Request:**
```bash
curl -X POST http://localhost:8000/api/organizations \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Company",
    "slug": "my-company",
    "subdomain": "my-company.ace.local",
    "active": true
  }'
```

### Get Organization Details

**Endpoint:** `GET /api/organizations/{org_id}`

**Requires:** `org_admin` role (own organization only)

**Request:**
```bash
curl -X GET http://localhost:8000/api/organizations/1 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Update Organization

**Endpoint:** `PUT /api/organizations/{org_id}`

**Requires:** `org_admin` role (own organization only)

**Request:**
```bash
curl -X PUT http://localhost:8000/api/organizations/1 \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Company Name"
  }'
```

### Delete Organization

**Endpoint:** `DELETE /api/organizations/{org_id}`

**Warning:** Cascades to all users, surveys, and responses!

**Request:**
```bash
curl -X DELETE http://localhost:8000/api/organizations/1
```

---

## User Management

### List Users in Organization

**Endpoint:** `GET /api/organizations/{org_id}/users`

**Requires:** `org_admin` role

**Request:**
```bash
curl -X GET http://localhost:8000/api/organizations/1/users \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Create User

**Endpoint:** `POST /api/organizations/{org_id}/users`

**Requires:** `org_admin` role

**Request:**
```bash
curl -X POST http://localhost:8000/api/organizations/1/users \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser",
    "email": "newuser@company.com",
    "password": "securepass123",
    "role": "org_user",
    "organization_id": 1,
    "is_active": true
  }'
```

**Roles:**
- `org_admin`: Can manage users, surveys, and view responses
- `org_user`: Can only view responses (read-only)

### Update User

**Endpoint:** `PUT /api/organizations/{org_id}/users/{user_id}`

**Requires:** `org_admin` role

**Request:**
```bash
curl -X PUT http://localhost:8000/api/organizations/1/users/2 \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "updated@company.com",
    "role": "org_admin"
  }'
```

**Safety checks:**
- Cannot demote yourself if you're the last admin
- Cannot deactivate your own account

### Delete User

**Endpoint:** `DELETE /api/organizations/{org_id}/users/{user_id}`

**Requires:** `org_admin` role

**Request:**
```bash
curl -X DELETE http://localhost:8000/api/organizations/1/users/2 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Safety checks:**
- Cannot delete yourself
- Cannot delete the last admin

---

## Survey Management

### List Surveys

**Endpoint:** `GET /api/organizations/{org_id}/surveys`

**Requires:** Any authenticated user in the organization

**Query Parameters:**
- `status`: Filter by status (draft, live, archived)
- `skip`: Pagination offset
- `limit`: Pagination limit

**Request:**
```bash
# All surveys
curl -X GET http://localhost:8000/api/organizations/1/surveys \
  -H "Authorization: Bearer YOUR_TOKEN"

# Only live surveys
curl -X GET "http://localhost:8000/api/organizations/1/surveys?status=live" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Create Survey

**Endpoint:** `POST /api/organizations/{org_id}/surveys`

**Requires:** `org_admin` role

**Regular Survey:**
```bash
curl -X POST http://localhost:8000/api/organizations/1/surveys \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Customer Feedback Survey",
    "slug": "customer-feedback",
    "survey_type": "regular",
    "status": "draft",
    "organization_id": 1,
    "flow_json": {
      "nodes": [
        {
          "id": "q1",
          "type": "choice",
          "question": "How satisfied are you?",
          "choices": [
            {"text": "Very satisfied", "score": 100},
            {"text": "Satisfied", "score": 75},
            {"text": "Neutral", "score": 50},
            {"text": "Dissatisfied", "score": 25}
          ]
        }
      ]
    }
  }'
```

**A/B Test Survey:**
```bash
curl -X POST http://localhost:8000/api/organizations/1/surveys \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Headline Test",
    "slug": "headline-test",
    "survey_type": "ab_test",
    "status": "draft",
    "organization_id": 1,
    "variant_a_flow": {
      "nodes": [
        {
          "id": "q1",
          "type": "choice",
          "question": "Option A: Are you interested in our product?"
        }
      ]
    },
    "variant_b_flow": {
      "nodes": [
        {
          "id": "q1",
          "type": "choice",
          "question": "Option B: Would you like to try our solution?"
        }
      ]
    }
  }'
```

### Get Survey Details

**Endpoint:** `GET /api/organizations/{org_id}/surveys/{survey_id}`

**Requires:** Any authenticated user in the organization

**Request:**
```bash
curl -X GET http://localhost:8000/api/organizations/1/surveys/1 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Update Survey

**Endpoint:** `PUT /api/organizations/{org_id}/surveys/{survey_id}`

**Requires:** `org_admin` role

**Note:** Cannot edit flow of a live survey (must archive first)

**Request:**
```bash
curl -X PUT http://localhost:8000/api/organizations/1/surveys/1 \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Survey Name"
  }'
```

### Publish Survey

**Endpoint:** `POST /api/organizations/{org_id}/surveys/{survey_id}/publish`

**Requires:** `org_admin` role

Changes status from `draft` to `live`. Survey must have valid flow.

**Request:**
```bash
curl -X POST http://localhost:8000/api/organizations/1/surveys/1/publish \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Archive Survey

**Endpoint:** `POST /api/organizations/{org_id}/surveys/{survey_id}/archive`

**Requires:** `org_admin` role

Changes status to `archived`. Use this before editing a live survey.

**Request:**
```bash
curl -X POST http://localhost:8000/api/organizations/1/surveys/1/archive \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Get Survey Statistics

**Endpoint:** `GET /api/organizations/{org_id}/surveys/{survey_id}/stats`

**Requires:** Any authenticated user in the organization

**Request:**
```bash
curl -X GET http://localhost:8000/api/organizations/1/surveys/1/stats \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "survey_id": 1,
  "total_responses": 150,
  "completed_responses": 120,
  "avg_score": 72.5,
  "avg_completion_time_minutes": 3.2,
  "variant_a_responses": 75,
  "variant_b_responses": 75,
  "variant_a_avg_score": 70.0,
  "variant_b_avg_score": 75.0
}
```

### Get Survey Responses

**Endpoint:** `GET /api/organizations/{org_id}/surveys/{survey_id}/responses`

**Requires:** Any authenticated user in the organization

**Request:**
```bash
curl -X GET http://localhost:8000/api/organizations/1/surveys/1/responses \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Delete Survey

**Endpoint:** `DELETE /api/organizations/{org_id}/surveys/{survey_id}`

**Requires:** `org_admin` role

**Warning:** Cascades to all survey responses!

**Note:** Cannot delete live surveys (archive first)

**Request:**
```bash
curl -X DELETE http://localhost:8000/api/organizations/1/surveys/1 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Survey Responses

### Public Endpoints (No Authentication Required)

These endpoints are for customers filling out surveys.

#### Get Survey by Slug

**Endpoint:** `GET /s/{survey_slug}`

Returns the survey flow for customers to fill out.

**Request:**
```bash
curl -X GET http://localhost:8000/s/customer-feedback
```

**For A/B tests:** Randomly assigns variant A or B

**Response:**
```json
{
  "survey_id": 1,
  "name": "Customer Feedback Survey",
  "slug": "customer-feedback",
  "survey_type": "regular",
  "variant": null,
  "flow": {
    "nodes": [...]
  }
}
```

#### Get Specific A/B Variant

**Endpoints:**
- `GET /s/{survey_slug}/a` - Get variant A
- `GET /s/{survey_slug}/b` - Get variant B

**Request:**
```bash
curl -X GET http://localhost:8000/s/headline-test/a
```

#### Submit Survey Response

**Endpoint:** `POST /s/{survey_slug}/submit`

**Request:**
```bash
curl -X POST http://localhost:8000/s/customer-feedback/submit \
  -H "Content-Type: application/json" \
  -d '{
    "survey_id": 1,
    "sid": "unique-session-id",
    "variant": null,
    "survey_answers": {
      "q1": {"text": "Very satisfied", "score": 100},
      "q2": {"text": "Yes", "score": 50}
    },
    "name": "John Doe",
    "email": "john@example.com",
    "phone": "+1234567890"
  }'
```

**Automatic Behavior:**
- Calculates score from answers (0-100)
- Determines interest level (Low/Medium/High)
- Updates existing response if SID already exists

#### Complete Survey

**Endpoint:** `POST /s/{survey_slug}/complete?sid={session_id}`

Marks survey as completed (sets `survey_completed_at`).

**Request:**
```bash
curl -X POST "http://localhost:8000/s/customer-feedback/complete?sid=unique-session-id"
```

---

## Database Operations

### Run Database Migration

```bash
# Migrate from old schema to new multi-tenant schema
python3 scripts/migrate_schema_v2.py

# Rollback (if needed)
python3 scripts/migrate_schema_v2.py --rollback
```

### Seed Test Data

```bash
# Create test organization with users
python3 scripts/seed_test_org.py
```

### Direct Database Access

**SQLite (development):**
```bash
# If sqlite3 is installed
sqlite3 ace_dev.db

# Or via Python
python3 -c "
from app.core.db import SessionLocal
from app.models.orm import Organization, User, Survey
db = SessionLocal()
orgs = db.query(Organization).all()
print(f'Organizations: {len(orgs)}')
db.close()
"
```

**PostgreSQL (production):**
```bash
# Connect to database
psql -h localhost -U ace_user -d ace_production

# List tables
\dt

# View users
SELECT username, email, role FROM users;
```

---

## Deployment

### Environment Variables

Create `.env` file:
```bash
# Database
DATABASE_URL=postgresql://ace_user:PASSWORD@localhost:5432/ace_production

# Security
ACE_SECRET=your-super-secret-jwt-key-change-in-production
ACE_JWT_EXPIRE_MIN=1440

# Logging
ACE_LOG_LEVEL=INFO
```

### PostgreSQL Setup

```bash
# 1. Run setup script
bash scripts/setup_postgres.sh

# 2. Migrate data (if from SQLite)
python3 scripts/migrate_to_postgres.py

# 3. Update .env with PostgreSQL connection
DATABASE_URL=postgresql://ace_user:ace_dev_password_change_in_production@localhost:5432/ace_production
```

### Production Deployment Checklist

- [ ] Change `ACE_SECRET` to a strong random key
- [ ] Update database password in `DATABASE_URL`
- [ ] Set `ACE_LOG_LEVEL=WARNING` or `ERROR`
- [ ] Configure CORS for your frontend domain
- [ ] Set up SSL/TLS certificates
- [ ] Configure reverse proxy (nginx/caddy)
- [ ] Set up backup strategy for PostgreSQL
- [ ] Create first organization and admin user
- [ ] Test all endpoints with production credentials

### CORS Configuration

Edit `app/main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://yourdomain.com",
        "https://app.yourdomain.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Subdomain Setup (Future)

**Current:** Path-based URLs
- `/s/{survey-slug}` - Regular survey
- `/s/{survey-slug}/a` - A/B variant A
- `/s/{survey-slug}/b` - A/B variant B

**Future:** Subdomain-based URLs
- `{org-slug}.yourdomain.com/s/{survey-slug}`

Requires:
- Wildcard DNS: `*.yourdomain.com → server IP`
- Wildcard SSL certificate
- Update public survey endpoint to extract org from subdomain

---

## Common Workflows

### 1. Onboard New Organization

```bash
# 1. Create organization
curl -X POST http://localhost:8000/api/organizations \
  -H "Content-Type: application/json" \
  -d '{"name": "New Org", "slug": "new-org", "active": true}'

# 2. Create admin user (org_id from step 1)
curl -X POST http://localhost:8000/api/organizations/{org_id}/users \
  -H "Authorization: Bearer SUPER_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "orgadmin",
    "email": "admin@neworg.com",
    "password": "temp_password",
    "role": "org_admin",
    "organization_id": {org_id}
  }'

# 3. Admin logs in and creates first survey
```

### 2. Create and Launch Survey

```bash
# 1. Login as org admin
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"test123"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")

# 2. Create survey in draft mode
SURVEY_ID=$(curl -s -X POST http://localhost:8000/api/organizations/1/surveys \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{...survey data...}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

# 3. Test survey flow
curl -X GET http://localhost:8000/s/your-survey-slug

# 4. Publish when ready
curl -X POST http://localhost:8000/api/organizations/1/surveys/$SURVEY_ID/publish \
  -H "Authorization: Bearer $TOKEN"

# 5. Share URL with customers
echo "Survey live at: http://yourdomain.com/s/your-survey-slug"
```

### 3. Monitor Survey Performance

```bash
# Get real-time stats
curl -X GET http://localhost:8000/api/organizations/1/surveys/1/stats \
  -H "Authorization: Bearer $TOKEN"

# View all responses
curl -X GET http://localhost:8000/api/organizations/1/surveys/1/responses \
  -H "Authorization: Bearer $TOKEN"

# For A/B tests, compare variant performance in stats
```

---

## Troubleshooting

### Backend Won't Start
```bash
# Check logs
tail -f /tmp/ace_backend.log

# Verify database
python3 -c "from app.core.db import engine; engine.connect()"

# Check port availability
lsof -i :8000
```

### Authentication Fails
```bash
# Verify user exists
python3 -c "
from app.core.db import SessionLocal
from app.models.orm import User
db = SessionLocal()
user = db.query(User).filter(User.username=='admin').first()
print(f'User: {user.username if user else \"Not found\"}')
print(f'Active: {user.is_active if user else \"N/A\"}')
db.close()
"

# Test password hash
python3 -c "
from app.auth.security import verify_password, hash_password
print(verify_password('test123', hash_password('test123')))
"
```

### Survey Not Showing
- Check survey status is `live`
- Verify slug is correct
- Check organization is active
- Review backend logs for errors

---

## Support

For issues or questions:
1. Check backend logs: `/tmp/ace_backend.log`
2. Review this operations guide
3. Check API documentation: `http://localhost:8000/docs`
4. Verify database state with direct queries

**Database Schema Reference:** See `app/models/orm.py`

**API Endpoints Reference:** See `app/api/*.py`
