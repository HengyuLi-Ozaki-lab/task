#!/bin/bash
#
# TASK Test Runner
# Executes tests defined in test_definitions.conf
#
# Usage: ./run_tests.sh [options] [test_name...]
#   -l, --list     List available tests
#   -c, --clean    Clean up test outputs after running
#   -v, --verbose  Show detailed output
#   -t, --timeout  Override default timeout (seconds)
#   -h, --help     Show this help message
#
# Examples:
#   ./run_tests.sh                    # Run all tests
#   ./run_tests.sh eq_iter01          # Run specific test
#   ./run_tests.sh eq_iter01 tx_std   # Run multiple tests
#   ./run_tests.sh -l                 # List available tests
#

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TASK_DIR="$(dirname "$SCRIPT_DIR")"
TEST_OUTPUT_DIR="$SCRIPT_DIR/test_output"
TEST_DEF_FILE="$SCRIPT_DIR/test_definitions.conf"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Options
CLEAN=0
VERBOSE=0
TIMEOUT_OVERRIDE=""
LIST_ONLY=0
SELECTED_TESTS=()

# Counters
TOTAL=0
PASSED=0
FAILED=0
SKIPPED=0

# Track completed tests for dependency resolution
declare -A COMPLETED_TESTS

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -c|--clean)
            CLEAN=1
            shift
            ;;
        -v|--verbose)
            VERBOSE=1
            shift
            ;;
        -t|--timeout)
            TIMEOUT_OVERRIDE="$2"
            shift 2
            ;;
        -l|--list)
            LIST_ONLY=1
            shift
            ;;
        -h|--help)
            echo "TASK Test Runner"
            echo ""
            echo "Usage: $0 [options] [test_name...]"
            echo ""
            echo "Options:"
            echo "  -l, --list     List available tests"
            echo "  -c, --clean    Clean up test outputs after running"
            echo "  -v, --verbose  Show detailed output"
            echo "  -t, --timeout  Override default timeout (seconds)"
            echo "  -h, --help     Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                    # Run all tests"
            echo "  $0 eq_iter01          # Run specific test"
            echo "  $0 eq_iter01 tx_std   # Run multiple tests"
            echo "  $0 -l                 # List available tests"
            exit 0
            ;;
        -*)
            echo "Unknown option: $1"
            exit 1
            ;;
        *)
            SELECTED_TESTS+=("$1")
            shift
            ;;
    esac
done

# Check if test definition file exists
if [[ ! -f "$TEST_DEF_FILE" ]]; then
    echo -e "${RED}Error: Test definition file not found: $TEST_DEF_FILE${NC}"
    exit 1
fi

# Function to get module binary path
get_binary() {
    local module="$1"
    case "$module" in
        eq) echo "$TASK_DIR/eq/eq" ;;
        tr) echo "$TASK_DIR/tr/tr2" ;;
        ti) echo "$TASK_DIR/ti/ti" ;;
        fp) echo "$TASK_DIR/fp/fp" ;;
        wr) echo "$TASK_DIR/wr/wr" ;;
        wrx) echo "$TASK_DIR/wrx/wrx" ;;
        tx) echo "$TASK_DIR/tx/tx2" ;;
        tot) echo "$TASK_DIR/tot/tot" ;;
        *) echo "" ;;
    esac
}

# Function to parse test definition
parse_test_def() {
    local line="$1"
    # Remove comments and trim
    line="${line%%#*}"
    line="$(echo "$line" | xargs)"

    if [[ -z "$line" ]]; then
        return 1
    fi

    IFS=':' read -r TEST_NAME MODULE INPUT_FILE DEPENDS TIMEOUT DESCRIPTION <<< "$line"
    return 0
}

# Function to list all tests
list_tests() {
    echo "========================================"
    echo "  Available Tests"
    echo "========================================"
    echo ""
    printf "%-15s %-6s %-10s %s\n" "TEST_NAME" "MODULE" "TIMEOUT" "DESCRIPTION"
    printf "%-15s %-6s %-10s %s\n" "---------" "------" "-------" "-----------"

    while IFS= read -r line; do
        if parse_test_def "$line"; then
            local binary=$(get_binary "$MODULE")
            local status=""
            if [[ ! -x "$binary" ]]; then
                status=" (not built)"
            fi
            printf "%-15s %-6s %-10s %s%s\n" "$TEST_NAME" "$MODULE" "${TIMEOUT}s" "$DESCRIPTION" "$status"
        fi
    done < "$TEST_DEF_FILE"
    echo ""
}

