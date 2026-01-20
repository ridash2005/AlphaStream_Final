#!/bin/bash
# AlphaStream Backend Startup Script
# Starts Adaptive RAG server first, then the main backend

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Create logs directory
mkdir -p logs

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║      AlphaStream Backend Startup       ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}Shutting down services...${NC}"
    
    # Kill Adaptive RAG server
    if [ ! -z "$RAG_PID" ] && kill -0 $RAG_PID 2>/dev/null; then
        echo "Stopping Adaptive RAG Server (PID: $RAG_PID)..."
        kill $RAG_PID 2>/dev/null || true
        wait $RAG_PID 2>/dev/null || true
    fi
    
    # Kill main backend
    if [ ! -z "$BACKEND_PID" ] && kill -0 $BACKEND_PID 2>/dev/null; then
        echo "Stopping Backend Server (PID: $BACKEND_PID)..."
        kill $BACKEND_PID 2>/dev/null || true
        wait $BACKEND_PID 2>/dev/null || true
    fi
    
    echo -e "${GREEN}All services stopped.${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

# ============================================================================
# Step 1: Start Adaptive RAG Server
# ============================================================================
echo -e "\n${GREEN}[1/2] Starting Pathway Adaptive RAG Server (port 8001)...${NC}"
uv run python -m src.pipeline.adaptive_rag_server > logs/adaptive_rag.log 2>&1 &
RAG_PID=$!
echo "  → PID: $RAG_PID"
echo "  → Logs: logs/adaptive_rag.log"

# Wait for Adaptive RAG to initialize
echo "  → Waiting for server to initialize..."
sleep 3

# Check if it's still running
if ! kill -0 $RAG_PID 2>/dev/null; then
    echo -e "${YELLOW}Warning: Adaptive RAG server may have failed to start.${NC}"
    echo "Check logs/adaptive_rag.log for details."
fi

# ============================================================================
# Step 2: Start Main Backend
# ============================================================================
echo -e "\n${GREEN}[2/2] Starting Main Backend Server (port 8000)...${NC}"
uv run uvicorn src.api.app:app --host 0.0.0.0 --port 8000 2>&1 | tee logs/backend.log &
BACKEND_PID=$!
echo "  → PID: $BACKEND_PID"
echo "  → Logs: logs/backend.log"

# ============================================================================
# Status
# ============================================================================
echo -e "\n${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║         Services Started!              ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo ""
echo "  📡 Adaptive RAG: http://localhost:8001/v2/answer"
echo "  🚀 Backend API:  http://localhost:8000"
echo "  📊 Health Check: http://localhost:8000/health"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
echo ""

# Wait for backend process (foreground wait)
wait $BACKEND_PID
