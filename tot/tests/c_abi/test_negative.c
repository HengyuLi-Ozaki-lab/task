/*
 * Phase L-6: C ABI negative tests for the tot orchestrator.
 *
 * The happy paths for tot_init -> tot_set_param[_str] -> tot_run ->
 * tot_get_state -> tot_finalize are covered by test_smoke.c (stubs +
 * dispatcher error paths), test_param.c (namespaced success +
 * per-module reject), and test_run_so.c (dlopen libtotapi.so cycle).
 *
 * This driver concentrates on the *rejection* contracts that the
 * orchestrator imposes ON TOP OF the per-module registries, mirroring
 * eq/tests/c_abi/test_negative.c and tr/tests/c_abi/test_negative.c:
 *
 *   1. Pre-init: tot_init / tot_run / tot_get_state / tot_finalize are
 *      L-3/L-4/L-5 stubs returning TOT_ERR_NOT_IMPL today (rc=4) so we
 *      pin that contract here. Once L-6 fan-out lands these will return
 *      TOT_OK / TOT_ERR_NOT_INIT respectively and the test should be
 *      flipped to mirror the eq/tr negative pattern (see EXPECT_EQ
 *      lines below for the future-proof markers).
 *
 *   2. Unknown / malformed namespace prefixes are rejected with
 *      TOT_ERR_INVALID by the dispatcher itself (no per-module call
 *      reached). This is the happy-path contract for set_param /
 *      set_param_str regardless of init state, because the dispatcher
 *      runs in pure logic.
 *
 *   3. Missing prefix (bare "RR") -> TOT_ERR_INVALID.
 *
 *   4. Double-finalize is safe (returns TOT_ERR_NOT_IMPL today; once
 *      L-6 lands this will be TOT_OK or TOT_ERR_NOT_INIT -- both
 *      acceptable, but it must not crash).
 *
 *   5. Post-finalize: any subsequent dispatcher reject still returns
 *      TOT_ERR_INVALID (proves the dispatcher logic is independent of
 *      the orchestrator init state, which is correct because per-module
 *      registries hold their own state).
 *
 * The macros are kept verbose so a regression points at the failing
 * step by name rather than just an exit code.
 */
#include <stdio.h>
#include "tot_api.h"

#define EXPECT_OK(rc, step) do { \
    if ((rc) != 0) { \
        fprintf(stderr, "FAIL " step ": expected 0, got %d\n", (rc)); \
        return (__LINE__); \
    } \
} while (0)

#define EXPECT_EQ(actual, expected, step) do { \
    if ((actual) != (expected)) { \
        fprintf(stderr, "FAIL " step ": got %d, expected %d\n", \
                (int)(actual), (int)(expected)); \
        return (__LINE__); \
    } \
} while (0)

