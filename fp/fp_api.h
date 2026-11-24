#ifndef FP_API_H
#define FP_API_H

#include <stddef.h>  /* size_t for fp_state_size (#246) */

#ifdef __cplusplus
extern "C" {
#endif

/*
 * TASK/FP C ABI public header.
 *
 * Phase L-3 status: function symbols are present in libfpapi (built from
 * fp_api.f90) and wired to the real FPCOMM state:
 *   fp_init       -> mtx_initialize + pl_init + eq_init + ob_init +
 *                    fp_init (Fortran). Returns FP_OK.
 *   fp_set_param  -> dispatches through fp_param_registry to the
 *                    matching FPCOMM variable. ~40 namelist names
 *                    supported (see fp_param_registry.f90 for the
 *                    SELECT CASE list); unknown names return
 *                    FP_ERR_INVALID.
 *   fp_run        -> fp_prep on first call + fp_loop with NTMAX set to
 *                    the requested step count.
 *   fp_get_state  -> populates scalars + profile arrays (RNT/RWT/RTT/
 *                    RJT/RPCT/RPWT) + the volume-integrated global
 *                    scalars (TOTAL_IP ... PLASMA_VOLUME) from FPCOMM.
 *   fp_finalize   -> clears lifecycle flags. Note: FPCOMM arrays are
 *                    NOT deallocated (fp_allocate / fp_deallocate
 *                    asymmetry) so a single fp_init/fp_run/fp_finalize
 *                    per process is the supported lifecycle at L-3.
 *
 * See docs/superpowers/plans/2026-04-18-fp-library-L3-param-registry.md.
 *
 * Memory note: in C, RNT[NSAMAX][NRMAX] is row-major; in Fortran the
 * matching declaration is RNT(NRMAX, NSAMAX) (column-major). Layouts agree
 * byte-for-byte, but only RNT[0..nsamax-1][0..nrmax-1] are valid runtime
 * values (the remainder is padding up to FP_MAX_*).
 *
 * ABI note: fp_state_t only ever grows at the END of the struct, so the
 * offsets of pre-existing members are stable. Every change must be
 * mirrored in fp/fp_state.f90 and python/fplib/_ffi.py::FpStateC, and
 * libfpapi.so rebuilt (`make -C fp libfpapi.so`).
 */

#define FP_MAX_NRMAX  100
#define FP_MAX_NSAMAX 8

/*
 * fp_state_t ABI version. Bumped whenever a field is added/removed/reordered
 * in fp_state_t (i.e. whenever sizeof(fp_state_t) changes), together with
 * the FP_STATE_ABI_VERSION PARAMETER in fp_state.f90 that the library
 * exports through fp_state_abi_version(); tests/c_abi/test_negative.c
 * fails when the two drift. In-tree consumers (the C-ABI drivers,
 * python/fplib/_ffi.py) rebuild from this header and check the library's
 * version and sizeof at load time (#246).
 *
 * History:
 *   1 -> initial layout
 *   2 -> appended the seven global scalars TOTAL_IP .. PLASMA_VOLUME
 *        (56 bytes); existing field offsets preserved.
 */
#define FP_STATE_ABI_VERSION 2

/* Error codes returned by every fp_* entry point. */
enum fp_error {
    FP_OK              = 0,
    FP_ERR_INVALID     = 1,  /* invalid parameter name or value     */
    FP_ERR_NOT_INIT    = 2,  /* fp_init has not been called yet     */
    FP_ERR_CALC_FAILED = 3,  /* calculation / initialization failed */
    FP_ERR_NOT_IMPL    = 4   /* reserved (was L-2 stub return)      */
};

typedef struct {
    int    nrmax;
    int    nsamax;
    int    npmax;
    int    nthmax;
    int    ntg2;
    double timefp;
    double RNT [FP_MAX_NSAMAX][FP_MAX_NRMAX];
    double RWT [FP_MAX_NSAMAX][FP_MAX_NRMAX];
    double RTT [FP_MAX_NSAMAX][FP_MAX_NRMAX];
    double RJT [FP_MAX_NSAMAX][FP_MAX_NRMAX];
    double RPCT[FP_MAX_NSAMAX][FP_MAX_NRMAX];
    double RPWT[FP_MAX_NSAMAX][FP_MAX_NRMAX];
    /* Global (volume-integrated) plasma scalars, species-summed at the
     * latest NTG1 sample. These are the quantities FP otherwise only
     * WRITEs to unit 6: the rtotal* line block (fp/fpsave.f90:305-311),
     * the W column of the per-species line (fp/fpsave.f90:252) and the
     * TVOLR banner (fp/fpprep.f90:237). Zero until the first run, and
     * again after any successful set (fp_set_param, fp_set_param_str, or
     * tot's fp: parameters; #253) until the next run that is made. */
    double TOTAL_IP;          /* total plasma current  [MA]  */
    double STORED_ENERGY;     /* stored energy         [MJ]  */
    double COLLISION_POWER;   /* total collision power [MW]  */
    double ABSORPTION_POWER;  /* total absorbed power  [MW]  */
    double ABSORPTION_WR;     /* WR (ray-tracing) part [MW]  */
    double ABSORPTION_WM;     /* WM (full-wave) part   [MW]  */
    double PLASMA_VOLUME;     /* TVOLR                 [m^3] */
} fp_state_t;

int fp_init(void);
int fp_run(int ntmax);
int fp_set_param(const char* name, double value);
int fp_set_param_str(const char* name, const char* value);
int fp_get_state(fp_state_t* state);
int fp_finalize(void);

/* Layout query (#246): the library's FP_STATE_ABI_VERSION and
   sizeof(fp_state_t), callable before fp_init. Compare both with this
   header's values before passing a struct to fp_get_state; a mismatch
   means the library and this header come from different commits. */
int    fp_state_abi_version(void);
size_t fp_state_size(void);

/*
 * The distribution function FNS(NTHMAX,NPMAX,NRMAX,NSAMAX), its grid and
 * its normalisation (task-web-client #232).
 *
 * fp_fns_info_t has a layout version of its own, kept as for fp_state_t
 * (#246): fields are appended at the end only, FP_FNS_INFO_ABI_VERSION
 * goes up with the PARAMETER of that name in fp_state.f90, and
 * fp_fns_info_abi_version() / fp_fns_info_size(), callable before
 * fp_init, let a caller compare both.
 *
 * The three getters answer only while the run is prepared and no
 * successful set (fp_set_param, fp_set_param_str, tot's "fp:") has been
 * made since; otherwise, as before the first fp_run, FP_ERR_CALC_FAILED.
 * FP_ERR_NOT_INIT before fp_init. FP_ERR_INVALID for nsa outside
 * 1..NSAMAX, a NULL pointer, or a length other than the mesh's.
 * The checks are made in this order: FP_ERR_NOT_INIT, then FP_ERR_CALC_FAILED,
 * then FP_ERR_INVALID, so a NULL pointer before the first run returns
 * FP_ERR_CALC_FAILED.
 *
 * fp_get_fns copies FNS(1:nthmax, 1:npmax, 1:nrmax, nsa) in Fortran
 * order, so as a C array it is f[nr][np][nth]. The values are FP's own,
 * unscaled: n = rnfp0 * sum(VOLP * f) [1e20 m^-3] for MODELA = 0, with
 * VOLP = 2 pi sin(thm) pm^2 delp delth. pm, theta0, pmax and delp are
 * indexed by the namelist species ns; ptfp0, vtfp0, amfp, aefp, rnfp0, rtfp0 and
 * FNS by the kinetic one.
 */
#define FP_FNS_INFO_ABI_VERSION 1

typedef struct {
    int    nsa, ns;                /* kinetic species (1-origin) and its namelist species */
    int    nthmax, npmax, nrmax;
    int    modela;                 /* 1: bounce-averaged, theta is the value at B-min */
    double timefp;                 /* s */
    double amfp, aefp;             /* kg, C */
    double rnfp0, rtfp0;           /* 1e20 m^-3, keV */
    double ptfp0, vtfp0;           /* kg m/s, m/s */
    double theta0;                 /* T/(m c^2) as FP uses it; 0 when MODELR = 0 */
    double pmax, delp, delth;      /* normalised momentum range and steps; rad */
} fp_fns_info_t;

int    fp_fns_info_abi_version(void);
size_t fp_fns_info_size(void);
int    fp_get_fns_info(int nsa, fp_fns_info_t* info);
int    fp_get_fns_grid(int nsa, double* pm, int npm, double* thm, int nthm,
                       double* rm, int nrm);
int    fp_get_fns(int nsa, double* buf, int nbuf);

#ifdef __cplusplus
}
#endif

#endif /* FP_API_H */
