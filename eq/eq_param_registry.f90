! eq_param_registry.f90
!
! Phase L-2: parameter-registry SHELL.
!
! This module defines the public entry point eq_param_set(name, value,
! ierr) that the C ABI layer (eq_api.f90) calls in response to a
! runtime eq_set_param(...) request.
!
! In L-2 the registry is deliberately a stub: every call returns
! ierr = 4 (EQ_ERR_NOT_IMPL) so the ABI surface is stable and
! downstream linkers can resolve the symbol, while the actual
! parameter table is deferred to Phase L-3. The same shape/contract
! is used by tr_param_registry (Phase L-3 implemented) and
! ti_param_registry (Phase L-3 implemented), so wiring in the real
! SELECT CASE dispatch is a purely local change later.

MODULE eq_param_registry
  USE, INTRINSIC :: ISO_C_BINDING, ONLY: C_DOUBLE
  IMPLICIT NONE
  PRIVATE
  PUBLIC :: eq_param_set

CONTAINS

  SUBROUTINE eq_param_set(name, value, ierr)
    CHARACTER(LEN=*),  INTENT(IN)  :: name
    REAL(C_DOUBLE),    INTENT(IN)  :: value
    INTEGER,           INTENT(OUT) :: ierr
    ! Suppress unused-argument warnings without touching COMMON state.
    IF (LEN_TRIM(name) < 0) ierr = 0
    IF (value /= value)     ierr = 0
    ! L-2 stub: every parameter is "not implemented" until L-3.
    ierr = 4
  END SUBROUTINE eq_param_set

END MODULE eq_param_registry