int main(void) {
    int rc;
    tot_state_t s;

    /* ---- 1: pre-init contract.
     * At L-3/L-4/L-5 the orchestrator entry points are stubs and
     * return TOT_ERR_NOT_IMPL regardless of init state. Pin that
     * exact contract here. Once L-6 fan-out lands these will return
     * TOT_OK (init/finalize) or TOT_ERR_NOT_INIT (run/get_state); at
     * that point this block needs to be split:
     *
     *   EXPECT_EQ(tot_get_state(&s), TOT_ERR_NOT_INIT, ...);
     *   EXPECT_EQ(tot_run(1),        TOT_ERR_NOT_INIT, ...);
     *
     * For now we accept TOT_ERR_NOT_IMPL so the test does not
     * spuriously fail on the L-5 stub .so. */
    rc = tot_get_state(&s);
    if (rc != TOT_ERR_NOT_IMPL && rc != TOT_ERR_NOT_INIT) {
        fprintf(stderr, "FAIL get_state-before-init: got %d, "
                        "expected TOT_ERR_NOT_IMPL or TOT_ERR_NOT_INIT\n", rc);
        return __LINE__;
    }
    rc = tot_run(1);
    if (rc != TOT_ERR_NOT_IMPL && rc != TOT_ERR_NOT_INIT) {
        fprintf(stderr, "FAIL run-before-init: got %d, "
                        "expected TOT_ERR_NOT_IMPL or TOT_ERR_NOT_INIT\n", rc);
        return __LINE__;
    }

    /* ---- 2 + 3: dispatcher rejects unknown / missing namespaces
     * regardless of init state. The dispatcher runs in pure logic so
     * these contracts hold even before tot_init. */
    EXPECT_EQ(tot_set_param("RR", 6.2),
              TOT_ERR_INVALID, "set_param-no-prefix");
    EXPECT_EQ(tot_set_param("zz:RR", 6.2),
              TOT_ERR_INVALID, "set_param-unknown-namespace");
    EXPECT_EQ(tot_set_param(":RR", 6.2),
              TOT_ERR_INVALID, "set_param-empty-prefix");
    EXPECT_EQ(tot_set_param("tr:", 0.0),
              TOT_ERR_INVALID, "set_param-prefix-only");
    EXPECT_EQ(tot_set_param_str("KNAMEQ", "x"),
              TOT_ERR_INVALID, "set_param_str-no-prefix");
    EXPECT_EQ(tot_set_param_str("zz:KNAMEQ", "x"),
              TOT_ERR_INVALID, "set_param_str-unknown-namespace");

    /* ---- init (still a stub at L-5, may return NOT_IMPL or OK once
     *        L-6 lands; both acceptable). */
    rc = tot_init();
    if (rc != TOT_OK && rc != TOT_ERR_NOT_IMPL) {
        fprintf(stderr, "FAIL tot_init: got %d, "
                        "expected TOT_OK or TOT_ERR_NOT_IMPL\n", rc);
        return __LINE__;
    }

    /* ---- unknown bare-name reject (per-module registry rejects with
     * TOT_ERR_INVALID). Each namespace is exercised independently so
     * a regression in one per-module dispatcher is pinpointed. */
    EXPECT_EQ(tot_set_param("tr:DEFINITELY_NOT_A_PARAM", 0.0),
              TOT_ERR_INVALID, "set_param-tr-unknown");
    EXPECT_EQ(tot_set_param("eq:DEFINITELY_NOT_A_PARAM", 0.0),
              TOT_ERR_INVALID, "set_param-eq-unknown");
    EXPECT_EQ(tot_set_param("fp:DEFINITELY_NOT_A_PARAM", 0.0),
              TOT_ERR_INVALID, "set_param-fp-unknown");
    EXPECT_EQ(tot_set_param("ti:DEFINITELY_NOT_A_PARAM", 0.0),
              TOT_ERR_INVALID, "set_param-ti-unknown");
    EXPECT_EQ(tot_set_param("wr:DEFINITELY_NOT_A_PARAM", 0.0),
              TOT_ERR_INVALID, "set_param-wr-unknown");
    EXPECT_EQ(tot_set_param("wrx:DEFINITELY_NOT_A_PARAM", 0.0),
              TOT_ERR_INVALID, "set_param-wrx-unknown");

    /* ---- string setter on a namespace without a string registry
     * (fp / ti / wrx have no string back-end at L-3) -> INVALID. */
    EXPECT_EQ(tot_set_param_str("fp:KANY", "x"),
              TOT_ERR_INVALID, "set_param_str-fp-no-string-registry");
    EXPECT_EQ(tot_set_param_str("ti:KANY", "x"),
              TOT_ERR_INVALID, "set_param_str-ti-no-string-registry");
    EXPECT_EQ(tot_set_param_str("wrx:KANY", "x"),
              TOT_ERR_INVALID, "set_param_str-wrx-no-string-registry");

    /* ---- sanity: a valid set_param after the malformed barrage must
     * still succeed -- the rejected calls must not have left any
     * per-module dispatcher in a broken state. */
    EXPECT_OK(tot_set_param("eq:RR", 6.2),  "set_param-eq-RR-after-bad");
    EXPECT_OK(tot_set_param("tr:DT", 0.001), "set_param-tr-DT-after-bad");
    EXPECT_OK(tot_set_param_str("tr:KNAMEQ", "eqdata.test"),
              "set_param_str-tr-KNAMEQ-after-bad");

    /* ---- 4: double-finalize is safe (no crash). At L-5 finalize is
     * a stub returning NOT_IMPL; once L-6 lands either OK or NOT_INIT
     * is acceptable. */
    rc = tot_finalize();
    if (rc != TOT_OK && rc != TOT_ERR_NOT_IMPL) {
        fprintf(stderr, "FAIL tot_finalize #1: got %d, "
                        "expected TOT_OK or TOT_ERR_NOT_IMPL\n", rc);
        return __LINE__;
    }
    rc = tot_finalize();
    if (rc != TOT_OK && rc != TOT_ERR_NOT_IMPL && rc != TOT_ERR_NOT_INIT) {
        fprintf(stderr, "FAIL tot_finalize #2: got %d, "
                        "expected TOT_OK / TOT_ERR_NOT_IMPL / "
                        "TOT_ERR_NOT_INIT\n", rc);
        return __LINE__;
    }

    /* ---- 5: post-finalize the dispatcher still rejects bad
     * namespaces (pure logic, independent of tot init state). */
    EXPECT_EQ(tot_set_param("RR", 0.0),
              TOT_ERR_INVALID, "set_param-no-prefix-after-finalize");
    EXPECT_EQ(tot_set_param("zz:RR", 0.0),
              TOT_ERR_INVALID, "set_param-bad-ns-after-finalize");

    printf("OK: Layer 2 negative tests for tot orchestrator "
           "(pre-init / unknown-namespace / missing-prefix / "
           "double-finalize / post-finalize)\n");
    return 0;
}
