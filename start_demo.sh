#!/bin/bash
# AlphaStream Demo Startup Script
# Starts Adaptive RAG server, Backend, and Frontend.
# Enhanced visibility into Pathway loading.

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║      AlphaStream DEMO ENVIRONMENT          ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}"

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}Shutting down demo services...${NC}"
    if [ ! -z "$RAG_PID" ]; then kill $RAG_PID 2>/dev/null || true; fi
    if [ ! -z "$BACKEND_PID" ]; then kill $BACKEND_PID 2>/dev/null || true; fi
    if [ ! -z "$FRONTEND_PID" ]; then kill $FRONTEND_PID 2>/dev/null || true; fi
    if [ ! -z "$TAIL_PID" ]; then kill $TAIL_PID 2>/dev/null || true; fi
    exit 0
}
trap cleanup SIGINT SIGTERM

# Ensure logs directory exists
mkdir -p backend/logs

# -----------------
# 1. START PATHWAY RAG
# -----------------
echo -e "\n${GREEN}[1/3] Starting Pathway Adaptive RAG Server...${NC}"
echo "      (Tailing logs to show loading status)"

cd backend
uv run python -m src.pipeline.adaptive_rag_server > logs/adaptive_rag_demo.log 2>&1 &
RAG_PID=$!
cd ..

# Tail the logs in the background to show progress on console
tail -f backend/logs/adaptive_rag_demo.log | grep --line-buffered -E "Pathway|Loading|Ingesting|Server started" &
TAIL_PID=$!

# Wait a bit for initialization
sleep 5

# -----------------
# 2. START BACKEND
# -----------------
echo -e "\n${GREEN}[2/3] Starting Main Backend Server...${NC}"
cd backend
uv run uvicorn src.api.app:app --host 0.0.0.0 --port 8000 > logs/backend_demo.log 2>&1 &
BACKEND_PID=$!
cd ..

sleep 2

# -----------------
# 3. START FRONTEND
# -----------------
echo -e "\n${GREEN}[3/3] Starting Frontend...${NC}"
cd frontend
npm run dev > /dev/null 2>&1 &
FRONTEND_PID=$!
cd ..

echo -e "\n${GREEN}╔════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║         DEMO ENVIRONMENT READY!            ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════╝${NC}"
echo ""
echo "  👉 Frontend:     http://localhost:5173"
echo "  👉 Backend API:  http://localhost:8000"
echo ""
echo -e "${YELLOW}To run a demo scenario open a NEW terminal:${NC}"
echo "  python scripts/run_demo.py --ticker AAPL --scenario bullish"
echo ""
echo -e "${BLUE}Streaming Pathway & Backend logs below... (Press Ctrl+C to stop)${NC}"

# Stop the specific tail and tail both logs together
kill $TAIL_PID 2>/dev/null || true
tail -f backend/logs/adaptive_rag_demo.log backend/logs/backend_demo.log
