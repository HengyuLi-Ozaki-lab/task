! tot_api.f90
!
! Phase L-2: C ABI entry points for libtotapi.so (foundation layer).
!
! TOT is the orchestrator module — in real operation its init / run /
! get_state / set_param / finalize fan out to the per-module APIs
! (tr_init + ti_init + fp_init + wr_init, tr_run, tr_get_state + ...,
! per-module *_set_param dispatch, *_finalize in reverse order). At L-2
! we only lay the ABI scaffolding: all five entry points are STUBS that
! return ierr=4 ("not implemented"). Real composition wires up in L-3+
! once every participating module has its own L-2 merged.
!
! The Fortran-side names are tot_api_* to avoid colliding with any
! existing `SUBROUTINE tot_init` style names in tot*.f90; the C-side
! public symbols tot_init, tot_run, tot_set_param, tot_get_state and
! tot_finalize are bound through BIND(C, NAME=...) so external callers
! see the spec'd symbols.
!
! Crucially, this file does NOT `USE tr_api` / `USE ti_api` / etc. at
! L-2 — keeping the stub module self-contained means the independent
! SRCS_API target builds without hard-depending on any per-module L-2
! branch. Those USEs come back in L-3+.
!
! See docs/superpowers/specs/2026-04-17-tr-library-design.md  Section 4
! and docs/superpowers/plans/2026-04-18-tot-library-L2-c-abi-foundation.md.

MODULE tot_api
  USE, INTRINSIC :: ISO_C_BINDING
  USE tot_state, ONLY: tot_state_c, TOT_MAX_NRMAX, TOT_MAX_NSMAX
  USE tot_param_registry, ONLY: tot_param_set, tot_param_set_str
  IMPLICIT NONE
  PRIVATE
  PUBLIC :: tot_api_init, tot_api_run, tot_api_get_state, &
            tot_api_set_param, tot_api_set_param_str, tot_api_finalize

  ! Error codes (must match tot_api.h enum):
  !   0 = OK
  !   1 = invalid parameter name / value
  !   2 = not initialized
  !   3 = per-module init / calculation failed
  !   4 = not implemented (Phase L-2 stub return)
  INTEGER(C_INT), PARAMETER :: TOT_ERR_OK              = 0
  INTEGER(C_INT), PARAMETER :: TOT_ERR_INVALID         = 1
  INTEGER(C_INT), PARAMETER :: TOT_ERR_NOT_IMPLEMENTED = 4

