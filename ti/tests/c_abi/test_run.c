/*
 * Phase L-3: test_run
 *
 * Exercises the full ti_init -> ti_run -> ti_get_state -> ti_finalize
 * cycle and checks that ti_run(N) actually advances simulation time
 * by ~N*DT:
 *
 *   ti_init;
 *   ti_set_param("DT", dt);
 *   ti_get_state(&s0);       // T0 (expected 0.0 after init)
 *   ti_run(nstp);
 *   ti_get_state(&s1);       // T1 should be ~ T0 + nstp*dt
 *   abs((T1 - T0) - nstp*dt) < tol
 *
 * Tolerance is generous (1e-6) because the plasma solver may introduce
 * minor time adjustments; the goal is to confirm ti_run drives ti_exec
 * end-to-end, not to pin a bit-exact number.
 */
#include <stdio.h>
#include <math.h>
#include "ti_api.h"

int main(void) {
    int rc;
    ti_state_t s0, s1;
    const double dt   = 0.01;
    const int    nstp = 5;

    rc = ti_init();                   if (rc != 0) return 1;
    rc = ti_set_param("DT", dt);      if (rc != 0) return 2;
    /* Keep NTSTEP=1 so per-step printing does not batch updates. */
    rc = ti_set_param("NTSTEP", 1);   if (rc != 0) return 3;
    rc = ti_get_state(&s0);           if (rc != 0) return 4;
    rc = ti_run(nstp);                if (rc != 0) {
        fprintf(stderr, "ti_run(%d) -> %d\n", nstp, rc); return 5;
    }
    rc = ti_get_state(&s1);           if (rc != 0) return 6;

    double dT       = s1.T - s0.T;
    double expected = nstp * dt;
    if (fabs(dT - expected) > 1e-6) {
        fprintf(stderr,
                "expected T to advance by %g (nstp=%d * dt=%g), got %g\n",
                expected, nstp, dt, dT);
        return 7;
    }

    rc = ti_finalize();               if (rc != 0) return 8;

    printf("OK: ti_run advanced T by %g (expected ~%g, nstp=%d)\n",
           dT, expected, nstp);
    return 0;
}
