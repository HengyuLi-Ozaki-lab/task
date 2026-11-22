#ifndef TR_API_H
#define TR_API_H

#include <stddef.h>  /* size_t for tr_state_size (#246) */

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

/*
 * tr_state_t ABI version. Bumped whenever a field is added/removed/reordered
 * in tr_state_t (i.e. whenever sizeof(tr_state_t) changes). Out-of-tree
 * binary consumers should compare TR_STATE_ABI_VERSION at compile time
 * against any cached layout assumption and recompile when it bumps. In-tree
 * consumers (tot_api_check_*, python/trlib/_ffi.py) all rebuild from this
 * header, so they are kept in sync automatically by the build system.
 * Since #246 the same value is a PARAMETER in tr_state.f90, exported by
 * tr_state_abi_version() together with sizeof via tr_state_size(); bump
 * both places together. tests/c_abi/test_negative.c fails when they
 * drift, and python/trlib/_ffi.py refuses a library whose version or
 * size differs from its struct at load time.
 *
 * History:
 *   1 -> initial layout (Phase L-2)
 *   2 -> appended AJRFT [MA] (L-7b-i); existing field offsets preserved.
 */
#define TR_STATE_ABI_VERSION 2

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
    /* L-7b-i: total RF + external driven current [MA]. Mirrors AJRFT in
       tr_state_c; placed at struct end to preserve existing field offsets. */
    double AJRFT;
} tr_state_t;

/*
 * Issue #143 pre-run parameter validation API.
 *
 * Read-only cross-parameter consistency check. Call after tr_init and
 * any tr_set_param / tr_set_param_str, before tr_run. Must NOT modify
 * any tr state.
 */
enum tr_diag_code {
    TR_DIAG_OUT_OF_RANGE           = 1,
    TR_DIAG_INCONSISTENT_PAIR      = 2,
    TR_DIAG_OUT_OF_RANGE_AFTER_DEP = 3,
    TR_DIAG_FILE_MISSING           = 4,
    TR_DIAG_MISSING_REQUIRED       = 5
};

#define TR_DIAG_PARAM_LEN 64
#define TR_DIAG_MSG_LEN   128

/*
 * One diagnostic entry. Matches tr_state.f90::tr_diag_entry_c byte-for-byte.
 * param / msg are C_NULL_CHAR-padded on write (Fortran zero-fills then
 * overwrites with TRIM of the source + appends C_NULL_CHAR).
 */
typedef struct tr_diag_entry {
    char param[TR_DIAG_PARAM_LEN];
    int  code;
    char msg[TR_DIAG_MSG_LEN];
} tr_diag_entry_t;

int tr_init(void);
int tr_run(int ntmax);
/* tr_set_param and tr_set_param_str return TR_ERR_INVALID for a name of
 * more than 64 characters, and tr_set_param_str for a value of more than
 * 80 (KNAMEQ is CHARACTER(LEN=80)): neither is cut. Trailing blanks are
 * not counted, as long as the string ends within 4096 characters of the
 * buffer's end.
 *
 * Names that start with "eq:" belong to EQ's registry (eq:RB, eq:NSGMAX,
 * eq:NRMAX, ...; MODELG 9 sets EQ's wall and grid through them). An accepted
 * set makes the next tr_run prepare again. An unknown name returns
 * TR_ERR_INVALID. These are refused too (TR_ERR_INVALID, one line on unit 6):
 *  - eq:RR, eq:RA, eq:RKAP, eq:RDLT, eq:BB, eq:RIP and eq:KNAMEQ, which do
 *    nothing through TR (MODELG 9 overwrites EQ's copies from TR's device, and
 *    TR passes its own KNAMEQ to EQ): set TR's own RR, RA, ... instead (for
 *    eq:RIP, RIPS and RIPE);
 *  - every eq: name once the process has made its first preparation attempt
 *    (failed or not; across tr_finalize and tr_init): until the pinned bpsd has
 *    k-yoshimi/bpsd#7 an EQ grid change in one process corrupts memory, so eq:
 *    names are set before the process's first preparation attempt (a tr_run
 *    refused by its own checks before tr_prep does not count). This comes off
 *    with the one-NRMAX-per-process guard of tr_run.
 * That guard closes only the direct route. Under MODELG 9 any input that
 * moves EQ's plasma grid (NRPMAX: TR's RA, RR and other device inputs, MODELG,
 * the eq: names, the drift between NTEQIT re-solves) needs a bpsd with
 * k-yoshimi/bpsd#7. TOT's eq: dispatcher calls eq_param_set directly: the guard
 * does not apply in totlib or the mono build.
 * Under MODELG 3, 5 and 8 EQ's NRMAX is TR's NRMAX + 1, NTHMAX is 64 and
 * NSUMAX is 0 (tr_set_metric). */
int tr_set_param(const char* name, double value);
int tr_set_param_str(const char* name, const char* value);
int tr_get_state(tr_state_t* state);
int tr_finalize(void);

