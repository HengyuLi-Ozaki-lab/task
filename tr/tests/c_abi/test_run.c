/*
 * Phase L-3: test_run
 *
 * Exercises the full tr_init -> tr_run -> tr_get_state -> tr_finalize
 * cycle and checks that tr_run(N) actually advances simulation time
 * by ~N*DT:
 *
 *   tr_init;
 *   tr_set_param("DT", dt);
 *   tr_get_state(&s0);       // T0 (expected 0.0 after init)
 *   tr_run(nstp);
 *   tr_get_state(&s1);       // T1 should be ~ T0 + nstp*dt
 *   abs((T1 - T0) - nstp*dt) < tol
 *
 * The default namelist leaves MDLUF=0 (no UFILE input) so NTMAX can be
 * set freely without bumping against the NTAMAX clamp inside tr_loop.
 *
 * Tolerance is generous (1e-6) because the plasma solver may introduce
 * minor time adjustments; the goal is to confirm tr_run drives tr_loop
 * end-to-end, not to pin a bit-exact number.
 */
#include <stdio.h>
#include <math.h>
#include "tr_api.h"

int main(void) {
    int rc;
    tr_state_t s0, s1;
    const double dt   = 0.01;
    const int    nstp = 5;

    rc = tr_init();                   if (rc != 0) return 1;
    rc = tr_set_param("DT", dt);      if (rc != 0) return 2;
    /* Keep NTSTEP=1 so per-step printing does not batch updates. */
    rc = tr_set_param("NTSTEP", 1);   if (rc != 0) return 3;
    rc = tr_get_state(&s0);           if (rc != 0) return 4;
    rc = tr_run(nstp);                if (rc != 0) return 5;
    rc = tr_get_state(&s1);           if (rc != 0) return 6;

    double dT       = s1.T - s0.T;
    double expected = nstp * dt;
    if (fabs(dT - expected) > 1e-6) {
        fprintf(stderr,
                "expected T to advance by %g (nstp=%d * dt=%g), got %g\n",
                expected, nstp, dt, dT);
        return 7;
    }

    rc = tr_finalize();               if (rc != 0) return 8;

    printf("OK: tr_run advanced T by %g (expected ~%g, nstp=%d)\n",
           dT, expected, nstp);
    return 0;
}
