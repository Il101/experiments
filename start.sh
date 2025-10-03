#!/bin/bash

# Breakout Bot Trading System - Startup Script
# This script starts all components of the trading system

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
LOG_DIR="logs"
PID_DIR="pids"

# Create necessary directories
mkdir -p $LOG_DIR
mkdir -p $PID_DIR

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
    echo "║                              Startup Script                                ║"
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

# Function to kill process on port
kill_port() {
    local port=$1
    local pid=$(lsof -ti:$port)
    if [ ! -z "$pid" ]; then
        print_warning "Killing process on port $port (PID: $pid)"
        kill -9 $pid 2>/dev/null || true
        sleep 2
    fi
}

# Function to start API server
start_api() {
    print_status "Starting API server on port $API_PORT..."
    
    if check_port $API_PORT; then
        print_warning "Port $API_PORT is already in use. Attempting to free it..."
        kill_port $API_PORT
    fi
    
    # Start API server in background
    nohup python3 -m uvicorn breakout_bot.api.main:app --host 0.0.0.0 --port $API_PORT --reload > $LOG_DIR/api.log 2>&1 &
    echo $! > $PID_DIR/api.pid
    
    # Wait for API to start
    print_status "Waiting for API server to start..."
    for i in {1..30}; do
        if curl -s http://localhost:$API_PORT/api/health >/dev/null 2>&1; then
            print_success "API server started successfully on port $API_PORT"
            return 0
        fi
        sleep 1
    done
    
    print_error "Failed to start API server"
    return 1
}

# Function to start frontend
start_frontend() {
    print_status "Starting frontend development server on port $FRONTEND_PORT..."
    
    if check_port $FRONTEND_PORT; then
        print_warning "Port $FRONTEND_PORT is already in use. Attempting to free it..."
        kill_port $FRONTEND_PORT
    fi
    
    # Start frontend in background
    cd frontend
    nohup npm run dev -- --port $FRONTEND_PORT > ../$LOG_DIR/frontend.log 2>&1 &
    echo $! > ../$PID_DIR/frontend.pid
    cd ..
    
    # Wait for frontend to start
    print_status "Waiting for frontend to start..."
    for i in {1..30}; do
        if curl -s http://localhost:$FRONTEND_PORT >/dev/null 2>&1; then
            print_success "Frontend started successfully on port $FRONTEND_PORT"
            return 0
        fi
        sleep 1
    done
    
    print_error "Failed to start frontend"
    return 1
}

