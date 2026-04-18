#!/bin/bash
#
# check_regression.sh <test_name> <test_output_dir> <baselines_dir> [tolerance] [--generate-baseline]
#
# Reads <test_output_dir>/tr_regress.dat (produced when tr2 is run with
# TR_REGRESS_DUMP=1), extracts metrics to JSON, and compares with
# <baselines_dir>/<test_name>/metrics.json. Exits 0 on match, 1 on mismatch,
# 2 on missing dump, 3 on missing baseline.
#
# With --generate-baseline, the extracted JSON is written as baseline instead.
#
set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TEST_NAME="${1:?usage: $0 <test_name> <output_dir> <baselines_dir> [tol] [--generate-baseline]}"
OUTPUT_DIR="${2:?}"
BASELINES_DIR="${3:?}"
TOL="${4:-1e-10}"
MODE="${5:-compare}"

DUMP="$OUTPUT_DIR/tr_regress.dat"
METRICS_ACTUAL="$OUTPUT_DIR/metrics.json"
METRICS_BASE="$BASELINES_DIR/$TEST_NAME/metrics.json"

if [[ ! -f "$DUMP" ]]; then
    echo "check_regression: dump not found: $DUMP" >&2
    echo "  did the test run with TR_REGRESS_DUMP=1 exported?" >&2
    exit 2
fi

if ! python3 "$SCRIPT_DIR/extract_tr_metrics.py" "$DUMP" > "$METRICS_ACTUAL"; then
    echo "check_regression: failed to parse $DUMP" >&2
    exit 2
fi

if [[ "$MODE" == "--generate-baseline" ]]; then
    mkdir -p "$(dirname "$METRICS_BASE")"
    cp "$METRICS_ACTUAL" "$METRICS_BASE"
    echo "Baseline written: $METRICS_BASE"
    exit 0
fi

if [[ ! -f "$METRICS_BASE" ]]; then
    echo "check_regression: baseline not found: $METRICS_BASE" >&2
    echo "  run with --generate-baseline to create it." >&2
    exit 3
fi

python3 "$SCRIPT_DIR/compare_metrics.py" \
    --baseline "$METRICS_BASE" \
    --actual "$METRICS_ACTUAL" \
    --tolerance "$TOL"
