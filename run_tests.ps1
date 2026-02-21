# Test runner script for Cloud Document Archive (PowerShell)
# Usage: .\run_tests.ps1 [all|cov|quick|unit]

param(
    [string]$TestMode = "all"
)

Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   Cloud Document Archive v2.0.0 - Test Suite Runner           ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Check if pytest is installed
try {
    $null = pytest --version 2>$null
} catch {
    Write-Host "Installing test dependencies..."
    pip install pytest pytest-asyncio pytest-cov httpx
}

Write-Host "Running tests..." -ForegroundColor Green
Write-Host ""

switch ($TestMode) {
    "cov" {
        Write-Host "Running tests with coverage report..." -ForegroundColor Yellow
        pytest tests/ -v --cov=app --cov-report=html --cov-report=term-missing
        Write-Host ""
        Write-Host "Coverage report generated in htmlcov/index.html" -ForegroundColor Green
    }
    "quick" {
        Write-Host "Running quick tests (authentication only)..." -ForegroundColor Yellow
        pytest tests/test_auth.py tests/test_routes.py -v
    }
    "unit" {
        Write-Host "Running unit tests..." -ForegroundColor Yellow
        pytest tests/ -v -m "not integration"
    }
    default {
        Write-Host "Running all tests..." -ForegroundColor Yellow
        pytest tests/ -v
    }
}

Write-Host ""
Write-Host "Test run complete!" -ForegroundColor Green
