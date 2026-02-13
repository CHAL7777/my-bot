#!/bin/bash

# Telegram Quiz Bot DNS Fix - Deployment Test Script
# This script helps verify that the DNS fix works correctly

set -e

echo "🔍 Telegram Quiz Bot DNS Fix - Deployment Test"
echo "=============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    print_error "docker-compose not found. Please install Docker Compose."
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    print_warning ".env file not found. Make sure environment variables are set."
fi

echo ""
echo "Step 1: Stopping existing containers..."
docker-compose down || true

echo ""
echo "Step 2: Rebuilding bot container..."
docker-compose build --no-cache bot

echo ""
echo "Step 3: Starting services..."
docker-compose up -d

echo ""
echo "Step 4: Waiting for services to start..."
sleep 10

# Get container ID
CONTAINER_ID=$(docker ps --filter "name=telegram-quiz-bot" --format "{{.ID}}" | head -n1)

if [ -z "$CONTAINER_ID" ]; then
    print_error "Bot container not found. Check docker-compose status."
    docker-compose logs
    exit 1
fi

print_status "Bot container found: $CONTAINER_ID"

echo ""
echo "Step 5: Testing DNS resolution..."
if docker exec "$CONTAINER_ID" python test_dns_resolution.py; then
    print_status "DNS resolution test passed!"
else
    print_error "DNS resolution test failed!"
    echo ""
    echo "Debug information:"
    echo "Container resolv.conf:"
    docker exec "$CONTAINER_ID" cat /etc/resolv.conf
    echo ""
    echo "Container logs:"
    docker-compose logs bot
    exit 1
fi

echo ""
echo "Step 6: Checking bot startup logs..."
if docker-compose logs bot | grep -q "Starting Quiz Bot"; then
    print_status "Bot startup detected in logs"
else
    print_warning "Bot startup not clearly detected. Check logs manually."
fi

echo ""
echo "Step 7: Checking for DNS errors in recent logs..."
if docker-compose logs --tail=50 bot | grep -q "Temporary failure in name resolution"; then
    print_error "DNS resolution errors still present in logs!"
    docker-compose logs --tail=20 bot
    exit 1
else
    print_status "No DNS resolution errors found in recent logs"
fi

echo ""
echo "🎉 Deployment test completed successfully!"
echo ""
echo "Next steps:"
echo "1. Monitor the bot logs: docker-compose logs -f bot"
echo "2. Test bot functionality in Telegram"
echo "3. Check that users can interact with the bot"
echo ""
echo "Useful commands:"
echo "- View logs: docker-compose logs -f bot"
echo "- Restart bot: docker-compose restart bot"
echo "- Stop all: docker-compose down"
echo "- Test DNS again: docker exec $CONTAINER_ID python test_dns_resolution.py"