# Function to start trading engine
start_engine() {
    print_status "Starting trading engine..."
    
    # Start engine with breakout_v1 preset
    curl -X POST http://localhost:$API_PORT/api/engine/start \
        -H "Content-Type: application/json" \
        -d '{"preset": "breakout_v1"}' >/dev/null 2>&1
    
    # Wait for engine to start
    sleep 3
    
    # Check engine status
    local status=$(curl -s http://localhost:$API_PORT/api/engine/status | python3 -c "import json, sys; data=json.load(sys.stdin); print(data['state'])" 2>/dev/null || echo "error")
    
    if [ "$status" != "error" ]; then
        print_success "Trading engine started successfully (State: $status)"
        return 0
    else
        print_warning "Trading engine started but may be in error state"
        return 1
    fi
}

# Function to show system status
show_status() {
    print_status "System Status:"
    echo ""
    
    # API Status
    if check_port $API_PORT; then
        local api_status=$(curl -s http://localhost:$API_PORT/api/health | python3 -c "import json, sys; data=json.load(sys.stdin); print(data['status'])" 2>/dev/null || echo "error")
        print_success "API Server: Running on port $API_PORT (Status: $api_status)"
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
    if check_port $API_PORT; then
        local engine_status=$(curl -s http://localhost:$API_PORT/api/engine/status | python3 -c "import json, sys; data=json.load(sys.stdin); print(data['state'])" 2>/dev/null || echo "error")
        print_success "Trading Engine: $engine_status"
    else
        print_error "Trading Engine: Not accessible"
    fi
    
    echo ""
    print_status "Access URLs:"
    echo "  🌐 Frontend: http://localhost:$FRONTEND_PORT"
    echo "  🔌 API: http://localhost:$API_PORT"
    echo "  📊 API Docs: http://localhost:$API_PORT/docs"
    echo "  🔍 Health: http://localhost:$API_PORT/api/health"
    echo "  📈 Engine Status: http://localhost:$API_PORT/api/engine/status"
    echo ""
}

# Function to stop all services
stop_all() {
    print_status "Stopping all services..."
    
    # Stop API
    if [ -f $PID_DIR/api.pid ]; then
        local api_pid=$(cat $PID_DIR/api.pid)
        if kill -0 $api_pid 2>/dev/null; then
            print_status "Stopping API server (PID: $api_pid)..."
            kill $api_pid
        fi
        rm -f $PID_DIR/api.pid
    fi
    
    # Stop Frontend
    if [ -f $PID_DIR/frontend.pid ]; then
        local frontend_pid=$(cat $PID_DIR/frontend.pid)
        if kill -0 $frontend_pid 2>/dev/null; then
            print_status "Stopping frontend (PID: $frontend_pid)..."
            kill $frontend_pid
        fi
        rm -f $PID_DIR/frontend.pid
    fi
    
    # Kill any remaining processes on our ports
    kill_port $API_PORT
    kill_port $FRONTEND_PORT
    
    print_success "All services stopped"
}

# Function to show logs
show_logs() {
    local service=$1
    case $service in
        "api")
            print_status "Showing API logs (last 50 lines):"
            tail -50 $LOG_DIR/api.log
            ;;
        "frontend")
            print_status "Showing frontend logs (last 50 lines):"
            tail -50 $LOG_DIR/frontend.log
            ;;
        "all")
            print_status "Showing all logs:"
            echo "=== API LOGS ==="
            tail -20 $LOG_DIR/api.log
            echo ""
            echo "=== FRONTEND LOGS ==="
            tail -20 $LOG_DIR/frontend.log
            ;;
        *)
            print_error "Usage: $0 logs [api|frontend|all]"
            ;;
    esac
}

# Function to show help
show_help() {
    echo "Breakout Bot Trading System - Startup Script"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  start     Start all services (default)"
    echo "  stop      Stop all services"
    echo "  restart   Restart all services"
    echo "  status    Show system status"
    echo "  logs      Show logs (api|frontend|all)"
    echo "  help      Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 start"
    echo "  $0 status"
    echo "  $0 logs api"
    echo "  $0 stop"
}

# Main script logic
main() {
    local command=${1:-start}
    
    case $command in
        "start")
            print_header
            print_status "Starting Breakout Bot Trading System..."
            echo ""
            
            # Check dependencies
            if ! command -v python3 &> /dev/null; then
                print_error "Python3 is not installed"
                exit 1
            fi
            
            if ! command -v npm &> /dev/null; then
                print_error "npm is not installed"
                exit 1
            fi
            
            # Start services
            start_api
            start_frontend
            start_engine
            
            echo ""
            show_status
            print_success "Breakout Bot Trading System started successfully!"
            print_status "Press Ctrl+C to stop all services"
            
            # Keep script running and show logs
            while true; do
                sleep 10
                if ! check_port $API_PORT || ! check_port $FRONTEND_PORT; then
                    print_error "One or more services stopped unexpectedly"
                    break
                fi
            done
            ;;
        "stop")
            print_header
            stop_all
            ;;
        "restart")
            print_header
            stop_all
            sleep 2
            main start
            ;;
        "status")
            print_header
            show_status
            ;;
        "logs")
            show_logs $2
            ;;
        "help")
            show_help
            ;;
        *)
            print_error "Unknown command: $command"
            show_help
            exit 1
            ;;
    esac
}

# Trap Ctrl+C to stop all services
trap 'echo ""; print_status "Received interrupt signal..."; stop_all; exit 0' INT

# Run main function
main "$@"
