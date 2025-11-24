# Quick Deployment Guide

## 🎯 Goal: Deploy Changes in SECONDS, not minutes

## Three Deployment Modes

### ⚡ Mode 1: Hot Reload (Instant - Recommended for Testing)
**Best for:** Rapid iteration, testing features
**Speed:** Changes apply in <5 seconds
**Setup:** Use on server once, then just rsync files

```bash
# On server - first time setup
docker compose -f docker-compose.hotreload.yml up -d

# From your local machine - deploy changes instantly
rsync -avz ./app/ root@YOUR-IP:/root/ACE-RealEstate/app/
# Changes apply automatically! No restart needed!
```

**Backend changes:** Instant (uvicorn auto-reloads)  
**Frontend changes:** Need rebuild (but only the changed app)

---

### 🚀 Mode 2: Quick Deploy (1-2 minutes)
**Best for:** Production after testing
**Speed:** 60-120 seconds
**Rebuilds:** Everything

```bash
# Configure once
echo "SERVER_IP=1.2.3.4" > .deploy-config

# Then just run
./deploy.sh 1.2.3.4
```

**What it does:**
1. Syncs all code (5-10 sec)
2. Rebuilds Docker images (30-60 sec)
3. Restarts services (10-20 sec)

---

### ⚡ Mode 3: Backend-Only Deploy (5-10 seconds)
**Best for:** Quick Python fixes
**Speed:** 5-10 seconds
**Rebuilds:** Nothing, just restart

```bash
./deploy-backend.sh 1.2.3.4
```

**What it does:**
1. Syncs backend code only (3-5 sec)
2. Restarts backend container (2-5 sec)

---

## Comparison

| Mode | Speed | Use Case | Rebuilds |
|------|-------|----------|----------|
| Hot Reload | **Instant** | Development/Testing | None |
| Quick Deploy | 1-2 min | Production updates | All |
| Backend-Only | 5-10 sec | Quick Python fixes | None |

## Workflow Examples

### Example 1: Testing New Feature
```bash
# Use hot reload mode on server
# On server:
docker compose -f docker-compose.hotreload.yml up -d

# Make changes locally, then:
rsync -avz ./app/ root@YOUR-IP:/root/ACE-RealEstate/app/
# ✅ Change is live in 2 seconds!
```

### Example 2: Frontend Change
```bash
# Edit frontend locally
# Test locally first
cd frontend/manager-dashboard && ng serve

# Deploy to production
./deploy.sh 1.2.3.4
# ✅ Live in 1-2 minutes
```

### Example 3: Quick Bug Fix
```bash
# Fix bug in app/api/surveys.py
# Test locally

# Deploy backend only
./deploy-backend.sh 1.2.3.4
# ✅ Fixed in 5 seconds!
```

## Pro Tips

### 1. Use Hot Reload on Test Server
- Keep production stable with normal docker-compose.yml
- Use hot reload on test server for rapid iteration
- Once stable, deploy to production

### 2. Set Up SSH Keys (Skip Password)
```bash
ssh-copy-id root@YOUR-IP
# Now deploys are one command, no password!
```

### 3. Save Server IP
```bash
echo "export ACE_SERVER=1.2.3.4" >> ~/.bashrc
source ~/.bashrc

# Now deploy with:
./deploy.sh $ACE_SERVER
```

### 4. Watch Logs During Deploy
```bash
# In another terminal
ssh root@YOUR-IP "cd /root/ACE-RealEstate && docker compose logs -f backend"
```

## Initial Setup (Do Once)

### 1. Add Server to .deploy-config
```bash
nano .deploy-config
# Change: SERVER_IP=your-actual-server-ip
```

### 2. Setup SSH Keys
```bash
ssh-keygen -t ed25519
ssh-copy-id root@your-server-ip
```

### 3. First Deploy
```bash
./deploy.sh your-server-ip
```

### 4. Enable Hot Reload (Optional)
```bash
ssh root@your-server-ip
cd /root/ACE-RealEstate
docker compose down
docker compose -f docker-compose.hotreload.yml up -d
```

Now you're ready for lightning-fast deployments! ⚡

## Troubleshooting

**rsync not found?**
```bash
sudo apt install rsync
```

**Permission denied?**
```bash
ssh-copy-id root@your-server-ip
```

**Backend not restarting?**
```bash
ssh root@your-server-ip
docker compose logs backend
```

**Frontend changes not showing?**
- Clear browser cache (Ctrl+Shift+R)
- Frontend needs rebuild: `docker compose build dashboard`
