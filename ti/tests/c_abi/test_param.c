/*
 * Phase L-3: test_param
 *
 * Exercises ti_set_param and ti_get_state together:
 *   - call ti_init (allocate_ticomm happens inside)
 *   - call ti_set_param for scalar names (RR, BB), an array subscript
 *     (PN[1], PA[2]), and an unknown name; verify the return codes.
 *   - call ti_get_state and check that nrmax/nsmax come back > 0 (proof
 *     that the TICOMM defaults set by ti_init are readable).
 *   - call ti_finalize.
 *
 * We don't assert the stored numerical values here: RR/BB/PN are not
 * part of ti_state_t by design. Layer-1 tests (L-6) will diff the
 * Fortran-driven run against a C-driven run that uses the same inputs.
 */
#include <stdio.h>
#include "ti_api.h"

int main(void) {
    int rc;
    ti_state_t s;

    rc = ti_init();
    if (rc != 0) { fprintf(stderr, "ti_init -> %d\n", rc); return 10; }

    rc = ti_set_param("RR", 7.5);
    if (rc != 0) { fprintf(stderr, "set RR -> %d\n", rc); return 11; }

    rc = ti_set_param("BB", 5.3);
    if (rc != 0) { fprintf(stderr, "set BB -> %d\n", rc); return 12; }

    rc = ti_set_param("PN[1]", 0.42);
    if (rc != 0) { fprintf(stderr, "set PN[1] -> %d\n", rc); return 13; }

    /* Atomic mass via plcomm true name PA (ti renames pa->pm internally
     * but the C ABI uses PA per the L-3 plan). */
    rc = ti_set_param("PA[2]", 2.0);
    if (rc != 0) { fprintf(stderr, "set PA[2] -> %d\n", rc); return 14; }

    /* Array subscript out of range must be rejected. */
    rc = ti_set_param("PN[0]", 0.0);
    if (rc == 0) {
        fprintf(stderr, "PN[0] (idx=0) should have been rejected\n");
        return 15;
    }

    /* Unknown parameter must be rejected. */
    rc = ti_set_param("NOT_A_REAL_PARAM", 0.0);
    if (rc == 0) {
        fprintf(stderr, "unknown name should have been rejected\n");
        return 16;
    }

    /* 2D subscript: MODEL_BND[1,2] is a valid combination. */
    rc = ti_set_param("MODEL_BND[1,2]", 1.0);
    if (rc != 0) { fprintf(stderr, "set MODEL_BND[1,2] -> %d\n", rc); return 17; }

    /* get_state must succeed after init. */
    rc = ti_get_state(&s);
    if (rc != 0) { fprintf(stderr, "ti_get_state -> %d\n", rc); return 18; }

    if (s.nrmax <= 0 || s.nsmax <= 0) {
        fprintf(stderr, "bad state: nrmax=%d nsmax=%d\n", s.nrmax, s.nsmax);
        return 19;
    }

    rc = ti_finalize();
    if (rc != 0) { fprintf(stderr, "ti_finalize -> %d\n", rc); return 20; }

    printf("OK: ti_set_param + ti_get_state (nrmax=%d, nsmax=%d, nsa_max=%d)\n",
           s.nrmax, s.nsmax, s.nsa_max);
    return 0;
}
