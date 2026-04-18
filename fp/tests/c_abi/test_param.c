/*
 * Phase L-3: test_param
 *
 * Exercises fp_set_param and fp_get_state together:
 *   - call fp_init (the FPCOMM defaults are populated by fpinit::fp_init).
 *   - call fp_set_param to change NRMAX (= 20) and a couple of geometry
 *     scalars (RR, BB) and an array element (PN[1]); verify the return
 *     codes.
 *   - call fp_get_state and check that state.nrmax reflects the value
 *     just written (proof that fp_set_param wrote to the live FPCOMM
 *     variable that fp_get_state then reads back).
 *   - reject invalid names and out-of-range subscripts.
 *   - call fp_finalize.
 */
#include <stdio.h>
#include "fp_api.h"

int main(void) {
    int rc;
    fp_state_t s;

    rc = fp_init();
    if (rc != FP_OK) { fprintf(stderr, "fp_init -> %d\n", rc); return 10; }

    /* Scalar real parameters. */
    rc = fp_set_param("RR", 7.5);
    if (rc != FP_OK) { fprintf(stderr, "set RR -> %d\n", rc); return 11; }

    rc = fp_set_param("BB", 5.3);
    if (rc != FP_OK) { fprintf(stderr, "set BB -> %d\n", rc); return 12; }

    /* Scalar int parameter that fp_state mirrors directly. */
    rc = fp_set_param("NRMAX", 20.0);
    if (rc != FP_OK) { fprintf(stderr, "set NRMAX -> %d\n", rc); return 13; }

    /* 1-origin array element. */
    rc = fp_set_param("PN[1]", 0.42);
    if (rc != FP_OK) { fprintf(stderr, "set PN[1] -> %d\n", rc); return 14; }

    /* Array subscript 0 must be rejected (1-origin). */
    rc = fp_set_param("PN[0]", 0.0);
    if (rc == FP_OK) {
        fprintf(stderr, "PN[0] (idx=0) should have been rejected\n");
        return 15;
    }

    /* Unknown parameter must be rejected. */
    rc = fp_set_param("NOT_A_REAL_PARAM", 0.0);
    if (rc == FP_OK) {
        fprintf(stderr, "unknown name should have been rejected\n");
        return 16;
    }

    /* get_state must succeed after init. */
    rc = fp_get_state(&s);
    if (rc != FP_OK) { fprintf(stderr, "fp_get_state -> %d\n", rc); return 17; }

    /* Hard-constraint: NRMAX must come back as exactly the value just set. */
    if (s.nrmax != 20) {
        fprintf(stderr, "expected nrmax=20 from fp_get_state, got %d\n", s.nrmax);
        return 18;
    }

    if (s.nsamax <= 0) {
        fprintf(stderr, "bad state: nsamax=%d (expected > 0)\n", s.nsamax);
        return 19;
    }

    rc = fp_finalize();
    if (rc != FP_OK) { fprintf(stderr, "fp_finalize -> %d\n", rc); return 20; }

    printf("OK: fp_set_param + fp_get_state (nrmax=%d, nsamax=%d)\n",
           s.nrmax, s.nsamax);
    return 0;
}