CONTAINS

  FUNCTION tot_api_init() RESULT(ierr) BIND(C, NAME="tot_init")
    INTEGER(C_INT) :: ierr
    ! L-2 stub. L-3 will fan out to pl_init / eq_init / tr_api_init /
    ! ti_api_init / fp_api_init / wr_api_init / wm_api_init (mirroring
    ! totmain.f90's ordering) and run mtx_initialize.
    ierr = TOT_ERR_NOT_IMPLEMENTED
  END FUNCTION tot_api_init

  FUNCTION tot_api_run(ntmax_in) RESULT(ierr) BIND(C, NAME="tot_run")
    ! NOTE: dummy arg is ntmax_in (not ntmax) to avoid future case-
    ! insensitive collisions when L-3 adds USE trcomm, ONLY: NTMAX.
    INTEGER(C_INT), VALUE, INTENT(IN) :: ntmax_in
    INTEGER(C_INT) :: ierr
    ! Reference the input to avoid an unused-dummy warning while still
    ! returning the documented stub error code.
    IF (ntmax_in == HUGE(ntmax_in)) THEN
       ierr = TOT_ERR_NOT_IMPLEMENTED
    ELSE
       ierr = TOT_ERR_NOT_IMPLEMENTED
    END IF
  END FUNCTION tot_api_run

  FUNCTION tot_api_get_state(state) RESULT(ierr) BIND(C, NAME="tot_get_state")
    TYPE(tot_state_c), INTENT(OUT) :: state
    INTEGER(C_INT) :: ierr
    ! L-2 stub: zero the struct so callers don't see uninitialized
    ! memory (presence flags read 0 = "module absent"). L-3 will fan out
    ! to tr_api_get_state / ti_api_get_state / ... and populate the
    ! nested state slots.
    state%tr_present = 0
    state%ti_present = 0
    state%fp_present = 0
    state%wr_present = 0
    state%nt     = 0
    state%nrmax  = 0
    state%nsmax  = 0
    state%T      = 0.0_C_DOUBLE
    state%WPT    = 0.0_C_DOUBLE
    state%AJT    = 0.0_C_DOUBLE
    state%Q0     = 0.0_C_DOUBLE
    state%BETA0  = 0.0_C_DOUBLE
    state%BETAP0 = 0.0_C_DOUBLE
    state%BETAA  = 0.0_C_DOUBLE
    state%BETAN  = 0.0_C_DOUBLE
    state%TAUE1  = 0.0_C_DOUBLE
    state%TAUE2  = 0.0_C_DOUBLE
    state%ZEFF0  = 0.0_C_DOUBLE
    state%ALI    = 0.0_C_DOUBLE
    state%RQ1    = 0.0_C_DOUBLE
    state%RN     = 0.0_C_DOUBLE
    state%RT     = 0.0_C_DOUBLE
    state%AJ     = 0.0_C_DOUBLE
    state%QP     = 0.0_C_DOUBLE
    ierr = TOT_ERR_NOT_IMPLEMENTED
  END FUNCTION tot_api_get_state

  !-------------------------------------------------------------------
  ! tot_set_param : dispatch a namespaced parameter to the matching
  ! per-module registry.
  !
  ! name   - NUL-terminated C string of the form "<ns>:<bare>" where
  !          <ns> is one of {eq, tr, fp, ti, wr, wrx}. Calls without a
  !          prefix are rejected (TOT_ERR_INVALID) because the tot
  !          parameter space is the UNION of the six backing modules
  !          and there is no single "owner" to default to.
  ! value  - scalar double.
  !
  ! Returns:
  !   0 = success
  !   1 = invalid (bad prefix, unknown bare name, downstream rejected)
  !-------------------------------------------------------------------
  FUNCTION tot_api_set_param(name, value) RESULT(ierr) BIND(C, NAME="tot_set_param")
    CHARACTER(KIND=C_CHAR), DIMENSION(*), INTENT(IN) :: name
    REAL(C_DOUBLE), VALUE,                INTENT(IN) :: value
    INTEGER(C_INT) :: ierr
    CHARACTER(LEN=128) :: fname
    INTEGER :: rc

    CALL c_string_to_fortran(name, fname)
    CALL tot_param_set(TRIM(fname), value, rc)
    IF (rc == 0) THEN
       ierr = TOT_ERR_OK
    ELSE
       ierr = TOT_ERR_INVALID
    END IF
  END FUNCTION tot_api_set_param

  !-------------------------------------------------------------------
  ! tot_set_param_str : string-valued companion to tot_set_param.
  !
  ! At L-3 only the `tr:` namespace has a backing string setter (for
  ! KNAMEQ and friends). All other namespaces return TOT_ERR_INVALID
  ! until their registries grow a matching `_str` entry point.
  !-------------------------------------------------------------------
  FUNCTION tot_api_set_param_str(name, value) RESULT(ierr) &
       BIND(C, NAME="tot_set_param_str")
    CHARACTER(KIND=C_CHAR), DIMENSION(*), INTENT(IN) :: name
    CHARACTER(KIND=C_CHAR), DIMENSION(*), INTENT(IN) :: value
    INTEGER(C_INT) :: ierr
    CHARACTER(LEN=128) :: fname
    CHARACTER(LEN=256) :: fvalue
    INTEGER :: rc

    CALL c_string_to_fortran(name,  fname)
    CALL c_string_to_fortran(value, fvalue)
    CALL tot_param_set_str(TRIM(fname), TRIM(fvalue), rc)
    IF (rc == 0) THEN
       ierr = TOT_ERR_OK
    ELSE
       ierr = TOT_ERR_INVALID
    END IF
  END FUNCTION tot_api_set_param_str

  FUNCTION tot_api_finalize() RESULT(ierr) BIND(C, NAME="tot_finalize")
    INTEGER(C_INT) :: ierr
    ! L-2 stub. L-3 will finalize each module in reverse init order
    ! (ti_api_finalize / fp_api_finalize / wm_api_finalize /
    !  wr_api_finalize / tr_api_finalize / eq_finalize / pl_finalize)
    ! followed by mtx_finalize, matching totmain.f90:79.
    ierr = TOT_ERR_NOT_IMPLEMENTED
  END FUNCTION tot_api_finalize

  !-------------------------------------------------------------------
  ! Copy a NUL-terminated C char array into a fixed-length Fortran
  ! buffer, space-padded. Safe against names/values longer than the
  ! destination: we stop at the first NUL or at LEN(dst), whichever
  ! comes first.
  !-------------------------------------------------------------------
  SUBROUTINE c_string_to_fortran(c_str, f_str)
    CHARACTER(KIND=C_CHAR), DIMENSION(*), INTENT(IN)  :: c_str
    CHARACTER(LEN=*),                     INTENT(OUT) :: f_str
    INTEGER :: i
    f_str = ' '
    DO i = 1, LEN(f_str)
       IF (c_str(i) == C_NULL_CHAR) EXIT
       f_str(i:i) = c_str(i)
    END DO
  END SUBROUTINE c_string_to_fortran

END MODULE tot_api
