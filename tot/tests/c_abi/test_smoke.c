/*
 * Phase L-2 C ABI smoke test for the tot orchestrator.
 *
 * Goal at L-2: verify that
 *   1. tot_api.h is valid C (compiles cleanly with -Wall -Wextra),
 *   2. the BIND(C) symbols emitted by tot_api.f90 link against the C
 *      prototypes in tot_api.h, and
 *   3. each entry point returns TOT_ERR_NOT_IMPL (=4) as documented.
 *
 * Orchestrator fan-out (tot_init -> tr_init + ti_init + ..., etc.) and
 * numerical correctness are out of scope until Phase L-3+.
 */
#include <stdio.h>
#include "tot_api.h"

static int expect_not_impl(const char *name, int rc) {
    if (rc == TOT_ERR_NOT_IMPL) {
        printf("OK  %-14s returned TOT_ERR_NOT_IMPL (=%d)\n", name, rc);
        return 0;
    }
    fprintf(stderr,
            "FAIL %s returned %d, expected TOT_ERR_NOT_IMPL (=%d)\n",
            name, rc, TOT_ERR_NOT_IMPL);
    return 1;
}

int main(void) {
    int failures = 0;
    tot_state_t st;

    failures += expect_not_impl("tot_init",      tot_init());
    failures += expect_not_impl("tot_run",       tot_run(0));
    failures += expect_not_impl("tot_set_param", tot_set_param("RR", 6.2));
    failures += expect_not_impl("tot_get_state", tot_get_state(&st));
    failures += expect_not_impl("tot_finalize",  tot_finalize());

    if (failures != 0) {
        fprintf(stderr, "%d stub(s) returned wrong code\n", failures);
        return 1;
    }
    printf("Phase L-2 C ABI smoke OK: 5/5 stubs returned TOT_ERR_NOT_IMPL\n");
    return 0;
}
