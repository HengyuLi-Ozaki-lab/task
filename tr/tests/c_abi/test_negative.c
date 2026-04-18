/*
 * Phase L-6: C ABI negative tests.
 *
 * The happy paths for tr_init -> tr_set_param -> tr_run ->
 * tr_get_state -> tr_finalize are covered by test_smoke.c,
 * test_param.c, test_run.c and test_run_so.c. This driver concentrates
 * on the *rejection* contracts stated in tr_api.h:
 *
 *   1. tr_get_state / tr_run / tr_set_param must report TR_ERR_NOT_INIT
 *      (or some non-zero error code) when called before tr_init or
 *      after tr_finalize.
 *   2. tr_set_param must reject clearly bogus names.
 *   3. tr_set_param must reject out-of-range array subscripts.
 *   4. tr_set_param must reject malformed subscript syntax.
 *   5. tr_init must be safe to call twice back-to-back (re-init).
 *   6. tr_finalize must be safe to call twice back-to-back.
 *
 * Each failure returns a distinct exit code so regressions point at the
 * exact contract that slipped.
 */
#include <stdio.h>
#include "tr_api.h"

/* Accept any non-zero code for "rejected"; we don't pin TR_ERR_INVALID
 * vs TR_ERR_NOT_INIT because different backends may map the negative
 * path to either code legitimately. The happy-path tests already pin
 * TR_OK (=0). */
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
    tr_state_t s;

    /* ---- 1: calls before init must be rejected ------------------ */
    rc = tr_get_state(&s);
    EXPECT_ERR(rc, "get_state-before-init");
    rc = tr_set_param("RR", 6.2);
    EXPECT_ERR(rc, "set_param-before-init");
    rc = tr_run(1);
    EXPECT_ERR(rc, "run-before-init");

    /* ---- init once ---------------------------------------------- */
    EXPECT_OK(tr_init(), "tr_init #1");

    /* ---- 2: unknown parameter names ----------------------------- */
    rc = tr_set_param("DEFINITELY_NOT_A_PARAM", 0.0);
    EXPECT_ERR(rc, "set_param-unknown-name");

    /* Empty name is also invalid. */
    rc = tr_set_param("", 0.0);
    EXPECT_ERR(rc, "set_param-empty-name");

    /* ---- 3: out-of-range array subscripts ----------------------- */
    rc = tr_set_param("PN[0]", 1.0);
    EXPECT_ERR(rc, "set_param-PN[0]");
    rc = tr_set_param("PN[99999]", 1.0);
    EXPECT_ERR(rc, "set_param-PN[99999]");

    /* ---- 4: malformed subscript syntax -------------------------- */
    rc = tr_set_param("PN[", 1.0);
    EXPECT_ERR(rc, "set_param-PN[");
    rc = tr_set_param("PN]", 1.0);
    EXPECT_ERR(rc, "set_param-PN]");
    rc = tr_set_param("PN[abc]", 1.0);
    EXPECT_ERR(rc, "set_param-PN[abc]");

    /* ---- 5: re-init is safe ------------------------------------- */
    EXPECT_OK(tr_init(), "tr_init #2 (re-init)");

    /* After re-init, a normal set_param still works. */
    EXPECT_OK(tr_set_param("RR", 6.2), "set_param-after-reinit");

    /* ---- 6: double finalize is safe ----------------------------- */
    EXPECT_OK(tr_finalize(),           "tr_finalize #1");
    /* Second finalize: either OK (idempotent) or an error code -- both
     * are acceptable contracts, but it must not crash. We accept any
     * integer return value. */
    (void) tr_finalize();

    /* ---- post-finalize: operations on closed state are rejected - */
    rc = tr_run(1);
    EXPECT_ERR(rc, "run-after-finalize");

    printf("OK: Layer 2 negative tests (init/finalize/name/subscript)\n");
    return 0;
}
