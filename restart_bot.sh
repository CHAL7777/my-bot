#!/bin/bash
# Telegram Quiz Bot - Restart Script
# Use this script to restart the bot when you don't have docker group permissions

echo "🔄 Restarting Telegram Quiz Bot..."

# Check if we can run docker-compose without sudo
if docker-compose ps > /dev/null 2>&1; then
    echo "Using docker-compose directly..."
    docker-compose restart bot
else
    echo "Using sudo for docker-compose commands..."
    sudo docker-compose restart bot
fi

echo "✅ Bot restart command executed!"
echo ""
echo "To check if the bot is running:"
echo "  docker-compose logs -f bot"
echo ""
echo "To stop the bot:"
echo "  sudo docker-compose down"

