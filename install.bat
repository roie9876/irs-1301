@echo off
chcp 65001 >nul 2>&1
title irs-1301 — התקנה

echo.
echo ============================================
echo   התקנת עוזר דוח שנתי 1301
echo ============================================
echo.

:: Check Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [X] Python לא נמצא. הורד מ- https://www.python.org/downloads/
    echo     חשוב: סמן "Add Python to PATH" בהתקנה!
    pause
    exit /b 1
)

:: Check Node
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo [X] Node.js לא נמצא. הורד מ- https://nodejs.org/
    pause
    exit /b 1
)

echo [✓] Python ו-Node.js נמצאו
echo.

:: Create venv if needed
if not exist ".venv\Scripts\python.exe" (
    echo יוצר סביבה וירטואלית...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo [X] יצירת סביבה וירטואלית נכשלה
        pause
        exit /b 1
    )
)
echo [✓] סביבה וירטואלית קיימת
echo.

:: Install backend dependencies
echo מתקין חבילות Python...
.venv\Scripts\pip install -r backend\requirements.txt --quiet
if %errorlevel% neq 0 (
    echo [X] התקנת חבילות Python נכשלה
    pause
    exit /b 1
)
echo [✓] חבילות Python הותקנו
echo.

:: Install frontend dependencies
echo מתקין חבילות Node.js...
cd frontend
call npm install --silent
if %errorlevel% neq 0 (
    echo [X] התקנת חבילות Node.js נכשלה
    pause
    exit /b 1
)
cd ..
echo [✓] חבילות Node.js הותקנו
echo.

echo ============================================
echo   ההתקנה הושלמה בהצלחה!
echo   להפעלה: לחץ פעמיים על start.bat
echo ============================================
echo.
pause
