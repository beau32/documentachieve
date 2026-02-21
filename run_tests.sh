#!/bin/bash
# Test runner script for Cloud Document Archive

set -e

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║   Cloud Document Archive v2.0.0 - Test Suite Runner           ║"
echo "╚════════════════════════════════════════════════════════════════╝"

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo "Installing test dependencies..."
    pip install pytest pytest-asyncio pytest-cov httpx
fi

echo ""
echo "Running tests..."
echo ""

# Run all tests with coverage
if [ "$1" == "cov" ] || [ "$1" == "coverage" ]; then
    echo "Running tests with coverage report..."
    pytest tests/ -v --cov=app --cov-report=html --cov-report=term-missing
    echo ""
    echo "Coverage report generated in htmlcov/index.html"
elif [ "$1" == "" ]; then
    echo "Running all tests..."
    pytest tests/ -v
elif [ "$1" == "quick" ]; then
    echo "Running quick tests (authentication only)..."
    pytest tests/test_auth.py tests/test_routes.py -v
elif [ "$1" == "unit" ]; then
    echo "Running unit tests..."
    pytest tests/ -v -m "not integration"
else
    echo "Running specified test: $1"
    pytest "tests/$1" -v
fi

echo ""
echo "Test run complete!"
