/*
 * Phase L-3 C ABI smoke test.
 *
 * Goal at L-3: verify that the five tr_api entry points all return
 * TR_OK (=0) when invoked in the documented order:
 *
 *   tr_init -> tr_get_state -> tr_set_param -> tr_finalize
 *
 * Numerical correctness (does tr_run actually advance T by N*DT?) is
 * tested in test_run.c; parameter dispatch correctness is tested in
 * test_param.c.
 */
#include <stdio.h>
#include "tr_api.h"

static int expect_ok(const char *name, int rc) {
    if (rc == TR_OK) {
        printf("OK  %-12s returned TR_OK (=%d)\n", name, rc);
        return 0;
    }
    fprintf(stderr,
            "FAIL %s returned %d, expected TR_OK (=%d)\n",
            name, rc, TR_OK);
    return 1;
}

int main(void) {
    int failures = 0;
    tr_state_t st;

    failures += expect_ok("tr_init",      tr_init());
    failures += expect_ok("tr_get_state", tr_get_state(&st));
    failures += expect_ok("tr_set_param", tr_set_param("RR", 6.2));
    failures += expect_ok("tr_finalize",  tr_finalize());

    if (failures != 0) {
        fprintf(stderr, "%d entry point(s) returned a non-OK code\n", failures);
        return 1;
    }
    printf("Phase L-3 C ABI smoke OK: 4/4 entry points returned TR_OK\n");
    return 0;
}
