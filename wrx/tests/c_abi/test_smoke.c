/*
 * Phase L-2 C ABI smoke test for TASK/WRX.
 *
 * Goal at L-2: verify that
 *   1. wrx_api.h is valid C (compiles cleanly with -Wall -Wextra),
 *   2. the BIND(C) symbols emitted by wrx_api.f90 link against the C
 *      prototypes in wrx_api.h, and
 *   3. each entry point returns WRX_ERR_NOT_IMPL (=4) as documented.
 *
 * Numerical correctness is out of scope until Phase L-3.
 */
#include <stdio.h>
#include "wrx_api.h"

static int expect_not_impl(const char *name, int rc) {
    if (rc == WRX_ERR_NOT_IMPL) {
        printf("OK  %-13s returned WRX_ERR_NOT_IMPL (=%d)\n", name, rc);
        return 0;
    }
    fprintf(stderr,
            "FAIL %s returned %d, expected WRX_ERR_NOT_IMPL (=%d)\n",
            name, rc, WRX_ERR_NOT_IMPL);
    return 1;
}

int main(void) {
    int failures = 0;
    wrx_state_t st;

    failures += expect_not_impl("wrx_init",      wrx_init());
    failures += expect_not_impl("wrx_run",       wrx_run(0));
    failures += expect_not_impl("wrx_set_param", wrx_set_param("RF", 170.0));
    failures += expect_not_impl("wrx_get_state", wrx_get_state(&st));
    failures += expect_not_impl("wrx_finalize",  wrx_finalize());

    if (failures != 0) {
        fprintf(stderr, "%d stub(s) returned wrong code\n", failures);
        return 1;
    }
    printf("Phase L-2 C ABI smoke OK: 5/5 stubs returned WRX_ERR_NOT_IMPL\n");
    return 0;
}
