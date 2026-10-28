#ifndef TI_API_H
#define TI_API_H

#include <stddef.h>  /* size_t for ti_state_size (#246) */

#ifdef __cplusplus
extern "C" {
#endif

/*
 * TASK/TI C ABI public header.
 *
 * Phase L-2 status: function symbols are present in libtiapi (built from
 * ti_api.f90); each entry point is a stub returning TI_ERR_NOT_IMPL
 * (=4). Real bodies arrive in Phase L-3.
 *
 * Memory note: in C, RNA[NRMAX][NSA_MAX] is row-major; in Fortran the
 * matching declaration is RNA(NSA_MAX, NRMAX) (column-major). Layouts
 * agree byte-for-byte, but only RNA[0..nrmax-1][0..nsa_max-1] are valid
 * runtime values (the remainder is padding up to TI_MAX_*).
 */

#define TI_MAX_NRMAX   200
#define TI_MAX_NSA_MAX 20

/*
 * ti_state_t ABI version. Bumped whenever a field is added/removed/reordered
 * in ti_state_t (i.e. whenever sizeof(ti_state_t) changes), together with
 * the TI_STATE_ABI_VERSION PARAMETER in ti_state.f90 that the library
 * exports through ti_state_abi_version(); tests/c_abi/test_negative.c
 * fails when the two drift. In-tree consumers (the C-ABI drivers,
 * python/tilib/_ffi.py) rebuild from this header and check the library's
 * version and sizeof at load time (#246).
 *
 * History:
 *   1 -> initial layout
 */
#define TI_STATE_ABI_VERSION 1

/* Error codes returned by every ti_* entry point. */
enum ti_error {
    TI_OK              = 0,
    TI_ERR_INVALID     = 1,  /* invalid parameter name or value     */
    TI_ERR_NOT_INIT    = 2,  /* ti_init has not been called yet     */
    TI_ERR_CALC_FAILED = 3,  /* calculation / initialization failed */
    TI_ERR_NOT_IMPL    = 4   /* L-2 stub return: not implemented    */
};

typedef struct {
    int    nt, nrmax, nsa_max, nsmax;
    double T;
    double residual_loop_max;
    int    icount_loop_max;
    int    icount_mat_max;
    double RNA[TI_MAX_NRMAX][TI_MAX_NSA_MAX];
    double RTA[TI_MAX_NRMAX][TI_MAX_NSA_MAX];
    double RUA[TI_MAX_NRMAX][TI_MAX_NSA_MAX];
    double RBP[TI_MAX_NRMAX];
    double RQP[TI_MAX_NRMAX];
    double RJP[TI_MAX_NRMAX];
    double ZEFF[TI_MAX_NRMAX];
    double BETA[TI_MAX_NRMAX];
    double BETAP[TI_MAX_NRMAX];
} ti_state_t;

int ti_init(void);
int ti_run(int ntmax);
int ti_set_param(const char* name, double value);
int ti_get_state(ti_state_t* state);
int ti_finalize(void);

/* Layout query (#246): the library's TI_STATE_ABI_VERSION and
   sizeof(ti_state_t), callable before ti_init. Compare both with this
   header's values before passing a struct to ti_get_state; a mismatch
   means the library and this header come from different commits. */
int    ti_state_abi_version(void);
size_t ti_state_size(void);

#ifdef __cplusplus
}
#endif

#endif /* TI_API_H */
