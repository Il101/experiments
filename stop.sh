#!/bin/bash

# Breakout Bot Trading System - Stop Script
# This script stops all components of the trading system

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
API_PORT=8000
FRONTEND_PORT=5173
PID_DIR="pids"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to check if port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Function to kill process on port
kill_port() {
    local port=$1
    local pid=$(lsof -ti:$port)
    if [ ! -z "$pid" ]; then
        print_warning "Killing process on port $port (PID: $pid)"
        kill -9 $pid 2>/dev/null || true
        sleep 1
    fi
}

# Function to stop all services
stop_all() {
    print_status "Stopping Breakout Bot Trading System..."
    echo ""
    
    # Stop API
    if [ -f $PID_DIR/api.pid ]; then
        local api_pid=$(cat $PID_DIR/api.pid)
        if kill -0 $api_pid 2>/dev/null; then
            print_status "Stopping API server (PID: $api_pid)..."
            kill $api_pid
            sleep 2
        fi
        rm -f $PID_DIR/api.pid
    fi
    
    # Stop Frontend
    if [ -f $PID_DIR/frontend.pid ]; then
        local frontend_pid=$(cat $PID_DIR/frontend.pid)
        if kill -0 $frontend_pid 2>/dev/null; then
            print_status "Stopping frontend (PID: $frontend_pid)..."
            kill $frontend_pid
            sleep 2
        fi
        rm -f $PID_DIR/frontend.pid
    fi
    
    # Kill any remaining processes on our ports
    if check_port $API_PORT; then
        kill_port $API_PORT
    fi
    
    if check_port $FRONTEND_PORT; then
        kill_port $FRONTEND_PORT
    fi
    
    # Clean up PID directory if empty
    if [ -d $PID_DIR ] && [ -z "$(ls -A $PID_DIR)" ]; then
        rmdir $PID_DIR
    fi
    
    print_success "All services stopped successfully"
}

# Main script logic
main() {
    stop_all
}

# Run main function
main "$@"
