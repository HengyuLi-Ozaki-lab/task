#ifndef WR_API_H
#define WR_API_H

#include <stddef.h>  /* size_t for wr_state_size (#246) */

#ifdef __cplusplus
extern "C" {
#endif

/*
 * TASK/WR C ABI public header.
 *
 * Phase L-2 status: function symbols are present in libwrapi (built from
 * wr_api.f90); each entry point is a stub returning WR_ERR_NOT_IMPL (=4).
 * Real bodies arrive in Phase L-3 (wr_param_registry) and beyond.
 *
 * See docs/superpowers/plans/2026-04-18-wr-library-L2-c-abi-foundation.md.
 *
 * Upper bounds for the fixed-size state struct:
 *   WR_MAX_NRAYMAX must equal NRAYM in wrcomm.f90 (currently 100).
 *   WR_MAX_NRAY_EQ must equal NEQ+1 in wrcomm.f90 (NEQ=8 ⇒ 9 elements
 *   for RAYS(0:NEQ, ...)). Runtime nraymax/nrsmax/nrlmax are carried in
 *   the state struct and must be <= WR_MAX_*.
 *
 * Memory note: in C, rays_end[NRAYMAX][NRAY_EQ] is row-major; in Fortran
 * the matching declaration is rays_end(NRAY_EQ, NRAYMAX) (column-major).
 * The two layouts agree byte-for-byte.
 */

#define WR_MAX_NRAYMAX 100
#define WR_MAX_NRSMAX  200
#define WR_MAX_NRLMAX  400
#define WR_MAX_NRAY_EQ 9

/*
 * wr_state_t ABI version. Bumped whenever a field is added/removed/reordered
 * in wr_state_t (i.e. whenever sizeof(wr_state_t) changes), together with
 * the WR_STATE_ABI_VERSION PARAMETER in wr_state.f90 that the library
 * exports through wr_state_abi_version(); tests/c_abi/test_negative.c
 * fails when the two drift. In-tree consumers (the C-ABI drivers,
 * python/wrlib/_ffi.py) rebuild from this header and check the library's
 * version and sizeof at load time (#246).
 *
 * History:
 *   1 -> initial layout
 */
#define WR_STATE_ABI_VERSION 1

/* Error codes returned by every wr_* entry point. */
enum wr_error {
    WR_OK              = 0,
    WR_ERR_INVALID     = 1,  /* invalid parameter name or value     */
    WR_ERR_NOT_INIT    = 2,  /* wr_init has not been called yet     */
    WR_ERR_CALC_FAILED = 3,  /* calculation / initialization failed */
    WR_ERR_NOT_IMPL    = 4   /* L-2 stub return: not implemented    */
};

typedef struct {
    int    nraymax, nrsmax, nrlmax;
    double pos_pwrmax_rs, pwrmax_rs, pos_pwrmax_rl, pwrmax_rl;
    int    nstp_end           [WR_MAX_NRAYMAX];
    double pos_pwrmax_rs_nray [WR_MAX_NRAYMAX];
    double pwrmax_rs_nray     [WR_MAX_NRAYMAX];
    double pos_pwrmax_rl_nray [WR_MAX_NRAYMAX];
    double pwrmax_rl_nray     [WR_MAX_NRAYMAX];
    double rays_end           [WR_MAX_NRAYMAX][WR_MAX_NRAY_EQ];
    double pos_nrs            [WR_MAX_NRSMAX];
    double pwr_nrs            [WR_MAX_NRSMAX];
    double pos_nrl            [WR_MAX_NRLMAX];
    double pwr_nrl            [WR_MAX_NRLMAX];
} wr_state_t;

int wr_init(void);
int wr_run(int nray_request);
int wr_set_param(const char* name, double value);
int wr_get_state(wr_state_t* state);
int wr_finalize(void);

/* Layout query (#246): the library's WR_STATE_ABI_VERSION and
   sizeof(wr_state_t), callable before wr_init. Compare both with this
   header's values before passing a struct to wr_get_state; a mismatch
   means the library and this header come from different commits. */
int    wr_state_abi_version(void);
size_t wr_state_size(void);

#ifdef __cplusplus
}
#endif

#endif /* WR_API_H */
