! wr_state.f90
!
! Phase L-2: C-interoperable state struct for the WR library API.
!
! Mirrors wr_api.h::wr_state_t exactly. Fixed-size arrays per
! docs/superpowers/plans/2026-04-18-wr-library-L2-c-abi-foundation.md.
!
! L-2 scope: type definition only. Population from wrcomm happens in
! wr_api::wr_get_state during Phase L-3.
!
! Field layout matches wrcomm.f90 declarations:
!   - RAYS(0:NEQ, 0:NSTPMAX, NRAYMAX) with NEQ=8 ⇒ first dim has 9 elements.
!   - pos_pwrmax_rs / pwrmax_rs / pos_pwrmax_rl / pwrmax_rl : global scalars.
!   - pos_pwrmax_rs_nray / pwrmax_rs_nray / pos_pwrmax_rl_nray /
!     pwrmax_rl_nray : per-ray arrays of length NRAYMAX.
!   - pos_nrs/pwr_nrs : minor-radius profile of length NRSMAX.
!   - pos_nrl/pwr_nrl : major-radius profile of length NRLMAX.

MODULE wr_state
  USE, INTRINSIC :: ISO_C_BINDING
  IMPLICIT NONE
  PRIVATE
  PUBLIC :: wr_state_c, &
            WR_MAX_NRAYMAX, WR_MAX_NRSMAX, WR_MAX_NRLMAX, WR_MAX_NRAY_EQ

  ! Upper bounds (must match wr_api.h).
  ! WR_MAX_NRAYMAX mirrors NRAYM in wrcomm.f90 (currently 100).
  ! WR_MAX_NRAY_EQ mirrors NEQ+1 in wrcomm.f90 (NEQ=8 ⇒ 9 elements for 0:NEQ).
  INTEGER(C_INT), PARAMETER :: WR_MAX_NRAYMAX = 100
  INTEGER(C_INT), PARAMETER :: WR_MAX_NRSMAX  = 200
  INTEGER(C_INT), PARAMETER :: WR_MAX_NRLMAX  = 400
  INTEGER(C_INT), PARAMETER :: WR_MAX_NRAY_EQ = 9

  TYPE, BIND(C) :: wr_state_c
     ! Runtime dimensions (<= WR_MAX_*).
     INTEGER(C_INT) :: nraymax
     INTEGER(C_INT) :: nrsmax
     INTEGER(C_INT) :: nrlmax
     ! Global peak power location/value (rs = minor radius, rl = major radius).
     REAL(C_DOUBLE) :: pos_pwrmax_rs
     REAL(C_DOUBLE) :: pwrmax_rs
     REAL(C_DOUBLE) :: pos_pwrmax_rl
     REAL(C_DOUBLE) :: pwrmax_rl
     ! Per-ray scalars and end-state RAYS(0:NEQ, end, j).
     INTEGER(C_INT) :: nstp_end           (WR_MAX_NRAYMAX)
     REAL(C_DOUBLE) :: pos_pwrmax_rs_nray (WR_MAX_NRAYMAX)
     REAL(C_DOUBLE) :: pwrmax_rs_nray     (WR_MAX_NRAYMAX)
     REAL(C_DOUBLE) :: pos_pwrmax_rl_nray (WR_MAX_NRAYMAX)
     REAL(C_DOUBLE) :: pwrmax_rl_nray     (WR_MAX_NRAYMAX)
     REAL(C_DOUBLE) :: rays_end           (WR_MAX_NRAY_EQ, WR_MAX_NRAYMAX)
     ! Profiles (zero-padded beyond actual dim).
     REAL(C_DOUBLE) :: pos_nrs            (WR_MAX_NRSMAX)
     REAL(C_DOUBLE) :: pwr_nrs            (WR_MAX_NRSMAX)
     REAL(C_DOUBLE) :: pos_nrl            (WR_MAX_NRLMAX)
     REAL(C_DOUBLE) :: pwr_nrl            (WR_MAX_NRLMAX)
  END TYPE wr_state_c

END MODULE wr_state
