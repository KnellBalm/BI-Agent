#!/bin/bash
# QA Test Runner Script
# Run comprehensive test suite with quality checks

set -e

echo "================================================"
echo "BI-Agent QA Test Suite"
echo "================================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ $2${NC}"
    else
        echo -e "${RED}✗ $2${NC}"
    fi
}

# Navigate to project root
cd "$(dirname "$0")/.."

echo "Step 1: Code Quality Checks"
echo "----------------------------"

# Ruff linting
echo "Running ruff linting..."
ruff check backend/ tests/ --fix || RUFF_EXIT=$?
print_status ${RUFF_EXIT:-0} "Ruff linting"

# Black formatting check
echo "Running black format check..."
black --check backend/ tests/ || BLACK_EXIT=$?
print_status ${BLACK_EXIT:-0} "Black formatting"

# MyPy type checking
echo "Running mypy type checking..."
mypy backend/ --ignore-missing-imports || MYPY_EXIT=$?
print_status ${MYPY_EXIT:-0} "MyPy type checking"

echo ""
echo "Step 2: Unit Tests"
echo "------------------"

# Run unit tests with coverage
pytest tests/unit/ -v --cov=backend --cov-report=term-missing || UNIT_EXIT=$?
print_status ${UNIT_EXIT:-0} "Unit tests"

echo ""
echo "Step 3: Integration Tests"
echo "-------------------------"

# Run integration tests
pytest tests/integration/ -v || INTEGRATION_EXIT=$?
print_status ${INTEGRATION_EXIT:-0} "Integration tests"

echo ""
echo "Step 4: Performance Benchmarks"
echo "-------------------------------"

# Run performance tests
pytest tests/performance/ -v -s || PERF_EXIT=$?
print_status ${PERF_EXIT:-0} "Performance benchmarks"

echo ""
echo "Step 5: Coverage Report"
echo "-----------------------"

# Generate HTML coverage report
coverage html
echo "Coverage report generated at: htmlcov/index.html"

# Get coverage percentage
COVERAGE=$(coverage report | tail -1 | awk '{print $NF}' | sed 's/%//')
echo "Total coverage: ${COVERAGE}%"

if (( $(echo "$COVERAGE < 90" | bc -l) )); then
    echo -e "${YELLOW}⚠ Warning: Coverage below 90% target${NC}"
else
    echo -e "${GREEN}✓ Coverage meets 90% target${NC}"
fi

echo ""
echo "================================================"
echo "QA Test Suite Complete"
echo "================================================"
echo ""

# Summary
TOTAL_ERRORS=0
TOTAL_ERRORS=$((TOTAL_ERRORS + ${RUFF_EXIT:-0}))
TOTAL_ERRORS=$((TOTAL_ERRORS + ${BLACK_EXIT:-0}))
TOTAL_ERRORS=$((TOTAL_ERRORS + ${MYPY_EXIT:-0}))
TOTAL_ERRORS=$((TOTAL_ERRORS + ${UNIT_EXIT:-0}))
TOTAL_ERRORS=$((TOTAL_ERRORS + ${INTEGRATION_EXIT:-0}))

if [ $TOTAL_ERRORS -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some checks failed. Please review the output above.${NC}"
    exit 1
fi
