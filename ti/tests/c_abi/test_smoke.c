/*
 * Phase L-2 C ABI smoke test.
 *
 * Goal at L-2: verify that
 *   1. ti_api.h is valid C (compiles cleanly with -Wall -Wextra),
 *   2. the BIND(C) symbols emitted by ti_api.f90 link against the C
 *      prototypes in ti_api.h, and
 *   3. each entry point returns TI_ERR_NOT_IMPL (=4) as documented.
 *
 * Numerical correctness is out of scope until Phase L-3.
 */
#include <stdio.h>
#include "ti_api.h"

static int expect_not_impl(const char *name, int rc) {
    if (rc == TI_ERR_NOT_IMPL) {
        printf("OK  %-12s returned TI_ERR_NOT_IMPL (=%d)\n", name, rc);
        return 0;
    }
    fprintf(stderr,
            "FAIL %s returned %d, expected TI_ERR_NOT_IMPL (=%d)\n",
            name, rc, TI_ERR_NOT_IMPL);
    return 1;
}

int main(void) {
    int failures = 0;
    ti_state_t st;

    failures += expect_not_impl("ti_init",      ti_init());
    failures += expect_not_impl("ti_run",       ti_run(0));
    failures += expect_not_impl("ti_set_param", ti_set_param("RR", 6.2));
    failures += expect_not_impl("ti_get_state", ti_get_state(&st));
    failures += expect_not_impl("ti_finalize",  ti_finalize());

    if (failures != 0) {
        fprintf(stderr, "%d stub(s) returned wrong code\n", failures);
        return 1;
    }
    printf("Phase L-2 C ABI smoke OK: 5/5 stubs returned TI_ERR_NOT_IMPL\n");
    return 0;
}
