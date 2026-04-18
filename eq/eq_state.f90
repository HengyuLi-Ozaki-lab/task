! eq_state.f90
!
! Phase L-2: C-interoperable state struct for the EQ library API.
!
! Mirrors eq_api.h::eq_state_t exactly. Fixed-size arrays so the C
! layout is stable regardless of the runtime NRMAX / NTHMAX / NSUMAX
! values.
!
! L-2 scope: type definition only. Population of the struct happens
! through eq_api::eq_get_state, which in turn reads the legacy F77
! COMMON blocks (eqcom0.inc / eqcom1.inc) through the F77 bridge in
! eq_api_common.f. The real registry of settable parameters arrives
! in Phase L-3.
!
! Memory layout note:
!   In C, profile arrays are 1D or row-major; in Fortran they appear
!   1D with matching sizes. Only 1..NRMAX (etc.) carry valid runtime
!   data, the rest is padding up to EQ_MAX_*.

MODULE eq_state
  USE, INTRINSIC :: ISO_C_BINDING
  IMPLICIT NONE
  PRIVATE
  PUBLIC :: eq_state_c, &
            EQ_MAX_NRGM, EQ_MAX_NZGM, EQ_MAX_NPSM, &
            EQ_MAX_NRM,  EQ_MAX_NTHM, EQ_MAX_NSUM

  ! Upper bounds for the C-visible arrays. Chosen small enough to keep
  ! eq_state_t a reasonable size (~MB range) while still covering the
  ! default grids used by eq / pl / ak drivers.
  INTEGER(C_INT), PARAMETER :: EQ_MAX_NRGM = 257
  INTEGER(C_INT), PARAMETER :: EQ_MAX_NZGM = 257
  INTEGER(C_INT), PARAMETER :: EQ_MAX_NPSM = 257
  INTEGER(C_INT), PARAMETER :: EQ_MAX_NRM  = 257
  INTEGER(C_INT), PARAMETER :: EQ_MAX_NTHM = 513
  INTEGER(C_INT), PARAMETER :: EQ_MAX_NSUM = 513

  TYPE, BIND(C) :: eq_state_c
     ! Grid dimensions (mirrors NRGMAX/NZGMAX/NPSMAX/NRMAX/NTHMAX/NSUMAX
     ! in eqcom1.inc EQPRN2/EQPRN3).
     INTEGER(C_INT)  :: nrgmax
     INTEGER(C_INT)  :: nzgmax
     INTEGER(C_INT)  :: npsmax
     INTEGER(C_INT)  :: nrmax
     INTEGER(C_INT)  :: nthmax
     INTEGER(C_INT)  :: nsumax
     ! Global scalars (EQGLB1..EQGLB2).
     REAL(C_DOUBLE)  :: raxis
     REAL(C_DOUBLE)  :: zaxis
     REAL(C_DOUBLE)  :: psi0
     REAL(C_DOUBLE)  :: psipa
     REAL(C_DOUBLE)  :: psita
     REAL(C_DOUBLE)  :: qaxis
     REAL(C_DOUBLE)  :: qsurf
     REAL(C_DOUBLE)  :: betat
     REAL(C_DOUBLE)  :: betap
     REAL(C_DOUBLE)  :: pvol
     REAL(C_DOUBLE)  :: raave
     REAL(C_DOUBLE)  :: ripx
     ! 1D profiles indexed 1..npsmax (EQOUT2/EQOUT3).
     REAL(C_DOUBLE)  :: psips(EQ_MAX_NPSM)
     REAL(C_DOUBLE)  :: ppps(EQ_MAX_NPSM)
     REAL(C_DOUBLE)  :: ttps(EQ_MAX_NPSM)
     REAL(C_DOUBLE)  :: qqps(EQ_MAX_NPSM)
     ! Equilibrium grid samples (EQOUT1).
     REAL(C_DOUBLE)  :: rg(EQ_MAX_NRGM)
     REAL(C_DOUBLE)  :: zg(EQ_MAX_NZGM)
  END TYPE eq_state_c

END MODULE eq_state
