#ifndef WR_API_H
#define WR_API_H

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

#ifdef __cplusplus
}
#endif

#endif /* WR_API_H */
