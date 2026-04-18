#ifndef EQ_API_H
#define EQ_API_H

#ifdef __cplusplus
extern "C" {
#endif

/*
 * TASK/EQ C ABI public header.
 *
 * Phase L-2 status: function symbols are present in libeqapi (built from
 * eq_api.f90). eq_init / eq_finalize / eq_get_state return EQ_OK; eq_run
 * and eq_set_param return EQ_ERR_NOT_IMPL (=4) pending the L-3 registry
 * + calc dispatch work. The struct layout and enum are final, so
 * downstream consumers can compile against this header today.
 *
 * Memory note: every array in eq_state_t is fixed-size (max-capacity).
 * Valid runtime slots are 1..nrmax / 1..npsmax / 1..nrgmax / etc.;
 * the remainder is zero-padded by eq_get_state before return.
 */

#define EQ_MAX_NRGM 513
#define EQ_MAX_NZGM 513
#define EQ_MAX_NPSM 513
#define EQ_MAX_NRM  1001
#define EQ_MAX_NTHM 2049
#define EQ_MAX_NSUM 1343

/* Error codes returned by every eq_* entry point. */
enum eq_error {
    EQ_OK              = 0,
    EQ_ERR_INVALID     = 1,  /* invalid parameter name or value     */
    EQ_ERR_NOT_INIT    = 2,  /* eq_init has not been called yet     */
    EQ_ERR_CALC_FAILED = 3,  /* calculation / initialization failed */
    EQ_ERR_NOT_IMPL    = 4   /* L-2 stub return: not implemented    */
};

typedef struct eq_state_t {
    /* grid counters */
    int    nrgmax;
    int    nzgmax;
    int    npsmax;
    int    nrmax;
    int    nthmax;
    int    nsumax;
    /* plasma scalars */
    double raxis;
    double zaxis;
    double psi0;
    double psipa;
    double psita;
    double qaxis;
    double qsurf;
    double betat;
    double betap;
    double pvol;
    double raave;
    double ripx;
    /* 1D profiles (sampled at 1..npsmax) */
    double psips[EQ_MAX_NPSM];
    double ppps[EQ_MAX_NPSM];
    double ttps[EQ_MAX_NPSM];
    double qqps[EQ_MAX_NPSM];
    /* R / Z grid coordinates */
    double rg[EQ_MAX_NRGM];
    double zg[EQ_MAX_NZGM];
} eq_state_t;

int eq_init(void);
int eq_run(int mode);
int eq_set_param(const char* name, double value);
int eq_get_state(eq_state_t* state);
int eq_finalize(void);

#ifdef __cplusplus
}
#endif

#endif /* EQ_API_H */