# Function to check if test should run
should_run_test() {
    local test_name="$1"

    # If no tests specified, run all
    if [[ ${#SELECTED_TESTS[@]} -eq 0 ]]; then
        return 0
    fi

    # Check if test is in selected list
    for selected in "${SELECTED_TESTS[@]}"; do
        if [[ "$selected" == "$test_name" ]]; then
            return 0
        fi
    done

    return 1
}

# Function to check and run dependencies
run_dependencies() {
    local depends="$1"

    if [[ "$depends" == "none" || -z "$depends" ]]; then
        return 0
    fi

    IFS=',' read -ra DEP_ARRAY <<< "$depends"
    for dep in "${DEP_ARRAY[@]}"; do
        dep="$(echo "$dep" | xargs)"  # trim whitespace

        # Check if dependency already completed
        if [[ "${COMPLETED_TESTS[$dep]}" == "1" ]]; then
            continue
        fi

        # Find and run dependency
        while IFS= read -r line; do
            if parse_test_def "$line"; then
                if [[ "$TEST_NAME" == "$dep" ]]; then
                    echo -e "  ${CYAN}Running dependency: $dep${NC}"
                    run_single_test "$TEST_NAME" "$MODULE" "$INPUT_FILE" "$DEPENDS" "$TIMEOUT" "$DESCRIPTION"
                    break
                fi
            fi
        done < "$TEST_DEF_FILE"

        # Check if dependency succeeded
        if [[ "${COMPLETED_TESTS[$dep]}" != "1" ]]; then
            echo -e "  ${RED}Dependency failed: $dep${NC}"
            return 1
        fi
    done

    return 0
}

# Function to run a single test
run_single_test() {
    local test_name="$1"
    local module="$2"
    local input_file="$3"
    local depends="$4"
    local timeout="$5"
    local description="$6"

    # Skip if already completed
    if [[ "${COMPLETED_TESTS[$test_name]}" == "1" ]]; then
        return 0
    fi

    TOTAL=$((TOTAL + 1))

    # Override timeout if specified
    if [[ -n "$TIMEOUT_OVERRIDE" ]]; then
        timeout="$TIMEOUT_OVERRIDE"
    fi

    local binary=$(get_binary "$module")
    local module_dir="$TASK_DIR/$module"

    # Handle @inputs prefix for local test inputs
    local full_input_path
    if [[ "$input_file" == @* ]]; then
        full_input_path="$SCRIPT_DIR/${input_file#@}"
    else
        full_input_path="$module_dir/$input_file"
    fi

    echo -n "[$TOTAL] $test_name ($description) ... "

    # Check if binary exists
    if [[ ! -x "$binary" ]]; then
        echo -e "${YELLOW}SKIP${NC} (module not built)"
        SKIPPED=$((SKIPPED + 1))
        return 0
    fi

    # Check if input file exists
    if [[ ! -f "$full_input_path" ]]; then
        echo -e "${YELLOW}SKIP${NC} (input file not found: $full_input_path)"
        SKIPPED=$((SKIPPED + 1))
        return 0
    fi

    # Run dependencies first
    if ! run_dependencies "$depends"; then
        echo -e "${YELLOW}SKIP${NC} (dependency failed)"
        SKIPPED=$((SKIPPED + 1))
        return 0
    fi

    # Create test output directory
    local test_dir="$TEST_OUTPUT_DIR/$test_name"
    mkdir -p "$test_dir"

    # Copy module-specific parameter files
    case "$module" in
        tx)
            # TX requires txparm file in working directory
            if [[ -f "$TASK_DIR/tx/in/txparm.std" ]]; then
                cp "$TASK_DIR/tx/in/txparm.std" "$test_dir/txparm"
            fi
            ;;
    esac

    # Copy dependency outputs if needed
    if [[ "$depends" != "none" && -n "$depends" ]]; then
        IFS=',' read -ra DEP_ARRAY <<< "$depends"
        for dep in "${DEP_ARRAY[@]}"; do
            dep="$(echo "$dep" | xargs)"
            local dep_dir="$TEST_OUTPUT_DIR/$dep"
            if [[ -d "$dep_dir" ]]; then
                # Copy output files (eqdata.*, etc.)
                cp "$dep_dir"/eqdata.* "$test_dir/" 2>/dev/null || true
                cp "$dep_dir"/*.gs "$test_dir/" 2>/dev/null || true
            fi
        done
    fi

    # Run the test
    cd "$test_dir"
    local log_file="$test_dir/output.log"

    # For TR/FP/TI/TOT modules, enable regression dump (env-guarded inside the dumper).
    local mod_env=()
    case "$module" in
        tr) mod_env=(env TR_REGRESS_DUMP=1) ;;
        fp) mod_env=(env FP_REGRESS_DUMP=1) ;;
        ti) mod_env=(env TI_REGRESS_DUMP=1) ;;
        wr) mod_env=(env WR_REGRESS_DUMP=1) ;;
        wrx) mod_env=(env WRX_REGRESS_DUMP=1) ;;
        tot)
            mod_env=(env TOT_REGRESS_DUMP=1)
            cp "$SCRIPT_DIR/inputs/eqdata."* "$test_dir/" 2>/dev/null || true
            cp "$SCRIPT_DIR/inputs/eqdata-"* "$test_dir/" 2>/dev/null || true
            cp "$SCRIPT_DIR/inputs/${test_name}.eqparm" "$test_dir/eqparm" 2>/dev/null || true
            cp "$SCRIPT_DIR/inputs/${test_name}.trparm" "$test_dir/trparm" 2>/dev/null || true
            ;;
    esac

    if [[ $VERBOSE -eq 1 ]]; then
        echo ""
        "${mod_env[@]}" timeout "$timeout" "$binary" < "$full_input_path" 2>&1 | tee "$log_file"
        local exit_code=${PIPESTATUS[0]}
    else
        "${mod_env[@]}" timeout "$timeout" "$binary" < "$full_input_path" > "$log_file" 2>&1
        local exit_code=$?
    fi

    cd "$SCRIPT_DIR"

    # Check result - CLOSED message is the primary success indicator
    if [[ $exit_code -eq 124 ]]; then
        echo -e "${YELLOW}TIMEOUT${NC} (exceeded ${timeout}s)"
        FAILED=$((FAILED + 1))
    elif grep -q "CLOSED" "$log_file" 2>/dev/null; then
        # CLOSED message found - calculation completed successfully.
        # For TR module, also verify numerical metrics against baseline.
        local reg_ok=1
        if [[ "$module" == "tr" || "$module" == "fp" || "$module" == "ti" || "$module" == "wr" || "$module" == "wrx" || "$module" == "tot" ]]; then
            if ! "$SCRIPT_DIR/scripts/check_regression.sh" \
                    "$test_name" "$test_dir" "$SCRIPT_DIR/baselines" "1e-10" \
                    > "$test_dir/regression.log" 2>&1; then
                reg_ok=0
            fi
        fi
        if [[ $reg_ok -eq 0 ]]; then
            echo -e "${RED}REGRESSION${NC} (metrics drift; see $test_dir/regression.log)"
            FAILED=$((FAILED + 1))
        elif [[ $exit_code -ne 0 ]]; then
            echo -e "${GREEN}PASS${NC} (warning: exit code $exit_code)"
            PASSED=$((PASSED + 1))
            COMPLETED_TESTS[$test_name]=1
        else
            echo -e "${GREEN}PASS${NC}"
            PASSED=$((PASSED + 1))
            COMPLETED_TESTS[$test_name]=1
        fi
    elif [[ $exit_code -eq 0 ]]; then
        echo -e "${RED}FAIL${NC} (no CLOSED message)"
        FAILED=$((FAILED + 1))
        if [[ $VERBOSE -eq 1 ]]; then
            echo "  Last 10 lines of log:"
            tail -10 "$log_file" | sed 's/^/    /'
        fi
    else
        echo -e "${RED}FAIL${NC} (exit code: $exit_code)"
        FAILED=$((FAILED + 1))
        if [[ $VERBOSE -eq 1 ]]; then
            echo "  Last 10 lines of log:"
            tail -10 "$log_file" | sed 's/^/    /'
        fi
    fi
}

# ============================================================
# Main Execution
# ============================================================

# List mode
if [[ $LIST_ONLY -eq 1 ]]; then
    list_tests
    exit 0
fi

echo "========================================"
echo "  TASK Test Runner"
echo "========================================"
echo "Date: $(date)"
if [[ ${#SELECTED_TESTS[@]} -gt 0 ]]; then
    echo "Selected tests: ${SELECTED_TESTS[*]}"
else
    echo "Running: All tests"
fi
echo ""

# Create output directory
mkdir -p "$TEST_OUTPUT_DIR"

# Run tests
while IFS= read -r line; do
    if parse_test_def "$line"; then
        if should_run_test "$TEST_NAME"; then
            run_single_test "$TEST_NAME" "$MODULE" "$INPUT_FILE" "$DEPENDS" "$TIMEOUT" "$DESCRIPTION"
        fi
    fi
done < "$TEST_DEF_FILE"

# Summary
echo ""
echo "========================================"
echo "  Test Summary"
echo "========================================"
echo "Total:   $TOTAL"
echo -e "Passed:  ${GREEN}$PASSED${NC}"
echo -e "Failed:  ${RED}$FAILED${NC}"
echo -e "Skipped: ${YELLOW}$SKIPPED${NC}"
echo ""

if [[ $FAILED -eq 0 && $TOTAL -gt 0 ]]; then
    echo -e "${GREEN}All tests passed!${NC}"
elif [[ $TOTAL -eq 0 ]]; then
    echo -e "${YELLOW}No tests were run.${NC}"
else
    echo -e "${RED}Some tests failed. Check $TEST_OUTPUT_DIR for logs.${NC}"
fi

# Cleanup if requested
if [[ $CLEAN -eq 1 ]]; then
    echo ""
    echo "Cleaning up test outputs..."
    rm -rf "$TEST_OUTPUT_DIR"
    echo "Done."
fi

# Return appropriate exit code
if [[ $FAILED -gt 0 ]]; then
    exit 1
fi
exit 0
