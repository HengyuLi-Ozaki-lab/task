! tot_param_registry.f90
!
! Phase L-3: namespaced dispatcher for the tot orchestrator C ABI.
!
! tot is an integrator: its param set is the UNION of the six backing
! libraries (eq, tr, fp, ti, wrx, ...). To disambiguate same-named
! parameters across those libraries (e.g. `RR` exists in almost all of
! them, `DT` exists in both tr and ti), callers MUST supply a namespace
! prefix `<ns>:<name>`. The prefix is stripped and the bare name is
! handed off to the corresponding per-module registry.
!
! Supported namespaces (L-3):
!   eq:<name>   -> eq_param_set   (subroutine, separate OUT ierr)
!   tr:<name>   -> tr_param_set   (function, returns ierr)
!   fp:<name>   -> fp_param_set   (function, returns ierr)
!   ti:<name>   -> ti_param_set   (function, returns ierr)
!   wrx:<name>  -> wrx_param_set  (function, returns ierr)
!   wr:<name>   -> wrx_param_set  (alias: tot links wrx/libwr.a, not wr/)
!
! The `wr:` alias reflects the tot link graph: tot pulls in
! `../wrx/libwr.a` (note the directory is `wrx/` but the archive is
! still named `libwr.a`). Using `wr_param_registry` from the `wr/` tree
! directly would pull in a second copy of MODULE wrcomm and clash at
! link time, so `wr:` is routed to `wrx_param_set` instead. A caller
! that needs the non-wrx `wr_param_registry` must drive the `wr` binary
! directly through `libwrapi.so`, not through tot.
!
! String setter (tot_param_set_str):
!   `tr:` and `eq:` are supported: both tr_param_registry and
!   eq_param_registry export a `*_param_set_str` entry point (KNAMEQ,
!   KNAMWR, KNAMWM, ... on eq; KNAMEQ on tr). Other namespaces return
!   ierr=1 on string entries until their registries add a symmetric
!   `_str` entry point.
!
! Return codes (match tot_api.h):
!   0 = success
!   1 = invalid: missing prefix, unknown prefix, unknown bare name, or
!       underlying registry returned a non-zero code
!
! See docs/superpowers/plans/2026-04-18-tot-library-L3-param-registry.md.

MODULE tot_param_registry
  USE, INTRINSIC :: ISO_C_BINDING, ONLY: C_DOUBLE
  IMPLICIT NONE
  PRIVATE
  PUBLIC :: tot_param_set, tot_param_set_str, tot_param_split

