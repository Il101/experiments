#!/bin/bash

# Breakout Bot Production Deployment Script
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT=${1:-production}
BACKUP_DIR="./backups/$(date +%Y%m%d_%H%M%S)"

echo -e "${GREEN}🚀 Starting Breakout Bot deployment to ${ENVIRONMENT}${NC}"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker and try again.${NC}"
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ docker-compose is not installed. Please install it and try again.${NC}"
    exit 1
fi

# Create backup directory
echo -e "${YELLOW}📦 Creating backup directory: ${BACKUP_DIR}${NC}"
mkdir -p "$BACKUP_DIR"

# Backup existing data if it exists
if [ -d "./data" ]; then
    echo -e "${YELLOW}💾 Backing up existing data...${NC}"
    cp -r ./data "$BACKUP_DIR/"
fi

if [ -d "./logs" ]; then
    echo -e "${YELLOW}💾 Backing up existing logs...${NC}"
    cp -r ./logs "$BACKUP_DIR/"
fi

# Create necessary directories
echo -e "${YELLOW}📁 Creating necessary directories...${NC}"
mkdir -p data logs reports pids

# Set proper permissions
echo -e "${YELLOW}🔐 Setting proper permissions...${NC}"
chmod 755 data logs reports pids
chmod 600 .env 2>/dev/null || true

# Build and start services
echo -e "${YELLOW}🔨 Building and starting services...${NC}"
docker-compose down --remove-orphans
docker-compose build --no-cache
docker-compose up -d

# Wait for services to be ready
echo -e "${YELLOW}⏳ Waiting for services to be ready...${NC}"
sleep 30

# Health check
echo -e "${YELLOW}🏥 Performing health checks...${NC}"

# Check API health
if curl -f http://localhost:8000/api/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ API is healthy${NC}"
else
    echo -e "${RED}❌ API health check failed${NC}"
    docker-compose logs breakout-bot-api
    exit 1
fi

# Check frontend
if curl -f http://localhost:3000 > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Frontend is healthy${NC}"
else
    echo -e "${RED}❌ Frontend health check failed${NC}"
    docker-compose logs breakout-bot-frontend
    exit 1
fi

# Check Redis
if docker-compose exec -T redis redis-cli ping | grep -q PONG; then
    echo -e "${GREEN}✅ Redis is healthy${NC}"
else
    echo -e "${RED}❌ Redis health check failed${NC}"
    docker-compose logs redis
    exit 1
fi

# Show service status
echo -e "${GREEN}📊 Service Status:${NC}"
docker-compose ps

# Show access URLs
echo -e "${GREEN}🌐 Access URLs:${NC}"
echo -e "  Frontend: http://localhost:3000"
echo -e "  API: http://localhost:8000"
echo -e "  API Docs: http://localhost:8000/api/docs"
echo -e "  Grafana: http://localhost:3001 (admin/admin)"
echo -e "  Prometheus: http://localhost:9090"

echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
echo -e "${YELLOW}📝 Next steps:${NC}"
echo -e "  1. Configure your trading settings in the frontend"
echo -e "  2. Set up monitoring dashboards in Grafana"
echo -e "  3. Review logs: docker-compose logs -f"
echo -e "  4. Monitor system: docker-compose ps"
