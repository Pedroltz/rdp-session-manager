#!/bin/bash
# RDP Session Manager - Professional Test Runner
# Executes all unit tests with beautiful colored output

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Symbols
CHECK="✓"
CROSS="✗"
ARROW="→"
STAR="★"

# Banner
print_banner() {
    echo -e "${CYAN}${BOLD}"
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║                                                                ║"
    echo "║          RDP Session Manager - Test Suite                      ║"
    echo "║                                                                ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Print section header
print_section() {
    echo -e "\n${BLUE}${BOLD}$1${NC}"
    echo -e "${BLUE}$(printf '─%.0s' {1..60})${NC}"
}

# Print test file status
print_test_file() {
    local file=$1
    local status=$2
    local count=$3

    if [ "$status" = "ok" ]; then
        echo -e "  ${GREEN}${CHECK}${NC} ${BOLD}${file}${NC} ${GREEN}(${count} tests passed)${NC}"
    else
        echo -e "  ${RED}${CROSS}${NC} ${BOLD}${file}${NC} ${RED}(failed)${NC}"
    fi
}

# Print summary
print_summary() {
    local total=$1
    local passed=$2
    local failed=$3
    local duration=$4

    echo -e "\n${CYAN}${BOLD}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}${BOLD}║                       TEST SUMMARY                             ║${NC}"
    echo -e "${CYAN}${BOLD}╚════════════════════════════════════════════════════════════════╝${NC}"

    echo -e "\n  ${BOLD}Total Tests:${NC}     ${CYAN}${total}${NC}"

    if [ "$passed" -gt 0 ]; then
        echo -e "  ${BOLD}Passed:${NC}          ${GREEN}${passed} ${CHECK}${NC}"
    fi

    if [ "$failed" -gt 0 ]; then
        echo -e "  ${BOLD}Failed:${NC}          ${RED}${failed} ${CROSS}${NC}"
    fi

    echo -e "  ${BOLD}Duration:${NC}        ${YELLOW}${duration}s${NC}"

    echo -e "\n${CYAN}$(printf '─%.0s' {1..64})${NC}\n"

    if [ "$failed" -eq 0 ]; then
        echo -e "${GREEN}${BOLD}  ${CHECK} ALL TESTS PASSED! ${CHECK}${NC}\n"
        return 0
    else
        echo -e "${RED}${BOLD}  ${CROSS} SOME TESTS FAILED ${CROSS}${NC}\n"
        return 1
    fi
}

# Main execution
main() {
    # Clear screen and show banner
    clear
    print_banner

    # Change to project root directory
    cd "$(dirname "$0")/.." || exit 1

    print_section "${ARROW} Running Unit Tests"

    # Start timer
    START_TIME=$(date +%s)

    # Run tests and capture output
    echo ""
    TEST_OUTPUT=$(python3 -m unittest discover tests/ -v 2>&1)
    TEST_EXIT_CODE=$?

    # Parse output
    TEST_COUNT=$(echo "$TEST_OUTPUT" | grep -E "^test_" | wc -l)

    # Extract test results by file
    print_section "${ARROW} Test Results by Module"
    echo ""

    # Count tests per file
    for test_file in tests/test_*.py; do
        if [ -f "$test_file" ]; then
            filename=$(basename "$test_file")
            module_name="${filename%.py}"

            # Count tests in this module
            file_test_count=$(echo "$TEST_OUTPUT" | grep -c "($module_name\.")

            if [ $file_test_count -gt 0 ]; then
                # Check if any test in this module failed
                if echo "$TEST_OUTPUT" | grep -q "FAIL.*$module_name\." || echo "$TEST_OUTPUT" | grep -q "ERROR.*$module_name\."; then
                    print_test_file "$filename" "fail" "$file_test_count"
                else
                    print_test_file "$filename" "ok" "$file_test_count"
                fi
            fi
        fi
    done

    # Calculate duration
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))

    # Parse final results
    if echo "$TEST_OUTPUT" | grep -q "^Ran"; then
        TOTAL_TESTS=$(echo "$TEST_OUTPUT" | grep "^Ran" | awk '{print $2}')

        if echo "$TEST_OUTPUT" | grep -q "^OK"; then
            PASSED_TESTS=$TOTAL_TESTS
            FAILED_TESTS=0
        elif echo "$TEST_OUTPUT" | grep -q "FAILED"; then
            FAILED_TESTS=$(echo "$TEST_OUTPUT" | grep "FAILED" | grep -oP 'failures=\K\d+' || echo "0")
            ERROR_TESTS=$(echo "$TEST_OUTPUT" | grep "FAILED" | grep -oP 'errors=\K\d+' || echo "0")
            FAILED_TESTS=$((FAILED_TESTS + ERROR_TESTS))
            PASSED_TESTS=$((TOTAL_TESTS - FAILED_TESTS))
        else
            TOTAL_TESTS=$TEST_COUNT
            PASSED_TESTS=0
            FAILED_TESTS=$TOTAL_TESTS
        fi
    else
        TOTAL_TESTS=$TEST_COUNT
        PASSED_TESTS=0
        FAILED_TESTS=$TOTAL_TESTS
    fi

    # Show detailed output if tests failed
    if [ $TEST_EXIT_CODE -ne 0 ]; then
        print_section "${ARROW} Detailed Error Output"
        echo ""
        echo "$TEST_OUTPUT" | grep -A 10 "FAIL\|ERROR" || echo "$TEST_OUTPUT"
    fi

    # Print summary
    print_summary "$TOTAL_TESTS" "$PASSED_TESTS" "$FAILED_TESTS" "$DURATION"

    # Return appropriate exit code
    return $TEST_EXIT_CODE
}

# Run main function
main
exit $?
