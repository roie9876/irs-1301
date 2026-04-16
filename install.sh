#!/bin/bash
set -e

echo ""
echo "============================================"
echo "  התקנת עוזר דוח שנתי 1301"
echo "============================================"
echo ""

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "[X] Python3 לא נמצא. התקן עם: brew install python"
    exit 1
fi

# Check Node
if ! command -v node &>/dev/null; then
    echo "[X] Node.js לא נמצא. התקן עם: brew install node"
    exit 1
fi

echo "[✓] Python ו-Node.js נמצאו"
echo ""

# Create venv if needed
if [ ! -f ".venv/bin/python" ]; then
    echo "יוצר סביבה וירטואלית..."
    python3 -m venv .venv
fi
echo "[✓] סביבה וירטואלית קיימת"
echo ""

# Install backend
echo "מתקין חבילות Python..."
.venv/bin/pip install -r backend/requirements.txt --quiet
echo "[✓] חבילות Python הותקנו"
echo ""

# Install frontend
echo "מתקין חבילות Node.js..."
cd frontend && npm install --silent && cd ..
echo "[✓] חבילות Node.js הותקנו"
echo ""

echo "============================================"
echo "  ההתקנה הושלמה בהצלחה!"
echo "  להפעלה: ./start.sh"
echo "============================================"
echo ""
