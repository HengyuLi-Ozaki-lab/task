#!/bin/bash
#
# check_regression.sh <test_name> <test_output_dir> <baselines_dir> [tolerance] [--generate-baseline]
#
# Module-dispatching wrapper. Looks at <test_name> prefix to decide which
# module's dump+extractor to use:
#
#   tr_*  -> tr_regress.dat / extract_tr_metrics.py  (TR module)
#   wr_*  -> wr_regress.dat / extract_wr_metrics.py  (WR module)
#
# Reads the appropriate dump (produced when the module binary is run with
# {TR,WR}_REGRESS_DUMP=1), extracts metrics to JSON, and compares with
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

# Dispatch on test_name prefix to determine which module's artifacts to use.
case "$TEST_NAME" in
    wr_*)
        DUMP_NAME="wr_regress.dat"
        EXTRACTOR="$SCRIPT_DIR/extract_wr_metrics.py"
        SCHEMA="wr"
        ;;
    tr_*)
        DUMP_NAME="tr_regress.dat"
        EXTRACTOR="$SCRIPT_DIR/extract_tr_metrics.py"
        SCHEMA="tr"
        ;;
    *)
        # Default to TR for backward compatibility (no prefix dispatch).
        DUMP_NAME="tr_regress.dat"
        EXTRACTOR="$SCRIPT_DIR/extract_tr_metrics.py"
        SCHEMA="tr"
        ;;
esac

DUMP="$OUTPUT_DIR/$DUMP_NAME"
METRICS_ACTUAL="$OUTPUT_DIR/metrics.json"
METRICS_BASE="$BASELINES_DIR/$TEST_NAME/metrics.json"

if [[ ! -f "$DUMP" ]]; then
    echo "check_regression: dump not found: $DUMP" >&2
    echo "  did the test run with the appropriate *_REGRESS_DUMP=1 exported?" >&2
    exit 2
fi

if ! python3 "$EXTRACTOR" "$DUMP" > "$METRICS_ACTUAL"; then
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
    --schema "$SCHEMA" \
    --baseline "$METRICS_BASE" \
    --actual "$METRICS_ACTUAL" \
    --tolerance "$TOL"
