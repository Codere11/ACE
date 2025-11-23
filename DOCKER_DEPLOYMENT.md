# Docker Deployment Guide

Complete guide for deploying ACE Real Estate platform using Docker.

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- At least 2GB RAM available
- At least 10GB disk space

## Quick Start (Development)

### 1. Set Environment Variables

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` with your values:

```env
# Database
POSTGRES_PASSWORD=your_secure_password_here

# API Keys
DEEPSEEK_API_KEY=your-deepseek-api-key

# Security
ACE_SECRET=your-jwt-secret-key-change-in-production

# Application
ACE_LOG_LEVEL=INFO
ACE_ENFORCE_DUAL_CONTACT=1
```

### 2. Build and Start Services

```bash
# Development mode (exposed ports, debug logging)
docker-compose -f docker-compose.dev.yml up -d

# Production mode (with nginx reverse proxy)
docker-compose up -d
```

### 3. Access Applications

**Development Mode:**
- Manager Dashboard: http://localhost:4400
- ACE Chatbot: http://localhost:4200
- Portal (Admin): http://localhost:4500
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

**Production Mode (with Nginx):**
- Manager Dashboard: http://localhost/
- ACE Chatbot: http://localhost/chatbot/
- Portal (Admin): http://localhost/admin/
- Backend API: http://localhost/api/
- Health Check: http://localhost/health/status

### 4. Initialize Database

The database is automatically initialized on first startup. To seed with sample data:

```bash
docker exec -it ace-backend-dev python scripts/seed_db.py
```

## Docker Commands Reference

### Managing Services

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# Restart a specific service
docker-compose restart backend

# View logs
docker-compose logs -f backend
docker-compose logs -f dashboard

# View all logs
docker-compose logs -f

# Check service status
docker-compose ps
```

### Rebuilding Images

```bash
# Rebuild all images
docker-compose build

# Rebuild specific service
docker-compose build backend

# Rebuild without cache
docker-compose build --no-cache

# Rebuild and restart
docker-compose up -d --build
```

### Database Management

```bash
# Access PostgreSQL shell
docker exec -it ace-postgres psql -U ace_user -d ace_production

# Backup database
docker exec ace-postgres pg_dump -U ace_user ace_production > backup.sql

# Restore database
cat backup.sql | docker exec -i ace-postgres psql -U ace_user -d ace_production

# View database logs
docker-compose logs -f postgres
```

### Debugging

```bash
# Enter backend container
docker exec -it ace-backend bash

# Enter frontend container
docker exec -it ace-dashboard sh

# View container resource usage
docker stats

# Inspect container
docker inspect ace-backend

# View backend logs (last 100 lines)
docker-compose logs --tail=100 backend
```

## Production Deployment

### Environment Configuration

For production, ensure you set strong passwords and secrets:

```env
POSTGRES_PASSWORD=$(openssl rand -base64 32)
ACE_SECRET=$(openssl rand -base64 32)
```

### Using Docker Compose (Production)

```bash
# Build and start with production config
docker-compose up -d

# View only errors
docker-compose logs -f | grep ERROR
```

### Volume Management

Persistent data is stored in Docker volumes:

```bash
# List volumes
docker volume ls

# Inspect volume
docker volume inspect ace-realestate_postgres_data

# Backup volume
docker run --rm -v ace-realestate_postgres_data:/data -v $(pwd):/backup ubuntu tar czf /backup/postgres_backup.tar.gz /data

# Restore volume
docker run --rm -v ace-realestate_postgres_data:/data -v $(pwd):/backup ubuntu tar xzf /backup/postgres_backup.tar.gz -C /
```

## Deployment to Cloud Platforms

### Railway.app

1. Install Railway CLI:
```bash
npm install -g @railway/cli
```

2. Login and initialize:
```bash
railway login
railway init
```

3. Add PostgreSQL:
```bash
railway add --plugin postgresql
```

4. Deploy:
```bash
railway up
```

### Fly.io

1. Install flyctl:
```bash
curl -L https://fly.io/install.sh | sh
```

2. Login:
```bash
flyctl auth login
```

3. Launch app:
```bash
flyctl launch
```

4. Deploy:
```bash
flyctl deploy
```

### Render.com

1. Create `render.yaml` (already included if you need it)
2. Connect GitHub repository
3. Render auto-deploys on push

### DigitalOcean App Platform

1. Connect repository
2. Configure build settings:
   - Backend: Docker, port 8000
   - Frontend: Docker, port 80
3. Add PostgreSQL database
4. Deploy

## Nginx Configuration

### Custom Domain Setup

Edit `nginx/conf.d/ace.conf` and replace `localhost` with your domain:

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    # ... rest of config
}
```

### SSL/HTTPS Setup

For production, use Let's Encrypt:

```bash
# Install certbot
docker run -it --rm --name certbot \
  -v "/etc/letsencrypt:/etc/letsencrypt" \
  -v "/var/lib/letsencrypt:/var/lib/letsencrypt" \
  certbot/certbot certonly --standalone \
  -d yourdomain.com

# Update nginx config to use SSL
# See nginx/conf.d/ace-ssl.conf.example
```

## Troubleshooting

### Backend won't start

```bash
# Check logs
docker-compose logs backend

# Common issues:
# - Database not ready: Wait 30 seconds and retry
# - Missing .env: Copy .env.example to .env
# - Port conflict: Change port in docker-compose.yml
```

### Frontend build fails

```bash
# Check Node version in Dockerfile (should be 18+)
# Clear build cache
docker-compose build --no-cache chatbot
```

### Database connection issues

```bash
# Verify postgres is running
docker-compose ps postgres

# Check connection
docker exec ace-backend python -c "from app.core.db import engine; engine.connect()"
```

### Port conflicts

If ports are already in use, edit `docker-compose.yml`:

```yaml
ports:
  - "8001:8000"  # Change 8000 to 8001
```

## Monitoring

### Health Checks

```bash
# Backend health
curl http://localhost:8000/health/status

# Container health
docker inspect --format='{{.State.Health.Status}}' ace-backend
```

### Resource Usage

```bash
# Real-time monitoring
docker stats

# Disk usage
docker system df
```

## Cleanup

```bash
# Stop and remove containers
docker-compose down

# Remove volumes (WARNING: deletes data)
docker-compose down -v

# Remove all unused Docker resources
docker system prune -a
```

## Security Checklist

- [ ] Change default passwords in .env
- [ ] Set strong ACE_SECRET
- [ ] Enable HTTPS in production
- [ ] Configure firewall rules
- [ ] Set up regular database backups
- [ ] Review nginx security headers
- [ ] Limit exposed ports in production
- [ ] Use secrets management for API keys
- [ ] Enable Docker security scanning
- [ ] Keep Docker images updated

## Next Steps

1. **Configure Domain**: Point your domain to the server IP
2. **Setup SSL**: Use Let's Encrypt for HTTPS
3. **Configure Backups**: Set up automated database backups
4. **Monitoring**: Add application monitoring (Sentry, DataDog, etc.)
5. **CI/CD**: Set up automated deployments on GitHub push
6. **Scaling**: Consider Kubernetes for high availability

## Support

For issues or questions:
- Check logs: `docker-compose logs -f`
- Review this guide
- Check Docker documentation
- Verify environment variables are set correctly
