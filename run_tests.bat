@echo off
REM Testing Commands for Code Review Agent
REM Run these commands from project root: E:\PycharmProjects\code-review-agent

setlocal enabledelayedexpansion

REM ============================================================
REM MENU
REM ============================================================

:menu
cls
echo.
echo ============================================================
echo Code Review Agent - Testing Commands
echo ============================================================
echo.
echo QUICK COMMANDS:
echo  1. Run all tests
echo  2. Run all tests (verbose)
echo  3. Run all tests (with output)
echo  4. Run specific test file
echo.
echo COMPONENT TESTS:
echo  5. Test static checks
echo  6. Test compression
echo  7. Test LLM client
echo  8. Test ScaleDown
echo  9. Test API endpoint
echo 10. Test issue ranking
echo.
echo ADVANCED:
echo 11. Stop on first failure
echo 12. Show slowest tests
echo 13. Generate coverage report
echo 14. Run with debugging
echo.
echo CONFIGURATION:
echo 15. Verify ScaleDown config
echo 16. Verify API key
echo.
echo 17. Exit
echo.
echo ============================================================
echo.

set /p choice="Enter your choice (1-17): "

if "%choice%"=="1" goto test_all
if "%choice%"=="2" goto test_verbose
if "%choice%"=="3" goto test_output
if "%choice%"=="4" goto test_file
if "%choice%"=="5" goto test_static
if "%choice%"=="6" goto test_compress
if "%choice%"=="7" goto test_llm
if "%choice%"=="8" goto test_scaledown
if "%choice%"=="9" goto test_api
if "%choice%"=="10" goto test_ranking
if "%choice%"=="11" goto test_fail_fast
if "%choice%"=="12" goto test_slowest
if "%choice%"=="13" goto test_coverage
if "%choice%"=="14" goto test_debug
if "%choice%"=="15" goto verify_scaledown
if "%choice%"=="16" goto verify_api
if "%choice%"=="17" goto end

goto menu

REM ============================================================
REM COMMANDS
REM ============================================================

:test_all
echo Running all tests...
pytest
pause
goto menu

:test_verbose
echo Running all tests (verbose)...
pytest -v
pause
goto menu

:test_output
echo Running all tests (with output)...
pytest -v -s
pause
goto menu

:test_file
set /p file="Enter test file (e.g., test_compressor.py): "
echo Running tests from !file!...
pytest tests/!file! -v
pause
goto menu

:test_static
echo Testing static checks...
pytest tests/test_static_checks.py -v
pause
goto menu

:test_compress
echo Testing compression...
pytest tests/test_compressor.py -v
pause
goto menu

:test_llm
echo Testing LLM client...
pytest tests/test_llm_client.py -v
pause
goto menu

:test_scaledown
echo Testing ScaleDown...
pytest tests/test_scaledown_compression.py -v
pause
goto menu

:test_api
echo Testing API endpoint...
pytest tests/test_api_review_endpoint.py -v
pause
goto menu

:test_ranking
echo Testing issue ranking...
pytest tests/test_ranking.py -v
pause
goto menu

:test_fail_fast
echo Running tests (stop on first failure)...
pytest -x -v
pause
goto menu

:test_slowest
echo Running tests (show slowest 5)...
pytest --durations=5 -v
pause
goto menu

:test_coverage
echo Generating coverage report...
pytest --cov=app --cov-report=html -v
echo.
echo Coverage report saved to: htmlcov\index.html
pause
goto menu

:test_debug
echo Running tests with debugging (drops into debugger on failure)...
pytest -v -s --pdb
pause
goto menu

:verify_scaledown
echo Verifying ScaleDown configuration...
python test_scaledown_provider.py
pause
goto menu

:verify_api
echo Verifying API key...
python validate_api_key.py
pause
goto menu

:end
echo.
echo Thank you for testing!
echo.
exit /b 0
