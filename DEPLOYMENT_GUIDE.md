# ACE Real Estate - Deployment Guide

## Prerequisites
- A VPS or cloud server (Ubuntu 20.04+ recommended)
- Domain name (or subdomain)
- SSH access to server

## Step 1: Choose Hosting Provider

### Recommended Options:

**Budget-friendly:**
- **Hetzner** (~€5/month) - Best price/performance
- **DigitalOcean** ($6/month) - Easy to use
- **Vultr** ($6/month) - Fast deployment

**Specs needed:**
- 2GB RAM minimum
- 2 vCPU
- 50GB SSD

## Step 2: Get a Domain

### Free Options (for testing):
- **subdomain.is** - Free .is subdomain
- **FreeDNS** - Free subdomains
- Use your VPS IP directly (not recommended for production)

### Paid Options:
- **Namecheap** - Cheap domains (~$10/year)
- **Cloudflare Registrar** - At-cost pricing
- **Porkbun** - Good prices

## Step 3: Server Setup

### 3.1 SSH into your server
```bash
ssh root@your-server-ip
```

### 3.2 Update system
```bash
apt update && apt upgrade -y
```

### 3.3 Install Docker
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
apt install docker-compose-plugin -y

# Verify installation
docker --version
docker compose version
```

### 3.4 Install Git
```bash
apt install git -y
```

### 3.5 Create a deploy user (optional but recommended)
```bash
adduser deploy
usermod -aG docker deploy
su - deploy
```

## Step 4: Deploy Application

### 4.1 Clone repository
```bash
cd ~
git clone https://github.com/yourusername/ACE-RealEstate.git
cd ACE-RealEstate
```

Or upload via rsync from your local machine:
```bash
# Run from your local machine
rsync -avz --exclude 'node_modules' --exclude 'venv' --exclude '*.pyc' \
  /home/maksich/Documents/ACE-RealEstate/ \
  root@your-server-ip:/root/ACE-RealEstate/
```

### 4.2 Create environment file
```bash
cp .env.example .env
nano .env
```

Fill in:
```env
POSTGRES_PASSWORD=your_secure_random_password_here
ACE_SECRET=your_jwt_secret_min_32_chars_random_string
DEEPSEEK_API_KEY=sk-your-deepseek-api-key
DOMAIN=yourdomain.com
```

Generate secure passwords:
```bash
# Generate PostgreSQL password
openssl rand -base64 32

# Generate JWT secret
openssl rand -base64 48
```

### 4.3 Update frontend API URLs

**For Chatbot:**
Edit `frontend/ACE-Chatbot/src/environments/environment.prod.ts`:
```typescript
export const environment = {
  production: true,
  apiUrl: 'https://yourdomain.com/api'  // Update this
};
```

**For Manager Dashboard:**
Edit `frontend/manager-dashboard/src/environments/environment.prod.ts`:
```typescript
export const environment = {
  production: true,
  apiUrl: 'https://yourdomain.com/api'  // Update this
};
```

Or update the hardcoded URLs in the services to read from environment.

### 4.4 Build and start services
```bash
# Build images (first time - takes 5-10 minutes)
docker compose build

# Start all services
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f
```

### 4.5 Create initial admin user
```bash
# Access backend container
docker compose exec backend python

# In Python shell:
from app.core.db import SessionLocal
from app.models.orm import User, Organization
from passlib.context import CryptContext

db = SessionLocal()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Create organization
org = Organization(slug="demo-agency", name="Demo Real Estate Agency", active=True)
db.add(org)
db.commit()
db.refresh(org)

# Create admin user
admin = User(
    username="admin",
    email="admin@yourdomain.com",
    password_hash=pwd_context.hash("changeme123"),
    role="org_admin",
    organization_id=org.id,
    is_active=True
)
db.add(admin)
db.commit()

