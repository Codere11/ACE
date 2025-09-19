# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

ACE Real Estate is a comprehensive multi-tenant real estate lead generation and management system. It combines a Python FastAPI backend with multiple Angular frontends, providing chatbot functionality, lead management, and administrative interfaces.

**Technology Stack:**
- Backend: FastAPI (Python 3.x) with SQLAlchemy ORM
- Frontend: Angular 19.x (3 separate applications)
- Database: SQLite (dev) / PostgreSQL (production)
- AI Integration: DeepSeek API for lead qualification
- Authentication: JWT-based

## Common Development Commands

### Backend Development
```bash
# Start the backend server (creates venv if needed)
./run_backend.sh

# Manual backend setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --port 8000 --reload

# Database seeding
python scripts/seed_db.py

# Run backend tests
python -m pytest tests/ -v

# Run specific test
python -m pytest tests/test_auth.py -v
```

### Frontend Development
```bash
# ACE Chatbot (main customer-facing interface)
cd frontend/ACE-Chatbot
npm install
ng serve  # runs on http://localhost:4200

# Manager Dashboard
cd frontend/manager-dashboard  
npm install
ng serve --port 4400  # avoid port conflicts

# Portal (admin interface)
cd portal/portal
npm install
ng serve --port 4500  # avoid port conflicts

# Build for production
ng build --configuration production

# Run frontend tests
ng test

# Generate new components
ng generate component component-name
```

### Development Workflow
```bash
# Start full development environment
./run_backend.sh &  # Backend on :8000
cd frontend/ACE-Chatbot && ng serve --port 4200 &  # Main chatbot
cd frontend/manager-dashboard && ng serve --port 4400 &  # Manager UI
cd portal/portal && ng serve --port 4500 &  # Admin portal
```

## Architecture Overview

### Backend Architecture (`app/`)

**Core Components:**
- `app/main.py` - FastAPI application with all route registrations
- `app/core/` - Configuration, database connection, logging, sessions
- `app/models/` - Pydantic models and SQLAlchemy ORM definitions
- `app/services/` - Business logic layer (flow, leads, chat, AI integration)
- `app/api/` - REST API endpoints organized by domain

**Key Services:**
- **Flow Service** (`services/flow_service.py`) - Manages conversation flow engine with node-based chatbot logic
- **DeepSeek Service** (`services/deepseek_service.py`) - AI integration for lead qualification and scoring
- **Lead Service** (`services/lead_service.py`) - Lead management and scoring logic
- **Chat Store** (`services/chat_store.py`) - Message persistence and session management

**Authentication & Authorization:**
- JWT-based auth in `app/auth/` and `app/portal/routes.py`
- Multi-tenant architecture with role-based access (admin/manager)
- Database-backed users with tenant isolation

**Database Models:**
- `Tenant` - Multi-tenant customer isolation
- `User` - Authentication with role-based permissions  
- `ConversationFlow` - Per-tenant chatbot flow configuration
- `Lead` - Lead data with AI-generated scores and qualification

### Frontend Architecture

**Three Separate Angular Applications:**

1. **ACE-Chatbot** (`frontend/ACE-Chatbot/`) - Customer-facing chatbot interface
2. **Manager Dashboard** (`frontend/manager-dashboard/`) - Lead management UI with charts
3. **Portal** (`portal/portal/`) - Admin interface for tenant management

Each Angular app is independent with its own package.json and can run on different ports.

### Configuration System

**Environment & Flow Configuration:**
- `data/conversation_config.json` - AI prompts, product definition, qualification rules
- `data/conversation_flow.json` - Node-based conversation flow definition
- `app/core/config.py` - Loads and processes configuration with dual-contact enforcement

**Key Environment Variables:**
- `DATABASE_URL` - Database connection (defaults to SQLite)
- `DEEPSEEK_API_KEY` - AI service integration
- `ACE_LOG_LEVEL` - Logging verbosity
- `ACE_SECRET` - JWT secret key
- `ACE_ENFORCE_DUAL_CONTACT` - Enforce contact collection (default: enabled)

### Multi-Tenant System

The system supports multiple real estate agencies (tenants):
- Each tenant has isolated data and conversation flows
- Admin users can manage all tenants
- Manager users are restricted to their tenant
- Static chatbot interfaces served per tenant at `/instances/{slug}/chatbot/`

## Development Patterns

### Adding New API Endpoints
1. Create route in appropriate `app/api/` file
2. Add business logic in `app/services/`
3. Update models in `app/models/` if needed
4. Register router in `app/main.py`

### Modifying Conversation Flow
1. Update `data/conversation_flow.json` for node definitions
2. Modify `app/services/flow_service.py` for flow logic
3. Update `data/conversation_config.json` for AI prompts

### Database Changes
1. Modify SQLAlchemy models in `app/models/orm.py`
2. Update bootstrap in `app/services/bootstrap_db.py`
3. Consider migration strategy for existing data

### Testing Strategy
- Backend tests in `tests/` directory
- Use pytest for Python testing
- Angular tests with Jasmine/Karma per frontend
- Test chat flows with different conversation paths

## Key Integration Points

### AI Integration (DeepSeek)
- Lead qualification happens in `services/deepseek_service.py`
- Prompt templates defined in `conversation_config.json`
- Results update lead scoring and categorization automatically

### Session Management
- Chat sessions stored in `app/core/sessions.py`
- Lead data persistence through `services/lead_service.py`
- Message history in `services/chat_store.py`

### Static File Serving
- Per-tenant chatbot UIs mounted at startup via `mount_instance_chatbots()`
- Frontend builds deployed to tenant-specific directories

## Important Notes

- The system enforces dual-contact collection (email/phone) on first interaction by default
- All conversation flows are node-based with support for choices, open input, and AI actions
- Lead scoring ranges 0-100 with automatic AI qualification
- Multi-tenant isolation is enforced at the database and API level
- CORS is configured for multiple frontend ports in development