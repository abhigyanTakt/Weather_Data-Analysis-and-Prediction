@echo off
setlocal
title ClimaTrend Weather and Climate Intelligence Platform
cd /d "%~dp0"

echo =====================================================================
echo       ClimaTrend -- Weather and Climate Intelligence Platform
echo =====================================================================
echo.

:: 1. Check if virtual environment exists
if not exist ".venv\Scripts\activate.bat" (
    echo [!] Virtual environment not found in .venv.
    echo [*] Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment. Ensure Python 3.10+ is installed and in your PATH.
        pause
        exit /b 1
    )
    echo [*] Installing dependencies from requirements.txt...
    call .venv\Scripts\activate.bat
    python -m pip install --upgrade pip
    pip install -r requirements.txt
) else (
    call .venv\Scripts\activate.bat
)

:: 2. Auto-initialize .env if not present
if not exist ".env" (
    if exist ".env.example" (
        echo [*] Initializing .env configuration from .env.example template...
        copy .env.example .env >nul
    )
)

:: 3. Command Line Argument Routing
if /i "%~1"=="test" goto run_tests
if /i "%~1"=="--test" goto run_tests
if /i "%~1"=="scheduler" goto run_scheduler
if /i "%~1"=="--scheduler" goto run_scheduler
if /i "%~1"=="backtest" goto run_backtest
if /i "%~1"=="--backtest" goto run_backtest
if /i "%~1"=="init-db" goto run_init_db
if /i "%~1"=="--init-db" goto run_init_db
if /i "%~1"=="db" goto run_init_db
if /i "%~1"=="check" goto run_check
if /i "%~1"=="--check" goto run_check
if /i "%~1"=="doctor" goto run_check
if /i "%~1"=="clean" goto run_clean
if /i "%~1"=="--clean" goto run_clean
if /i "%~1"=="install" goto install_deps
if /i "%~1"=="--install" goto install_deps
if /i "%~1"=="help" goto show_help
if /i "%~1"=="--help" goto show_help
if /i "%~1"=="-h" goto show_help
if /i "%~1"=="/?" goto show_help

:: Default: Run Streamlit Dashboard (forwards any extra flags like --server.port)
echo [*] Launching ClimaTrend Web Application...
echo [*] Opening in your default browser at http://localhost:8501 ...
echo.
python -m streamlit run climatrend/app.py %*
if errorlevel 1 (
    echo.
    echo [ERROR] Streamlit exited with an error code.
    pause
)
goto end

:run_tests
echo [*] Running complete ClimaTrend test suite (36 tests across all modules)...
echo.
python -m pytest -v
if errorlevel 1 (
    echo.
    echo [!] Some tests encountered errors.
    pause
) else (
    echo.
    echo [OK] All 36 tests passed successfully!
)
goto end

:run_scheduler
echo [*] Launching ClimaTrend Background Alert Scheduler (APScheduler)...
echo [*] Monitoring Open-Meteo, USGS, FIRMS, and climatological baselines...
echo.
python -m climatrend.climate.scheduler
goto end

:run_backtest
echo [*] Running ClimaTrend 10-Year Historical ERA5 Alert Backtest and Threshold Calibration...
echo.
python -m climatrend.climate.regional_alerts.backtester
if errorlevel 1 (
    echo.
    echo [!] Backtest failed.
    pause
) else (
    echo.
    echo [OK] Backtest completed. Reports stored in docs/backtest_reports/
)
goto end

:run_init_db
echo [*] Initializing / verifying ClimaTrend SQLite database and seed data...
echo.
python -m climatrend.climate.db.database
if errorlevel 1 (
    echo.
    echo [ERROR] Database initialization failed.
    pause
) else (
    echo.
    echo [OK] Database schema and initial seeds ready.
)
goto end

:run_check
echo [*] Running ClimaTrend environment and system health check...
echo.
python -c "import sys, streamlit, xgboost, shap, pulp, apscheduler, openai; print('[OK] Core and ML packages imported successfully (Streamlit, XGBoost, SHAP, PuLP, APScheduler, OpenAI).')"
if errorlevel 1 (
    echo [ERROR] Missing critical dependencies. Run 'run.bat install' to fix.
    pause
    goto end
)
python -c "import os; from dotenv import load_dotenv; load_dotenv(); key = os.getenv('NVIDIA_API_KEY'); print('[OK] NVIDIA NIM API Key configured:', bool(key and not key.startswith('your_')))"
python -m climatrend.climate.db.database
echo.
echo [OK] All system checks passed! Ready to run.
goto end

:run_clean
echo [*] Cleaning Python bytecode cache and pytest cache...
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d" 2>nul
if exist ".pytest_cache" rd /s /q ".pytest_cache" 2>nul
echo [OK] Cache files cleaned.
goto end

:install_deps
echo [*] Updating and installing dependencies from requirements.txt...
python -m pip install --upgrade pip
pip install -r requirements.txt
echo.
echo [OK] Dependency sync complete.
goto end

:show_help
echo Usage: run.bat [command] [args...]
echo.
echo Available Commands:
echo   (no args)    Launch the full ClimaTrend Streamlit web application
echo   test         Run all 36 automated unit and integration tests via pytest
echo   scheduler    Start the background real-time disaster and alert scheduler daemon
echo   backtest     Execute 10-year historical ERA5 hazard alert backtest and calibration
echo   init-db      Initialize / verify SQLite schema and seed alert rules and regions
echo   check        Run system health check (packages, .env, DB connectivity)
echo   clean        Clean temporary Python bytecode (__pycache__) and pytest cache
echo   install      Install / update Python dependencies from requirements.txt
echo   help         Display this help guide
echo.
echo Examples:
echo   run.bat                     ^<-- Runs web app on http://localhost:8501
echo   run.bat --server.port 8502  ^<-- Runs web app on port 8502
echo   run.bat test                ^<-- Runs full pytest suite
echo   run.bat check               ^<-- Verifies environment and dependencies
echo.
goto end

:end
endlocal
