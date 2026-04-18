! wr_api.f90
!
! Phase L-2: C ABI entry points for libwrapi.so (foundation layer).
!
! All five functions are STUBS that return ierr=4 ("not implemented").
! The Fortran-side names are wr_api_* to avoid colliding with the existing
! `SUBROUTINE wr_init` in wrinit.f90; the C-side public names wr_init,
! wr_run, wr_set_param, wr_get_state, wr_finalize are bound through
! BIND(C, NAME=...) so external callers see the spec'd symbols.
!
! Real bodies (init/finalize delegating to wr_allocate / wr_deallocate,
! set_param dispatching through wr_param_registry, get_state populating
! from wrcomm, run delegating to wr_setup + wr_exec) arrive in Phase L-3.
!
! See docs/superpowers/plans/2026-04-18-wr-library-L2-c-abi-foundation.md.

MODULE wr_api
  USE, INTRINSIC :: ISO_C_BINDING
  USE wr_state, ONLY: wr_state_c, &
                      WR_MAX_NRAYMAX, WR_MAX_NRSMAX, WR_MAX_NRLMAX, &
                      WR_MAX_NRAY_EQ
  IMPLICIT NONE
  PRIVATE
  PUBLIC :: wr_api_init, wr_api_run, wr_api_get_state, &
            wr_api_set_param, wr_api_finalize

  ! Error codes (must match wr_api.h enum):
  !   0 = OK
  !   1 = invalid parameter name / value
  !   2 = not initialized
  !   3 = calculation / initialization failed
  !   4 = not implemented (Phase L-2 stub return)
  INTEGER(C_INT), PARAMETER :: WR_ERR_NOT_IMPLEMENTED = 4

CONTAINS

  FUNCTION wr_api_init() RESULT(ierr) BIND(C, NAME="wr_init")
    INTEGER(C_INT) :: ierr
    ! L-2 stub. L-3 will invoke pl_init / EQINIT / dp_init / wr_init
    ! and mark the global initialized flag.
    ierr = WR_ERR_NOT_IMPLEMENTED
  END FUNCTION wr_api_init

  FUNCTION wr_api_run(nray_request) RESULT(ierr) BIND(C, NAME="wr_run")
    ! nray_request > 0 overrides namelist NRAYMAX before wr_setup; 0 keeps it.
    INTEGER(C_INT), VALUE, INTENT(IN) :: nray_request
    INTEGER(C_INT) :: ierr
    ! Reference the input to avoid an unused-dummy warning while still
    ! returning the documented stub error code.
    IF (nray_request == HUGE(nray_request)) THEN
       ierr = WR_ERR_NOT_IMPLEMENTED
    ELSE
       ierr = WR_ERR_NOT_IMPLEMENTED
    END IF
  END FUNCTION wr_api_run

  FUNCTION wr_api_get_state(state) RESULT(ierr) BIND(C, NAME="wr_get_state")
    TYPE(wr_state_c), INTENT(OUT) :: state
    INTEGER(C_INT) :: ierr
    ! L-2 stub: zero the struct so callers don't see uninitialized memory.
    ! L-3 will populate from wrcomm (NRAYMAX, NRSMAX, NRLMAX, RAYS,
    ! pos_nrs/pwr_nrs, pos_nrl/pwr_nrl, pos_pwrmax_*, pwrmax_*, ...).
    state%nraymax = 0
    state%nrsmax  = 0
    state%nrlmax  = 0
    state%pos_pwrmax_rs      = 0.0_C_DOUBLE
    state%pwrmax_rs          = 0.0_C_DOUBLE
    state%pos_pwrmax_rl      = 0.0_C_DOUBLE
    state%pwrmax_rl          = 0.0_C_DOUBLE
    state%nstp_end           = 0
    state%pos_pwrmax_rs_nray = 0.0_C_DOUBLE
    state%pwrmax_rs_nray     = 0.0_C_DOUBLE
    state%pos_pwrmax_rl_nray = 0.0_C_DOUBLE
    state%pwrmax_rl_nray     = 0.0_C_DOUBLE
    state%rays_end           = 0.0_C_DOUBLE
    state%pos_nrs            = 0.0_C_DOUBLE
    state%pwr_nrs            = 0.0_C_DOUBLE
    state%pos_nrl            = 0.0_C_DOUBLE
    state%pwr_nrl            = 0.0_C_DOUBLE
    ierr = WR_ERR_NOT_IMPLEMENTED
  END FUNCTION wr_api_get_state

  FUNCTION wr_api_set_param(name, value) RESULT(ierr) BIND(C, NAME="wr_set_param")
    CHARACTER(KIND=C_CHAR), DIMENSION(*), INTENT(IN) :: name
    REAL(C_DOUBLE), VALUE, INTENT(IN) :: value
    INTEGER(C_INT) :: ierr
    ! Touch the inputs so the compiler does not warn about unused args.
    IF (name(1) == C_NULL_CHAR .AND. value == HUGE(value)) THEN
       ierr = WR_ERR_NOT_IMPLEMENTED
    ELSE
       ierr = WR_ERR_NOT_IMPLEMENTED
    END IF
  END FUNCTION wr_api_set_param

  FUNCTION wr_api_finalize() RESULT(ierr) BIND(C, NAME="wr_finalize")
    INTEGER(C_INT) :: ierr
    ! L-2 stub. L-3 will invoke wr_deallocate and reset the initialized flag.
    ierr = WR_ERR_NOT_IMPLEMENTED
  END FUNCTION wr_api_finalize

END MODULE wr_api
