/*
 * Phase L-4: test_run_so
 *
 * dlopen libfpapi.so, dlsym the 5 C ABI entry points, and exercise the
 * full init -> set_param -> run -> get_state -> finalize cycle. This
 * proves the shared object is loadable, has the expected external
 * symbols, and that the Fortran-side lifecycle works when driven from
 * a C binary that never saw libfp.a.
 *
 * Usage:
 *   FPLIB_PATH=/path/to/libfpapi.so ./test_run_so   (FPLIB_PATH optional,
 *                                                    defaults to ./libfpapi.so)
 *
 * Return values:
 *   0  = OK
 *   1..12 = step that failed (mirrors test_run.c numbering)
 *   90 = dlopen failed
 *   91 = dlsym failed (one of the 5 entry points missing)
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dlfcn.h>

#include "fp_api.h"

typedef int (*fp_init_fn)(void);
typedef int (*fp_run_fn)(int);
typedef int (*fp_set_param_fn)(const char *, double);
typedef int (*fp_get_state_fn)(fp_state_t *);
typedef int (*fp_finalize_fn)(void);

int main(void) {
    const char *path = getenv("FPLIB_PATH");
    if (!path || !*path) path = "./libfpapi.so";

    /* RTLD_LAZY: libfpapi.so may legitimately have unresolved
     * references to graphics symbols (PAGES, PAGEE, GRD1D, FPGRFA, ...)
     * emitted by FPCOMM routines that are unreachable from the C ABI
     * happy path (gated by IDBGFP debug flags). With RTLD_NOW the
     * dynamic loader would refuse to load the .so even though we never
     * call those routines. RTLD_LAZY defers resolution until the first
     * call, which never happens for graphics from a Python wrapper. */
    void *h = dlopen(path, RTLD_LAZY);
    if (!h) {
        fprintf(stderr, "dlopen(%s) failed: %s\n", path, dlerror());
        return 90;
    }

    fp_init_fn       f_init       = (fp_init_fn)       dlsym(h, "fp_init");
    fp_run_fn        f_run        = (fp_run_fn)        dlsym(h, "fp_run");
    fp_set_param_fn  f_set_param  = (fp_set_param_fn)  dlsym(h, "fp_set_param");
    fp_get_state_fn  f_get_state  = (fp_get_state_fn)  dlsym(h, "fp_get_state");
    fp_finalize_fn   f_finalize   = (fp_finalize_fn)   dlsym(h, "fp_finalize");
    if (!f_init || !f_run || !f_set_param || !f_get_state || !f_finalize) {
        fprintf(stderr,
                "dlsym missing one of fp_{init,run,set_param,get_state,finalize}:"
                " init=%p run=%p set=%p get=%p fin=%p\n",
                (void*)f_init, (void*)f_run, (void*)f_set_param,
                (void*)f_get_state, (void*)f_finalize);
        dlclose(h);
        return 91;
    }

    /* Mirror the test_run.c cycle so the .so is proven to be a drop-in
     * replacement for the static libfp.a link path. */
    int rc;
    fp_state_t s;

    rc = f_init();
    if (rc != FP_OK) { fprintf(stderr, "fp_init -> %d\n", rc); dlclose(h); return 1; }

    /* Minimum-cost configuration mirroring test_run.c. */
    rc = f_set_param("NSMAX",  1.0); if (rc != FP_OK) { dlclose(h); return 2; }
    rc = f_set_param("NSAMAX", 1.0); if (rc != FP_OK) { dlclose(h); return 3; }
    rc = f_set_param("NSBMAX", 1.0); if (rc != FP_OK) { dlclose(h); return 4; }
    rc = f_set_param("NRMAX",  1.0); if (rc != FP_OK) { dlclose(h); return 5; }
    rc = f_set_param("NTHMAX", 16.0); if (rc != FP_OK) { dlclose(h); return 6; }
    rc = f_set_param("NPMAX",  16.0); if (rc != FP_OK) { dlclose(h); return 7; }
    rc = f_set_param("DELT",   1.0e-3); if (rc != FP_OK) { dlclose(h); return 8; }

    rc = f_run(1);
    if (rc != FP_OK) { fprintf(stderr, "fp_run -> %d\n", rc); dlclose(h); return 9; }

    rc = f_get_state(&s);
    if (rc != FP_OK) { fprintf(stderr, "fp_get_state -> %d\n", rc); dlclose(h); return 10; }

    if (!(s.timefp > 0.0)) {
        fprintf(stderr, "expected TIMEFP > 0 after fp_run(1), got %g\n", s.timefp);
        dlclose(h);
        return 11;
    }

    rc = f_finalize();
    if (rc != FP_OK) { fprintf(stderr, "fp_finalize -> %d\n", rc); dlclose(h); return 12; }

    printf("OK: dlopen(%s) + init/set_param/run/get_state/finalize cycle"
           " advanced TIMEFP to %g (nrmax=%d, ntg2=%d)\n",
           path, s.timefp, s.nrmax, s.ntg2);

    dlclose(h);
    return 0;
}
