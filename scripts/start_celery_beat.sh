#!/bin/bash
# Celery beat scheduler startup script
#
# This script starts the Celery beat scheduler for periodic tasks.
# Currently, no periodic tasks are configured (all tasks are triggered by API).
#
# Usage:
#   ./scripts/start_celery_beat.sh

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Starting Celery Beat Scheduler ===${NC}"

# Check if Redis is running
if ! redis-cli ping > /dev/null 2>&1; then
    echo -e "${RED}Error: Redis is not running!${NC}"
    echo -e "${YELLOW}Please start Redis first:${NC}"
    echo "  redis-server"
    exit 1
fi

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo -e "${GREEN}Activating virtual environment...${NC}"
    source .venv/bin/activate
fi

# Start Celery beat
echo -e "${GREEN}Starting Celery beat scheduler${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
echo ""

celery -A genreport.core.tasks.celery_app beat \
    --loglevel=info

echo -e "${GREEN}Celery beat stopped${NC}"
