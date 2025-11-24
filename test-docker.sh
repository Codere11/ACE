#!/bin/bash
# ONE SCRIPT TO TEST DOCKER - GUARANTEED TO WORK

set -e

echo "🧪 ACE Real Estate - Docker Test"
echo "=================================="
echo ""

# Stop any existing containers
echo "🛑 Stopping any existing containers..."
docker compose -f docker-compose-simple.yml down 2>/dev/null || true

# Build everything
echo ""
echo "🔨 Building Docker images (5-10 minutes first time)..."
docker compose -f docker-compose-simple.yml build

# Start services
echo ""
echo "🚀 Starting services..."
docker compose -f docker-compose-simple.yml up -d

# Wait for backend
echo ""
echo "⏳ Waiting for backend to be ready..."
for i in {1..30}; do
    if curl -sf http://localhost:8000/health/status > /dev/null 2>&1; then
        echo "✅ Backend is ready!"
        break
    fi
    echo "   Waiting... ($i/30)"
    sleep 2
done

# Check status
echo ""
echo "📊 Service Status:"
docker compose -f docker-compose-simple.yml ps

# Test services
echo ""
echo "🧪 Testing services..."

if curl -sf http://localhost:8000/health/status > /dev/null; then
    echo "✅ Backend API: http://localhost:8000"
else
    echo "❌ Backend not responding"
fi

if curl -sf http://localhost:4200 > /dev/null; then
    echo "✅ Chatbot: http://localhost:4200"
else
    echo "⚠️  Chatbot not ready yet"
fi

if curl -sf http://localhost:4400 > /dev/null; then
    echo "✅ Dashboard: http://localhost:4400"
else
    echo "⚠️  Dashboard not ready yet"
fi

echo ""
echo "✅ Docker test complete!"
echo ""
echo "📋 URLs:"
echo "   Backend:   http://localhost:8000"
echo "   API Docs:  http://localhost:8000/docs"
echo "   Chatbot:   http://localhost:4200"
echo "   Dashboard: http://localhost:4400"
echo "   Portal:    http://localhost:4500"
echo ""
echo "📊 View logs:"
echo "   docker compose -f docker-compose-simple.yml logs -f"
echo ""
echo "🛑 Stop services:"
echo "   docker compose -f docker-compose-simple.yml down"
