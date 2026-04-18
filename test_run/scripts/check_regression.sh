#!/bin/bash
#
# check_regression.sh <test_name> <test_output_dir> <baselines_dir> [tolerance] [--generate-baseline]
#
# Reads <test_output_dir>/<module>_regress.dat (produced when the binary is
# run with the matching <MODULE>_REGRESS_DUMP=1 env var), extracts metrics
# to JSON, and compares with <baselines_dir>/<test_name>/metrics.json.
# Exit codes: 0 = match, 1 = mismatch, 2 = missing/malformed dump,
#             3 = missing baseline, 4 = unsupported test name prefix.
#
# Module dispatch is by the test_name prefix:
#   tr_*  -> tr_regress.dat  / extract_tr_metrics.py
#   fp_*  -> fp_regress.dat  / extract_fp_metrics.py
#   ti_*  -> ti_regress.dat  / extract_ti_metrics.py
#   tot_* -> tot_regress.dat / extract_tot_metrics.py
#
# With --generate-baseline as the 5th arg, the extracted JSON is written
# as the baseline instead of being compared.
#
set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

TEST_NAME="${1:?usage: $0 <test_name> <output_dir> <baselines_dir> [tol] [--generate-baseline]}"
OUTPUT_DIR="${2:?}"
BASELINES_DIR="${3:?}"
TOL="${4:-1e-10}"
MODE="${5:-compare}"

case "$TEST_NAME" in
  tr_*)  DUMP_BASENAME="tr_regress.dat";  EXTRACTOR="extract_tr_metrics.py" ;;
  fp_*)  DUMP_BASENAME="fp_regress.dat";  EXTRACTOR="extract_fp_metrics.py" ;;
  ti_*)  DUMP_BASENAME="ti_regress.dat";  EXTRACTOR="extract_ti_metrics.py" ;;
  tot_*) DUMP_BASENAME="tot_regress.dat"; EXTRACTOR="extract_tot_metrics.py" ;;
  *)
    echo "check_regression: unsupported test name prefix: $TEST_NAME" >&2
    echo "  expected one of: tr_*, fp_*, ti_*, tot_*" >&2
    exit 4
    ;;
esac

DUMP="$OUTPUT_DIR/$DUMP_BASENAME"
METRICS_ACTUAL="$OUTPUT_DIR/metrics.json"
METRICS_BASE="$BASELINES_DIR/$TEST_NAME/metrics.json"

if [[ ! -f "$DUMP" ]]; then
    echo "check_regression: dump not found: $DUMP" >&2
    echo "  did the test run with the matching *_REGRESS_DUMP=1 env var exported?" >&2
    exit 2
fi

if [[ ! -x "$SCRIPT_DIR/$EXTRACTOR" && ! -f "$SCRIPT_DIR/$EXTRACTOR" ]]; then
    echo "check_regression: extractor not found: $SCRIPT_DIR/$EXTRACTOR" >&2
    exit 2
fi

if ! python3 "$SCRIPT_DIR/$EXTRACTOR" "$DUMP" > "$METRICS_ACTUAL"; then
    echo "check_regression: failed to parse $DUMP with $EXTRACTOR" >&2
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
