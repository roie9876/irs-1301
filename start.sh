#!/bin/bash
set -e

echo ""
echo "============================================"
echo "  מפעיל את עוזר דוח שנתי 1301..."
echo "============================================"
echo ""

# Check venv
if [ ! -f ".venv/bin/python" ]; then
    echo "[X] סביבה וירטואלית לא נמצאה. הרץ קודם: ./install.sh"
    exit 1
fi

if [ ! -d "frontend/node_modules" ]; then
    echo "[X] חבילות לא הותקנו. הרץ קודם: ./install.sh"
    exit 1
fi

cleanup() {
    echo ""
    echo "סוגר את האפליקציה..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit 0
}
trap cleanup INT TERM

# Start backend
echo "מפעיל Backend..."
cd backend && ../.venv/bin/python -m uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!
cd ..

sleep 2

# Start frontend
echo "מפעיל Frontend..."
cd frontend && npm run dev &
FRONTEND_PID=$!
cd ..

sleep 2

echo ""
echo "============================================"
echo "  האפליקציה רצה!"
echo ""
echo "  http://localhost:5173"
echo ""
echo "  לסגירה: Ctrl+C"
echo "============================================"
echo ""

# Open browser
if command -v open &>/dev/null; then
    open http://localhost:5173
elif command -v xdg-open &>/dev/null; then
    xdg-open http://localhost:5173
fi

wait
