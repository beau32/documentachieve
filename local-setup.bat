@echo off
REM Local Storage Setup Script for Windows
REM Quick setup for development/testing with local directories

setlocal enabledelayedexpansion
cd /d "%~dp0"

echo.
echo ================================
echo Local Storage Setup Script
echo ================================
echo.

REM 1. Create directories
echo Creating directory structure...
if not exist "documents" mkdir documents
if not exist "documents_archive" mkdir documents_archive
if not exist "documents_deep_archive" mkdir documents_deep_archive
if not exist "iceberg_warehouse" mkdir iceberg_warehouse
echo [OK] Directories created
echo.

REM 2. Create config.yaml if it doesn't exist
if not exist "config.yaml" (
    echo Creating config.yaml...
    (
        echo app:
        echo   name: Cloud Document Archive
        echo   debug: true
        echo   host: 0.0.0.0
        echo   port: 8000
        echo.
        echo storage:
        echo   provider: local
        echo   
        echo   local:
        echo     storage_path: ./documents
        echo     archive_path: ./documents_archive
        echo     deep_archive_path: ./documents_deep_archive
        echo.
        echo database:
        echo   url: sqlite:///./document_archive.db
        echo.
        echo iceberg:
        echo   warehouse_path: ./iceberg_warehouse
        echo   enable_local_mode: true
    ) > config.yaml
    echo [OK] config.yaml created
) else (
    echo config.yaml already exists, skipping
)
echo.

REM 3. Create sample test document
echo Creating sample test document...
(
    echo Sample test document created at %date% %time%
) > _sample_test.txt
echo [OK] Sample document created at _sample_test.txt
echo.

REM 4. Check Python
echo Checking Python environment...
python --version >nul 2>&1
if not %errorlevel%==0 (
    echo ERROR: Python not found. Please install Python 3.8+
    pause
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [OK] Python %PYTHON_VERSION% found
echo.

REM 5. Setup virtual environment
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    echo [OK] Virtual environment created
    echo.
    
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
    echo [OK] Virtual environment activated
    echo.
    
    if exist "requirements.txt" (
        echo Installing dependencies...
        pip install -q -r requirements.txt
        echo [OK] Dependencies installed
        echo.
    )
) else (
    echo Virtual environment already exists
    echo To activate: venv\Scripts\activate.bat
    echo.
)

REM 6. Display summary
echo ================================
echo Setup Complete!
echo ================================
echo.
echo Directory Structure:
echo    documents\             - Standard tier (active)
echo    documents_archive\     - Archive tier (90+ days)
echo    documents_deep_archive\ - Deep archive (365+ days)
echo    iceberg_warehouse\     - Iceberg metadata
echo.
echo Configuration:
echo    config.yaml - Local storage configuration
echo.
echo Next Steps:
echo    1. Activate venv: venv\Scripts\activate.bat
echo    2. Run the app: python -m app.main
echo    3. Open http://localhost:8000 in browser
echo    4. See LOCAL_STORAGE.md for API examples
echo.
echo Test Upload:
echo    curl -X POST http://localhost:8000/archive ^
echo      -H "Content-Type: application/json" ^
echo      -d "{\"document_base64\": \"SGVsbG8gV29ybGQh\", \"filename\": \"test.txt\"}"
echo.
echo Happy archiving!
echo.
pause
