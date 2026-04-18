! ti_state.f90
!
! Phase L-2: C-interoperable state struct for the TI library API.
!
! Mirrors ti_api.h::ti_state_t exactly. Fixed-size arrays so the C
! layout is stable regardless of the runtime nrmax / nsa_max values.
!
! L-2 scope: type definition only. Population from TICOMM happens in
! ti_api::ti_get_state during Phase L-3.
!
! Memory layout note:
!   In C, RNA[NRMAX][NSA_MAX] is row-major;
!   in Fortran the matching declaration is RNA(NSA_MAX, NRMAX) (column-major).
!   The two layouts agree byte-for-byte, but only RNA(0:nsa_max-1, 0:nrmax-1)
!   carry valid runtime data (the rest is padding up to TI_MAX_*).

MODULE ti_state
  USE, INTRINSIC :: ISO_C_BINDING
  IMPLICIT NONE
  PRIVATE
  PUBLIC :: ti_state_c, TI_MAX_NRMAX, TI_MAX_NSA_MAX

  INTEGER(C_INT), PARAMETER :: TI_MAX_NRMAX   = 200
  INTEGER(C_INT), PARAMETER :: TI_MAX_NSA_MAX = 20

  TYPE, BIND(C) :: ti_state_c
     INTEGER(C_INT)  :: nt
     INTEGER(C_INT)  :: nrmax
     INTEGER(C_INT)  :: nsa_max
     INTEGER(C_INT)  :: nsmax
     REAL(C_DOUBLE)  :: T
     REAL(C_DOUBLE)  :: residual_loop_max
     INTEGER(C_INT)  :: icount_loop_max
     INTEGER(C_INT)  :: icount_mat_max
     REAL(C_DOUBLE)  :: RNA(TI_MAX_NSA_MAX, TI_MAX_NRMAX)
     REAL(C_DOUBLE)  :: RTA(TI_MAX_NSA_MAX, TI_MAX_NRMAX)
     REAL(C_DOUBLE)  :: RUA(TI_MAX_NSA_MAX, TI_MAX_NRMAX)
     REAL(C_DOUBLE)  :: RBP(TI_MAX_NRMAX)
     REAL(C_DOUBLE)  :: RQP(TI_MAX_NRMAX)
     REAL(C_DOUBLE)  :: RJP(TI_MAX_NRMAX)
     REAL(C_DOUBLE)  :: ZEFF(TI_MAX_NRMAX)
     REAL(C_DOUBLE)  :: BETA(TI_MAX_NRMAX)
     REAL(C_DOUBLE)  :: BETAP(TI_MAX_NRMAX)
  END TYPE ti_state_c

END MODULE ti_state
