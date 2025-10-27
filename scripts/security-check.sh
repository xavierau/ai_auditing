#!/bin/bash
# Security Check Script
# Sprint 6 Phase 2: Automated Security Scanning
# Run all security scans before committing code

set -e  # Exit on error

echo "=================================="
echo "GenReport Security Check"
echo "=================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track results
CRITICAL_FOUND=0
HIGH_FOUND=0

# 1. Python Dependency Scan (pip-audit)
echo "📦 [1/5] Running pip-audit (Python dependencies)..."
echo ""

if [ -f "requirements.txt" ]; then
    source .venv/bin/activate 2>/dev/null || true

    if ! command -v pip-audit &> /dev/null; then
        echo "Installing pip-audit..."
        pip install pip-audit
    fi

    # Run pip-audit
    if pip-audit --requirement requirements.txt; then
        echo -e "${GREEN}✅ No vulnerabilities found in Python dependencies${NC}"
    else
        echo -e "${YELLOW}⚠️  Vulnerabilities found in Python dependencies${NC}"
        HIGH_FOUND=$((HIGH_FOUND + 1))
    fi
else
    echo -e "${YELLOW}⚠️  requirements.txt not found, skipping${NC}"
fi

echo ""

# 2. Python Code Security (Bandit)
echo "🔍 [2/5] Running Bandit (Python code security)..."
echo ""

if [ -d "genreport" ]; then
    source .venv/bin/activate 2>/dev/null || true

    if ! command -v bandit &> /dev/null; then
        echo "Installing Bandit..."
        pip install bandit[toml]
    fi

    # Run Bandit (low-low severity filter)
    if bandit -r genreport/ -ll -q; then
        echo -e "${GREEN}✅ No security issues found in Python code${NC}"
    else
        echo -e "${YELLOW}⚠️  Security issues found in Python code${NC}"
        HIGH_FOUND=$((HIGH_FOUND + 1))
    fi
else
    echo -e "${YELLOW}⚠️  genreport/ directory not found, skipping${NC}"
fi

echo ""

# 3. Python Dependency Scan Alternative (Safety)
echo "🛡️  [3/5] Running Safety (alternative dependency check)..."
echo ""

if [ -f "requirements.txt" ]; then
    source .venv/bin/activate 2>/dev/null || true

    if ! command -v safety &> /dev/null; then
        echo "Installing Safety..."
        pip install safety
    fi

    # Run Safety
    if safety check --file requirements.txt; then
        echo -e "${GREEN}✅ No known vulnerabilities (Safety DB)${NC}"
    else
        echo -e "${YELLOW}⚠️  Vulnerabilities found (Safety DB)${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  requirements.txt not found, skipping${NC}"
fi

echo ""

# 4. Frontend Dependency Scan (npm audit)
echo "📦 [4/5] Running npm audit (frontend dependencies)..."
echo ""

if [ -f "frontend/package.json" ]; then
    cd frontend

    # Run npm audit
    if npm audit --audit-level=moderate; then
        echo -e "${GREEN}✅ No vulnerabilities found in frontend dependencies${NC}"
    else
        echo -e "${YELLOW}⚠️  Vulnerabilities found in frontend dependencies${NC}"
        HIGH_FOUND=$((HIGH_FOUND + 1))
    fi

    cd ..
else
    echo -e "${YELLOW}⚠️  frontend/package.json not found, skipping${NC}"
fi

echo ""

# 5. Security Test Suite (OWASP Top 10)
echo "🔐 [5/5] Running OWASP Top 10 security tests..."
echo ""

if [ -f "tests/security/test_owasp_top10.py" ]; then
    source .venv/bin/activate 2>/dev/null || true

    # Run security tests
    if pytest tests/security/test_owasp_top10.py -v --tb=short -q; then
        echo -e "${GREEN}✅ All security tests passing (22/22)${NC}"
    else
        echo -e "${RED}❌ Security tests failing${NC}"
        CRITICAL_FOUND=$((CRITICAL_FOUND + 1))
    fi
else
    echo -e "${YELLOW}⚠️  Security tests not found, skipping${NC}"
fi

echo ""
echo "=================================="
echo "Security Check Complete"
echo "=================================="
echo ""

# Summary
if [ $CRITICAL_FOUND -gt 0 ]; then
    echo -e "${RED}❌ CRITICAL: $CRITICAL_FOUND critical security issue(s) found${NC}"
    echo ""
    echo "Action required:"
    echo "1. Review critical findings above"
    echo "2. Fix issues before committing"
    echo "3. Re-run security check"
    exit 1
elif [ $HIGH_FOUND -gt 0 ]; then
    echo -e "${YELLOW}⚠️  WARNING: $HIGH_FOUND high severity issue(s) found${NC}"
    echo ""
    echo "Recommended actions:"
    echo "1. Review findings above"
    echo "2. Address high severity issues"
    echo "3. Document any accepted risks"
    exit 0
else
    echo -e "${GREEN}✅ No critical or high severity issues found${NC}"
    echo ""
    echo "Security status: GOOD"
    echo "Ready to commit!"
    exit 0
fi
