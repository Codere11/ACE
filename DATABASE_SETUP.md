# 🗄️ Database Setup Guide

## Quick Start (Local Development)

### 1. Run the Setup Script
```bash
cd /home/maksich/Documents/ACE-RealEstate
./scripts/setup_postgres.sh
```

This will:
- Create PostgreSQL database: `ace_production`
- Create user: `ace_user` with password
- Set up proper permissions

### 2. Configure Environment Variables
```bash
# Copy the example env file
cp .env.example .env

# The script will show you the DATABASE_URL - it should already be in .env.example
# DATABASE_URL=postgresql://ace_user:ace_dev_password_change_in_production@localhost:5432/ace_production
```

### 3. Migrate Existing Data (if you have SQLite data)
```bash
# Activate your venv first
source venv/bin/activate

# Run migration
python scripts/migrate_to_postgres.py
```

### 4. Start the Backend
```bash
./run_backend.sh
```

---

## Production Deployment

### Option 1: Render.com (FREE)
1. Create account on [render.com](https://render.com)
2. Create PostgreSQL database (FREE tier)
3. Copy the **Internal Database URL** from Render
4. Set as `DATABASE_URL` environment variable in your web service

### Option 2: Railway.app
1. Create account on [railway.app](https://railway.app)
2. Create new project → Add PostgreSQL
3. Copy `DATABASE_URL` from Variables tab
4. Add to your backend service environment

### Option 3: DigitalOcean
1. Create Managed PostgreSQL database ($15/mo)
2. Get connection string from dashboard
3. Update firewall to allow your app's IP

---

## Database Schema

Current tables:
- `clients` - Multi-tenant clients
- `conversations` - Chat sessions
- `messages` - Chat messages
- `leads` - Survey responses and lead data
- `events` - Analytics events

---

## Troubleshooting

### "Password authentication failed"
Run the setup script again or manually set the password:
```bash
sudo -u postgres psql
ALTER USER ace_user WITH PASSWORD 'your_new_password';
\q
```

### "Database does not exist"
```bash
sudo -u postgres createdb ace_production
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ace_production TO ace_user;"
```

### "Permission denied"
```bash
sudo -u postgres psql ace_production
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ace_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ace_user;
\q
```

---

## Migration Checklist

- [ ] PostgreSQL installed and running
- [ ] Database and user created
- [ ] `.env` file configured with DATABASE_URL
- [ ] Run `python scripts/migrate_to_postgres.py`
- [ ] Backend starts successfully
- [ ] Can create survey and see responses
- [ ] Old SQLite data migrated (if applicable)
