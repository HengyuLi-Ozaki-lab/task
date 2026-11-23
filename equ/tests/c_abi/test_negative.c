/*
 * test_negative: the refusals of the EQU C ABI, through dlopen.
 *
 *   EQULIB_PATH=/path/to/libequapi.so ./test_negative
 *
 * Exit 0 when every case behaves; otherwise the number of the first
 * failing case. Needs no input file: the one run it starts is refused by
 * the checks (the default coil file name 'init' names no file).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dlfcn.h>
#include "equ_api.h"

static void *h;
static void *sym(const char *n) {
    void *p = dlsym(h, n);
    if (!p) { fprintf(stderr, "missing %s\n", n); exit(91); }
    return p;
}
#define CHECK(n, cond) do { if (!(cond)) { \
    fprintf(stderr, "case %d failed: %s\n", n, #cond); return n; } } while (0)

int main(void) {
    const char *path = getenv("EQULIB_PATH");
    if (!path || !*path) path = "./libequapi.so";
    h = dlopen(path, RTLD_LAZY);
    if (!h) { fprintf(stderr, "dlopen(%s): %s\n", path, dlerror()); return 90; }

    int (*init)(void) = (int (*)(void)) sym("equ_init");
    int (*read_parm)(const char *) = (int (*)(const char *)) sym("equ_read_parm");
    int (*set)(const char *, double) = (int (*)(const char *, double)) sym("equ_set_param");
    int (*set_str)(const char *, const char *) =
        (int (*)(const char *, const char *)) sym("equ_set_param_str");
    int (*validate)(equ_diag_entry_t *, int, int *) =
        (int (*)(equ_diag_entry_t *, int, int *)) sym("equ_validate");
    int (*run)(int) = (int (*)(int)) sym("equ_run");
    int (*get_state)(equ_state_t *) = (int (*)(equ_state_t *)) sym("equ_get_state");
    int (*get_psi)(int, int, double *) = (int (*)(int, int, double *)) sym("equ_get_psi_rz");
    int (*write_g)(const char *, int) = (int (*)(const char *, int)) sym("equ_write_geqdsk");
    int (*last_error)(char *, int) = (int (*)(char *, int)) sym("equ_last_error");
    int (*finalize)(void) = (int (*)(void)) sym("equ_finalize");
    int (*abi)(void) = (int (*)(void)) sym("equ_state_abi_version");
    size_t (*size)(void) = (size_t (*)(void)) sym("equ_state_size");

    static equ_state_t st;
    equ_diag_entry_t diag[64];
    double psi[4];
    char msg[300], longname[80];
    int nd;

    /* 1-9: every call before equ_init returns EQU_ERR_NOT_INIT. */
    CHECK(1, read_parm("x") == EQU_ERR_NOT_INIT);
    CHECK(2, set("NR", 129) == EQU_ERR_NOT_INIT);
    CHECK(3, set_str("KNAMCOIL", "x") == EQU_ERR_NOT_INIT);
    CHECK(4, validate(diag, 64, &nd) == EQU_ERR_NOT_INIT);
    CHECK(5, run(1) == EQU_ERR_NOT_INIT);
    CHECK(6, get_state(&st) == EQU_ERR_NOT_INIT);
    CHECK(7, get_psi(257, 257, psi) == EQU_ERR_NOT_INIT);
    CHECK(8, write_g("x", 1) == EQU_ERR_NOT_INIT);
    CHECK(9, last_error(msg, 300) == EQU_ERR_NOT_INIT);
    /* 10: the layout query works before init. */
    CHECK(10, abi() == EQU_STATE_ABI_VERSION && size() == sizeof(equ_state_t));

    CHECK(11, init() == EQU_OK);
    /* 12-20: names and values the registry refuses. */
    CHECK(12, set("NO_SUCH_NAME", 1) == EQU_ERR_INVALID);
    CHECK(13, set("IVAC", 1) == EQU_ERR_INVALID);          /* bare array      */
    CHECK(14, set("IVAC[19]", 1) == EQU_ERR_INVALID);      /* above 0..18     */
    CHECK(15, set("CP[0]", 1) == EQU_ERR_INVALID);         /* below 1..10     */
    CHECK(16, set("NR[1]", 129) == EQU_ERR_INVALID);       /* subscript on a scalar */
    CHECK(17, set("NR", 129.5) == EQU_ERR_INVALID);        /* fraction on an integer */
    CHECK(18, set("BTV", 1.0 / 0.0) == EQU_ERR_INVALID);   /* not finite      */
    CHECK(19, set("IVTAB", 1) == EQU_ERR_INVALID);         /* unused by EQU   */
    memset(longname, 'A', 70); longname[70] = '\0';
    CHECK(20, set(longname, 1) == EQU_ERR_INVALID);        /* over 63 characters */
    CHECK(21, set_str("TITLE", "fits") == EQU_OK);
    CHECK(22, set_str("DEVICE", "LONGER_THAN_8") == EQU_ERR_INVALID);
    CHECK(23, set_str("NR", "1") == EQU_ERR_INVALID);
    CHECK(24, set("IVAC[0]", 0) == EQU_OK && set("CP[10]", 0.05) == EQU_OK);
    /* 25: an error text after a refusal. */
    CHECK(25, set("NO_SUCH_NAME", 1) == EQU_ERR_INVALID &&
              last_error(msg, 300) == EQU_OK && strstr(msg, "NO_SUCH_NAME") != NULL);

    /* 26-29: run modes and the checks before a run. */
    CHECK(26, run(-1) == EQU_ERR_INVALID);
    CHECK(27, run(2) == EQU_ERR_NOT_IMPL);
    CHECK(28, validate(diag, 64, &nd) == EQU_ERR_INVALID && nd >= 1);
    CHECK(29, set_str("KNAMCOIL", "no-such-coil-file") == EQU_OK && run(1) == EQU_ERR_INVALID &&
              last_error(msg, 300) == EQU_OK && strstr(msg, "KNAMCOIL") != NULL);
    /* 30-32: nothing to read before a successful run. */
    CHECK(30, get_state(&st) == EQU_OK && st.nr == 0 && st.mode == -1);
    CHECK(31, get_psi(257, 257, psi) == EQU_ERR_INVALID);
    CHECK(32, write_g("never.geqdsk", 1) == EQU_ERR_INVALID);
    /* 33: read_parm of a file that is not there. */
    CHECK(33, read_parm("no-such-equparm") == EQU_ERR_INVALID);
    /* 34-35: finalize twice, then the library is uninitialised again. */
    CHECK(34, finalize() == EQU_OK && finalize() == EQU_OK);
    CHECK(35, run(1) == EQU_ERR_NOT_INIT);
    /* 36: init again after finalize. */
    CHECK(36, init() == EQU_OK && set("NR", 129) == EQU_OK);

    printf("OK: %s: 36 refusal cases\n", path);
    dlclose(h);
    return 0;
}
