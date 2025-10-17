#!/bin/bash
# Celery worker startup script
#
# This script starts a Celery worker for processing background tasks.
# The worker handles Excel file parsing with tenant isolation.
#
# Usage:
#   ./scripts/start_celery_worker.sh

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Starting Celery Worker ===${NC}"

# Check if Redis is running
if ! redis-cli ping > /dev/null 2>&1; then
    echo -e "${RED}Error: Redis is not running!${NC}"
    echo -e "${YELLOW}Please start Redis first:${NC}"
    echo "  redis-server"
    exit 1
fi

# Check environment
if [ -z "$DATABASE_URL" ]; then
    echo -e "${YELLOW}Warning: DATABASE_URL not set. Using .env file.${NC}"
fi

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo -e "${GREEN}Activating virtual environment...${NC}"
    source .venv/bin/activate
fi

# Start Celery worker
echo -e "${GREEN}Starting Celery worker with queues: parsing, default${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
echo ""

celery -A genreport.core.tasks.celery_app worker \
    --loglevel=info \
    --queues=parsing,default \
    --concurrency=2 \
    --max-tasks-per-child=100 \
    --time-limit=600 \
    --soft-time-limit=540

echo -e "${GREEN}Celery worker stopped${NC}"
