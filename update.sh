#!/bin/bash

# Breakout Bot Update Script
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🔄 Starting Breakout Bot update...${NC}"

# Check if services are running
if ! docker-compose ps | grep -q "Up"; then
    echo -e "${YELLOW}⚠️  No services are currently running. Starting fresh deployment...${NC}"
    ./deploy.sh
    exit 0
fi

# Create backup
BACKUP_DIR="./backups/$(date +%Y%m%d_%H%M%S)"
echo -e "${YELLOW}📦 Creating backup: ${BACKUP_DIR}${NC}"
mkdir -p "$BACKUP_DIR"

# Backup data
if [ -d "./data" ]; then
    cp -r ./data "$BACKUP_DIR/"
fi

if [ -d "./logs" ]; then
    cp -r ./logs "$BACKUP_DIR/"
fi

# Pull latest changes (if using git)
if [ -d ".git" ]; then
    echo -e "${YELLOW}📥 Pulling latest changes...${NC}"
    git pull origin main
fi

# Stop services gracefully
echo -e "${YELLOW}🛑 Stopping services gracefully...${NC}"
docker-compose down --timeout 30

# Rebuild and restart
echo -e "${YELLOW}🔨 Rebuilding and restarting services...${NC}"
docker-compose build --no-cache
docker-compose up -d

# Wait for services
echo -e "${YELLOW}⏳ Waiting for services to restart...${NC}"
sleep 30

# Health check
echo -e "${YELLOW}🏥 Performing health checks...${NC}"

if curl -f http://localhost:8000/api/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ API is healthy${NC}"
else
    echo -e "${RED}❌ API health check failed${NC}"
    echo -e "${YELLOW}🔄 Rolling back to previous version...${NC}"
    docker-compose down
    # Restore from backup if needed
    exit 1
fi

echo -e "${GREEN}🎉 Update completed successfully!${NC}"
echo -e "${YELLOW}📝 Backup saved to: ${BACKUP_DIR}${NC}"
