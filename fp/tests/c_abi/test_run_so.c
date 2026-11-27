/*
 * Phase L-4: test_run_so
 *
 * dlopen libfpapi.so, dlsym the original five C ABI entry points
 * (fp_init, fp_run, fp_set_param, fp_get_state, fp_finalize) and the
 * task-web-client #232 functions (fp_set_param_str, fp_fns_info_abi_version,
 * fp_fns_info_size, fp_get_fns_info, fp_get_fns_grid, fp_get_fns), and exercise the
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
 *   92 = fp_state_abi_version / fp_state_size missing (library predates #246)
 *   93 = layout version or size differs from fp_api.h (#246)
 *   20..49 = a check of the distribution function failed (task-web-client #232)
 *   50..65 = a further check of the distribution function (task-web-client #232)
 *   94 = fp_set_param_str or one of the five task-web-client #232 functions is missing
 *   95 = fp_fns_info_t's layout version or size differs from fp_api.h
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dlfcn.h>
#include <math.h>

#include "fp_api.h"

typedef int (*fp_init_fn)(void);
typedef int (*fp_run_fn)(int);
typedef int (*fp_set_param_fn)(const char *, double);
typedef int (*fp_get_state_fn)(fp_state_t *);
typedef int (*fp_finalize_fn)(void);

/* task-web-client #232 */
typedef int    (*fp_set_param_str_fn)(const char *, const char *);
typedef int    (*fp_fns_info_abi_version_fn)(void);
typedef size_t (*fp_fns_info_size_fn)(void);
typedef int    (*fp_get_fns_info_fn)(int, fp_fns_info_t *);
typedef int    (*fp_get_fns_grid_fn)(int, double *, int, double *, int, double *, int);
typedef int    (*fp_get_fns_fn)(int, double *, int);

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

    /* #246: the layout query must agree with this header before any
     * fp_state_t is passed. 92 = symbols missing (library predates
     * #246), 93 = version or size differs (library and header from
     * different commits). */
    typedef int    (*fp_abi_version_fn)(void);
    typedef size_t (*fp_state_size_fn)(void);
    fp_abi_version_fn f_abi  = (fp_abi_version_fn) dlsym(h, "fp_state_abi_version");
    fp_state_size_fn  f_size = (fp_state_size_fn)  dlsym(h, "fp_state_size");
    if (!f_abi || !f_size) {
        fprintf(stderr, "dlsym missing fp_state_abi_version / fp_state_size (#246)\n");
        dlclose(h);
        return 92;
    }
    if (f_abi() != FP_STATE_ABI_VERSION || f_size() != sizeof(fp_state_t)) {
        fprintf(stderr,
                "layout mismatch: library v%d / %lu bytes, fp_api.h v%d / %lu bytes\n",
                f_abi(), (unsigned long) f_size(),
                FP_STATE_ABI_VERSION, (unsigned long) sizeof(fp_state_t));
        dlclose(h);
        return 93;
    }

    /* task-web-client #232: the distribution function's five functions, and its record's
     * layout query, which must agree with this header. */
    fp_set_param_str_fn        f_set_str   = (fp_set_param_str_fn)        dlsym(h, "fp_set_param_str");
    fp_fns_info_abi_version_fn f_fns_abi   = (fp_fns_info_abi_version_fn) dlsym(h, "fp_fns_info_abi_version");
    fp_fns_info_size_fn        f_fns_size  = (fp_fns_info_size_fn)        dlsym(h, "fp_fns_info_size");
    fp_get_fns_info_fn         f_fns_info  = (fp_get_fns_info_fn)         dlsym(h, "fp_get_fns_info");
    fp_get_fns_grid_fn         f_fns_grid  = (fp_get_fns_grid_fn)         dlsym(h, "fp_get_fns_grid");
    fp_get_fns_fn              f_fns       = (fp_get_fns_fn)              dlsym(h, "fp_get_fns");
    if (!f_set_str || !f_fns_abi || !f_fns_size || !f_fns_info || !f_fns_grid || !f_fns) {
        fprintf(stderr, "dlsym missing fp_set_param_str or one of the task-web-client #232 functions\n");
        dlclose(h);
        return 94;
    }
    if (f_fns_abi() != FP_FNS_INFO_ABI_VERSION || f_fns_size() != sizeof(fp_fns_info_t)) {
        fprintf(stderr,
                "fns_info layout mismatch: library v%d / %lu bytes, fp_api.h v%d / %lu bytes\n",
                f_fns_abi(), (unsigned long) f_fns_size(),
                FP_FNS_INFO_ABI_VERSION, (unsigned long) sizeof(fp_fns_info_t));
        dlclose(h);
        return 95;
    }
    {
        fp_fns_info_t info;
        double buf[4];
        /* Before fp_init. */
        if (f_fns_info(1, &info) != FP_ERR_NOT_INIT) { dlclose(h); return 20; }
        if (f_fns_grid(1, buf, 1, buf, 1, buf, 1) != FP_ERR_NOT_INIT) { dlclose(h); return 21; }
        if (f_fns(1, buf, 1) != FP_ERR_NOT_INIT) { dlclose(h); return 22; }
    }

    /* Mirror the test_run.c cycle so the .so is proven to be a drop-in
     * replacement for the static libfp.a link path. */
    int rc;
    fp_state_t s;

    rc = f_init();
    if (rc != FP_OK) { fprintf(stderr, "fp_init -> %d\n", rc); dlclose(h); return 1; }

    {
        /* task-web-client #232: no distribution before the first run. */
        fp_fns_info_t info;
        double buf[4];
        if (f_fns_info(1, &info) != FP_ERR_CALC_FAILED) { dlclose(h); return 23; }
        if (f_fns_grid(1, buf, 1, buf, 1, buf, 1) != FP_ERR_CALC_FAILED) { dlclose(h); return 24; }
        if (f_fns(1, buf, 1) != FP_ERR_CALC_FAILED) { dlclose(h); return 25; }
    }

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

    /* ---- the distribution function after a run (task-web-client #232) ---- */
    {
        fp_fns_info_t info;
        double *pm, *thm, *rm, *f;
        int i, nth, np, nr, n;

        rc = f_fns_info(1, &info);
        if (rc != FP_OK) { fprintf(stderr, "fp_get_fns_info -> %d\n", rc); dlclose(h); return 26; }
        if (info.nsa != 1 || info.ns != 1 || info.nthmax != s.nthmax ||
            info.npmax != s.npmax || info.nrmax != s.nrmax) {
            fprintf(stderr, "fns_info dims %d %d %d %d %d\n", info.nsa, info.ns,
                    info.nthmax, info.npmax, info.nrmax);
            dlclose(h);
            return 27;
        }
        if (!(info.ptfp0 > 0.0 && info.vtfp0 > 0.0 && info.delp > 0.0 && info.delth > 0.0 &&
              info.timefp == s.timefp)) { dlclose(h); return 28; }
        if (info.theta0 != 0.0) { dlclose(h); return 51; }   /* default MODELR = 0 */
        nth = info.nthmax; np = info.npmax; nr = info.nrmax; n = nth * np * nr;
        if (fabs(info.pmax - info.delp * np) > 1e-12 * info.pmax) { dlclose(h); return 52; }
        pm = malloc(sizeof(double) * np); thm = malloc(sizeof(double) * nth);
        rm = malloc(sizeof(double) * nr); f = malloc(sizeof(double) * n);
        if (!pm || !thm || !rm || !f) { dlclose(h); return 29; }
        for (i = 0; i < np; ++i) pm[i] = NAN;
        for (i = 0; i < nth; ++i) thm[i] = NAN;
        for (i = 0; i < nr; ++i) rm[i] = NAN;
        for (i = 0; i < n; ++i) f[i] = NAN;

        rc = f_fns_grid(1, pm, np, thm, nth, rm, nr);
        if (rc != FP_OK) { fprintf(stderr, "fp_get_fns_grid -> %d\n", rc); dlclose(h); return 30; }
        for (i = 0; i < np; ++i) if (pm[i] != info.delp * (i + 0.5)) { dlclose(h); return 31; }
        for (i = 0; i < nth; ++i) if (thm[i] != info.delth * (i + 0.5)) { dlclose(h); return 32; }
        for (i = 1; i < nr; ++i) if (!(rm[i] > rm[i - 1])) { dlclose(h); return 33; }

        rc = f_fns(1, f, n);
        if (rc != FP_OK) { fprintf(stderr, "fp_get_fns -> %d\n", rc); dlclose(h); return 34; }
        for (i = 0; i < n; ++i) if (!isfinite(f[i])) { dlclose(h); return 35; }
        if (!(f[0] > 0.0)) { dlclose(h); return 50; }

        /* Refusals after a run. */
        if (f_fns(1, f, n - 1) != FP_ERR_INVALID) { dlclose(h); return 36; }
        if (f_fns(1, NULL, n) != FP_ERR_INVALID) { dlclose(h); return 37; }
        if (f_fns(0, f, n) != FP_ERR_INVALID) { dlclose(h); return 38; }
        if (f_fns(2, f, n) != FP_ERR_INVALID) { dlclose(h); return 39; }      /* NSAMAX = 1 */
        if (f_fns_info(1, NULL) != FP_ERR_INVALID) { dlclose(h); return 40; }
        if (f_fns_grid(1, pm, np - 1, thm, nth, rm, nr) != FP_ERR_INVALID) { dlclose(h); return 41; }
        if (f_fns_grid(1, pm, np, NULL, nth, rm, nr) != FP_ERR_INVALID) { dlclose(h); return 42; }

        /* A successful set makes them refuse until the next run (#253). */
        if (f_set_param("DELT", 1.0e-3) != FP_OK) { dlclose(h); return 43; }
        if (f_fns_info(1, &info) != FP_ERR_CALC_FAILED) { dlclose(h); return 44; }
        if (f_fns(1, f, n) != FP_ERR_CALC_FAILED) { dlclose(h); return 45; }
        if (f_run(1) != FP_OK) { dlclose(h); return 46; }
        if (f_fns(1, f, n) != FP_OK) { dlclose(h); return 47; }
        if (f_set_str("KNAMEQ", "eqdata") != FP_OK) { dlclose(h); return 48; }
        if (f_fns_grid(1, pm, np, thm, nth, rm, nr) != FP_ERR_CALC_FAILED) { dlclose(h); return 49; }

        /* A second pass on an asymmetric mesh: nr != nth != np. */
        if (f_set_param("NRMAX", 3.0) != FP_OK) { dlclose(h); return 53; }
        if (f_set_param("NTHMAX", 12.0) != FP_OK) { dlclose(h); return 54; }
        if (f_run(0) != FP_OK) { dlclose(h); return 55; }
        if (f_fns_info(1, &info) != FP_OK) { dlclose(h); return 56; }
        if (!(info.nrmax == 3 && info.nthmax == 12 && info.npmax == 16)) { dlclose(h); return 57; }
        free(pm); free(thm); free(rm); free(f);
        nth = info.nthmax; np = info.npmax; nr = info.nrmax; n = nth * np * nr;
        pm = malloc(sizeof(double) * np); thm = malloc(sizeof(double) * nth);
        rm = malloc(sizeof(double) * nr); f = malloc(sizeof(double) * n);
        if (!pm || !thm || !rm || !f) { dlclose(h); return 29; }
        for (i = 0; i < np; ++i) pm[i] = NAN;
        for (i = 0; i < nth; ++i) thm[i] = NAN;
        for (i = 0; i < nr; ++i) rm[i] = NAN;
        for (i = 0; i < n; ++i) f[i] = NAN;
        if (f_fns_grid(1, pm, np, thm, nth, rm, nr) != FP_OK) { dlclose(h); return 58; }
        if (f_fns(1, f, n) != FP_OK) { dlclose(h); return 59; }
        for (i = 0; i < np; ++i) if (pm[i] != info.delp * (i + 0.5)) { dlclose(h); return 60; }
        for (i = 0; i < nth; ++i) if (thm[i] != info.delth * (i + 0.5)) { dlclose(h); return 61; }
        for (i = 1; i < nr; ++i) if (!(rm[i] > rm[i - 1])) { dlclose(h); return 62; }
        for (i = 0; i < n; ++i) if (!isfinite(f[i])) { dlclose(h); return 63; }
        if (!(f[0] > 0.0)) { dlclose(h); return 64; }
        if (f_fns_grid(1, pm, nth, thm, np, rm, nr) != FP_ERR_INVALID) { dlclose(h); return 65; }

        free(pm); free(thm); free(rm); free(f);
    }

    rc = f_finalize();
    if (rc != FP_OK) { fprintf(stderr, "fp_finalize -> %d\n", rc); dlclose(h); return 12; }

    printf("OK: dlopen(%s) + init/set_param/run/get_state/finalize cycle"
           " advanced TIMEFP to %g (nrmax=%d, ntg2=%d)\n",
           path, s.timefp, s.nrmax, s.ntg2);

    dlclose(h);
    return 0;
}
