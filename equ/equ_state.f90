! equ_state.f90
!
! C-interoperable types of the EQU library interface (equ_api.f90).
! Mirrors equ_api.h byte for byte: equ_state_c is equ_state_t,
! equ_diag_entry_c is equ_diag_entry_t. Fixed-size arrays at EQU's
! compile-time maxima (equcomm.f90: irdm, izdm, ivdm, isrzdm, icvdm), so
! the layout does not depend on NR, NZ, NV or the boundary's length. Only
! 1..n of each array carries data; equ_get_state zeroes the rest.
!
! Changing the layout: append fields at the end (never reorder or
! remove), bump EQU_STATE_ABI_VERSION here and in equ_api.h, mirror the
! field in python/equlib/_ffi.py and state.py, and rebuild
! libequapi.so in the same commit (the rule of EQ's #246).

MODULE equ_state
  USE, INTRINSIC :: ISO_C_BINDING
  IMPLICIT NONE
  PRIVATE
  PUBLIC :: EQU_STATE_ABI_VERSION, equ_state_c, equ_diag_entry_c
  PUBLIC :: EQU_MAX_NR, EQU_MAX_NZ, EQU_MAX_NV, EQU_MAX_NSU, EQU_NCV
  PUBLIC :: EQU_DIAG_PARAM_LEN, EQU_DIAG_MSG_LEN
  PUBLIC :: EQU_DIAG_OUT_OF_RANGE, EQU_DIAG_INCONSISTENT_PAIR, &
            EQU_DIAG_OUT_OF_RANGE_AFTER_DEP, EQU_DIAG_FILE_MISSING, &
            EQU_DIAG_MISSING_REQUIRED

  INTEGER(C_INT), PARAMETER :: EQU_STATE_ABI_VERSION = 1

  INTEGER(C_INT), PARAMETER :: EQU_MAX_NR  = 257   ! irdm
  INTEGER(C_INT), PARAMETER :: EQU_MAX_NZ  = 257   ! izdm
  INTEGER(C_INT), PARAMETER :: EQU_MAX_NV  = 101   ! ivdm
  INTEGER(C_INT), PARAMETER :: EQU_MAX_NSU = 1542  ! isrzdm
  INTEGER(C_INT), PARAMETER :: EQU_NCV     = 19    ! coil groups 0..icvdm

  TYPE, BIND(C) :: equ_state_c
     INTEGER(C_INT) :: nr, nz, nv, nsu
     INTEGER(C_INT) :: mode            ! mode of the run (0 or 1); -1 before one
     INTEGER(C_INT) :: fct_steps       ! |ieq| of the last FCT loop
     INTEGER(C_INT) :: fct_converged   ! 1 when ieq < 0 (erreq < EEQMAX)
     INTEGER(C_INT) :: xpoint_status   ! iisep: > 0 found, <= 0 the code's status
     REAL(C_DOUBLE) :: erreq
     REAL(C_DOUBLE) :: raxis, zaxis, psi_axis
     REAL(C_DOUBLE) :: rsep, zsep, psi_sep
     REAL(C_DOUBLE) :: ip, ip_target, rbt
     REAL(C_DOUBLE) :: beta_t, beta_s, beta_j, li
     REAL(C_DOUBLE) :: q_axis, q_surf, q95, qqj
     REAL(C_DOUBLE) :: rmaj, rpla, elip, trig, el95, volume
     REAL(C_DOUBLE) :: cvac(EQU_NCV)
     REAL(C_DOUBLE) :: rg(EQU_MAX_NR)
     REAL(C_DOUBLE) :: zg(EQU_MAX_NZ)
     REAL(C_DOUBLE) :: psi(EQU_MAX_NV)
     REAL(C_DOUBLE) :: psit(EQU_MAX_NV)
     REAL(C_DOUBLE) :: pressure(EQU_MAX_NV)
     REAL(C_DOUBLE) :: q(EQU_MAX_NV)
     REAL(C_DOUBLE) :: f(EQU_MAX_NV)
     REAL(C_DOUBLE) :: vol(EQU_MAX_NV)
     REAL(C_DOUBLE) :: rminor(EQU_MAX_NV)
     REAL(C_DOUBLE) :: rcentre(EQU_MAX_NV)
     REAL(C_DOUBLE) :: kappa(EQU_MAX_NV)
     REAL(C_DOUBLE) :: delta(EQU_MAX_NV)
     REAL(C_DOUBLE) :: rsu(EQU_MAX_NSU)
     REAL(C_DOUBLE) :: zsu(EQU_MAX_NSU)
  END TYPE equ_state_c

  ! Diagnostics of equ_validate (EQ's record and codes).
  INTEGER(C_INT), PARAMETER :: EQU_DIAG_PARAM_LEN = 64
  INTEGER(C_INT), PARAMETER :: EQU_DIAG_MSG_LEN   = 128
  INTEGER(C_INT), PARAMETER :: EQU_DIAG_OUT_OF_RANGE           = 1
  INTEGER(C_INT), PARAMETER :: EQU_DIAG_INCONSISTENT_PAIR      = 2
  INTEGER(C_INT), PARAMETER :: EQU_DIAG_OUT_OF_RANGE_AFTER_DEP = 3
  INTEGER(C_INT), PARAMETER :: EQU_DIAG_FILE_MISSING           = 4
  INTEGER(C_INT), PARAMETER :: EQU_DIAG_MISSING_REQUIRED       = 5

  TYPE, BIND(C) :: equ_diag_entry_c
     CHARACTER(KIND=C_CHAR) :: param(EQU_DIAG_PARAM_LEN)
     INTEGER(C_INT)         :: code
     CHARACTER(KIND=C_CHAR) :: msg(EQU_DIAG_MSG_LEN)
  END TYPE equ_diag_entry_c
END MODULE equ_state
