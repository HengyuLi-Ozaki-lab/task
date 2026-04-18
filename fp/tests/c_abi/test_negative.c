/*
 * Phase L-6: C ABI negative tests for libfpapi.so.
 *
 * The happy paths for fp_init -> fp_set_param -> fp_run ->
 * fp_get_state -> fp_finalize are covered by test_smoke.c,
 * test_param.c, test_run.c and test_run_so.c. This driver concentrates
 * on the *rejection* contracts stated in fp_api.h:
 *
 *   1. fp_get_state / fp_run / fp_set_param must return a non-zero
 *      error code (FP_ERR_NOT_INIT or a subclass) when called before
 *      fp_init or after fp_finalize.
 *   2. fp_set_param must reject clearly bogus names (FP_ERR_INVALID).
 *   3. fp_set_param must reject out-of-range array subscripts.
 *   4. fp_set_param must reject malformed subscript syntax.
 *   5. fp_init must be safe to call twice back-to-back (re-init).
 *   6. fp_finalize must be safe to call twice back-to-back.
 *
 * Each failure returns a distinct exit code (the current __LINE__) so
 * regressions point at the exact contract that slipped. The L-3 tests
 * already pin FP_OK on happy paths; we accept any non-zero rc here
 * because different error conditions can legitimately map to either
 * FP_ERR_INVALID or FP_ERR_NOT_INIT depending on the code path.
 *
 * Mirrors tr/tests/c_abi/test_negative.c (PR #53, Phase L-6).
 */
#include <stdio.h>
#include "fp_api.h"

/* Accept any non-zero code for "rejected"; we don't pin FP_ERR_INVALID
 * vs FP_ERR_NOT_INIT because different backends may map the negative
 * path to either code legitimately. The happy-path tests already pin
 * FP_OK (=0). */
#define EXPECT_ERR(rc, step) do { \
    if ((rc) == FP_OK) { \
        fprintf(stderr, "FAIL " step ": expected non-zero rc, got FP_OK\n"); \
        return (__LINE__); \
    } \
} while (0)

#define EXPECT_OK(rc, step) do { \
    if ((rc) != FP_OK) { \
        fprintf(stderr, "FAIL " step ": expected FP_OK, got %d\n", (rc)); \
        return (__LINE__); \
    } \
} while (0)

int main(void) {
    int rc;
    fp_state_t s;

    /* ---- 1: calls before init must be rejected ------------------ */
    rc = fp_get_state(&s);
    EXPECT_ERR(rc, "get_state-before-init");
    rc = fp_set_param("RR", 6.2);
    EXPECT_ERR(rc, "set_param-before-init");
    rc = fp_run(1);
    EXPECT_ERR(rc, "run-before-init");

    /* ---- init once ---------------------------------------------- */
    EXPECT_OK(fp_init(), "fp_init #1");

    /* ---- 2: unknown parameter names ----------------------------- */
    rc = fp_set_param("DEFINITELY_NOT_A_PARAM", 0.0);
    EXPECT_ERR(rc, "set_param-unknown-name");

    /* Empty name is also invalid. */
    rc = fp_set_param("", 0.0);
    EXPECT_ERR(rc, "set_param-empty-name");

    /* ---- 3: out-of-range array subscripts ----------------------- */
    rc = fp_set_param("PN[0]", 1.0);
    EXPECT_ERR(rc, "set_param-PN[0]");
    rc = fp_set_param("PN[99999]", 1.0);
    EXPECT_ERR(rc, "set_param-PN[99999]");

    /* ---- 4: malformed subscript syntax -------------------------- */
    rc = fp_set_param("PN[", 1.0);
    EXPECT_ERR(rc, "set_param-PN[");
    rc = fp_set_param("PN]", 1.0);
    EXPECT_ERR(rc, "set_param-PN]");
    rc = fp_set_param("PN[abc]", 1.0);
    EXPECT_ERR(rc, "set_param-PN[abc]");

    /* ---- 5: re-init is safe ------------------------------------- */
    EXPECT_OK(fp_init(), "fp_init #2 (re-init)");

    /* After re-init, a normal set_param still works. */
    EXPECT_OK(fp_set_param("RR", 6.2), "set_param-after-reinit");

    /* ---- 6: double finalize is safe ----------------------------- */
    EXPECT_OK(fp_finalize(), "fp_finalize #1");
    /* Second finalize: either OK (idempotent) or an error code -- both
     * are acceptable contracts, but it must not crash. We accept any
     * integer return value. */
    (void) fp_finalize();

    /* ---- post-finalize: operations on closed state are rejected - */
    rc = fp_run(1);
    EXPECT_ERR(rc, "run-after-finalize");

    printf("OK: Layer 2 negative tests (init/finalize/name/subscript)\n");
    return 0;
}
