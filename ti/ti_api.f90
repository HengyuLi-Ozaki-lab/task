! ti_api.f90
!
! Phase L-2: C ABI entry points for libtiapi.so (foundation layer).
!
! All five functions are STUBS that return ierr=4 ("not implemented").
! The Fortran-side names are ti_api_* to avoid colliding with the existing
! `SUBROUTINE ti_init` in tiinit.f90; the C-side public names ti_init,
! ti_run, ti_set_param, ti_get_state, ti_finalize are bound through
! BIND(C, NAME=...) so external callers see the spec'd symbols.
!
! Real bodies (init/finalize delegating to the existing ti_init /
! deallocate_ticomm, set_param dispatching through ti_param_registry,
! get_state populating from TICOMM, run delegating to ti_prep + ti_exec)
! arrive in Phase L-3.

MODULE ti_api
  USE, INTRINSIC :: ISO_C_BINDING
  USE ti_state, ONLY: ti_state_c
  IMPLICIT NONE
  PRIVATE
  PUBLIC :: ti_api_init, ti_api_run, ti_api_get_state, &
            ti_api_set_param, ti_api_finalize

  ! Error codes (must match ti_api.h enum):
  !   0 = OK
  !   1 = invalid parameter name / value
  !   2 = not initialized
  !   3 = calculation / initialization failed
  !   4 = not implemented (Phase L-2 stub return)
  INTEGER(C_INT), PARAMETER :: TI_ERR_NOT_IMPLEMENTED = 4

CONTAINS

  FUNCTION ti_api_init() RESULT(ierr) BIND(C, NAME="ti_init")
    INTEGER(C_INT) :: ierr
    ! L-2 stub. L-3 will call pl_init / eq_init / ti_init (tiinit.f90)
    ! to reproduce the standalone `ti` binary initialization sequence.
    ierr = TI_ERR_NOT_IMPLEMENTED
  END FUNCTION ti_api_init

  FUNCTION ti_api_run(ntmax_in) RESULT(ierr) BIND(C, NAME="ti_run")
    ! NOTE: dummy arg is ntmax_in (not ntmax) to avoid future case-
    ! insensitive collisions when L-3 adds USE ticomm, ONLY: NTMAX.
    INTEGER(C_INT), VALUE, INTENT(IN) :: ntmax_in
    INTEGER(C_INT) :: ierr
    ! Reference the input to avoid an unused-dummy warning while still
    ! returning the documented stub error code.
    IF (ntmax_in == HUGE(ntmax_in)) THEN
       ierr = TI_ERR_NOT_IMPLEMENTED
    ELSE
       ierr = TI_ERR_NOT_IMPLEMENTED
    END IF
  END FUNCTION ti_api_run

  FUNCTION ti_api_get_state(state) RESULT(ierr) BIND(C, NAME="ti_get_state")
    TYPE(ti_state_c), INTENT(OUT) :: state
    INTEGER(C_INT) :: ierr
    ! L-2 stub: zero the struct so callers don't see uninitialized memory.
    ! L-3 will populate from TICOMM.
    state%nt                = 0
    state%nrmax             = 0
    state%nsa_max           = 0
    state%nsmax             = 0
    state%T                 = 0.0_C_DOUBLE
    state%residual_loop_max = 0.0_C_DOUBLE
    state%icount_loop_max   = 0
    state%icount_mat_max    = 0
    state%RNA               = 0.0_C_DOUBLE
    state%RTA               = 0.0_C_DOUBLE
    state%RUA               = 0.0_C_DOUBLE
    state%RBP               = 0.0_C_DOUBLE
    state%RQP               = 0.0_C_DOUBLE
    state%RJP               = 0.0_C_DOUBLE
    state%ZEFF              = 0.0_C_DOUBLE
    state%BETA              = 0.0_C_DOUBLE
    state%BETAP             = 0.0_C_DOUBLE
    ierr = TI_ERR_NOT_IMPLEMENTED
  END FUNCTION ti_api_get_state

  FUNCTION ti_api_set_param(name, value) RESULT(ierr) BIND(C, NAME="ti_set_param")
    CHARACTER(KIND=C_CHAR), DIMENSION(*), INTENT(IN) :: name
    REAL(C_DOUBLE), VALUE, INTENT(IN) :: value
    INTEGER(C_INT) :: ierr
    ! Touch the inputs so the compiler does not warn about unused args.
    IF (name(1) == C_NULL_CHAR .AND. value == HUGE(value)) THEN
       ierr = TI_ERR_NOT_IMPLEMENTED
    ELSE
       ierr = TI_ERR_NOT_IMPLEMENTED
    END IF
  END FUNCTION ti_api_set_param

  FUNCTION ti_api_finalize() RESULT(ierr) BIND(C, NAME="ti_finalize")
    INTEGER(C_INT) :: ierr
    ! L-2 stub. L-3 will call deallocate_ticomm after a successful init.
    ierr = TI_ERR_NOT_IMPLEMENTED
  END FUNCTION ti_api_finalize

END MODULE ti_api
