@echo off
REM ============================================================
REM Code Review Agent - Full Application Starter
REM Starts both backend and frontend automatically
REM ============================================================

setlocal enabledelayedexpansion

REM Navigate to project directory
cd /d E:\PycharmProjects\code-review-agent

echo.
echo ============================================================
echo Code Review Agent - Starting Full Application
echo ============================================================
echo.

REM Check if venv is activated
if not defined VIRTUAL_ENV (
    echo Activating virtual environment...
    call .venv\Scripts\activate.bat
    echo Virtual environment activated
) else (
    echo Virtual environment already active
)

REM Load .env into this session so child windows inherit it.
REM (pydantic-settings reads .env for Python processes, but uvicorn reload/streamlit Windows shells
REM can miss it depending on how they're launched. This makes it explicit.)
if exist .env (
    for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
        set "line=%%A"
        if not "!line!"=="" (
            if not "!line:~0,1!"=="#" (
                set "key=%%A"
                set "val=%%B"
                if not "!key!"=="" set "!key!=!val!"
            )
        )
    )
)

echo.
echo ============================================================
echo Starting Backend Server...
echo ============================================================
echo.
echo Backend will run on: http://127.0.0.1:8000
echo API Docs available at: http://127.0.0.1:8000/docs
echo.

REM Start backend in a new window (inherits env from this script)
start "Code Review Agent - Backend" cmd /k "python -m uvicorn app.main:app --reload"

REM Wait for backend to start
timeout /t 3 /nobreak

echo.
echo ============================================================
echo Starting Frontend Interface...
echo ============================================================
echo.
echo Frontend will run on: http://localhost:8501
echo.

REM Start frontend in a new window (inherits env from this script)
start "Code Review Agent - Frontend" cmd /k "streamlit run ui.py"

REM Wait a bit for frontend to start
timeout /t 2 /nobreak

echo.
echo ============================================================
echo SUCCESS! Application is Starting
echo ============================================================
echo.
echo BACKEND:  http://127.0.0.1:8000
echo FRONTEND: http://localhost:8501
echo API DOCS: http://127.0.0.1:8000/docs
echo.
echo Two windows should have opened:
echo 1. Backend Server (FastAPI)
echo 2. Frontend UI (Streamlit)
echo.
echo Open your browser to: http://localhost:8501
echo.
echo To stop:
echo - Close both windows
echo - Or press CTRL+C in each window
echo.
echo ============================================================
echo.

pause
