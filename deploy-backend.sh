#!/bin/bash
# Super Fast Backend-Only Deploy (no frontend rebuild needed)
# Use this when you only changed Python code

set -e

SERVER_USER="root"
SERVER_IP="${1:-}"
SERVER_PATH="/root/ACE-RealEstate"

if [ -z "$SERVER_IP" ]; then
    echo "Usage: ./deploy-backend.sh <server-ip>"
    exit 1
fi

echo "⚡ Fast Backend Deploy to $SERVER_IP"
echo ""

# Sync only backend code
echo "📦 Syncing backend code..."
rsync -avz --progress \
    --exclude '*.pyc' \
    --exclude '__pycache__' \
    ./app/ ${SERVER_USER}@${SERVER_IP}:${SERVER_PATH}/app/

echo ""
echo "🔄 Restarting backend..."
ssh ${SERVER_USER}@${SERVER_IP} << 'ENDSSH'
cd /root/ACE-RealEstate
docker compose restart backend
echo "✅ Backend restarted!"
docker compose logs --tail=20 backend
ENDSSH

echo ""
echo "⚡ Backend deployed in seconds!"
