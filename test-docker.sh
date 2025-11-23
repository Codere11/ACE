#!/bin/bash
# Test script for Docker deployment

set -e

echo "========================================"
echo "ACE Real Estate Docker Deployment Test"
echo "========================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Docker
echo "1. Checking Docker installation..."
if command -v docker &> /dev/null; then
    echo -e "${GREEN}✓${NC} Docker is installed: $(docker --version)"
else
    echo -e "${RED}✗${NC} Docker is not installed"
    exit 1
fi

# Check Docker Compose
echo "2. Checking Docker Compose..."
if command -v docker-compose &> /dev/null; then
    echo -e "${GREEN}✓${NC} Docker Compose is installed: $(docker-compose --version)"
elif docker compose version &> /dev/null; then
    echo -e "${GREEN}✓${NC} Docker Compose v2 is installed: $(docker compose version)"
else
    echo -e "${RED}✗${NC} Docker Compose is not installed"
    exit 1
fi

# Check .env file
echo "3. Checking environment file..."
if [ -f .env ]; then
    echo -e "${GREEN}✓${NC} .env file exists"
else
    echo -e "${YELLOW}!${NC} .env file not found, creating from example..."
    cp .env.example .env
    echo -e "${YELLOW}!${NC} Please edit .env with your values before deployment"
fi

# Check Docker daemon
echo "4. Checking Docker daemon..."
if docker info &> /dev/null; then
    echo -e "${GREEN}✓${NC} Docker daemon is running"
else
    echo -e "${RED}✗${NC} Docker daemon is not running"
    exit 1
fi

# Check for port conflicts
echo "5. Checking for port conflicts..."
ports=(4200 4400 4500 8000 5432)
conflicts=0
for port in "${ports[@]}"; do
    if lsof -Pi :$port -sTCP:LISTEN -t &> /dev/null; then
        echo -e "${YELLOW}!${NC} Port $port is already in use"
        conflicts=$((conflicts + 1))
    else
        echo -e "${GREEN}✓${NC} Port $port is available"
    fi
done

if [ $conflicts -gt 0 ]; then
    echo -e "${YELLOW}Warning:${NC} $conflicts port(s) in use. You may need to stop services or edit docker-compose.yml"
fi

# Check disk space
echo "6. Checking disk space..."
available=$(df . | tail -1 | awk '{print $4}')
if [ $available -gt 10485760 ]; then
    echo -e "${GREEN}✓${NC} Sufficient disk space available"
else
    echo -e "${YELLOW}!${NC} Low disk space. At least 10GB recommended"
fi

echo ""
echo "========================================"
echo "Pre-flight checks complete!"
echo "========================================"
echo ""
echo "To start the application:"
echo ""
echo "  Development mode:"
echo "    docker compose -f docker-compose.dev.yml up -d"
echo ""
echo "  Production mode:"
echo "    docker compose up -d"
echo ""
echo "View logs:"
echo "    docker compose logs -f"
echo ""
echo "Stop services:"
echo "    docker compose down"
echo ""
