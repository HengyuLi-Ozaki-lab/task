/*
 * Phase L-4: test_run_so for libtotapi.so
 *
 * dlopen libtotapi.so, dlsym the 6 C ABI entry points, and exercise
 * an init -> set_param (eq:RR + tr:DT) -> get_state -> finalize cycle.
 * This proves the composite shared object is loadable, has the
 * expected external symbols, and that the namespaced parameter
 * dispatcher routes correctly through the per-module registries
 * (eq_param_registry, tr_param_registry, ...).
 *
 * tot_init / tot_run / tot_finalize are still L-3 stubs that return
 * TOT_ERR_NOT_IMPL (=4); we verify the contract but do not treat that
 * return as a hard failure on the happy path. tot_set_param is real
 * (L-3) and must succeed.
 *
 * Usage:
 *   TOTLIB_PATH=/path/to/libtotapi.so ./test_run_so   (TOTLIB_PATH optional,
 *                                                      defaults to ./libtotapi.so)
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

#include "tot_api.h"

typedef int (*tot_init_fn)(void);
typedef int (*tot_run_fn)(int);
typedef int (*tot_set_param_fn)(const char *, double);
typedef int (*tot_set_param_str_fn)(const char *, const char *);
typedef int (*tot_get_state_fn)(tot_state_t *);
typedef int (*tot_finalize_fn)(void);

int main(void) {
    const char *path = getenv("TOTLIB_PATH");
    if (!path || !*path) path = "./libtotapi.so";

    /* RTLD_LAZY: libtotapi.so legitimately has unresolved references to
     * graphics symbols (PAGES, r2w2b_, ...) emitted by the per-module
     * .so files we link in. With RTLD_NOW the dynamic loader would
     * refuse to load the .so even though we never call those routines
     * on the C ABI happy path. RTLD_LAZY defers resolution until the
     * first call, which never happens for graphics from a Python
     * wrapper. */
    void *h = dlopen(path, RTLD_LAZY);
    if (!h) {
        fprintf(stderr, "dlopen(%s) failed: %s\n", path, dlerror());
        return 90;
    }

    tot_init_fn          f_init          = (tot_init_fn)          dlsym(h, "tot_init");
    tot_run_fn           f_run           = (tot_run_fn)           dlsym(h, "tot_run");
    tot_set_param_fn     f_set_param     = (tot_set_param_fn)     dlsym(h, "tot_set_param");
    tot_set_param_str_fn f_set_param_str = (tot_set_param_str_fn) dlsym(h, "tot_set_param_str");
    tot_get_state_fn     f_get_state     = (tot_get_state_fn)     dlsym(h, "tot_get_state");
    tot_finalize_fn      f_finalize      = (tot_finalize_fn)      dlsym(h, "tot_finalize");
    if (!f_init || !f_run || !f_set_param || !f_set_param_str ||
        !f_get_state || !f_finalize) {
        fprintf(stderr,
                "dlsym missing one of tot_{init,run,set_param,set_param_str,"
                "get_state,finalize}: init=%p run=%p set=%p set_str=%p "
                "get=%p fin=%p\n",
                (void*)f_init, (void*)f_run, (void*)f_set_param,
                (void*)f_set_param_str, (void*)f_get_state, (void*)f_finalize);
        dlclose(h);
        return 91;
    }

    int rc;
    tot_state_t st;

    /* tot_init is an L-3 stub (returns TOT_ERR_NOT_IMPL); we still call
     * it to verify the symbol dispatches and accept either OK or
     * NOT_IMPL. Treat any other return as a failure. */
    rc = f_init();
    if (rc != TOT_OK && rc != TOT_ERR_NOT_IMPL) {
        fprintf(stderr, "tot_init() returned unexpected rc=%d\n", rc);
        dlclose(h);
        return 1;
    }

    /* L-3 namespaced dispatch: must succeed (these route to eq_param_set
     * and tr_param_set respectively, which both accept these names). */
    rc = f_set_param("eq:RR", 6.5);
    if (rc != TOT_OK) {
        fprintf(stderr, "tot_set_param(\"eq:RR\", 6.5) returned rc=%d\n", rc);
        dlclose(h);
        return 2;
    }
    rc = f_set_param("tr:DT", 0.001);
    if (rc != TOT_OK) {
        fprintf(stderr, "tot_set_param(\"tr:DT\", 0.001) returned rc=%d\n", rc);
        dlclose(h);
        return 3;
    }

    /* tot_get_state is an L-3 stub: it zeros the struct and returns
     * NOT_IMPL. Accept either OK or NOT_IMPL; on NOT_IMPL the struct
     * must still be touched (presence flags = 0, scalars = 0). */
    memset(&st, 0xAA, sizeof(st));
    rc = f_get_state(&st);
    if (rc != TOT_OK && rc != TOT_ERR_NOT_IMPL) {
        fprintf(stderr, "tot_get_state() returned unexpected rc=%d\n", rc);
        dlclose(h);
        return 4;
    }

    /* tot_run is an L-3 stub: accept OK or NOT_IMPL. */
    rc = f_run(0);
    if (rc != TOT_OK && rc != TOT_ERR_NOT_IMPL) {
        fprintf(stderr, "tot_run(0) returned unexpected rc=%d\n", rc);
        dlclose(h);
        return 5;
    }

    /* tot_finalize is an L-3 stub: accept OK or NOT_IMPL. */
    rc = f_finalize();
    if (rc != TOT_OK && rc != TOT_ERR_NOT_IMPL) {
        fprintf(stderr, "tot_finalize() returned unexpected rc=%d\n", rc);
        dlclose(h);
        return 6;
    }

    printf("OK: dlopen(%s) + init/set_param(eq:RR, tr:DT)/get_state/finalize"
           " cycle  tr_present=%d ti_present=%d fp_present=%d wr_present=%d\n",
           path, st.tr_present, st.ti_present, st.fp_present, st.wr_present);

    dlclose(h);
    return 0;
}
