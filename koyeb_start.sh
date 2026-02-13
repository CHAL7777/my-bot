#!/bin/bash
# =============================================================================
# Koyeb Startup Script for Telegram Quiz Bot
# =============================================================================
#
# This script starts the Telegram bot in webhook mode for deployment on Koyeb.
#
# Environment Variables Required:
#   BOT_TOKEN         - Telegram bot token
#   WEBHOOK_URL       - Full URL where bot is hosted
#   DATABASE_URL      - Supabase PostgreSQL connection string
#
# =============================================================================

set -e  # Exit on any error

# =============================================================================
# Color Output Functions - MUST be defined first
# =============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"; }

# =============================================================================
# Configuration - Always use /app as project root on Koyeb
# =============================================================================

# Always change to /app first - this is where Docker copies the code
cd /app

# Set project root to /app
PROJECT_ROOT="/app"

# Default port
PORT="${PORT:-8000}"
WEBHOOK_PATH="${WEBHOOK_PATH:-/webhook}"
LOG_LEVEL="${LOG_LEVEL:-info}"

# Create logs directory
mkdir -p /app/logs

# Note: /data directory is NOT created here since we're using PostgreSQL
# The application uses external PostgreSQL database, not SQLite
# This avoids permission issues on Koyeb

# =============================================================================
# Pre-flight Checks
# =============================================================================

preflight_checks() {
    log_info "Running pre-flight checks..."
    log_info "Working directory: $(pwd)"
    
    # Check required environment variables
    if [ -z "$BOT_TOKEN" ]; then
        log_error "BOT_TOKEN environment variable is not set!"
        exit 1
    fi
    
    if [ -z "$DATABASE_URL" ]; then
        log_error "DATABASE_URL environment variable is not set!"
        exit 1
    fi
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is not installed!"
        exit 1
    fi
    
    # Check DATABASE_URL format
    if [[ "$DATABASE_URL" != postgresql* ]]; then
        log_error "DATABASE_URL must be a PostgreSQL connection string (postgresql://...)"
        exit 1
    fi
    
    log_success "Pre-flight checks passed!"
}

# =============================================================================
# Database Initialization
# =============================================================================

init_database() {
    log_info "Initializing database..."
    
    # Create a flag file to track if we've initialized the database
    DB_INIT_FLAG="/app/.db_initialized"
    
    # Run initialization if flag doesn't exist or FORCE_DB_INIT is set
    if [ ! -f "$DB_INIT_FLAG" ] || [ "$FORCE_DB_INIT" = "true" ]; then
        log_info "Running database initialization script..."
        
        # Run the database initialization script with absolute path
        if python3 /app/scripts/init_db.py; then
            touch "$DB_INIT_FLAG"
            log_success "Database initialized successfully!"
        else
            log_warning "Database initialization encountered issues - continuing anyway"
        fi
    else
        log_info "Database already initialized (skipping)"
    fi
}

# =============================================================================
# Start the Application
# =============================================================================

start_app() {
    log_info "Starting Telegram Quiz Bot in webhook mode..."
    log_info "Port: $PORT"
    log_info "Webhook URL: ${WEBHOOK_URL:-not configured}"
    log_info "Database: Using external PostgreSQL (DATABASE_URL is set)"
    
    # Export environment for uvicorn
    export PORT
    export WEBHOOK_PATH
    
    # Start uvicorn with the webhook main app
    # Using absolute path for logs
    exec python3 -m uvicorn app.webhook_main:app \
        --host 0.0.0.0 \
        --port "$PORT" \
        --workers 1 \
        --log-level "$LOG_LEVEL" \
        --access-log \
        2>&1 | tee /app/logs/bot.log
}

# =============================================================================
# Main Execution
# =============================================================================

main() {
    echo "=============================================="
    echo "🚀 Telegram Quiz Bot - Koyeb Deployment"
    echo "=============================================="
    echo ""
    
    log_info "Project root: $PROJECT_ROOT"
    log_info "Python: $(python3 --version)"
    log_info "Port: $PORT"
    log_info "Using PostgreSQL (no /data directory needed)"
    
    # Run pre-flight checks
    preflight_checks
    
    # Initialize database (creates tables if needed)
    init_database
    
    # Start the application
    start_app
}

# Run main function
main "$@"

