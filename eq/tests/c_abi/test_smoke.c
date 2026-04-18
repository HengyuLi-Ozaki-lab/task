/*
 * test_smoke.c
 *
 * Phase L-2 smoke driver for the EQ C ABI.
 *
 * Exercises the four scaffold-level entry points:
 *   eq_init       -> expected EQ_OK
 *   eq_get_state  -> expected EQ_OK; prints grid dimensions
 *   eq_set_param  -> expected EQ_ERR_NOT_IMPL (registry stub)
 *   eq_finalize   -> expected EQ_OK
 *
 * eq_run is also poked to confirm the NOT_IMPL contract is visible.
 *
 * The test does NOT assert on any numerical value beyond the error
 * codes; the real regression story is that `make eq` still produces
 * a byte-identical binary, which is enforced by the build rules in
 * eq/Makefile (OBJ_API is not linked into libeq.a).
 */
#include <assert.h>
#include <stdio.h>
#include <string.h>

#include "eq_api.h"

int main(void) {
    int rc;
    eq_state_t state;

    printf("eq_api L-2 smoke\n");
    printf("  sizeof(eq_state_t) = %zu bytes\n", sizeof(eq_state_t));

    rc = eq_init();
    printf("  eq_init       rc=%d (expect %d=EQ_OK)\n", rc, EQ_OK);
    assert(rc == EQ_OK);

    memset(&state, 0xAA, sizeof(state));
    rc = eq_get_state(&state);
    printf("  eq_get_state  rc=%d (expect %d=EQ_OK)\n", rc, EQ_OK);
    assert(rc == EQ_OK);
    printf("    nrgmax=%d nzgmax=%d npsmax=%d\n",
           state.nrgmax, state.nzgmax, state.npsmax);
    printf("    nrmax=%d  nthmax=%d nsumax=%d\n",
           state.nrmax, state.nthmax, state.nsumax);
    printf("    raxis=%g zaxis=%g qaxis=%g psi0=%g betap=%g\n",
           state.raxis, state.zaxis, state.qaxis,
           state.psi0,  state.betap);

    rc = eq_run(0);
    printf("  eq_run(0)     rc=%d (expect %d=EQ_ERR_NOT_IMPL)\n",
           rc, EQ_ERR_NOT_IMPL);
    assert(rc == EQ_ERR_NOT_IMPL);

    rc = eq_set_param("RR", 3.0);
    printf("  eq_set_param  rc=%d (expect %d=EQ_ERR_NOT_IMPL)\n",
           rc, EQ_ERR_NOT_IMPL);
    assert(rc == EQ_ERR_NOT_IMPL);

    rc = eq_finalize();
    printf("  eq_finalize   rc=%d (expect %d=EQ_OK)\n", rc, EQ_OK);
    assert(rc == EQ_OK);

    /* After finalize the not-initialized contract must hold again. */
    rc = eq_run(0);
    printf("  eq_run post-fin rc=%d (expect %d=EQ_ERR_NOT_INIT)\n",
           rc, EQ_ERR_NOT_INIT);
    assert(rc == EQ_ERR_NOT_INIT);

    printf("eq_api L-2 smoke: PASS\n");
    return 0;
}
