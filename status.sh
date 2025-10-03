#!/bin/bash

# Breakout Bot Trading System - Status Script
# This script shows the status of all components

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
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

print_header() {
    echo -e "${PURPLE}"
    echo "╔══════════════════════════════════════════════════════════════════════════════╗"
    echo "║                        BREAKOUT BOT TRADING SYSTEM                          ║"
    echo "║                              Status Report                                 ║"
    echo "╚══════════════════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
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

# Function to get API status
get_api_status() {
    if check_port $API_PORT; then
        local api_status=$(curl -s http://localhost:$API_PORT/api/health | python3 -c "import json, sys; data=json.load(sys.stdin); print(data['status'])" 2>/dev/null || echo "error")
        echo "$api_status"
    else
        echo "not_running"
    fi
}

# Function to get engine status
get_engine_status() {
    if check_port $API_PORT; then
        local engine_status=$(curl -s http://localhost:$API_PORT/api/engine/status | python3 -c "import json, sys; data=json.load(sys.stdin); print(data['state'])" 2>/dev/null || echo "error")
        echo "$engine_status"
    else
        echo "not_accessible"
    fi
}

# Function to get engine preset
get_engine_preset() {
    if check_port $API_PORT; then
        local preset=$(curl -s http://localhost:$API_PORT/api/engine/status | python3 -c "import json, sys; data=json.load(sys.stdin); print(data['preset'])" 2>/dev/null || echo "unknown")
        echo "$preset"
    else
        echo "unknown"
    fi
}

# Function to get engine mode
get_engine_mode() {
    if check_port $API_PORT; then
        local mode=$(curl -s http://localhost:$API_PORT/api/engine/status | python3 -c "import json, sys; data=json.load(sys.stdin); print(data['mode'])" 2>/dev/null || echo "unknown")
        echo "$mode"
    else
        echo "unknown"
    fi
}

# Function to get positions count
get_positions_count() {
    if check_port $API_PORT; then
        local positions=$(curl -s http://localhost:$API_PORT/api/trading/positions | python3 -c "import json, sys; data=json.load(sys.stdin); print(len(data))" 2>/dev/null || echo "0")
        echo "$positions"
    else
        echo "0"
    fi
}

# Function to get logs count
get_logs_count() {
    if check_port $API_PORT; then
        local logs=$(curl -s http://localhost:$API_PORT/api/logs | python3 -c "import json, sys; data=json.load(sys.stdin); print(len(data))" 2>/dev/null || echo "0")
        echo "$logs"
    else
        echo "0"
    fi
}

# Function to show system status
show_status() {
    print_header
    echo ""
    
    # API Status
    local api_status=$(get_api_status)
    if [ "$api_status" = "healthy" ]; then
        print_success "API Server: Running on port $API_PORT (Status: $api_status)"
    elif [ "$api_status" = "error" ]; then
        print_warning "API Server: Running on port $API_PORT (Status: $api_status)"
    else
        print_error "API Server: Not running"
    fi
    
    # Frontend Status
    if check_port $FRONTEND_PORT; then
        print_success "Frontend: Running on port $FRONTEND_PORT"
    else
        print_error "Frontend: Not running"
    fi
    
    # Engine Status
    local engine_status=$(get_engine_status)
    local engine_preset=$(get_engine_preset)
    local engine_mode=$(get_engine_mode)
    
    if [ "$engine_status" = "not_accessible" ]; then
        print_error "Trading Engine: Not accessible"
    else
        print_success "Trading Engine: $engine_status (Preset: $engine_preset, Mode: $engine_mode)"
    fi
    
    # Positions
    local positions_count=$(get_positions_count)
    print_status "Open Positions: $positions_count"
    
    # Logs
    local logs_count=$(get_logs_count)
    print_status "System Logs: $logs_count entries"
    
    echo ""
    print_status "Access URLs:"
    echo "  🌐 Frontend: http://localhost:$FRONTEND_PORT"
    echo "  🔌 API: http://localhost:$API_PORT"
    echo "  📊 API Docs: http://localhost:$API_PORT/docs"
    echo "  🔍 Health: http://localhost:$API_PORT/api/health"
    echo "  📈 Engine Status: http://localhost:$API_PORT/api/engine/status"
    echo "  📋 Logs: http://localhost:$API_PORT/api/logs"
    echo "  📊 Scanner: http://localhost:$API_PORT/api/scanner/last"
    echo "  💼 Positions: http://localhost:$API_PORT/api/trading/positions"
    echo ""
    
    # Show recent logs if available
    if [ -f "logs/api.log" ]; then
        print_status "Recent API Logs (last 5 lines):"
        tail -5 logs/api.log | sed 's/^/  /'
        echo ""
    fi
    
    if [ -f "logs/frontend.log" ]; then
        print_status "Recent Frontend Logs (last 5 lines):"
        tail -5 logs/frontend.log | sed 's/^/  /'
        echo ""
    fi
}

# Function to show help
show_help() {
    echo "Breakout Bot Trading System - Status Script"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help     Show this help message"
    echo "  -v, --verbose  Show verbose output"
    echo ""
    echo "This script shows the current status of all system components."
}

# Main script logic
main() {
    local verbose=false
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -v|--verbose)
                verbose=true
                shift
                ;;
            *)
                print_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    show_status
}

# Run main function
main "$@"
