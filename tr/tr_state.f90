! tr_state.f90
!
! Phase L-2: C-interoperable state struct for the TR library API.
!
! Mirrors tr_api.h::tr_state_t exactly. Fixed-size arrays per
! docs/superpowers/specs/2026-04-17-tr-library-design.md  Section 4.2.
!
! L-2 scope: type definition only. Population from TRCOMM happens in
! tr_api::tr_get_state during Phase L-3.
!
! Memory layout note:
!   In C, RN[NRMAX][NSMAX] is row-major;
!   in Fortran the matching declaration is RN(NSMAX, NRMAX) (column-major).
!   The two layouts agree byte-for-byte, but only RN(0:nrmax-1, 0:nsmax-1)
!   carry valid runtime data (the rest is padding up to TR_MAX_*).

MODULE tr_state
  USE, INTRINSIC :: ISO_C_BINDING
  IMPLICIT NONE
  PRIVATE
  PUBLIC :: tr_state_c, TR_MAX_NRMAX, TR_MAX_NSMAX

  INTEGER(C_INT), PARAMETER :: TR_MAX_NRMAX = 500
  INTEGER(C_INT), PARAMETER :: TR_MAX_NSMAX = 8

  TYPE, BIND(C) :: tr_state_c
     INTEGER(C_INT)  :: nt
     INTEGER(C_INT)  :: nrmax
     INTEGER(C_INT)  :: nsmax
     REAL(C_DOUBLE)  :: T
     REAL(C_DOUBLE)  :: WPT
     REAL(C_DOUBLE)  :: AJT
     REAL(C_DOUBLE)  :: Q0
     REAL(C_DOUBLE)  :: BETA0
     REAL(C_DOUBLE)  :: BETAP0
     REAL(C_DOUBLE)  :: BETAA
     REAL(C_DOUBLE)  :: BETAN
     REAL(C_DOUBLE)  :: TAUE1
     REAL(C_DOUBLE)  :: TAUE2
     REAL(C_DOUBLE)  :: ZEFF0
     REAL(C_DOUBLE)  :: ALI
     REAL(C_DOUBLE)  :: RQ1
     REAL(C_DOUBLE)  :: RN(TR_MAX_NSMAX, TR_MAX_NRMAX)
     REAL(C_DOUBLE)  :: RT(TR_MAX_NSMAX, TR_MAX_NRMAX)
     REAL(C_DOUBLE)  :: AJ(TR_MAX_NRMAX)
     REAL(C_DOUBLE)  :: QP(TR_MAX_NRMAX)
  END TYPE tr_state_c

END MODULE tr_state
