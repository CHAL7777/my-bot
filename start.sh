#!/bin/bash

# Telegram Quiz Bot Startup Script for Multi-Platform Deployment
# Supports: Koyeb, Render, Docker, and other platforms

# ============================================================================
# Platform Detection
# ============================================================================

# Koyeb provides /data as persistent storage
if [ -d "/data" ]; then
    DATA_DIR="/data"
    echo "✅ Detected Koyeb platform (/data directory exists)"
    PLATFORM="koyeb"
# Render provides /opt/render/project/src
elif [ -d "/opt/render/project/src" ]; then
    DATA_DIR="/opt/render/project/src/data"
    echo "✅ Detected Render platform"
    PLATFORM="render"
# Fly.io provides /data
elif [ -d "/data" ]; then
    DATA_DIR="/data"
    echo "✅ Detected Fly.io platform"
    PLATFORM="flyio"
# Docker container - use /data (created in Dockerfile)
elif [ -d "/app" ]; then
    DATA_DIR="/data"
    echo "✅ Detected Docker container environment"
    PLATFORM="docker"
# Default to /data for maximum compatibility
else
    DATA_DIR="/data"
    echo "✅ Using default data directory (/data)"
    PLATFORM="unknown"
fi

# ============================================================================
# Environment Setup
# ============================================================================

# PostgreSQL is REQUIRED for Koyeb deployment
# If DATABASE_URL is not set, the application will fail
if [ -n "$DATABASE_URL" ]; then
    export DB_TYPE="postgresql"
    echo "✅ PostgreSQL mode detected"
else
    echo "❌ ERROR: DATABASE_URL environment variable is not set!"
    echo ""
    echo "   For Koyeb deployment, you MUST set DATABASE_URL:"
    echo ""
    echo "   Example for Supabase:"
    echo "   DATABASE_URL=postgresql+asyncpg://postgres:password@db.project.supabase.co:5432/postgres?sslmode=require"
    echo ""
    echo "   Example for Neon:"
    echo "   DATABASE_URL=postgresql+asyncpg://user:password@ep-xyz.us-east-1.aws.neon.tech/dbname?sslmode=require"
    echo ""
    echo "   Please set this in your Koyeb environment variables and redeploy."
    echo ""
    exit 1
fi

# Koyeb uses port 10000 by default
export PORT=${PORT:-10000}

# ============================================================================
# Directory Creation (idempotent)
# ============================================================================

if [ ! -d "$DATA_DIR" ]; then
    mkdir -p "$DATA_DIR"
    echo "📁 Created data directory: $DATA_DIR"
else
    echo "📁 Data directory exists: $DATA_DIR"
fi

# Ensure logs directory exists
mkdir -p logs
echo "📁 Logs directory ready: logs/"

# ============================================================================
# Environment Verification
# ============================================================================

echo ""
echo "=== Environment Configuration ==="
echo "Platform: $PLATFORM"
echo "Database type: $DB_TYPE"
echo "Bot token configured: $([ -n "$BOT_TOKEN" ] && echo 'YES' || echo 'NO')"
echo "Webhook URL: ${WEBHOOK_URL:-not set}"
echo "Port: $PORT"
echo "Admin IDs: ${ADMIN_IDS:-not set}"
echo "================================"
echo ""

# ============================================================================
# Database Initialization
# ============================================================================

# Initialize database (idempotent - safe to run multiple times)
echo "🔧 Initializing database..."

if [ "$DB_TYPE" = "postgresql" ]; then
    echo "📊 PostgreSQL mode: executing schema..."
    
    # Try to execute PostgreSQL schema
    if [ -f "scripts/execute_postgres_schema.py" ]; then
        python scripts/execute_postgres_schema.py
        if [ $? -eq 0 ]; then
            echo "✅ PostgreSQL schema executed successfully"
        else
            echo "⚠️  Schema execution returned non-zero, tables may already exist"
        fi
    else
        echo "⚠️  Schema script not found, using SQLAlchemy auto-create"
        python -c "from app.db.base import init_db; import asyncio; asyncio.run(init_db())"
    fi
    
    # Also run SQLAlchemy create_all to ensure all tables exist
    python -c "from app.db.base import init_db; import asyncio; asyncio.run(init_db())" 2>/dev/null || true
    
else
    # SQLite mode
    python scripts/init_database.py
    if [ $? -eq 0 ]; then
        echo "✅ Database initialization complete"
    else
        echo "⚠️  Database initialization had issues, continuing..."
    fi
fi
echo ""

# ============================================================================
# Telegram Webhook Setup (Koyeb specific)
# ============================================================================

setup_webhook() {
    if [ -n "$BOT_TOKEN" ] && [ -n "$WEBHOOK_URL" ]; then
        echo "🔗 Setting up Telegram webhook..."
        
        # Clean the webhook URL - remove trailing spaces, /ping, and trailing slashes
        CLEAN_WEBHOOK_URL=$(echo "$WEBHOOK_URL" | sed 's/[[:space:]]*$//' | sed 's|/ping$||' | sed 's|/$||')
        WEBHOOK_FULL_URL="${CLEAN_WEBHOOK_URL}/webhook"
        
        echo "   Cleaned webhook URL: $CLEAN_WEBHOOK_URL"
        echo "   Full webhook URL: $WEBHOOK_FULL_URL"
        
        # Check if webhook is already set
        RESPONSE=$(curl -s "https://api.telegram.org/bot${BOT_TOKEN}/getWebhookInfo")
        CURRENT_URL=$(echo $RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('result', {}).get('url', ''))" 2>/dev/null || echo "")
        
        if [ "$CURRENT_URL" = "$WEBHOOK_FULL_URL" ]; then
            echo "✅ Webhook already configured: $WEBHOOK_FULL_URL"
        else
            # Set webhook
            SET_RESPONSE=$(curl -s -F "url=${WEBHOOK_FULL_URL}" "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook")
            OK=$(echo $SET_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('ok', False))" 2>/dev/null || echo "false")
            
            if [ "$OK" = "True" ] || [ "$OK" = "true" ]; then
                echo "✅ Webhook set successfully: $WEBHOOK_FULL_URL"
            else
                DESC=$(echo $SET_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('description', 'Unknown error'))" 2>/dev/null || echo "Failed")
                echo "⚠️  Webhook setup: $DESC"
                echo "   Response: $SET_RESPONSE"
            fi
        fi
    else
        echo "⚠️  Skipping webhook setup (BOT_TOKEN or WEBHOOK_URL not set)"
        if [ -z "$BOT_TOKEN" ]; then
            echo "   BOT_TOKEN is not set"
        fi
        if [ -z "$WEBHOOK_URL" ]; then
            echo "   WEBHOOK_URL is not set"
        fi
    fi
}

# Only setup webhook if not in dry-run mode
if [ "${DRY_RUN:-false}" != "true" ]; then
    setup_webhook
fi

echo ""

# ============================================================================
# Start Bot in Webhook Mode
# ============================================================================

echo "🚀 Starting Telegram Quiz Bot in webhook mode..."
echo "   Entrypoint: app.webhook_main:app"
echo "   Host: 0.0.0.0"
echo "   Port: $PORT"
echo "   Platform: $PLATFORM"
echo ""

# Run with uvicorn
exec uvicorn app.webhook_main:app --host 0.0.0.0 --port $PORT --log-level info
