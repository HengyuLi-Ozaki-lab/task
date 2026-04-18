#ifndef TR_API_H
#define TR_API_H

#ifdef __cplusplus
extern "C" {
#endif

/*
 * TASK/TR C ABI public header.
 *
 * Phase L-2 status: function symbols are present in libtrapi (built from
 * tr_api.f90); each entry point is a stub returning TR_ERR_NOT_IMPLEMENTED
 * (=4). Real bodies arrive in Phase L-3.
 *
 * See docs/superpowers/specs/2026-04-17-tr-library-design.md  Section 4.2.
 *
 * Memory note: in C, RN[NRMAX][NSMAX] is row-major; in Fortran the
 * matching declaration is RN(NSMAX, NRMAX) (column-major). Layouts agree
 * byte-for-byte, but only RN[0..nrmax-1][0..nsmax-1] are valid runtime
 * values (the remainder is padding up to TR_MAX_*).
 */

#define TR_MAX_NRMAX 500
#define TR_MAX_NSMAX 8

/* Error codes returned by every tr_* entry point. */
enum tr_error {
    TR_OK              = 0,
    TR_ERR_INVALID     = 1,  /* invalid parameter name or value     */
    TR_ERR_NOT_INIT    = 2,  /* tr_init has not been called yet     */
    TR_ERR_CALC_FAILED = 3,  /* calculation / initialization failed */
    TR_ERR_NOT_IMPL    = 4   /* L-2 stub return: not implemented    */
};

typedef struct {
    int    nt, nrmax, nsmax;
    double T, WPT, AJT, Q0, BETA0, BETAP0, BETAA, BETAN;
    double TAUE1, TAUE2, ZEFF0, ALI, RQ1;
    double RN[TR_MAX_NRMAX][TR_MAX_NSMAX];
    double RT[TR_MAX_NRMAX][TR_MAX_NSMAX];
    double AJ[TR_MAX_NRMAX];
    double QP[TR_MAX_NRMAX];
} tr_state_t;

int tr_init(void);
int tr_run(int ntmax);
int tr_set_param(const char* name, double value);
int tr_set_param_str(const char* name, const char* value);
int tr_get_state(tr_state_t* state);
int tr_finalize(void);

#ifdef __cplusplus
}
#endif

#endif /* TR_API_H */
