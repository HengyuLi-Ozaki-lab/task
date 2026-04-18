! fp_api.f90
!
! Phase L-2: C ABI entry points for libfpapi.so (foundation layer).
!
! All five functions are STUBS that return ierr=4 ("not implemented").
! The Fortran-side names are fp_api_* to avoid colliding with the existing
! `SUBROUTINE fp_init` in fpinit.f90; the C-side public names fp_init,
! fp_run, fp_set_param, fp_get_state, fp_finalize are bound through
! BIND(C, NAME=...) so external callers see the spec'd symbols.
!
! Real bodies (init delegating to pl_init/eq_init/ob_init/fp_init,
! run delegating to fp_prep+fp_loop, set_param dispatching through
! fp_param_registry, get_state populating from FPCOMM, finalize
! releasing fp allocations) arrive in Phase L-3 / L-4.
!
! See docs/superpowers/plans/2026-04-18-fp-library-L2-c-abi-foundation.md.

MODULE fp_api
  USE, INTRINSIC :: ISO_C_BINDING
  USE fp_state, ONLY: fp_state_c
  IMPLICIT NONE
  PRIVATE
  PUBLIC :: fp_api_init, fp_api_run, fp_api_get_state, &
            fp_api_set_param, fp_api_finalize

  ! Error codes (must match fp_api.h enum):
  !   0 = OK
  !   1 = invalid parameter name / value
  !   2 = not initialized
  !   3 = calculation / initialization failed
  !   4 = not implemented (Phase L-2 stub return)
  INTEGER(C_INT), PARAMETER :: FP_ERR_NOT_IMPLEMENTED = 4

CONTAINS

  FUNCTION fp_api_init() RESULT(ierr) BIND(C, NAME="fp_init")
    INTEGER(C_INT) :: ierr
    ! L-2 stub. L-3 will call pl_init/eq_init/ob_init/fp_init in sequence
    ! and mark the API as initialized.
    ierr = FP_ERR_NOT_IMPLEMENTED
  END FUNCTION fp_api_init

  FUNCTION fp_api_run(ntmax_in) RESULT(ierr) BIND(C, NAME="fp_run")
    ! NOTE: dummy arg is ntmax_in (not ntmax) to avoid future case-
    ! insensitive collisions when L-3 adds USE fpcomm, ONLY: NTMAX.
    INTEGER(C_INT), VALUE, INTENT(IN) :: ntmax_in
    INTEGER(C_INT) :: ierr
    ! Reference the input to avoid an unused-dummy warning while still
    ! returning the documented stub error code.
    IF (ntmax_in == HUGE(ntmax_in)) THEN
       ierr = FP_ERR_NOT_IMPLEMENTED
    ELSE
       ierr = FP_ERR_NOT_IMPLEMENTED
    END IF
  END FUNCTION fp_api_run

  FUNCTION fp_api_get_state(state) RESULT(ierr) BIND(C, NAME="fp_get_state")
    TYPE(fp_state_c), INTENT(OUT) :: state
    INTEGER(C_INT) :: ierr
    ! L-2 stub: zero the struct so callers don't see uninitialized memory.
    ! L-3 will populate from FPCOMM.
    state%nrmax  = 0
    state%nsamax = 0
    state%npmax  = 0
    state%nthmax = 0
    state%ntg2   = 0
    state%timefp = 0.0_C_DOUBLE
    state%RNT  = 0.0_C_DOUBLE
    state%RWT  = 0.0_C_DOUBLE
    state%RTT  = 0.0_C_DOUBLE
    state%RJT  = 0.0_C_DOUBLE
    state%RPCT = 0.0_C_DOUBLE
    state%RPWT = 0.0_C_DOUBLE
    ierr = FP_ERR_NOT_IMPLEMENTED
  END FUNCTION fp_api_get_state

  FUNCTION fp_api_set_param(name, value) RESULT(ierr) BIND(C, NAME="fp_set_param")
    CHARACTER(KIND=C_CHAR), DIMENSION(*), INTENT(IN) :: name
    REAL(C_DOUBLE), VALUE, INTENT(IN) :: value
    INTEGER(C_INT) :: ierr
    ! Touch the inputs so the compiler does not warn about unused args.
    IF (name(1) == C_NULL_CHAR .AND. value == HUGE(value)) THEN
       ierr = FP_ERR_NOT_IMPLEMENTED
    ELSE
       ierr = FP_ERR_NOT_IMPLEMENTED
    END IF
  END FUNCTION fp_api_set_param

  FUNCTION fp_api_finalize() RESULT(ierr) BIND(C, NAME="fp_finalize")
    INTEGER(C_INT) :: ierr
    ! L-2 stub. L-3 / L-4 will release fp allocations after a successful init.
    ierr = FP_ERR_NOT_IMPLEMENTED
  END FUNCTION fp_api_finalize

END MODULE fp_api
