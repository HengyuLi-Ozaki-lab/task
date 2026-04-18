/*
 * Phase L-6: C ABI negative tests for libwrapi.
 *
 * The happy paths for wr_init -> wr_set_param -> wr_run ->
 * wr_get_state -> wr_finalize are covered by test_smoke.c,
 * test_param.c, test_run.c, test_reinit.c and test_run_so.c. This
 * driver concentrates on the *rejection* and *lifecycle* contracts
 * stated in wr_api.h and wr_api.f90:
 *
 *   1. wr_set_param / wr_get_state / wr_run must report WR_ERR_NOT_INIT
 *      (2) when called before wr_init.
 *   2. wr_set_param must reject clearly bogus names.
 *   3. wr_set_param must reject out-of-range array subscripts.
 *   4. wr_set_param must reject malformed subscript syntax.
 *   5. wr_init must be safe to call twice back-to-back (idempotent).
 *   6. wr_finalize must be safe to call without a prior wr_init
 *      (idempotent -> returns 0).
 *   7. wr_finalize followed by another wr_init + wr_run must work
 *      without double-free (Bugbot HIGH on PR #36: wr_api_finalize
 *      calls wr_reset_alloc_state so the allocator's internal SAVE
 *      flags are cleared; this test is the negative-path complement
 *      to test_reinit.c which covers the positive path). Critically:
 *      after wr_finalize, *any* operation on the closed state (run,
 *      get_state, set_param) must return WR_ERR_NOT_INIT.
 *
 * wr-specific vs tr: test_reinit.c already covers the happy-path
 * double-lifecycle; we focus the negative driver on the rejection
 * contracts. We also verify post-finalize rejection explicitly, which
 * is the reset-on-deallocate invariant enforced by wr_api_finalize.
 *
 * Each failure returns a distinct exit code (line number via __LINE__)
 * so regressions point at the exact contract that slipped.
 */
#include <stdio.h>
#include "wr_api.h"

/* Accept any non-zero code for "rejected"; different backends may map
 * the negative path to either WR_ERR_INVALID or WR_ERR_NOT_INIT
 * legitimately. The happy-path tests already pin WR_OK (=0). */
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

/* wr_set_param before init must return exactly WR_ERR_NOT_INIT (2)
 * per wr_api.f90::wr_api_set_param. We pin it here because confusing
 * it with WR_ERR_INVALID would mask the "no init yet" case. */
#define EXPECT_NOT_INIT(rc, step) do { \
    if ((rc) != WR_ERR_NOT_INIT) { \
        fprintf(stderr, "FAIL " step ": expected WR_ERR_NOT_INIT (%d), got %d\n", \
                WR_ERR_NOT_INIT, (rc)); \
        return (__LINE__); \
    } \
} while (0)

int main(void) {
    int rc;
    wr_state_t s;

    /* ---- 1: calls before init must be rejected with NOT_INIT ------ */
    rc = wr_get_state(&s);
    EXPECT_NOT_INIT(rc, "get_state-before-init");
    rc = wr_set_param("RR", 6.2);
    EXPECT_NOT_INIT(rc, "set_param-before-init");
    rc = wr_run(1);
    EXPECT_NOT_INIT(rc, "run-before-init");

    /* ---- 6: wr_finalize without init is idempotent (returns 0) --- */
    EXPECT_OK(wr_finalize(), "finalize-without-init");

    /* ---- init once ---------------------------------------------- */
    EXPECT_OK(wr_init(), "wr_init #1");

    /* ---- 2: unknown parameter names ----------------------------- */
    rc = wr_set_param("DEFINITELY_NOT_A_PARAM", 0.0);
    EXPECT_ERR(rc, "set_param-unknown-name");

    /* Empty name is also invalid. */
    rc = wr_set_param("", 0.0);
    EXPECT_ERR(rc, "set_param-empty-name");

    /* ---- 3: out-of-range array subscripts ----------------------- */
    rc = wr_set_param("PN[0]", 1.0);
    EXPECT_ERR(rc, "set_param-PN[0]");
    rc = wr_set_param("PN[99999]", 1.0);
    EXPECT_ERR(rc, "set_param-PN[99999]");
    /* wr-specific: per-ray arrays sized NRAYM (=100). Asking for
     * RFIN[101] must fail. */
    rc = wr_set_param("RFIN[101]", 1.0);
    EXPECT_ERR(rc, "set_param-RFIN[101]");

    /* ---- 4: malformed subscript syntax -------------------------- */
    rc = wr_set_param("PN[", 1.0);
    EXPECT_ERR(rc, "set_param-PN[");
    rc = wr_set_param("PN]", 1.0);
    EXPECT_ERR(rc, "set_param-PN]");
    rc = wr_set_param("PN[abc]", 1.0);
    EXPECT_ERR(rc, "set_param-PN[abc]");

    /* ---- 5: re-init is safe (idempotent) ------------------------ */
    EXPECT_OK(wr_init(), "wr_init #2 (re-init, no finalize between)");

    /* After re-init, a normal set_param still works. */
    EXPECT_OK(wr_set_param("RR", 6.2), "set_param-after-reinit");

    /* ---- 6: double finalize is safe ----------------------------- */
    EXPECT_OK(wr_finalize(), "wr_finalize #1");
    /* Second finalize on a closed state: must return 0 (idempotent)
     * per wr_api.f90. */
    EXPECT_OK(wr_finalize(), "wr_finalize #2 (idempotent)");

    /* ---- 7: post-finalize operations are rejected --------------- *
     * This is the wr-specific reset-SAVE-on-deallocate invariant
     * from PR #36: after wr_finalize, the g_initialized flag is
     * false so wr_run / wr_get_state / wr_set_param must all return
     * WR_ERR_NOT_INIT (not crash, not silently succeed).             */
    rc = wr_run(1);
    EXPECT_NOT_INIT(rc, "run-after-finalize");
    rc = wr_get_state(&s);
    EXPECT_NOT_INIT(rc, "get_state-after-finalize");
    rc = wr_set_param("RR", 6.2);
    EXPECT_NOT_INIT(rc, "set_param-after-finalize");

    /* ---- 7b: but wr_init + full cycle after finalize works ------ *
     * This is covered in detail by test_reinit.c; we just verify the
     * happy-path re-open here so a regression in the reset-on-
     * deallocate fix shows up in EITHER test. */
    EXPECT_OK(wr_init(), "wr_init #3 (post-finalize re-open)");
    EXPECT_OK(wr_get_state(&s), "get_state-after-reopen");
    EXPECT_OK(wr_finalize(), "wr_finalize #3 (close after reopen)");

    printf("OK: Layer 2 negative tests "
           "(before-init / names / subscripts / reinit / post-finalize)\n");
    return 0;
}
