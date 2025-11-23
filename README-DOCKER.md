# ACE Real Estate - Docker Deployment

Complete Docker setup for the ACE Real Estate multi-tenant SaaS platform.

## 📦 What's Included

- **Backend**: FastAPI Python application (Port 8000)
- **Frontend - Manager Dashboard**: Angular app for lead management (Port 4400)
- **Frontend - Chatbot**: Customer-facing survey interface (Port 4200)
- **Frontend - Portal**: Admin interface for multi-tenant management (Port 4500)
- **Database**: PostgreSQL 15 (Port 5432)
- **Reverse Proxy**: Nginx for production routing (Port 80/443)

## 🚀 Quick Start

### 1. Prerequisites

```bash
# Verify installations
docker --version          # Should be 20.10+
docker compose version    # Should be 2.0+
```

### 2. Setup Environment

```bash
cd /home/maksich/Documents/ACE-RealEstate

# Create .env file
cp .env.example .env

# Edit with your values
nano .env
```

**Required Variables:**
- `POSTGRES_PASSWORD` - Secure database password
- `DEEPSEEK_API_KEY` - Your AI API key
- `ACE_SECRET` - JWT secret for authentication

### 3. Run Pre-flight Check

```bash
./test-docker.sh
```

### 4. Start Services

**Development Mode** (recommended for local testing):
```bash
docker compose -f docker-compose.dev.yml up -d
```

**Production Mode** (with Nginx reverse proxy):
```bash
docker compose up -d
```

### 5. Verify Deployment

```bash
# Check service status
docker compose ps

# Watch logs
docker compose logs -f

# Test backend health
curl http://localhost:8000/health/status
```

## 📍 Access Points

### Development Mode
- **Backend API**: http://localhost:8000/docs
- **Manager Dashboard**: http://localhost:4400
- **Chatbot**: http://localhost:4200
- **Admin Portal**: http://localhost:4500
- **PostgreSQL**: localhost:5432

### Production Mode
- **Manager Dashboard**: http://localhost/
- **Chatbot**: http://localhost/chatbot/
- **Admin Portal**: http://localhost/admin/
- **Backend API**: http://localhost/api/
- **Health Check**: http://localhost/health/status

## 🛠️ Common Commands

```bash
# View logs for specific service
docker compose logs -f backend
docker compose logs -f dashboard

# Restart a service
docker compose restart backend

# Rebuild after code changes
docker compose up -d --build backend

# Stop all services
docker compose down

# Stop and remove all data (WARNING: deletes database)
docker compose down -v

# Access backend container shell
docker exec -it ace-backend-dev bash

# Access database
docker exec -it ace-postgres-dev psql -U ace_user -d ace_production

# Seed database with sample data
docker exec -it ace-backend-dev python scripts/seed_db.py
```

## 📁 File Structure

```
ACE-RealEstate/
├── Dockerfile                      # Backend Docker image
├── docker-compose.yml              # Production orchestration
├── docker-compose.dev.yml          # Development orchestration
├── .dockerignore                   # Exclude from backend image
├── nginx/                          # Reverse proxy config
│   ├── nginx.conf                  # Main Nginx config
│   └── conf.d/
│       └── ace.conf                # Site routing rules
├── frontend/
│   ├── ACE-Chatbot/
│   │   ├── Dockerfile
│   │   ├── nginx.conf
│   │   └── .dockerignore
│   └── manager-dashboard/
│       ├── Dockerfile
│       ├── nginx.conf
│       └── .dockerignore
└── portal/portal/
    ├── Dockerfile
    ├── nginx.conf
    └── .dockerignore
```

## 🔧 Configuration

### Environment Variables

Edit `.env` file:

```env
# Database
POSTGRES_PASSWORD=your_secure_password

# API Keys
DEEPSEEK_API_KEY=sk-your-api-key

# Security
ACE_SECRET=your-jwt-secret-key

# Application
ACE_LOG_LEVEL=INFO
ACE_ENFORCE_DUAL_CONTACT=1
```

### Port Conflicts

If default ports are in use, edit `docker-compose.dev.yml`:

```yaml
ports:
  - "8001:8000"  # Backend: change 8000 to 8001
  - "4201:80"    # Chatbot: change 4200 to 4201
```

## 🚢 Deploying to Production

### Railway.app (Recommended)

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and deploy
railway login
railway init
railway up
```

### Fly.io

```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Deploy
flyctl launch
flyctl deploy
```

### Custom VPS/Server

1. Install Docker on server
2. Clone repository
3. Set environment variables
4. Run: `docker compose up -d`
5. Configure domain in `nginx/conf.d/ace.conf`
6. Setup SSL with Let's Encrypt

## 🐛 Troubleshooting

### Backend won't start
```bash
docker compose logs backend
# Common: Database not ready, wait 30s and check again
```

### Frontend build fails
```bash
# Rebuild without cache
docker compose build --no-cache chatbot
```

### Database connection issues
```bash
# Check database is running
docker compose ps postgres

# View database logs
docker compose logs postgres
```

### Port conflicts
```bash
# See what's using the port
lsof -i :8000

# Or use different ports in docker-compose.yml
```

## 📊 Monitoring

```bash
# View resource usage
docker stats

# Check container health
docker inspect --format='{{.State.Health.Status}}' ace-backend-dev

# View disk usage
docker system df
```

## 🔐 Security Checklist

- [ ] Change all default passwords in `.env`
- [ ] Set strong `ACE_SECRET` value
- [ ] Enable HTTPS with SSL certificate
- [ ] Configure firewall rules on server
- [ ] Set up automated database backups
- [ ] Review nginx security headers
- [ ] Keep Docker images updated
- [ ] Use secrets management for production

## 📚 Documentation

- **Quick Start**: `DOCKER_QUICKSTART.md`
- **Full Guide**: `DOCKER_DEPLOYMENT.md`
- **Operations**: `OPERATIONS.md`
- **Project Overview**: `WARP.md`

## 🆘 Support

1. Check logs: `docker compose logs -f`
2. Review documentation above
3. Run: `./test-docker.sh` to verify setup
4. Check GitHub issues or project documentation

## 📝 Notes

- Uses PostgreSQL instead of SQLite for production
- Multi-stage builds for optimized image sizes
- Health checks ensure service readiness
- Volume persistence for database data
- Nginx handles SSL termination and routing
- All services in isolated Docker network

---

**Need help?** Check `DOCKER_DEPLOYMENT.md` for detailed instructions.
