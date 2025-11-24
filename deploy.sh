#!/bin/bash
# Quick Deploy Script - Push changes to production in seconds

set -e

# Configuration
SERVER_USER="root"
SERVER_IP="${1:-}"
SERVER_PATH="/root/ACE-RealEstate"

if [ -z "$SERVER_IP" ]; then
    echo "Usage: ./deploy.sh <server-ip>"
    echo "Example: ./deploy.sh 192.168.1.100"
    exit 1
fi

echo "🚀 Quick Deploy to $SERVER_IP"
echo ""

# Step 1: Sync code (exclude heavy files)
echo "📦 Syncing code..."
rsync -avz --progress \
    --exclude 'node_modules' \
    --exclude 'venv' \
    --exclude '*.pyc' \
    --exclude '__pycache__' \
    --exclude '.git' \
    --exclude 'ace_dev.db' \
    --exclude 'ace_realestate.db' \
    --exclude 'dist' \
    --exclude '.angular' \
    ./ ${SERVER_USER}@${SERVER_IP}:${SERVER_PATH}/

echo ""
echo "✅ Code synced"

# Step 2: Deploy on server
echo ""
echo "🔄 Rebuilding and restarting services..."
ssh ${SERVER_USER}@${SERVER_IP} << 'ENDSSH'
cd /root/ACE-RealEstate

# Rebuild and restart
docker compose build --parallel
docker compose up -d

# Show status
echo ""
echo "📊 Service Status:"
docker compose ps

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📋 View logs: docker compose logs -f"
ENDSSH

echo ""
echo "🎉 Deploy finished! Your changes are live."
echo ""
echo "🔍 Quick checks:"
echo "   Backend:  curl https://yourdomain.com/api/health/status"
echo "   Frontend: curl https://yourdomain.com/dashboard"
