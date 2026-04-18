/*
 * Phase L-6: C ABI negative tests for TI.
 *
 * The happy paths for ti_init -> ti_set_param -> ti_run ->
 * ti_get_state -> ti_finalize are covered by test_smoke.c,
 * test_param.c, test_run.c and test_run_so.c. This driver concentrates
 * on the *rejection* contracts stated in ti_api.h:
 *
 *   1. ti_get_state / ti_run / ti_set_param must report TI_ERR_NOT_INIT
 *      (or some non-zero error code) when called before ti_init or
 *      after ti_finalize.
 *   2. ti_set_param must reject clearly bogus names.
 *   3. ti_set_param must reject out-of-range array subscripts.
 *   4. ti_set_param must reject malformed subscript syntax.
 *   5. ti_init must be safe to call twice back-to-back (re-init).
 *   6. ti_finalize must be safe to call twice back-to-back.
 *
 * Each failure returns a distinct exit code so regressions point at the
 * exact contract that slipped. The layout mirrors tr/tests/c_abi/
 * test_negative.c byte-for-byte where the contracts are identical.
 */
#include <stdio.h>
#include "ti_api.h"

/* Accept any non-zero code for "rejected"; we don't pin TI_ERR_INVALID
 * vs TI_ERR_NOT_INIT because different backends may map the negative
 * path to either code legitimately. The happy-path tests already pin
 * TI_OK (=0). */
#define EXPECT_ERR(rc, step) do { \
    if ((rc) == 0) { \
        fprintf(stderr, "FAIL " step ": expected non-zero rc, got 0\n"); \
        return (__LINE__); \
    } \
} while (0)

#define EXPECT_OK(rc, step) do { \
    if ((rc) != 0) { \
        fprintf(stderr, "FAIL " step ": expected 0, got %d\n", (rc)); \
        return (__LINE__); \
    } \
} while (0)

int main(void) {
    int rc;
    ti_state_t s;

    /* ---- 1: calls before init must be rejected ------------------ */
    rc = ti_get_state(&s);
    EXPECT_ERR(rc, "get_state-before-init");
    rc = ti_set_param("RR", 6.2);
    EXPECT_ERR(rc, "set_param-before-init");
    rc = ti_run(1);
    EXPECT_ERR(rc, "run-before-init");

    /* ---- init once ---------------------------------------------- */
    EXPECT_OK(ti_init(), "ti_init #1");

    /* ---- 2: unknown parameter names ----------------------------- */
    rc = ti_set_param("DEFINITELY_NOT_A_PARAM", 0.0);
    EXPECT_ERR(rc, "set_param-unknown-name");

    /* Empty name is also invalid. */
    rc = ti_set_param("", 0.0);
    EXPECT_ERR(rc, "set_param-empty-name");

    /* ---- 3: out-of-range array subscripts ----------------------- */
    rc = ti_set_param("PN[0]", 1.0);
    EXPECT_ERR(rc, "set_param-PN[0]");
    rc = ti_set_param("PN[99999]", 1.0);
    EXPECT_ERR(rc, "set_param-PN[99999]");

    /* ---- 4: malformed subscript syntax -------------------------- */
    rc = ti_set_param("PN[", 1.0);
    EXPECT_ERR(rc, "set_param-PN[");
    rc = ti_set_param("PN]", 1.0);
    EXPECT_ERR(rc, "set_param-PN]");
    rc = ti_set_param("PN[abc]", 1.0);
    EXPECT_ERR(rc, "set_param-PN[abc]");

    /* ---- 5: re-init is safe ------------------------------------- */
    EXPECT_OK(ti_init(), "ti_init #2 (re-init)");

    /* After re-init, a normal set_param still works. */
    EXPECT_OK(ti_set_param("RR", 6.2), "set_param-after-reinit");

    /* ---- 6: double finalize is safe ----------------------------- */
    EXPECT_OK(ti_finalize(),           "ti_finalize #1");
    /* Second finalize: either OK (idempotent) or an error code -- both
     * are acceptable contracts, but it must not crash. We accept any
     * integer return value. */
    (void) ti_finalize();

    /* ---- post-finalize: operations on closed state are rejected - */
    rc = ti_run(1);
    EXPECT_ERR(rc, "run-after-finalize");

    printf("OK: Layer 2 negative tests (init/finalize/name/subscript)\n");
    return 0;
}
