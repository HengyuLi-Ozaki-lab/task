! wrx_api.f90
!
! Phase L-2: C ABI entry points for libwrxapi.so (foundation layer).
!
! All five functions are STUBS that return ierr=4 ("not implemented").
! The Fortran-side names are wrx_api_* to avoid colliding with any
! existing wrx subroutines and with the future wr_api.f90 sibling; the
! C-side public names wrx_init, wrx_run, wrx_set_param, wrx_get_state,
! wrx_finalize are bound through BIND(C, NAME=...) so external callers
! see the spec'd wrx_* symbols (NOT wr_*).
!
! Real bodies (init wiring pl_init/dp_init/wr_init/EQINIT, set_param
! dispatching through a wrx_param_registry, get_state populating from
! WRCOMM, run delegating to wr_prep/wr_setup/wr_exec) arrive in
! Phase L-3.
!
! See docs/superpowers/plans/2026-04-18-wrx-library-L2-c-abi-foundation.md.

MODULE wrx_api
  USE, INTRINSIC :: ISO_C_BINDING
  USE wrx_state, ONLY: wrx_state_c
  IMPLICIT NONE
  PRIVATE
  PUBLIC :: wrx_api_init, wrx_api_run, wrx_api_get_state, &
            wrx_api_set_param, wrx_api_finalize

  ! Error codes (must match wrx_api.h enum):
  !   0 = OK
  !   1 = invalid parameter name / value
  !   2 = not initialized
  !   3 = calculation / initialization failed
  !   4 = not implemented (Phase L-2 stub return)
  INTEGER(C_INT), PARAMETER :: WRX_ERR_NOT_IMPLEMENTED = 4

CONTAINS

  FUNCTION wrx_api_init() RESULT(ierr) BIND(C, NAME="wrx_init")
    INTEGER(C_INT) :: ierr
    ! L-2 stub. L-3 will invoke pl_init / EQINIT / dp_init / wr_init in
    ! the order prescribed by wrmain.f90.
    ierr = WRX_ERR_NOT_IMPLEMENTED
  END FUNCTION wrx_api_init

  FUNCTION wrx_api_run(nstpmax_in) RESULT(ierr) BIND(C, NAME="wrx_run")
    ! NOTE: dummy arg is nstpmax_in (not nstpmax) to avoid future
    ! case-insensitive collisions when L-3 adds USE wrcomm, ONLY: NSTPMAX.
    INTEGER(C_INT), VALUE, INTENT(IN) :: nstpmax_in
    INTEGER(C_INT) :: ierr
    ! Reference the input to avoid an unused-dummy warning while still
    ! returning the documented stub error code.
    IF (nstpmax_in == HUGE(nstpmax_in)) THEN
       ierr = WRX_ERR_NOT_IMPLEMENTED
    ELSE
       ierr = WRX_ERR_NOT_IMPLEMENTED
    END IF
  END FUNCTION wrx_api_run

  FUNCTION wrx_api_get_state(state) RESULT(ierr) BIND(C, NAME="wrx_get_state")
    TYPE(wrx_state_c), INTENT(OUT) :: state
    INTEGER(C_INT) :: ierr
    ! L-2 stub: zero-fill the struct so callers do not observe
    ! uninitialized memory. L-3 will populate from WRCOMM.
    state%nraymax = 0
    state%nstpmax = 0
    state%nsamax  = 0
    state%nsmax   = 0
    state%modelg  = 0
    state%mdlwrq  = 0
    state%pwr_tot = 0.0_C_DOUBLE
    state%nstpmax_nray      = 0
    state%pwr_nray          = 0.0_C_DOUBLE
    state%pwr_nsa           = 0.0_C_DOUBLE
    state%pwr_nsa_nray      = 0.0_C_DOUBLE
    state%pos_pwrmax_rs_nsa = 0.0_C_DOUBLE
    state%pwrmax_rs_nsa     = 0.0_C_DOUBLE
    state%pos_pwrmax_rl_nsa = 0.0_C_DOUBLE
    state%pwrmax_rl_nsa     = 0.0_C_DOUBLE
    ierr = WRX_ERR_NOT_IMPLEMENTED
  END FUNCTION wrx_api_get_state

  FUNCTION wrx_api_set_param(name, value) RESULT(ierr) BIND(C, NAME="wrx_set_param")
    CHARACTER(KIND=C_CHAR), DIMENSION(*), INTENT(IN) :: name
    REAL(C_DOUBLE), VALUE, INTENT(IN) :: value
    INTEGER(C_INT) :: ierr
    ! Touch the inputs so the compiler does not warn about unused args.
    IF (name(1) == C_NULL_CHAR .AND. value == HUGE(value)) THEN
       ierr = WRX_ERR_NOT_IMPLEMENTED
    ELSE
       ierr = WRX_ERR_NOT_IMPLEMENTED
    END IF
  END FUNCTION wrx_api_set_param

  FUNCTION wrx_api_finalize() RESULT(ierr) BIND(C, NAME="wrx_finalize")
    INTEGER(C_INT) :: ierr
    ! L-2 stub. L-3 will call wr_deallocate after a successful
    ! wrx_run (which in turn will have called wr_allocate).
    ierr = WRX_ERR_NOT_IMPLEMENTED
  END FUNCTION wrx_api_finalize

END MODULE wrx_api