print(f"Created admin user: username=admin, password=changeme123, org_id={org.id}")
exit()
```

## Step 5: Configure Domain & SSL

### 5.1 Point domain to server
In your domain registrar (Namecheap, Cloudflare, etc.):
- Add **A record**: `@` → `your-server-ip`
- Add **A record**: `www` → `your-server-ip`

### 5.2 Install Certbot for SSL
```bash
apt install certbot python3-certbot-nginx -y
```

### 5.3 Update nginx configuration
Edit `nginx/conf.d/ace.conf` and replace `yourdomain.com` with your actual domain.

### 5.4 Reload nginx and get SSL certificate
```bash
docker compose restart nginx

# Get SSL certificate
certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

## Step 6: Verify Deployment

### Check services:
```bash
# All containers running?
docker compose ps

# Check logs for errors
docker compose logs backend
docker compose logs chatbot
docker compose logs dashboard
```

### Test URLs:
- Backend API: `https://yourdomain.com/api/health/status`
- Chatbot: `https://yourdomain.com`
- Manager Dashboard: `https://yourdomain.com/dashboard`
- Survey: `https://yourdomain.com/s/your-survey-slug`

### Login to Manager Dashboard:
- URL: `https://yourdomain.com/dashboard`
- Username: `admin`
- Password: `changeme123`
- **Change password immediately!**

## Step 7: Post-Deployment

### 7.1 Set up automatic SSL renewal
```bash
# Test renewal
certbot renew --dry-run

# Certbot adds cron automatically, but verify:
systemctl status certbot.timer
```

### 7.2 Set up backups
```bash
# Create backup script
cat > /root/backup-ace.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=/root/backups
mkdir -p $BACKUP_DIR

# Backup database
docker compose exec -T postgres pg_dump -U ace_user ace_production > $BACKUP_DIR/db_$DATE.sql

# Keep only last 7 days
find $BACKUP_DIR -name "db_*.sql" -mtime +7 -delete
EOF

chmod +x /root/backup-ace.sh

# Add to crontab (daily at 2 AM)
crontab -e
# Add: 0 2 * * * /root/backup-ace.sh
```

### 7.3 Set up monitoring (optional)
```bash
# Simple uptime monitoring
apt install uptimed -y
```

Or use external services:
- **UptimeRobot** - Free monitoring
- **Better Uptime** - Free tier available

## Updating the Application

### Method 1: Git Pull (if using Git)
```bash
cd ~/ACE-RealEstate
git pull
docker compose build
docker compose up -d
```

### Method 2: rsync from local
```bash
# Run from your local machine
rsync -avz --exclude 'node_modules' --exclude 'venv' \
  /home/maksich/Documents/ACE-RealEstate/ \
  root@your-server-ip:/root/ACE-RealEstate/

# Then on server
docker compose build
docker compose up -d
```

## Troubleshooting

### Containers won't start
```bash
docker compose logs backend
docker compose logs postgres
```

### Database connection errors
```bash
# Check postgres is running
docker compose ps postgres

# Check database exists
docker compose exec postgres psql -U ace_user -d ace_production -c "\dt"
```

### Frontend can't reach backend
- Check CORS settings in `app/main.py`
- Verify API URL in frontend environment files
- Check nginx proxy configuration

### SSL certificate issues
```bash
# Check certificate status
certbot certificates

# Force renewal
certbot renew --force-renewal
```

## Cost Estimate

**Monthly costs for test/production:**
- VPS: €5-10/month (Hetzner, DigitalOcean)
- Domain: ~€1/month ($10-15/year)
- **Total: ~€6-11/month**

**Free for testing:**
- Free subdomain (subdomain.is, FreeDNS)
- Free SSL (Let's Encrypt)

## Security Checklist

- [ ] Changed default passwords
- [ ] Set strong POSTGRES_PASSWORD
- [ ] Set strong ACE_SECRET
- [ ] SSL certificate installed
- [ ] Firewall configured (ufw)
- [ ] Regular backups enabled
- [ ] SSH key authentication (disable password login)
- [ ] Keep system updated: `apt update && apt upgrade`

## Support

If you encounter issues:
1. Check logs: `docker compose logs -f`
2. Verify environment variables in `.env`
3. Check nginx configuration
4. Verify domain DNS settings
