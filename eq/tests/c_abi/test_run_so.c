/*
 * Phase L-4: test_run_so
 *
 * dlopen libeqapi.so, dlsym the 6 C ABI entry points, and exercise a
 * minimal init -> set_param -> get_state -> finalize cycle. This
 * proves the shared object is loadable, has the expected external
 * symbols, and that the Fortran-side lifecycle works when driven from
 * a C binary that never saw libeq.a.
 *
 * eq_run(0) is still a NOT_IMPL stub at L-3 (see eq_api.h header doc),
 * so for the happy path we only invoke it to confirm the contract.
 *
 * Usage:
 *   EQLIB_PATH=/path/to/libeqapi.so ./test_run_so   (EQLIB_PATH optional,
 *                                                    defaults to ./libeqapi.so)
 *
 * Return values:
 *   0      = OK
 *   1..8   = step that failed
 *   90     = dlopen failed
 *   91     = dlsym failed (one of the 6 entry points missing)
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dlfcn.h>

#include "eq_api.h"

typedef int (*eq_init_fn)(void);
typedef int (*eq_run_fn)(int);
typedef int (*eq_set_param_fn)(const char *, double);
typedef int (*eq_set_param_str_fn)(const char *, const char *);
typedef int (*eq_get_state_fn)(eq_state_t *);
typedef int (*eq_finalize_fn)(void);

int main(void) {
    const char *path = getenv("EQLIB_PATH");
    if (!path || !*path) path = "./libeqapi.so";

    /* RTLD_LAZY: libeqapi.so legitimately has unresolved references to
     * graphics symbols (grd1d, r2w2b_, ...) emitted by PL/lib routines
     * that are unreachable from the C ABI happy path. With RTLD_NOW the
     * dynamic loader would refuse to load the .so even though we never
     * call those routines. RTLD_LAZY defers resolution until the first
     * call, which never happens for graphics from a Python wrapper. */
    void *h = dlopen(path, RTLD_LAZY);
    if (!h) {
        fprintf(stderr, "dlopen(%s) failed: %s\n", path, dlerror());
        return 90;
    }

    eq_init_fn          f_init          = (eq_init_fn)          dlsym(h, "eq_init");
    eq_run_fn           f_run           = (eq_run_fn)           dlsym(h, "eq_run");
    eq_set_param_fn     f_set_param     = (eq_set_param_fn)     dlsym(h, "eq_set_param");
    eq_set_param_str_fn f_set_param_str = (eq_set_param_str_fn) dlsym(h, "eq_set_param_str");
    eq_get_state_fn     f_get_state     = (eq_get_state_fn)     dlsym(h, "eq_get_state");
    eq_finalize_fn      f_finalize      = (eq_finalize_fn)      dlsym(h, "eq_finalize");
    if (!f_init || !f_run || !f_set_param || !f_set_param_str ||
        !f_get_state || !f_finalize) {
        fprintf(stderr,
                "dlsym missing one of eq_{init,run,set_param,set_param_str,"
                "get_state,finalize}: init=%p run=%p set=%p set_str=%p "
                "get=%p fin=%p\n",
                (void*)f_init, (void*)f_run, (void*)f_set_param,
                (void*)f_set_param_str, (void*)f_get_state, (void*)f_finalize);
        dlclose(h);
        return 91;
    }

    int rc;
    eq_state_t st;

    rc = f_init();                                 if (rc != 0) { dlclose(h); return 1; }
    rc = f_set_param("RR",     3.0);               if (rc != 0) { dlclose(h); return 2; }
    rc = f_set_param("BB",     3.0);               if (rc != 0) { dlclose(h); return 3; }
    rc = f_set_param("RIP",    1.0);               if (rc != 0) { dlclose(h); return 4; }
    rc = f_set_param("MDLEQF", 0.0);               if (rc != 0) { dlclose(h); return 5; }
    /* Exercise the string setter too so a broken/missing eq_set_param_str
     * export is caught by this test (Bugbot MED on L-4). */
    rc = f_set_param_str("KNAMEQ", "eqdata.ITER"); if (rc != 0) { dlclose(h); return 9; }

    memset(&st, 0xAA, sizeof(st));
    rc = f_get_state(&st);                   if (rc != 0) { dlclose(h); return 6; }

    /* eq_run(0) currently returns EQ_ERR_NOT_IMPL (L-3 stub); we verify
     * the contract but do not treat it as a hard failure for the happy
     * path. Once eq_run(0) is implemented this can be tightened. */
    rc = f_run(0);
    if (rc != EQ_OK && rc != EQ_ERR_NOT_IMPL) {
        fprintf(stderr, "eq_run(0) returned unexpected rc=%d\n", rc);
        dlclose(h);
        return 7;
    }

    rc = f_finalize();                       if (rc != 0) { dlclose(h); return 8; }

    printf("OK: dlopen(%s) + init/set_param/get_state/finalize cycle"
           " nrgmax=%d nzgmax=%d npsmax=%d raxis=%g zaxis=%g qaxis=%g\n",
           path, st.nrgmax, st.nzgmax, st.npsmax,
           st.raxis, st.zaxis, st.qaxis);

    dlclose(h);
    return 0;
}