/* Layout query (#246): the library's TR_STATE_ABI_VERSION and
   sizeof(tr_state_t), callable before tr_init. Compare both with this
   header's values before passing a struct to tr_get_state; a mismatch
   means the library and this header come from different commits. */
int    tr_state_abi_version(void);
size_t tr_state_size(void);

/*
 * Return codes:
 *   TR_OK           (0): *ndiag_out == 0; state validates cleanly
 *   TR_ERR_INVALID  (1): *ndiag_out >= 1; diagnostics are the payload
 *   TR_ERR_NOT_INIT (2): library not initialized
 * Caller workflow: validate -> fix any reported issues -> validate again
 * -> tr_run. The function does NOT mutate tr state.
 */
int tr_validate(tr_diag_entry_t* diag, int diag_cap, int* ndiag_out);

/* The first failure of the last tr_run, in the layout of a diagnostic entry.
   param: NONE, EQ_FAILED, NONFINITE, TR_CHECK, PREP_FAILED or OTHER (REFUSED is
   reserved for tr_continue, PR 3; nothing records it yet);
   code: the Fortran status; msg: "nt=<step> t=<time> s: <what failed>", cut at
   127 characters; for EQ_FAILED the text ends with EQ's own reason (EQ_ERRMSG)
   when EQ set one.
   Cleared at the start of every tr_run. Returns 0 always. */
int tr_last_error(tr_diag_entry_t* e);

/* L-7b-ii: BPSD broker round-trip verification.
 * Returns *ok = 1 on successful pull of the 3 eq-pushed BPSD slots
 * (device, equ1D, metric1D); 0 otherwise. plasmaf is intentionally
 * excluded -- it is tr's own BPSD output, absent on a fresh eq->tr
 * pipeline. Non-mutating: pulls into local discardable types; does
 * not change tr_state_t contents. */
void tr_check_bpsd_pull(int *ok);

/* Outputs by name (PR 2 of #96). The scalars are TR's global results as TRGLOB last computed them (output steps
   and the last step of a run), in the units of tr/trrslt_globals.f90; the names are listed by tr_scalar_name.
   tr_scalar_count: the number of names (31).
   tr_scalar_name: the i-th name (1-based) as a NUL-terminated string in buf of buflen characters;
     TR_ERR_INVALID past either end or when the name and its NUL do not fit.
   tr_get_scalar: the value of one name (exact, upper case); TR_ERR_NOT_INIT before tr_init, TR_ERR_INVALID for a
     name not listed (*value is left as it was). After tr_init and before the first tr_run the values are those of
     the previous lifecycle in this process (as tr_get_state's scalars are), 0 in a fresh process: read them after
     a run of one step or more. A tr_run of 0 steps evaluates no step: after a preparation (a first run, or a run
     after a changed parameter) T is 0 and the others are still the previous run's.
   PNFT is the power of the charged fusion products (alpha for D-T, MDLNF 1 to 4; alpha and proton for D-He3, MDLNF
     5 and 6) and QF = 5 PNFT / (POHT + PNBT + PRFST + PEXST) is the D-T gain whatever the reaction. RIP is the
     equilibrium's boundary current under MODELG 3, 5 and 8, the current set (RIPS to RIPE) otherwise. */
int tr_scalar_count(void);
int tr_scalar_name(int i, char* buf, int buflen);
int tr_get_scalar(const char* name, double* value);

/* The run's history by name (PR 2 of #96, Task 5b). TR records a row every NGTSTP steps (default 2) in single
   precision: the state at t = 0 first, then a row at every step that is a multiple of NGTSTP, so a call of tr_run adds the multiples among the steps it runs (nsteps / NGTSTP only when it starts on one: run(5) twice adds 3 and 3, run(1) adds 0 or 1).
   tr_prep starts the history again (tr_run prepares again after a changed parameter). NTM = 10001 rows; when they
   are full recording stops silently in TR, and tr_history_full reports it.
   tr_history_length: rows recorded (0 before a run). tr_history_full: 1 when the rows are full, else 0.
   tr_history_count / tr_history_name: the named columns, enumerated as tr_scalar_name does. "T" is the time;
     the others are TR's names in tr/trrslt_globals.f90's TRATOT, in its units (see tr_mcp's get_history schema).
   tr_history_get: copies the first min(n, rows) rows of the column `name` into buf and sets *got to that number.
     TR_ERR_NOT_INIT before tr_init; TR_ERR_INVALID for an unknown name or n < 0.
   A run that fails on a negative temperature (TR_CHECK in tr_last_error) ends its history on the last recorded
   step: the failed iterate is not a row (tr2 records it). Under MODELG 9 a step that ends with an EQ re-solve (a
   multiple of NTEQIT) is recorded before the re-solve, which then recomputes Q0: that row's Q0 differs from
   tr_get_scalar's; the other shared names agree. */
int tr_history_length(void);
int tr_history_full(void);
int tr_history_count(void);
int tr_history_name(int i, char* buf, int buflen);
int tr_history_get(const char* name, double* buf, int n, int* got);

#ifdef __cplusplus
}
#endif

#endif /* TR_API_H */
