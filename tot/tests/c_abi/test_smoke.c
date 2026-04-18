/*
 * Phase L-3 C ABI smoke test for the tot orchestrator.
 *
 * Init/run/get_state/finalize are still stubs at L-3 (orchestrator
 * fan-out lands in a later phase), so they continue to return
 * TOT_ERR_NOT_IMPL. tot_set_param (and the new tot_set_param_str)
 * now dispatches to real per-module registries, and therefore
 * returns TOT_OK when the namespaced name resolves and
 * TOT_ERR_INVALID when it does not. This smoke driver asserts both
 * sides of that dispatch without allocating any backing state
 * (so no init is required).
 */
#include <stdio.h>
#include "tot_api.h"

static int expect(const char *name, int rc, int expected) {
    if (rc == expected) {
        printf("OK  %-28s returned %d\n", name, rc);
        return 0;
    }
    fprintf(stderr,
            "FAIL %s returned %d, expected %d\n",
            name, rc, expected);
    return 1;
}

int main(void) {
    int failures = 0;
    tot_state_t st;

    /* Still-stub entry points. */
    failures += expect("tot_init",      tot_init(),      TOT_ERR_NOT_IMPL);
    failures += expect("tot_run",       tot_run(0),      TOT_ERR_NOT_IMPL);
    failures += expect("tot_get_state", tot_get_state(&st), TOT_ERR_NOT_IMPL);
    failures += expect("tot_finalize",  tot_finalize(),  TOT_ERR_NOT_IMPL);

    /* L-3 dispatcher: a bare name (no "<ns>:" prefix) is rejected. */
    failures += expect("set_param no-prefix",
                       tot_set_param("RR", 6.2),
                       TOT_ERR_INVALID);

    /* Unknown namespace is rejected. */
    failures += expect("set_param bad-ns",
                       tot_set_param("zz:RR", 6.2),
                       TOT_ERR_INVALID);

    /* Prefix-only (no bare name) is rejected. */
    failures += expect("set_param prefix-only",
                       tot_set_param("tr:", 0.0),
                       TOT_ERR_INVALID);

    /* String dispatch: same prefix rules, no state required to reject. */
    failures += expect("set_param_str no-prefix",
                       tot_set_param_str("KNAMEQ", "x"),
                       TOT_ERR_INVALID);
    failures += expect("set_param_str bad-ns",
                       tot_set_param_str("zz:KNAMEQ", "x"),
                       TOT_ERR_INVALID);

    if (failures != 0) {
        fprintf(stderr, "%d assertion(s) failed\n", failures);
        return 1;
    }
    printf("Phase L-3 tot smoke OK: stubs + dispatcher error paths verified\n");
    return 0;
}
