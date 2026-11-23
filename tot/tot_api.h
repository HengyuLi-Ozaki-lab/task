#ifndef TOT_API_H
#define TOT_API_H

#include <stddef.h>  /* size_t for tot_state_size (#246) */

#ifdef __cplusplus
extern "C" {
#endif

/*
 * TASK/TOT C ABI public header.
 *
 * TOT is the orchestrator: its api fans out to per-module APIs
 * (eq_init + tr_init + ti_init + fp_init + wr_init, tr_run,
 * tr_get_state + ..., per-module *_set_param, *_finalize). The eq
 * cascade was added in #209 — direct ctypes callers can drive
 * eq_set_param / eq_run right after tot_init() without an extra
 * eq_init() round trip.
 *
 * Phase 2c PR-A (#208) introduces a single-authoritative routing
 * contract for the Python wrappers: setting the MONO_LIB_PATH env
 * var makes every per-module wrapper (Eqlib / Trlib / ...) and the
 * Tot orchestrator wrapper load libtotapi_mono.so instead of each
 * loading its per-module lib<mod>api.so. This is plumbing only at
 * the C ABI level — no new symbols added to this header.
 *
 * Phase L-2 status: function
 * symbols are present in libtotapi (built from tot_api.f90); each
 * entry point is a stub returning TOT_ERR_NOT_IMPLEMENTED (=4). Real
 * composition arrives in Phase L-3+.
 *
 * Intentionally self-contained at L-2: this header does NOT include
 * tr_api.h / ti_api.h / fp_api.h / wr_api.h. That keeps the L-2 stub
 * usable even before every per-module L-2 has landed. L-3+ will either
 * include those headers and nest their state_t types, or expose the
 * composite view through a separate tot_api_compose.h.
 *
 * See docs/superpowers/specs/2026-04-17-tr-library-design.md  Section 4
 * and docs/superpowers/plans/2026-04-18-tot-library-L2-c-abi-foundation.md.
 *
 * Memory note: in C, RN[NRMAX][NSMAX] is row-major; in Fortran the
 * matching declaration is RN(NSMAX, NRMAX) (column-major). Layouts
 * agree byte-for-byte, but only RN[0..nrmax-1][0..nsmax-1] are valid
 * runtime values (the remainder is padding up to TOT_MAX_*).
 */

#define TOT_MAX_NRMAX 500
#define TOT_MAX_NSMAX 8

/*
 * tot_state_t ABI version. Bumped whenever a field is added/removed/
 * reordered in tot_state_t (i.e. whenever sizeof(tot_state_t) changes).
 * Out-of-tree binary consumers should compare TOT_STATE_ABI_VERSION at
 * compile time against any cached layout assumption and recompile when
 * it bumps. In-tree consumers (python/totlib/_ffi.py and any future
 * tot_api_check_* helpers) all rebuild from this header, so they are
 * kept in sync automatically by the build system.
 * Since #246 the same value is a PARAMETER in tot_state.f90, exported by
 * tot_state_abi_version() together with sizeof via tot_state_size(); bump
 * both places together. tests/c_abi/test_negative.c fails when they
 * drift, and python/totlib/_ffi.py refuses a library whose version or
 * size differs from its struct at load time.
 *
 * History:
 *   1 -> initial layout (Phase L-2)
 *   2 -> appended AJRFT [MA] (L-7b-i); existing field offsets preserved.
 */
#define TOT_STATE_ABI_VERSION 2

/* Error codes returned by every tot_* entry point. */
enum tot_error {
    TOT_OK              = 0,
    TOT_ERR_INVALID     = 1,  /* invalid parameter name or value        */
    TOT_ERR_NOT_INIT    = 2,  /* tot_init has not been called yet       */
    TOT_ERR_CALC_FAILED = 3,  /* per-module init / calculation failed   */
    TOT_ERR_NOT_IMPL    = 4   /* L-2 stub return: not implemented       */
};

typedef struct {
    /* ---- orchestrator presence flags (0 = absent, 1 = initialized) */
    int    tr_present;
    int    ti_present;
    int    fp_present;
    int    wr_present;

    /* ---- integrated scalar slots (aggregated from per-module state) */
    int    nt, nrmax, nsmax;
    double T, WPT, AJT, Q0, BETA0, BETAP0, BETAA, BETAN;
    double TAUE1, TAUE2, ZEFF0, ALI, RQ1;

    /* ---- integrated profile slots (TR-authoritative at L-2 scope)   */
    double RN[TOT_MAX_NRMAX][TOT_MAX_NSMAX];
    double RT[TOT_MAX_NRMAX][TOT_MAX_NSMAX];
    double AJ[TOT_MAX_NRMAX];
    double QP[TOT_MAX_NRMAX];

    /* L-7b-i: total RF + external driven current [MA]. Matches
     * tot_state.f90 end-of-struct placement; ABI v2. */
    double AJRFT;
} tot_state_t;

int tot_init(void);
int tot_run(int ntmax);
/*
 * tot_continue : tr_continue (tr/tr_api.h) through tot: advance the prepared case nsteps more steps without
 * preparing again. The control parameters set since the last tot_run or tot_continue ("tr:" RIPE, PNBTOT, PICTOT,
 * PECTOT, PLHTOT, NTEQIT, TPRST) take effect at its first step; NT, T and the history go on. tot runs only TR, as
 * tot_run does. Every "eq:" name set after a preparation is structural: the eq dispatcher tells TR (as tr_set_param
 * does), so the next tot_run prepares again and tot_continue refuses, naming it. TR refuses every eq: name after the process's first
 * preparation attempt (and eight names always: eq_name_refused, tr/tr_api.f90); that refusal is not applied in tot.
 * Returns 0; 1 (TOT_ERR_INVALID) when tr_continue refuses (nothing ran; the record, kind REFUSED, is TR's
 * tr_last_error, read through trlib in the same image) or nsteps < 0; 2 before tot_init; 3 when the loop fails
 * (the record is tr_last_error's).
 * tot has no parameter-class query: use tr_param_class ("eq:" names are 0) through trlib.
 */
int tot_continue(int nsteps);
/*
 * tot_set_param / tot_set_param_str : namespaced parameter dispatch.
 *
 * Names MUST include a namespace prefix separated by ':' because the
 * tot parameter space is the union of eq / tr / fp / ti / wr / wrx.
 * Examples:
 *   tot_set_param("eq:RR",  6.2);
 *   tot_set_param("tr:DT",  0.01);
 *   tot_set_param("fp:NSMAX", 2);
 *   tot_set_param("wrx:RF", 170.0);
 * A name without ':' is rejected with TOT_ERR_INVALID.
 *
 * tot_set_param_str handles CHARACTER variables (e.g. KNAMEQ). Only
 * the `tr:` namespace is backed by a string setter in L-3; the other
 * namespaces return TOT_ERR_INVALID for string calls until their
 * per-module registries add a symmetric `_str` entry point.
 */
int tot_set_param(const char* name, double value);
int tot_set_param_str(const char* name, const char* value);
int tot_get_state(tot_state_t* state);
int tot_finalize(void);

/* Layout query (#246): the library's TOT_STATE_ABI_VERSION and
   sizeof(tot_state_t), callable before tot_init. Compare both with this
   header's values before passing a struct to tot_get_state; a mismatch
   means the library and this header come from different commits. */
int    tot_state_abi_version(void);
size_t tot_state_size(void);

/*
 * tot_is_mono : introspection — am I the monolithic libtotapi*.so?
 *
 * Returns 1 if this .so was linked from the L-7b-ii monolithic target
 * (eq + tr + fp + ti + wrx + bpsd co-linked, single shared BPSD
 * broker, suitable for BPSD-mediated cross-module coupling). Returns
 * 0 if this is the default per-module image (libtotapi.so depending
 * on individual lib<mod>api.so files, each with private bpsd storage).
 *
 * Both libtotapi.so and libtotapi_mono.so export this symbol; the
 * return value is baked in at link time by the Makefile picking one
 * of tot/tot_mono_flag.f90 (default, returns 0) vs
 * tot/tot_mono_flag_mono.f90 (mono, returns 1). Python wrappers can
 * detect a missing symbol via try/except AttributeError and treat it
 * as 0 for backwards compatibility with older builds predating this
 * function.
 *
 * Use case: Python orchestrators (TotPipeline) decide whether the
 * eq -> tr BPSD coupling rule is safe to activate for the loaded
 * image. See L-7b-ii Phase 2b spec §3-§5.
 */
int tot_is_mono(void);

/*
 * tot_get_scalar : one of TR's named global results by "tr:<NAME>" (PR 2 of #96); the names and units are
 * tr_scalar_name's (tr/tr_api.h). Delegates to tr_get_scalar with the prefix removed.
 * Returns 0, 1 (no "tr:" prefix or unknown name) or 2 (tot_init not called).
 */
int tot_get_scalar(const char* name, double* value);

/*
 * The run's history by name through tot (Task 5b of #96): tr_history_* (tr/tr_api.h) with a "tr:" prefix on every
 * name. tot_history_length / tot_history_full are 0 before tot_init. tot_history_count: the number of columns.
 * tot_history_name: the i-th as "tr:<NAME>" (1, past either end or a buffer too short). tot_history_get: the first
 * min(n, rows) rows of "tr:<NAME>" into buf, *got set; 1 for another prefix, an unknown name or n < 0, 2 before
 * tot_init.
 */
int tot_history_length(void);
int tot_history_full(void);
int tot_history_count(void);
int tot_history_name(int i, char* buf, int buflen);
int tot_history_get(const char* name, double* buf, int n, int* got);

#ifdef __cplusplus
}
#endif

#endif /* TOT_API_H */
