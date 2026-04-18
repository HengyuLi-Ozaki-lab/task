/*
 * Phase L-2 C ABI smoke test for TASK/WR.
 *
 * Goal at L-2: verify that
 *   1. wr_api.h is valid C (compiles cleanly with -Wall -Wextra),
 *   2. the BIND(C) symbols emitted by wr_api.f90 link against the C
 *      prototypes in wr_api.h, and
 *   3. each entry point returns WR_ERR_NOT_IMPL (=4) as documented.
 *
 * Numerical correctness is out of scope until Phase L-3.
 */
#include <stdio.h>
#include "wr_api.h"

static int expect_not_impl(const char *name, int rc) {
    if (rc == WR_ERR_NOT_IMPL) {
        printf("OK  %-12s returned WR_ERR_NOT_IMPL (=%d)\n", name, rc);
        return 0;
    }
    fprintf(stderr,
            "FAIL %s returned %d, expected WR_ERR_NOT_IMPL (=%d)\n",
            name, rc, WR_ERR_NOT_IMPL);
    return 1;
}

int main(void) {
    int failures = 0;
    wr_state_t st;

    failures += expect_not_impl("wr_init",      wr_init());
    failures += expect_not_impl("wr_run",       wr_run(0));
    failures += expect_not_impl("wr_set_param", wr_set_param("RF", 5.0e9));
    failures += expect_not_impl("wr_get_state", wr_get_state(&st));
    failures += expect_not_impl("wr_finalize",  wr_finalize());

    if (failures != 0) {
        fprintf(stderr, "%d stub(s) returned wrong code\n", failures);
        return 1;
    }
    printf("Phase L-2 C ABI smoke OK: 5/5 stubs returned WR_ERR_NOT_IMPL\n");
    return 0;
}
