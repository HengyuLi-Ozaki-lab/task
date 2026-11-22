#ifndef EQU_API_H
#define EQU_API_H

#include <stddef.h>  /* size_t for equ_state_size */

#ifdef __cplusplus
extern "C" {
#endif

/*
 * TASK/EQU C ABI: the free-boundary equilibrium code equ/ as a library
 * (libequapi.so). Design: docs/superpowers/specs/2026-11-22-equ-library-design.md.
 *
 * Life cycle: equ_init; equ_read_parm and/or equ_set_param[_str];
 * optionally equ_validate; equ_run; equ_get_state, equ_get_psi_rz,
 * equ_write_geqdsk; equ_finalize. One instance per process (EQU keeps its
 * state in Fortran modules).
 *
 * The library reads no standard input and does not end the process on
 * the failures it knows of: they return EQU_ERR_CALC_FAILED and
 * equ_last_error says why. It prints the solver's progress on unit 6.
 *
 * Array parameters are NAME[i] with the index as Fortran declares it:
 * IVAC, NCOIL, CVAC, CVACST, CVACWG, CVACT are 0..18; RVAC, ZVAC 0..30;
 * ICP, CP, IEQOUT 1..10. A bare array name and a subscript on a scalar
 * are refused.
 */

#define EQU_MAX_NR  257   /* irdm   */
#define EQU_MAX_NZ  257   /* izdm   */
#define EQU_MAX_NV  101   /* ivdm   */
#define EQU_MAX_NSU 1542  /* isrzdm */
#define EQU_NCV     19    /* coil groups 0..18 */

/* Layout version of equ_state_t; equals EQU_STATE_ABI_VERSION in
 * equ_state.f90, which equ_state_abi_version() returns.
 * History: 1 -> initial layout. */
#define EQU_STATE_ABI_VERSION 1

enum equ_error {
    EQU_OK              = 0,
    EQU_ERR_INVALID     = 1,  /* invalid name, value, mode or call order */
    EQU_ERR_NOT_INIT    = 2,  /* equ_init has not been called            */
    EQU_ERR_CALC_FAILED = 3,  /* the solve or a file write failed        */
    EQU_ERR_NOT_IMPL    = 4   /* equ_run mode above 1                    */
};

/* Must match equ_state.f90::equ_state_c byte for byte. Valid entries are
 * 1..nr, 1..nz, 1..nv, 1..nsu; the rest is zero. Units are the code's,
 * except pressure (the code holds MPa; here Pa). */
typedef struct equ_state_t {
    int    nr, nz, nv, nsu;
    int    mode;            /* mode of the run (0 or 1); -1 before one   */
    int    fct_steps;       /* steps of the last FCT loop                */
    int    fct_converged;   /* 1 when that loop met EEQMAX               */
    int    xpoint_status;   /* iisep: > 0 an X point was found           */
    double erreq;           /* error of the last FCT loop                */
    double raxis, zaxis, psi_axis;
    double rsep, zsep, psi_sep;
    double ip;              /* computed plasma current [MA] (ttcu)      */
    double ip_target;       /* TCUR [MA]                                 */
    double rbt;             /* BTV, R*B_t [T m]                          */
    double beta_t, beta_s, beta_j, li;
    double q_axis, q_surf, q95, qqj;
    double rmaj, rpla, elip, trig, el95, volume;
    double cvac[EQU_NCV];   /* coil currents of groups 0..18            */
    double rg[EQU_MAX_NR];
    double zg[EQU_MAX_NZ];
    double psi[EQU_MAX_NV];      /* poloidal flux of surface n (1 = axis) */
    double psit[EQU_MAX_NV];     /* toroidal flux (hiv)                   */
    double pressure[EQU_MAX_NV]; /* Pa                                    */
    double q[EQU_MAX_NV];
    double f[EQU_MAX_NV];        /* R*B_t                                 */
    double vol[EQU_MAX_NV];
    double rminor[EQU_MAX_NV];
    double rcentre[EQU_MAX_NV];
    double kappa[EQU_MAX_NV];
    double delta[EQU_MAX_NV];
    double rsu[EQU_MAX_NSU];     /* plasma boundary, open polygon         */
    double zsu[EQU_MAX_NSU];
} equ_state_t;

enum equ_diag_code {
    EQU_DIAG_OUT_OF_RANGE           = 1,
    EQU_DIAG_INCONSISTENT_PAIR      = 2,
    EQU_DIAG_OUT_OF_RANGE_AFTER_DEP = 3,
    EQU_DIAG_FILE_MISSING           = 4,
    EQU_DIAG_MISSING_REQUIRED       = 5
};

#define EQU_DIAG_PARAM_LEN 64
#define EQU_DIAG_MSG_LEN   128

typedef struct {
    char param[EQU_DIAG_PARAM_LEN];
    int  code;
    char msg[EQU_DIAG_MSG_LEN];
} equ_diag_entry_t;

/* Resets every input to EQU's defaults (eqinit) and the solver's state;
 * always EQU_OK. */
int equ_init(void);

/* Reads an &EQU namelist file (as the program reads equparm). Names the
 * file does not give keep their values. EQU_ERR_INVALID: no such file,
 * a read error; equ_last_error has the text. Paths up to 1023 bytes. */
int equ_read_parm(const char *path);

/* Sets one parameter. EQU_ERR_INVALID: unknown or unused name, malformed
 * subscript, index out of range, value not finite, an integer parameter
 * given a fraction or a value beyond the default integer; a name over 63
 * characters. String names (DEVICE, DEVNAM, TITLE, KNAMCOIL) go through
 * equ_set_param_str; a value longer than the variable is refused. A set
 * that succeeds after a run drops that run's result; a refused one, like a
 * failed equ_read_parm, leaves it. */
int equ_set_param(const char *name, double value);
int equ_set_param_str(const char *name, const char *value);

/* Every check of the inputs in one batch; read-only (after a run it looks
 * at the inputs and leaves the run's result). EQU_OK and *ndiag = 0, or
 * EQU_ERR_INVALID with *ndiag entries (counted past cap). */
int equ_validate(equ_diag_entry_t *diags, int cap, int *ndiag);

/* mode 1: the menu's R (setup solve, the TR interface's profiles through
 * bpsd, FCT solve); mode 0: its first step alone. Applies the checks of
 * equ_validate first. A run starts from the inputs as last set: what a
 * previous run overwrote is restored. EQU_ERR_INVALID: a check failed or
 * mode < 0; EQU_ERR_NOT_IMPL: mode > 1; EQU_ERR_CALC_FAILED: the solve
 * failed (equ_last_error). An FCT loop that ends at IEQMAX is not a
 * failure: the state's fct_converged says so. */
int equ_run(int mode);

/* Fills *state (zeroed first). Before a successful run: EQU_OK, nr = 0. */
int equ_get_state(equ_state_t *state);

/* psi(R,Z) of the last run, psi[(iz-1)*nr + (ir-1)] for ir = 1..nr,
 * iz = 1..nz. EQU_ERR_INVALID: no equilibrium, or (nr, nz) differ. */
int equ_get_psi_rz(int nr, int nz, double *psi);

/* Writes the equilibrium of the last run as G-EQDSK, with EQU's own
 * writer (the program's E command). overwrite = 0 refuses an existing
 * file. EQU_ERR_INVALID: no equilibrium, a blank path or one over 80
 * characters; EQU_ERR_CALC_FAILED: the file was not written. */
int equ_write_geqdsk(const char *path, int overwrite);

/* The reason of the last failure, at most buflen-1 characters. */
int equ_last_error(char *buf, int buflen);

int equ_finalize(void);

/* Layout query, callable before equ_init. */
int    equ_state_abi_version(void);
size_t equ_state_size(void);

#ifdef __cplusplus
}
#endif

#endif /* EQU_API_H */
