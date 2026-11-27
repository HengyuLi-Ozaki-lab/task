/*
 * test_run_so: dlopen libequapi.so, check its layout against equ_api.h,
 * and run the QUEST example of equ/example through it.
 *
 *   EQULIB_PATH=/path/to/libequapi.so EQU_EXAMPLE_DIR=/path/to/equ/example \
 *       ./test_run_so
 *
 * It works in the current directory: it copies equparm.quest and
 * coildata.quest there (as equparm and coildata, the names the namelist
 * gives), runs mode 1 and writes a G-EQDSK file.
 *
 * Exit codes: 0 OK; 1..12 the step that failed; 90 dlopen; 91 an entry
 * point missing; 92 the layout query missing; 93 the layout differs.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dlfcn.h>
#include "equ_api.h"

#define SYM(name) name##_fn f_##name = (name##_fn) dlsym(h, #name)
typedef int (*equ_init_fn)(void);
typedef int (*equ_read_parm_fn)(const char *);
typedef int (*equ_set_param_fn)(const char *, double);
typedef int (*equ_set_param_str_fn)(const char *, const char *);
typedef int (*equ_validate_fn)(equ_diag_entry_t *, int, int *);
typedef int (*equ_run_fn)(int);
typedef int (*equ_get_state_fn)(equ_state_t *);
typedef int (*equ_get_psi_rz_fn)(int, int, double *);
typedef int (*equ_write_geqdsk_fn)(const char *, int);
typedef int (*equ_last_error_fn)(char *, int);
typedef int (*equ_finalize_fn)(void);
typedef int (*equ_state_abi_version_fn)(void);
typedef size_t (*equ_state_size_fn)(void);

static int copy_file(const char *from, const char *to) {
    FILE *a = fopen(from, "rb"), *b;
    char buf[4096];
    size_t n;
    if (!a) return -1;
    b = fopen(to, "wb");
    if (!b) { fclose(a); return -1; }
    while ((n = fread(buf, 1, sizeof buf, a)) > 0) fwrite(buf, 1, n, b);
    fclose(a);
    fclose(b);
    return 0;
}

int main(void) {
    const char *path = getenv("EQULIB_PATH");
    const char *ex = getenv("EQU_EXAMPLE_DIR");
    char from[2048];
    if (!path || !*path) path = "./libequapi.so";
    if (!ex || !*ex) ex = "example";

    void *h = dlopen(path, RTLD_LAZY);
    if (!h) { fprintf(stderr, "dlopen(%s): %s\n", path, dlerror()); return 90; }

    SYM(equ_init); SYM(equ_read_parm); SYM(equ_set_param); SYM(equ_set_param_str);
    SYM(equ_validate); SYM(equ_run); SYM(equ_get_state); SYM(equ_get_psi_rz);
    SYM(equ_write_geqdsk); SYM(equ_last_error); SYM(equ_finalize);
    if (!f_equ_init || !f_equ_read_parm || !f_equ_set_param || !f_equ_set_param_str ||
        !f_equ_validate || !f_equ_run || !f_equ_get_state || !f_equ_get_psi_rz ||
        !f_equ_write_geqdsk || !f_equ_last_error || !f_equ_finalize) {
        fprintf(stderr, "an equ_* entry point is missing\n");
        return 91;
    }
    SYM(equ_state_abi_version); SYM(equ_state_size);
    if (!f_equ_state_abi_version || !f_equ_state_size) return 92;
    if (f_equ_state_abi_version() != EQU_STATE_ABI_VERSION ||
        f_equ_state_size() != sizeof(equ_state_t)) {
        fprintf(stderr, "layout: library v%d / %lu bytes, header v%d / %lu bytes\n",
                f_equ_state_abi_version(), (unsigned long) f_equ_state_size(),
                EQU_STATE_ABI_VERSION, (unsigned long) sizeof(equ_state_t));
        return 93;
    }

    snprintf(from, sizeof from, "%s/equparm.quest", ex);
    if (copy_file(from, "equparm") != 0) { fprintf(stderr, "no %s\n", from); return 1; }
    snprintf(from, sizeof from, "%s/coildata.quest", ex);
    if (copy_file(from, "coildata") != 0) { fprintf(stderr, "no %s\n", from); return 1; }

    static equ_state_t st;
    static double psi[EQU_MAX_NR * EQU_MAX_NZ];
    equ_diag_entry_t diag[8];
    char msg[300];
    int nd = -1;

    if (f_equ_init() != EQU_OK) return 2;
    if (f_equ_read_parm("equparm") != EQU_OK) return 3;
    if (f_equ_validate(diag, 8, &nd) != EQU_OK || nd != 0) return 4;
    if (f_equ_run(1) != EQU_OK) {
        f_equ_last_error(msg, sizeof msg);
        fprintf(stderr, "equ_run(1): %s\n", msg);
        return 5;
    }
    memset(&st, 0xAA, sizeof st);
    if (f_equ_get_state(&st) != EQU_OK) return 6;
    if (st.nr != 257 || st.nz != 257 || st.nv <= 1 || st.mode != 1 || st.fct_steps <= 0)
        return 7;
    if (f_equ_get_psi_rz(st.nr, st.nz, psi) != EQU_OK) return 8;
    if (psi[0] == 0.0 && psi[st.nr * st.nz - 1] == 0.0) return 9;
    if (f_equ_write_geqdsk("quest.geqdsk", 1) != EQU_OK) {
        f_equ_last_error(msg, sizeof msg);
        fprintf(stderr, "equ_write_geqdsk: %s\n", msg);
        return 10;
    }
    printf("OK: %s: QUEST mode 1: nr=%d nz=%d nv=%d nsu=%d fct_steps=%d "
           "converged=%d ip=%.5f MA q_axis=%.5f\n", path, st.nr, st.nz, st.nv,
           st.nsu, st.fct_steps, st.fct_converged, st.ip, st.q_axis);
    if (f_equ_finalize() != EQU_OK) return 11;
    /* get_state zeroes the struct, then reports the missing init. */
    if (f_equ_get_state(&st) != EQU_ERR_NOT_INIT || st.nr != 0) return 12;
    dlclose(h);
    return 0;
}
