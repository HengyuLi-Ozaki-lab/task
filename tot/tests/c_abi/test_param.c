/*
 * Phase L-3: test_param
 *
 * Exercises the namespaced dispatcher wired into tot_set_param. For
 * each known per-module namespace we call a representative bare
 * name, then hit a few error paths (unknown bare name, bad prefix,
 * out-of-range subscript).
 *
 * tot_init() is still a stub at L-3 (returns NOT_IMPL) but the
 * dispatcher does not depend on any tot-level state, only on the
 * USE-linked per-module registries. We therefore skip the init/
 * finalize wrapper here and talk to the dispatcher directly.
 *
 * The concrete values picked below are chosen to satisfy each
 * per-module registry without triggering an index-out-of-range or a
 * type mismatch. We are testing the dispatcher wiring, not the
 * numerical validity of any particular choice.
 */
#include <stdio.h>
#include "tot_api.h"

static int check(const char *label, int rc, int expected) {
    if (rc == expected) {
        printf("OK  %-40s -> %d\n", label, rc);
        return 0;
    }
    fprintf(stderr, "FAIL %-40s -> %d (expected %d)\n",
            label, rc, expected);
    return 1;
}

int main(void) {
    int failures = 0;

    /* ---- success cases: one scalar per namespace (except eq, see below) */
    failures += check("tr:RR  = 6.2",
                      tot_set_param("tr:RR", 6.2),
                      TOT_OK);
    failures += check("tr:DT  = 0.01",
                      tot_set_param("tr:DT", 0.01),
                      TOT_OK);
    failures += check("tr:PN[1] = 0.7",
                      tot_set_param("tr:PN[1]", 0.7),
                      TOT_OK);

    failures += check("fp:NRMAX = 100",
                      tot_set_param("fp:NRMAX", 100.0),
                      TOT_OK);
    failures += check("fp:RR = 6.2",
                      tot_set_param("fp:RR", 6.2),
                      TOT_OK);

    failures += check("ti:RR = 6.2",
                      tot_set_param("ti:RR", 6.2),
                      TOT_OK);
    failures += check("ti:DT = 0.01",
                      tot_set_param("ti:DT", 0.01),
                      TOT_OK);

    failures += check("wrx:RR = 6.2",
                      tot_set_param("wrx:RR", 6.2),
                      TOT_OK);
    failures += check("wr:RR  = 6.2 (alias to wrx)",
                      tot_set_param("wr:RR", 6.2),
                      TOT_OK);

    /* eq L-3 landed in PR #78; eq_param_set now maps RR, RA, BB, ...
     * through plcomm_parm / eqcom1_mod. Unknown eq names continue to
     * return INVALID. */
    failures += check("eq:RR  = 6.2",
                      tot_set_param("eq:RR", 6.2),
                      TOT_OK);
    failures += check("eq:BB  = 5.3",
                      tot_set_param("eq:BB", 5.3),
                      TOT_OK);
    failures += check("eq:RIPFC[1] = 1.0e6",
                      tot_set_param("eq:RIPFC[1]", 1.0e6),
                      TOT_OK);
    failures += check("eq:NOSUCHVAR",
                      tot_set_param("eq:NOSUCHVAR", 0.0),
                      TOT_ERR_INVALID);

    /* ---- error paths ----------------------------------------------- */
    failures += check("unknown bare name (tr)",
                      tot_set_param("tr:NOSUCHVAR", 0.0),
                      TOT_ERR_INVALID);
    failures += check("unknown namespace",
                      tot_set_param("zz:RR", 0.0),
                      TOT_ERR_INVALID);
    failures += check("no prefix",
                      tot_set_param("RR", 0.0),
                      TOT_ERR_INVALID);
    failures += check("empty prefix",
                      tot_set_param(":RR", 0.0),
                      TOT_ERR_INVALID);
    failures += check("prefix-only",
                      tot_set_param("tr:", 0.0),
                      TOT_ERR_INVALID);

    /* ---- string dispatcher: tr: and eq: are supported today. */
    failures += check("tr:KNAMEQ = eqdata.ITER01",
                      tot_set_param_str("tr:KNAMEQ", "eqdata.ITER01"),
                      TOT_OK);
    failures += check("eq:KNAMEQ = eqdata.ITER01",
                      tot_set_param_str("eq:KNAMEQ", "eqdata.ITER01"),
                      TOT_OK);
    failures += check("unknown string name (tr)",
                      tot_set_param_str("tr:NOSUCHSTRING", "x"),
                      TOT_ERR_INVALID);
    failures += check("unknown string name (eq)",
                      tot_set_param_str("eq:NOSUCHSTRING", "x"),
                      TOT_ERR_INVALID);
    failures += check("string on unsupported namespace",
                      tot_set_param_str("wrx:ANYTHING", "x"),
                      TOT_ERR_INVALID);
    failures += check("string no prefix",
                      tot_set_param_str("KNAMEQ", "x"),
                      TOT_ERR_INVALID);

    if (failures != 0) {
        fprintf(stderr, "%d dispatch assertion(s) failed\n", failures);
        return 1;
    }
    printf("Phase L-3 tot test_param OK: namespaced dispatch verified\n");
    return 0;
}
