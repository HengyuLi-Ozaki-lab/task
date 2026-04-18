/*
 * Phase L-3 C ABI smoke test.
 *
 * Goal at L-3: verify that
 *   1. fp_api.h is valid C (compiles cleanly with -Wall -Wextra),
 *   2. the BIND(C) symbols emitted by fp_api.f90 link against the C
 *      prototypes in fp_api.h, and
 *   3. each entry point returns FP_OK after the documented init order.
 *
 * Numerical correctness is exercised in test_param.c / test_run.c.
 */
#include <stdio.h>
#include "fp_api.h"

static int expect_ok(const char *name, int rc) {
    if (rc == FP_OK) {
        printf("OK  %-12s returned FP_OK (=%d)\n", name, rc);
        return 0;
    }
    fprintf(stderr,
            "FAIL %s returned %d, expected FP_OK (=%d)\n",
            name, rc, FP_OK);
    return 1;
}

int main(void) {
    int failures = 0;
    fp_state_t st;

    failures += expect_ok("fp_init",      fp_init());
    /* fp_run(0): zero steps. fp_prep still runs on the first call so
       the FPCOMM arrays are allocated; fp_loop returns immediately
       because NTMAX is overwritten to 0. */
    failures += expect_ok("fp_run",       fp_run(0));
    failures += expect_ok("fp_set_param", fp_set_param("RR", 6.2));
    failures += expect_ok("fp_get_state", fp_get_state(&st));
    failures += expect_ok("fp_finalize",  fp_finalize());

    if (failures != 0) {
        fprintf(stderr, "%d entry point(s) returned wrong code\n", failures);
        return 1;
    }
    printf("Phase L-3 C ABI smoke OK: 5/5 entry points returned FP_OK\n");
    return 0;
}
