#!/bin/bash
# Security Validation Script
# Checks for common security issues before deployment

set -e

echo "=========================================="
echo " AI Stack - Security Validation"
echo "=========================================="
echo ""

ERRORS=0
WARNINGS=0

# Color codes
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

error() {
    echo -e "${RED}❌ ERROR: $1${NC}"
    ((ERRORS++))
}

warning() {
    echo -e "${YELLOW}⚠️  WARNING: $1${NC}"
    ((WARNINGS++))
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

info() {
    echo "ℹ️  $1"
}

# Check 1: .env file exists and is secure
echo "1. Checking environment configuration..."
if [ ! -f .env ]; then
    error ".env file not found. Copy .env.example to .env"
else
    # Check file permissions
    PERMS=$(stat -c "%a" .env 2>/dev/null || stat -f "%A" .env 2>/dev/null)
    if [ "$PERMS" != "600" ] && [ "$PERMS" != "400" ]; then
        warning ".env file permissions are $PERMS (should be 600). Run: chmod 600 .env"
    else
        success ".env file exists with secure permissions"
    fi

    # Check for default passwords
    if grep -q "CHANGE_ME\|changeme" .env; then
        error ".env contains default passwords. Update all passwords!"
    else
        success "No default passwords found in .env"
    fi
fi
echo ""

# Check 2: .gitignore exists
echo "2. Checking .gitignore..."
if [ ! -f .gitignore ]; then
    error ".gitignore not found. Secrets may be committed!"
else
    if grep -q ".env" .gitignore; then
        success ".gitignore includes .env"
    else
        error ".gitignore does not include .env!"
    fi
fi
echo ""

# Check 3: Check for SQL injection in n8n workflows
echo "3. Scanning n8n workflows for SQL injection patterns..."
VULNERABLE_COUNT=0

if [ -d "n8n-workflows" ]; then
    # Check for executeQuery with string interpolation
    for file in n8n-workflows/*.json; do
        if [ -f "$file" ]; then
            # Check for dangerous patterns
            if grep -q "executeQuery" "$file"; then
                if grep -q '\{\{ \$json' "$file" && grep -q "VALUES\|WHERE\|SET" "$file"; then
                    warning "Possible SQL injection in $(basename "$file")"
                    ((VULNERABLE_COUNT++))
                fi
            fi
        fi
    done

    if [ $VULNERABLE_COUNT -eq 0 ]; then
        success "No obvious SQL injection patterns found in workflows"
    else
        error "Found $VULNERABLE_COUNT workflow(s) with possible SQL injection"
        info "Review N8N_WORKFLOW_SECURITY_FIX_GUIDE.md for fixes"
    fi
else
    warning "n8n-workflows directory not found"
fi
echo ""

# Check 4: Python dependencies pinned
echo "4. Checking Python dependencies..."
if [ -f "containers/mcp-server/requirements.txt" ]; then
    if grep -q ">=" "containers/mcp-server/requirements.txt"; then
        warning "requirements.txt uses >= instead of == (unpinned versions)"
    else
        success "Python dependencies are pinned"
    fi
else
    warning "requirements.txt not found"
fi
echo ""

# Check 5: Check for exposed secrets in git
echo "5. Checking for exposed secrets in git history..."
if [ -d .git ]; then
    # Check if .env is in git history
    if git log --all --full-history -- ".env" 2>/dev/null | grep -q "commit"; then
        error ".env file found in git history! Secrets may be exposed!"
        info "To remove: git filter-branch --force --index-filter 'git rm --cached --ignore-unmatch .env' --prune-empty --tag-name-filter cat -- --all"
    else
        success "No .env file in git history"
    fi

    # Check for common secret patterns
    if git grep -E "(password|api_key|secret|token).*=.*['\"]" 2>/dev/null | grep -v ".example" | grep -v "#" | head -1; then
        warning "Possible secrets found in committed files (check output above)"
    fi
else
    info "Not a git repository, skipping git checks"
fi
echo ""

# Check 6: Database migration metadata column
echo "6. Checking database schema..."
if [ -f "migrations/006_openmemory_schema.sql" ]; then
    if grep -q "metadata JSONB" "migrations/006_openmemory_schema.sql"; then
        success "metadata column present in schema"
    else
        warning "metadata column missing from schema migration"
    fi
else
    warning "OpenMemory schema migration not found"
fi
echo ""

# Check 7: Docker network configuration
echo "7. Checking Docker configuration..."
if docker network ls | grep -q "ai-stack-network"; then
    success "ai-stack-network exists"
else
    info "ai-stack-network not found (run: docker network create ai-stack-network)"
fi
echo ""

# Check 8: Validate .env has required fields
echo "8. Validating .env configuration..."
if [ -f .env ]; then
    REQUIRED_VARS=(
        "POSTGRES_HOST"
        "POSTGRES_PASSWORD"
        "QDRANT_HOST"
        "OLLAMA_HOST"
        "DEFAULT_USER_ID"
    )

    for var in "${REQUIRED_VARS[@]}"; do
        if grep -q "^${var}=" .env; then
            success "$var is set"
        else
            error "$var is not set in .env"
        fi
    done
fi
echo ""

# Summary
echo "=========================================="
echo " Validation Summary"
echo "=========================================="
echo ""
echo "Errors: $ERRORS"
echo "Warnings: $WARNINGS"
echo ""

if [ $ERRORS -gt 0 ]; then
    echo -e "${RED}❌ VALIDATION FAILED${NC}"
    echo "Fix all errors before deploying to production!"
    exit 1
elif [ $WARNINGS -gt 0 ]; then
    echo -e "${YELLOW}⚠️  VALIDATION PASSED WITH WARNINGS${NC}"
    echo "Review warnings before deploying to production."
    exit 0
else
    echo -e "${GREEN}✅ ALL CHECKS PASSED${NC}"
    echo "System is ready for deployment!"
    exit 0
fi
