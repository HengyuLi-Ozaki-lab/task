/*
 * Phase L-3: test_run
 *
 * Exercises the full fp_init -> fp_set_param -> fp_run -> fp_get_state
 * -> fp_finalize cycle and checks that fp_run(N) actually advances
 * simulation time (TIMEFP > 0 after the loop).
 *
 *   fp_init;
 *   fp_set_param("NRMAX", 1);   // pick a tiny grid for speed
 *   fp_set_param("NSMAX", 1);
 *   fp_set_param("NSAMAX", 1);
 *   fp_set_param("NSBMAX", 1);
 *   fp_set_param("NTHMAX", 16);
 *   fp_set_param("NPMAX", 16);
 *   fp_set_param("DELT", 1.0e-3);
 *   fp_run(1);
 *   fp_get_state(&s);
 *   require s.timefp > 0
 *
 * The values mirror the smallest end of the existing fp_dt1 regression
 * input (NRMAX=1, NTMAX=1) so fp_loop is guaranteed to run a single
 * step at minimal cost.
 */
#include <stdio.h>
#include "fp_api.h"

int main(void) {
    int rc;
    fp_state_t s;

    rc = fp_init();
    if (rc != FP_OK) { fprintf(stderr, "fp_init -> %d\n", rc); return 1; }

    /* Minimum-cost configuration. fp_init populated NSMAX/NSAMAX/NSBMAX
       via fpinit::fp_init (NSMAX=1, NSAMAX=1, NSBMAX=1) but we set them
       explicitly so the test does not depend on those defaults. */
    rc = fp_set_param("NSMAX",  1.0); if (rc != FP_OK) return 2;
    rc = fp_set_param("NSAMAX", 1.0); if (rc != FP_OK) return 3;
    rc = fp_set_param("NSBMAX", 1.0); if (rc != FP_OK) return 4;
    rc = fp_set_param("NRMAX",  1.0); if (rc != FP_OK) return 5;
    rc = fp_set_param("NTHMAX", 16.0); if (rc != FP_OK) return 6;
    rc = fp_set_param("NPMAX",  16.0); if (rc != FP_OK) return 7;
    rc = fp_set_param("DELT",   1.0e-3); if (rc != FP_OK) return 8;

    rc = fp_run(1);
    if (rc != FP_OK) { fprintf(stderr, "fp_run -> %d\n", rc); return 9; }

    rc = fp_get_state(&s);
    if (rc != FP_OK) { fprintf(stderr, "fp_get_state -> %d\n", rc); return 10; }

    if (!(s.timefp > 0.0)) {
        fprintf(stderr, "expected TIMEFP > 0 after fp_run(1), got %g\n",
                s.timefp);
        return 11;
    }

    rc = fp_finalize();
    if (rc != FP_OK) { fprintf(stderr, "fp_finalize -> %d\n", rc); return 12; }

    printf("OK: fp_run advanced TIMEFP to %g (nrmax=%d, ntg2=%d)\n",
           s.timefp, s.nrmax, s.ntg2);
    return 0;
}
