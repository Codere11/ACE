# Docker Quick Start

Get ACE Real Estate running in 5 minutes.

## Prerequisites

- Docker and Docker Compose installed
- 2GB+ RAM available
- 10GB+ disk space

## Steps

### 1. Configure Environment

```bash
cd /home/maksich/Documents/ACE-RealEstate
cp .env.example .env
nano .env  # Edit with your values
```

Required variables:
- `POSTGRES_PASSWORD` - Database password
- `DEEPSEEK_API_KEY` - Your DeepSeek API key
- `ACE_SECRET` - JWT secret key

### 2. Run Pre-flight Check

```bash
./test-docker.sh
```

### 3. Start Services

**Development Mode** (recommended for testing):
```bash
docker-compose -f docker-compose.dev.yml up -d
```

**Production Mode** (with Nginx reverse proxy):
```bash
docker-compose up -d
```

### 4. Wait for Services to Start

```bash
# Watch logs
docker-compose logs -f

# Check status
docker-compose ps
```

Wait until you see "Application startup complete" in backend logs.

### 5. Access Applications

**Development Mode:**
- Backend API: http://localhost:8000/docs
- Manager Dashboard: http://localhost:4400
- Chatbot: http://localhost:4200
- Admin Portal: http://localhost:4500

**Production Mode (with Nginx):**
- Homepage: http://localhost
- Manager Dashboard: http://localhost/
- Chatbot: http://localhost/chatbot/
- Admin Portal: http://localhost/admin/
- Backend API: http://localhost/api/

### 6. Initialize with Sample Data (Optional)

```bash
docker exec -it ace-backend-dev python scripts/seed_db.py
```

## Common Commands

```bash
# View logs
docker-compose logs -f backend

# Restart a service
docker-compose restart backend

# Stop everything
docker-compose down

# Stop and remove data
docker-compose down -v

# Rebuild after code changes
docker-compose up -d --build
```

## Troubleshooting

**Backend won't start:**
```bash
docker-compose logs backend
# Usually: wait 30s for database or check .env
```

**Port already in use:**
```bash
# Stop conflicting services or edit docker-compose.yml ports
```

**Build fails:**
```bash
docker-compose build --no-cache
```

## Next Steps

1. Read full guide: `DOCKER_DEPLOYMENT.md`
2. Configure custom domain in `nginx/conf.d/ace.conf`
3. Set up SSL for production
4. Configure backups

## Architecture

```
┌─────────────────────────────────────────┐
│         Nginx Reverse Proxy             │
│            (port 80/443)                │
└────────────┬────────────────────────────┘
             │
    ┌────────┼────────┬──────────┐
    │        │        │          │
    ▼        ▼        ▼          ▼
┌────────┐ ┌────┐ ┌─────┐ ┌──────────┐
│Chatbot │ │Dash│ │Admin│ │ Backend  │
│  :80   │ │:80 │ │ :80 │ │  :8000   │
└────────┘ └────┘ └─────┘ └────┬─────┘
                                │
                                ▼
                         ┌──────────────┐
                         │  PostgreSQL  │
                         │    :5432     │
                         └──────────────┘
```

## Support

For detailed documentation, see `DOCKER_DEPLOYMENT.md`
