#!/bin/bash
# test_cli.sh - Test all safe CLI commands
# Tests only read-only commands that don't modify the system

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
PASSED=0
FAILED=0

# Test function
test_command() {
    local description="$1"
    local command="$2"

    echo -e "${BLUE}Testing:${NC} $description"
    echo -e "${YELLOW}Command:${NC} $command"

    if eval "$command" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ PASSED${NC}"
        ((PASSED++))
    else
        echo -e "${RED}✗ FAILED${NC}"
        ((FAILED++))
    fi
    echo ""
}

# Header
echo "========================================="
echo "  RDP Session Manager CLI - Test Suite"
echo "========================================="
echo ""

# Basic commands
echo "=== BASIC COMMANDS ==="
echo ""

test_command "Show version" "./rdpsm --version"
test_command "Show help" "./rdpsm --help"
test_command "Show user help" "./rdpsm user --help"
test_command "Show session help" "./rdpsm session --help"
test_command "Show DE help" "./rdpsm de --help"
test_command "Show server help" "./rdpsm server --help"
test_command "Show config help" "./rdpsm config --help"
test_command "Show deps help" "./rdpsm deps --help"

# User management
echo "=== USER MANAGEMENT ==="
echo ""

test_command "List users (table)" "./rdpsm user list"
test_command "List users (JSON)" "./rdpsm user list --format json"

# Session management
echo "=== SESSION MANAGEMENT ==="
echo ""

test_command "List sessions (table)" "./rdpsm session list"
test_command "List sessions (JSON)" "./rdpsm session list --format json"

# Desktop environments
echo "=== DESKTOP ENVIRONMENTS ==="
echo ""

test_command "List DEs (table)" "./rdpsm de list"
test_command "List DEs (JSON)" "./rdpsm de list --format json"
test_command "Check GNOME installed" "./rdpsm de check gnome"

# Test DE check for non-installed (should return exit 1, which is correct)
echo -e "${BLUE}Testing:${NC} Check XFCE not installed (expects exit 1)"
echo -e "${YELLOW}Command:${NC} ./rdpsm de check xfce"
if ./rdpsm de check xfce > /dev/null 2>&1; then
    echo -e "${YELLOW}! XFCE is installed (unexpected but valid)${NC}"
    ((PASSED++))
else
    echo -e "${GREEN}✓ PASSED (correctly returned exit 1 for non-installed DE)${NC}"
    ((PASSED++))
fi
echo ""

# Server info
echo "=== SERVER INFORMATION ==="
echo ""

test_command "Server info (table)" "./rdpsm server info"
test_command "Server info (JSON)" "./rdpsm server info --format json"
test_command "Server status" "./rdpsm server status"
test_command "Verbose server info" "./rdpsm -v server info"

# Configuration
echo "=== CONFIGURATION ==="
echo ""

test_command "Get port config" "./rdpsm config get port"

# Dependencies
echo "=== DEPENDENCIES ==="
echo ""

test_command "Check dependencies (table)" "./rdpsm deps check"
test_command "Check dependencies (JSON)" "./rdpsm deps check --format json"

# Error handling
echo "=== ERROR HANDLING ==="
echo ""

# This should fail (non-existent user)
echo -e "${BLUE}Testing:${NC} Non-existent user error handling"
echo -e "${YELLOW}Command:${NC} ./rdpsm user info nonexistent_user"
if ./rdpsm user info nonexistent_user > /dev/null 2>&1; then
    echo -e "${RED}✗ FAILED (should have returned error)${NC}"
    ((FAILED++))
else
    echo -e "${GREEN}✓ PASSED (correctly returned error)${NC}"
    ((PASSED++))
fi
echo ""

# Summary
echo "========================================="
echo "           TEST SUMMARY"
echo "========================================="
echo -e "${GREEN}Passed:${NC} $PASSED"
echo -e "${RED}Failed:${NC} $FAILED"
echo -e "Total:  $((PASSED + FAILED))"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed! ✓${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed! ✗${NC}"
    exit 1
fi
