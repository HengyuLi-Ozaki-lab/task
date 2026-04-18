/*
 * Phase L-3 C ABI smoke test.
 *
 * Goal at L-3: verify that the five ti_api entry points all return
 * TI_OK (=0) when invoked in the documented order:
 *
 *   ti_init -> ti_get_state -> ti_set_param -> ti_finalize
 *
 * Numerical correctness (does ti_run actually advance T by N*DT?) is
 * tested in test_run.c; parameter dispatch correctness is tested in
 * test_param.c.
 */
#include <stdio.h>
#include "ti_api.h"

static int expect_ok(const char *name, int rc) {
    if (rc == TI_OK) {
        printf("OK  %-12s returned TI_OK (=%d)\n", name, rc);
        return 0;
    }
    fprintf(stderr,
            "FAIL %s returned %d, expected TI_OK (=%d)\n",
            name, rc, TI_OK);
    return 1;
}

int main(void) {
    int failures = 0;
    ti_state_t st;

    failures += expect_ok("ti_init",      ti_init());
    failures += expect_ok("ti_get_state", ti_get_state(&st));
    failures += expect_ok("ti_set_param", ti_set_param("RR", 6.2));
    failures += expect_ok("ti_finalize",  ti_finalize());

    if (failures != 0) {
        fprintf(stderr, "%d entry point(s) returned a non-OK code\n", failures);
        return 1;
    }
    printf("Phase L-3 C ABI smoke OK: 4/4 entry points returned TI_OK\n");
    return 0;
}
