! tr_api.f90
!
! Phase L-2: C ABI entry points for libtrapi.so (foundation layer).
!
! All five functions are STUBS that return ierr=4 ("not implemented").
! The Fortran-side names are tr_api_* to avoid colliding with the existing
! `SUBROUTINE tr_init` in trinit.f90; the C-side public names tr_init,
! tr_run, tr_set_param, tr_get_state, tr_finalize are bound through
! BIND(C, NAME=...) so external callers see the spec'd symbols.
!
! Real bodies (init/finalize delegating to ALLOCATE_TRCOMM /
! DEALLOCATE_TRCOMM, set_param dispatching through tr_param_registry,
! get_state populating from TRCOMM, run delegating to tr_loop) arrive
! in Phase L-3.
!
! See docs/superpowers/specs/2026-04-17-tr-library-design.md  Section 4.

MODULE tr_api
  USE, INTRINSIC :: ISO_C_BINDING
  USE tr_state, ONLY: tr_state_c
  IMPLICIT NONE
  PRIVATE
  PUBLIC :: tr_api_init, tr_api_run, tr_api_get_state, &
            tr_api_set_param, tr_api_finalize

  ! Error codes (must match tr_api.h enum):
  !   0 = OK
  !   1 = invalid parameter name / value
  !   2 = not initialized
  !   3 = calculation / initialization failed
  !   4 = not implemented (Phase L-2 stub return)
  INTEGER(C_INT), PARAMETER :: TR_ERR_NOT_IMPLEMENTED = 4

CONTAINS

  FUNCTION tr_api_init() RESULT(ierr) BIND(C, NAME="tr_init")
    INTEGER(C_INT) :: ierr
    ! L-2 stub. L-3 will call ALLOCATE_TRCOMM and run the existing
    ! tr_init initialization sequence.
    ierr = TR_ERR_NOT_IMPLEMENTED
  END FUNCTION tr_api_init

  FUNCTION tr_api_run(ntmax_in) RESULT(ierr) BIND(C, NAME="tr_run")
    ! NOTE: dummy arg is ntmax_in (not ntmax) to avoid future case-
    ! insensitive collisions when L-3 adds USE trcomm, ONLY: NTMAX.
    INTEGER(C_INT), VALUE, INTENT(IN) :: ntmax_in
    INTEGER(C_INT) :: ierr
    ! Reference the input to avoid an unused-dummy warning while still
    ! returning the documented stub error code.
    IF (ntmax_in == HUGE(ntmax_in)) THEN
       ierr = TR_ERR_NOT_IMPLEMENTED
    ELSE
       ierr = TR_ERR_NOT_IMPLEMENTED
    END IF
  END FUNCTION tr_api_run

  FUNCTION tr_api_get_state(state) RESULT(ierr) BIND(C, NAME="tr_get_state")
    TYPE(tr_state_c), INTENT(OUT) :: state
    INTEGER(C_INT) :: ierr
    ! L-2 stub: zero the struct so callers don't see uninitialized memory.
    ! L-3 will populate from TRCOMM.
    state%nt    = 0
    state%nrmax = 0
    state%nsmax = 0
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
    ierr = TR_ERR_NOT_IMPLEMENTED
  END FUNCTION tr_api_get_state

  FUNCTION tr_api_set_param(name, value) RESULT(ierr) BIND(C, NAME="tr_set_param")
    CHARACTER(KIND=C_CHAR), DIMENSION(*), INTENT(IN) :: name
    REAL(C_DOUBLE), VALUE, INTENT(IN) :: value
    INTEGER(C_INT) :: ierr
    ! Touch the inputs so the compiler does not warn about unused args.
    IF (name(1) == C_NULL_CHAR .AND. value == HUGE(value)) THEN
       ierr = TR_ERR_NOT_IMPLEMENTED
    ELSE
       ierr = TR_ERR_NOT_IMPLEMENTED
    END IF
  END FUNCTION tr_api_set_param

  FUNCTION tr_api_finalize() RESULT(ierr) BIND(C, NAME="tr_finalize")
    INTEGER(C_INT) :: ierr
    ! L-2 stub. L-3 will call DEALLOCATE_TRCOMM after a successful init.
    ierr = TR_ERR_NOT_IMPLEMENTED
  END FUNCTION tr_api_finalize

END MODULE tr_api
