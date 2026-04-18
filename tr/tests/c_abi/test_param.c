/*
 * Phase L-3: test_param
 *
 * Exercises tr_set_param and tr_get_state together:
 *   - call tr_init (ALLOCATE_TRCOMM happens inside)
 *   - call tr_set_param for scalar names (RR, BB), an array subscript
 *     (PN[1]), and an unknown name; verify the return codes.
 *   - call tr_get_state and check that nrmax/nsmax come back > 0 (proof
 *     that the TRCOMM defaults set by tr_init are readable).
 *   - call tr_finalize.
 *
 * We don't assert the stored numerical values here: RR/BB/PN are not
 * part of tr_state_t by design (see §4.2 of the design doc). Layer-1
 * tests (L-6) will diff the Fortran-driven run against a C-driven run
 * that uses the same inputs.
 */
#include <stdio.h>
#include "tr_api.h"

int main(void) {
    int rc;
    tr_state_t s;

    rc = tr_init();
    if (rc != 0) { fprintf(stderr, "tr_init -> %d\n", rc); return 10; }

    rc = tr_set_param("RR", 7.5);
    if (rc != 0) { fprintf(stderr, "set RR -> %d\n", rc); return 11; }

    rc = tr_set_param("BB", 5.3);
    if (rc != 0) { fprintf(stderr, "set BB -> %d\n", rc); return 12; }

    rc = tr_set_param("PN[1]", 0.42);
    if (rc != 0) { fprintf(stderr, "set PN[1] -> %d\n", rc); return 13; }

    /* Array subscript out of range must be rejected. */
    rc = tr_set_param("PN[0]", 0.0);
    if (rc == 0) {
        fprintf(stderr, "PN[0] (idx=0) should have been rejected\n");
        return 14;
    }

    /* Unknown parameter must be rejected. */
    rc = tr_set_param("NOT_A_REAL_PARAM", 0.0);
    if (rc == 0) {
        fprintf(stderr, "unknown name should have been rejected\n");
        return 15;
    }

    /* L-6 registry extension: new scalars land in the table. */
    rc = tr_set_param("PNBENG", 1000.0);
    if (rc != 0) { fprintf(stderr, "set PNBENG -> %d\n", rc); return 19; }

    rc = tr_set_param("MODELG", 3.0);
    if (rc != 0) { fprintf(stderr, "set MODELG -> %d\n", rc); return 20; }

    /* L-6 string setter: KNAMEQ through tr_set_param_str. */
    rc = tr_set_param_str("KNAMEQ", "eqdata.ITER01");
    if (rc != 0) { fprintf(stderr, "set_str KNAMEQ -> %d\n", rc); return 21; }

    /* Unknown string-name must be rejected. */
    rc = tr_set_param_str("NOT_A_STRING_PARAM", "anything");
    if (rc == 0) {
        fprintf(stderr, "unknown string name should have been rejected\n");
        return 22;
    }

    /* get_state must succeed after init. */
    rc = tr_get_state(&s);
    if (rc != 0) { fprintf(stderr, "tr_get_state -> %d\n", rc); return 16; }

    if (s.nrmax <= 0 || s.nsmax <= 0) {
        fprintf(stderr, "bad state: nrmax=%d nsmax=%d\n", s.nrmax, s.nsmax);
        return 17;
    }

    rc = tr_finalize();
    if (rc != 0) { fprintf(stderr, "tr_finalize -> %d\n", rc); return 18; }

    printf("OK: tr_set_param + tr_get_state (nrmax=%d, nsmax=%d)\n",
           s.nrmax, s.nsmax);
    return 0;
}
