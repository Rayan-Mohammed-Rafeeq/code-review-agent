@echo off
setlocal

cd /d %~dp0

echo.
echo ===============================
echo Code Review Agent - Checks
echo ===============================
echo.

echo [1/3] Ruff (lint)
ruff check .
if errorlevel 1 goto fail

echo.
echo [2/3] Ruff (format check)
ruff format --check .
if errorlevel 1 goto fail

echo.
echo [3/3] Pyright (types)
pyright
if errorlevel 1 goto fail

echo.
echo All checks passed.
exit /b 0

:fail
echo.
echo Checks failed.
exit /b 1