CONTAINS

  !-------------------------------------------------------------------
  ! tot_param_set : numeric parameter dispatch.
  !
  ! name  - "<ns>:<bare>" where <ns> in {eq, tr, fp, ti, wr, wrx}.
  ! value - scalar double to be assigned.
  ! ierr  - 0 on success, 1 on any error (bad prefix / unknown name /
  !         downstream failure). Downstream non-zero codes are
  !         collapsed to 1 here; the per-module ABI test suites cover
  !         the finer-grained error channels.
  !-------------------------------------------------------------------
  SUBROUTINE tot_param_set(name, value, ierr)
    CHARACTER(LEN=*), INTENT(IN)  :: name
    REAL(C_DOUBLE),   INTENT(IN)  :: value
    INTEGER,          INTENT(OUT) :: ierr

    CHARACTER(LEN=16) :: prefix
    CHARACTER(LEN=LEN(name)) :: bare
    LOGICAL :: ok

    CALL tot_param_split(name, prefix, bare, ok)
    IF (.NOT. ok) THEN
       ! No prefix, empty prefix, or prefix with no body -> reject.
       ierr = 1
       RETURN
    END IF

    SELECT CASE (TRIM(prefix))
    CASE ("eq")
       CALL dispatch_eq(TRIM(bare), value, ierr)
    CASE ("tr")
       ierr = dispatch_tr(TRIM(bare), value)
    CASE ("fp")
       ierr = dispatch_fp(TRIM(bare), value)
    CASE ("ti")
       ierr = dispatch_ti(TRIM(bare), value)
    CASE ("wrx")
       ierr = dispatch_wrx(TRIM(bare), value)
    CASE ("wr")
       ! Alias to wrx: tot links wrx/libwr.a, not wr/libwr.a, so the
       ! only loadable `wr_param_set` symbol in this build is wrx's.
       ierr = dispatch_wrx(TRIM(bare), value)
    CASE DEFAULT
       ierr = 1
    END SELECT
  END SUBROUTINE tot_param_set

  !-------------------------------------------------------------------
  ! tot_param_split : the namespace and the bare name of "<ns>:<bare>", as both dispatchers read them (and tot_api's eq:
  ! guard, so that the guard and the dispatch agree on which names reach EQ). ok is false for no ':', an empty prefix
  ! or nothing after the ':'. The prefix is held in 16 characters, as it always was: a longer one is cut there.
  !-------------------------------------------------------------------
  SUBROUTINE tot_param_split(name, prefix, bare, ok)
    CHARACTER(LEN=*), INTENT(IN)  :: name
    CHARACTER(LEN=16), INTENT(OUT) :: prefix
    CHARACTER(LEN=*), INTENT(OUT) :: bare
    LOGICAL,          INTENT(OUT) :: ok
    INTEGER :: sep
    prefix = ' '
    bare = ' '
    sep = INDEX(name, ':')
    ok = .NOT. (sep < 2 .OR. sep >= LEN_TRIM(name))
    IF (.NOT. ok) RETURN
    prefix = name(1:sep-1)
    bare   = name(sep+1:)
  END SUBROUTINE tot_param_split

  !-------------------------------------------------------------------
  ! tot_param_set_str : string parameter dispatch.
  !
  ! tr and eq expose string setters (tr_param_set_str,
  ! eq_param_set_str). Other namespaces return ierr=1 until their
  ! registries add a symmetric `_str` entry point.
  !-------------------------------------------------------------------
  SUBROUTINE tot_param_set_str(name, value, ierr)
    CHARACTER(LEN=*), INTENT(IN)  :: name
    CHARACTER(LEN=*), INTENT(IN)  :: value
    INTEGER,          INTENT(OUT) :: ierr

    CHARACTER(LEN=16) :: prefix
    CHARACTER(LEN=LEN(name)) :: bare
    LOGICAL :: ok

    CALL tot_param_split(name, prefix, bare, ok)
    IF (.NOT. ok) THEN
       ierr = 1
       RETURN
    END IF

    SELECT CASE (TRIM(prefix))
    CASE ("tr")
       ierr = dispatch_tr_str(TRIM(bare), TRIM(value))
    CASE ("eq")
       ierr = dispatch_eq_str(TRIM(bare), TRIM(value))
    CASE ("fp", "ti", "wr", "wrx")
       ! Registry exists but no string entry point yet.
       ierr = 1
    CASE DEFAULT
       ierr = 1
    END SELECT
  END SUBROUTINE tot_param_set_str

  ! -------------------------------------------------------------------
  ! Per-module numeric dispatchers. Each is a thin shim so that the
  ! USE statement (which drags the module's PUBLIC list into this
  ! compilation unit) is contained and does not pollute the top of
  ! the file with six namespaces at once.
  ! -------------------------------------------------------------------

  SUBROUTINE dispatch_eq(bare, value, ierr)
    USE eq_param_registry, ONLY: eq_param_set
    USE tr_param_registry, ONLY: tr_param_note_external_set
    CHARACTER(LEN=*), INTENT(IN)  :: bare
    REAL(C_DOUBLE),   INTENT(IN)  :: value
    INTEGER,          INTENT(OUT) :: ierr
    INTEGER :: rc
    CALL eq_param_set(bare, value, rc)
    IF (rc == 0) THEN
       ! Where TR prepares from this EQ registry (the mono image), tell it (as tr_api_set_param does for "eq:"), so that
       ! the next tot_run prepares again and tot_continue refuses, naming this one. On the split build libtrapi.so
       ! carries its own EQ and this set does not reach it (macOS's two-level namespace binds this call to
       ! libeqapi.so's registry). tot_api's setters refuse an eq: set once TR has prepared the case
       ! (tr_api_eq_set_refused_in_case), so until k-yoshimi/bpsd#7 this counts only before a preparation; TR's
       ! process-wide guard and its always-refused names (eq_name_refused) are not applied here.
       CALL tr_param_note_external_set('eq:'//bare)
       ierr = 0
    ELSE
       ierr = 1
    END IF
  END SUBROUTINE dispatch_eq

  FUNCTION dispatch_tr(bare, value) RESULT(ierr)
    USE tr_param_registry, ONLY: tr_param_set
    CHARACTER(LEN=*), INTENT(IN) :: bare
    REAL(C_DOUBLE),   INTENT(IN) :: value
    INTEGER :: ierr
    IF (tr_param_set(bare, value) == 0) THEN
       ierr = 0
    ELSE
       ierr = 1
    END IF
  END FUNCTION dispatch_tr

  FUNCTION dispatch_fp(bare, value) RESULT(ierr)
    USE fp_param_registry, ONLY: fp_param_set
    CHARACTER(LEN=*), INTENT(IN) :: bare
    REAL(C_DOUBLE),   INTENT(IN) :: value
    INTEGER :: ierr
    IF (fp_param_set(bare, value) == 0) THEN
       ierr = 0
    ELSE
       ierr = 1
    END IF
  END FUNCTION dispatch_fp

  FUNCTION dispatch_ti(bare, value) RESULT(ierr)
    USE ti_param_registry, ONLY: ti_param_set
    CHARACTER(LEN=*), INTENT(IN) :: bare
    REAL(C_DOUBLE),   INTENT(IN) :: value
    INTEGER :: ierr
    IF (ti_param_set(bare, value) == 0) THEN
       ierr = 0
    ELSE
       ierr = 1
    END IF
  END FUNCTION dispatch_ti

  FUNCTION dispatch_wrx(bare, value) RESULT(ierr)
    USE wrx_param_registry, ONLY: wrx_param_set
    CHARACTER(LEN=*), INTENT(IN) :: bare
    REAL(C_DOUBLE),   INTENT(IN) :: value
    INTEGER :: ierr
    IF (wrx_param_set(bare, value) == 0) THEN
       ierr = 0
    ELSE
       ierr = 1
    END IF
  END FUNCTION dispatch_wrx

  FUNCTION dispatch_tr_str(bare, value) RESULT(ierr)
    USE tr_param_registry, ONLY: tr_param_set_str
    CHARACTER(LEN=*), INTENT(IN) :: bare
    CHARACTER(LEN=*), INTENT(IN) :: value
    INTEGER :: ierr
    IF (tr_param_set_str(bare, value) == 0) THEN
       ierr = 0
    ELSE
       ierr = 1
    END IF
  END FUNCTION dispatch_tr_str

  FUNCTION dispatch_eq_str(bare, value) RESULT(ierr)
    USE eq_param_registry, ONLY: eq_param_set_str
    USE tr_param_registry, ONLY: tr_param_note_external_set
    CHARACTER(LEN=*), INTENT(IN) :: bare
    CHARACTER(LEN=*), INTENT(IN) :: value
    INTEGER :: ierr
    IF (eq_param_set_str(bare, value) == 0) THEN
       CALL tr_param_note_external_set('eq:'//bare)    ! as dispatch_eq
       ierr = 0
    ELSE
       ierr = 1
    END IF
  END FUNCTION dispatch_eq_str

END MODULE tot_param_registry
