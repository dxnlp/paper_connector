#!/bin/bash

# HF Papers Explorer - Startup Script
# This script starts both the backend and frontend servers

echo "🚀 Starting HF Papers Explorer..."

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down servers...${NC}"
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start backend
echo -e "${GREEN}Starting backend server...${NC}"
cd "$SCRIPT_DIR/backend"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment and install dependencies
source venv/bin/activate
pip install -r requirements.txt -q

# Start FastAPI backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
echo -e "${GREEN}Backend started on http://localhost:8000${NC}"

# Wait a bit for backend to start
sleep 2

# Start frontend (serve pre-built dist)
echo -e "${GREEN}Starting frontend server...${NC}"
cd "$SCRIPT_DIR/frontend"

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi

# Build if dist doesn't exist
if [ ! -d "dist" ]; then
    echo "Building frontend..."
    npm run build
fi

# Serve the pre-built dist folder using npx serve
npx serve dist -l 5173 -s &
FRONTEND_PID=$!
echo -e "${GREEN}Frontend started on http://localhost:5173${NC}"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  HF Papers Explorer is running!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "  Backend API:  ${YELLOW}http://localhost:8000${NC}"
echo -e "  Frontend UI:  ${YELLOW}http://localhost:5173${NC}"
echo -e "  API Docs:     ${YELLOW}http://localhost:8000/docs${NC}"
echo ""
echo -e "  Press Ctrl+C to stop all servers"
echo ""

# Wait for both processes
wait
