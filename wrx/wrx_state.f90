! wrx_state.f90
!
! Phase L-2: C-interoperable state struct for the WRX library API.
!
! Mirrors wrx_api.h::wrx_state_t exactly. Fixed-size arrays per
! docs/superpowers/plans/2026-04-18-wrx-library-L2-c-abi-foundation.md.
!
! L-2 scope: type definition only. Population from WRCOMM happens in
! wrx_api::wrx_get_state during Phase L-3.
!
! Upper bounds:
!   WRX_MAX_NRAYMAX = 100  (matches NRAYM in wrcomm_parm)
!   WRX_MAX_NSAMAX  = 8    (matches NSM upper bound used by wr/dp)
!
! Actual runtime sizes are in nraymax/nsamax fields of the struct
! and must be <= these compile-time bounds.
!
! Memory layout note:
!   In C, pwr_nsa_nray[NRAYMAX][NSAMAX] is row-major;
!   in Fortran the matching declaration is pwr_nsa_nray(NSAMAX, NRAYMAX)
!   (column-major). The two layouts agree byte-for-byte.

MODULE wrx_state
  USE, INTRINSIC :: ISO_C_BINDING
  IMPLICIT NONE
  PRIVATE
  PUBLIC :: wrx_state_c, WRX_MAX_NRAYMAX, WRX_MAX_NSAMAX

  INTEGER(C_INT), PARAMETER :: WRX_MAX_NRAYMAX = 100
  INTEGER(C_INT), PARAMETER :: WRX_MAX_NSAMAX  = 8

  TYPE, BIND(C) :: wrx_state_c
     INTEGER(C_INT) :: nraymax
     INTEGER(C_INT) :: nstpmax
     INTEGER(C_INT) :: nsamax
     INTEGER(C_INT) :: nsmax
     INTEGER(C_INT) :: modelg
     INTEGER(C_INT) :: mdlwrq
     REAL(C_DOUBLE) :: pwr_tot
     INTEGER(C_INT) :: nstpmax_nray(WRX_MAX_NRAYMAX)
     REAL(C_DOUBLE) :: pwr_nray(WRX_MAX_NRAYMAX)
     REAL(C_DOUBLE) :: pwr_nsa(WRX_MAX_NSAMAX)
     REAL(C_DOUBLE) :: pwr_nsa_nray(WRX_MAX_NSAMAX, WRX_MAX_NRAYMAX)
     REAL(C_DOUBLE) :: pos_pwrmax_rs_nsa(WRX_MAX_NSAMAX)
     REAL(C_DOUBLE) :: pwrmax_rs_nsa(WRX_MAX_NSAMAX)
     REAL(C_DOUBLE) :: pos_pwrmax_rl_nsa(WRX_MAX_NSAMAX)
     REAL(C_DOUBLE) :: pwrmax_rl_nsa(WRX_MAX_NSAMAX)
  END TYPE wrx_state_c

END MODULE wrx_state
