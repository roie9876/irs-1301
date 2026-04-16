@echo off
chcp 65001 >nul 2>&1
title irs-1301 — עוזר דוח שנתי

echo.
echo ============================================
echo   מפעיל את עוזר דוח שנתי 1301...
echo ============================================
echo.

:: Check venv exists
if not exist ".venv\Scripts\python.exe" (
    echo [X] סביבה וירטואלית לא נמצאה. הרץ קודם install.bat
    pause
    exit /b 1
)

:: Check node_modules
if not exist "frontend\node_modules" (
    echo [X] חבילות לא הותקנו. הרץ קודם install.bat
    pause
    exit /b 1
)

echo מפעיל Backend (שרת API)...
start "irs-1301 Backend" /min cmd /c ".venv\Scripts\python -m uvicorn app.main:app --reload --port 8000 --app-dir backend"

:: Wait for backend to start
echo ממתין לשרת...
timeout /t 3 /nobreak >nul

echo מפעיל Frontend...
start "irs-1301 Frontend" /min cmd /c "cd frontend && npm run dev"

:: Wait for frontend to start
timeout /t 3 /nobreak >nul

echo.
echo ============================================
echo   האפליקציה רצה!
echo   פותח את הדפדפן...
echo.
echo   http://localhost:5173
echo.
echo   לסגירה: סגור את החלון הזה
echo ============================================
echo.

:: Open browser
start http://localhost:5173

echo לחץ על מקש כלשהו לסגירת האפליקציה...
pause >nul

:: Kill the backend and frontend processes
echo סוגר את האפליקציה...
taskkill /fi "WINDOWTITLE eq irs-1301 Backend*" /f >nul 2>&1
taskkill /fi "WINDOWTITLE eq irs-1301 Frontend*" /f >nul 2>&1
echo נסגר. להתראות!
