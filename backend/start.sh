#!/bin/bash
# AlphaStream Backend Startup Script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

mkdir -p logs

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║      AlphaStream Backend Startup       ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"

# Load .env if present
if [ -f .env ]; then
    export $(grep -v '^#' .env | grep -v '^$' | xargs) 2>/dev/null || true
fi

ENABLE_PATHWAY="${ENABLE_PATHWAY:-false}"
RAG_PID=""
BACKEND_PID=""

cleanup() {
    echo -e "\n${YELLOW}Shutting down...${NC}"
    [ -n "$RAG_PID" ] && kill "$RAG_PID" 2>/dev/null && wait "$RAG_PID" 2>/dev/null || true
    [ -n "$BACKEND_PID" ] && kill "$BACKEND_PID" 2>/dev/null && wait "$BACKEND_PID" 2>/dev/null || true
    echo -e "${GREEN}Stopped.${NC}"
    exit 0
}
trap cleanup SIGINT SIGTERM

# ── Pathway Adaptive RAG (optional) ──────────────────────────────────────────
if [ "$ENABLE_PATHWAY" = "true" ]; then
    echo -e "\n${GREEN}[1/2] Starting Pathway Adaptive RAG Server (port 8001)...${NC}"
    uv run python -m src.pipeline.adaptive_rag_server > logs/adaptive_rag.log 2>&1 &
    RAG_PID=$!
    echo "  → PID: $RAG_PID  |  Logs: logs/adaptive_rag.log"
    sleep 3
    if ! kill -0 "$RAG_PID" 2>/dev/null; then
        echo -e "${YELLOW}  ⚠ Adaptive RAG failed to start — falling back to manual RAG${NC}"
        RAG_PID=""
    fi
    STEP="[2/2]"
else
    echo -e "\n${YELLOW}  Pathway disabled (ENABLE_PATHWAY=false) — using manual RAG${NC}"
    STEP="[1/1]"
fi

# ── Main Backend ──────────────────────────────────────────────────────────────
echo -e "\n${GREEN}${STEP} Starting backend (port 8000)...${NC}"
uv run python -m uvicorn src.api.app:app --host 0.0.0.0 --port 8000 2>&1 | tee logs/backend.log &
BACKEND_PID=$!

echo ""
echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║         AlphaStream Ready!             ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo ""
echo "  🚀 Backend API:  http://localhost:8000"
echo "  📊 Health check: http://localhost:8000/health"
[ -n "$RAG_PID" ] && echo "  📡 Adaptive RAG: http://localhost:8001"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop  |  Logs: logs/backend.log${NC}"
echo ""

# Keep script alive so the trap can catch Ctrl+C and cleanly kill children.
# 'wait' with no args waits for all background jobs; it is interruptible by signals.
wait
