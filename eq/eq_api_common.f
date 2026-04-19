C     eq_api_common.f
C
C     Phase L-2: F77 bridge between the legacy eq COMMON blocks
C     (eqcomm.inc / eqcom0.inc / eqcom1.inc) and the F90 C-ABI layer
C     in eq_api.f90.
C
C     Why a dedicated F77 file?
C     - The eq state lives in F77 COMMON blocks accessed via
C       INCLUDE 'eqcomm.inc'. Pulling those into a F90 MODULE would
C       require invasive refactoring. Instead we expose small
C       SUBROUTINE getters / setters with plain scalar / array
C       arguments; these can be called safely from eq_api.f90.
C     - Keeping the bridge in fixed-form Fortran keeps the existing
C       INCLUDE directives unchanged and avoids case / continuation
C       surprises.
C
C     Naming: EQ_COMMON_* to make it clear these are *not* the public
C     C ABI (eq_init / eq_run / ...), only internal helpers.
C
C     Implicit-typing note: eqcomm.inc pulls in
C         USE plcomm
C         IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
C     so `USE` must be the first executable statement in every
C     SUBROUTINE. All local-argument / local-variable declarations
C     therefore go *after* the INCLUDE line.

C     ------------------------------------------------------------------
C     Query the compile-time grid dimension maxima (PARAMETERs in
C     eqcom0.inc). Exposed so callers can size buffers without having
C     to INCLUDE eqcom0.inc themselves.
C     ------------------------------------------------------------------
      SUBROUTINE EQ_COMMON_GET_GRID_DIMS(NRGM_OUT, NZGM_OUT,
     &                                   NPSM_OUT,
     &                                   NRM_OUT,  NTHM_OUT,
     &                                   NSUM_OUT)
      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      INTEGER NRGM_OUT, NZGM_OUT, NPSM_OUT
      INTEGER NRM_OUT,  NTHM_OUT, NSUM_OUT
      NRGM_OUT = NRGM
      NZGM_OUT = NZGM
      NPSM_OUT = NPSM
      NRM_OUT  = NRM
      NTHM_OUT = NTHM
      NSUM_OUT = NSUM
      RETURN
      END

C     ------------------------------------------------------------------
C     Return the active runtime grid counters (EQPRN2 / EQPRN3).
C     ------------------------------------------------------------------
      SUBROUTINE EQ_COMMON_GET_GRID_COUNTS(NRGMAX_OUT, NZGMAX_OUT,
     &                                     NPSMAX_OUT,
     &                                     NRMAX_OUT,  NTHMAX_OUT,
     &                                     NSUMAX_OUT)
      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      INTEGER NRGMAX_OUT, NZGMAX_OUT, NPSMAX_OUT
      INTEGER NRMAX_OUT,  NTHMAX_OUT, NSUMAX_OUT
      NRGMAX_OUT = NRGMAX
      NZGMAX_OUT = NZGMAX
      NPSMAX_OUT = NPSMAX
      NRMAX_OUT  = NRMAX
      NTHMAX_OUT = NTHMAX
      NSUMAX_OUT = NSUMAX
      RETURN
      END

C     ------------------------------------------------------------------
C     Return the secondary grid counters: NRVMAX (radial / volume),
C     NSGMAX (s grid for ortho-curvilinear PSI(s,t)) and NTGMAX
C     (theta grid). These live in eqcom1_mod alongside NRGMAX etc.
C     and are needed by the Layer 1 baseline metrics for MODELG=3
C     (EQRTSK) loads.
C     ------------------------------------------------------------------
      SUBROUTINE EQ_COMMON_GET_AUX_GRID_COUNTS(NRVMAX_OUT,
     &                                         NSGMAX_OUT,
     &                                         NTGMAX_OUT)
      USE eqcom1_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      INTEGER NRVMAX_OUT, NSGMAX_OUT, NTGMAX_OUT
      NRVMAX_OUT = NRVMAX
      NSGMAX_OUT = NSGMAX
      NTGMAX_OUT = NTGMAX
      RETURN
      END

C     ------------------------------------------------------------------
C     Scalar plasma parameters from EQGLB1 / EQGLB2 / EQGLB4.
C     ------------------------------------------------------------------
      SUBROUTINE EQ_COMMON_GET_SCALARS(RAXIS_OUT, ZAXIS_OUT,
     &                                 PSI0_OUT,  PSIPA_OUT,
     &                                 PSITA_OUT,
     &                                 QAXIS_OUT, QSURF_OUT,
     &                                 BETAT_OUT, BETAP_OUT,
     &                                 PVOL_OUT,  RAAVE_OUT,
     &                                 RIPX_OUT)
      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      REAL*8 RAXIS_OUT, ZAXIS_OUT, PSI0_OUT, PSIPA_OUT, PSITA_OUT
      REAL*8 QAXIS_OUT, QSURF_OUT, BETAT_OUT, BETAP_OUT
      REAL*8 PVOL_OUT,  RAAVE_OUT, RIPX_OUT
      RAXIS_OUT = RAXIS
      ZAXIS_OUT = ZAXIS
      PSI0_OUT  = PSI0
      PSIPA_OUT = PSIPA
      PSITA_OUT = PSITA
      QAXIS_OUT = QAXIS
      QSURF_OUT = QSURF
      BETAT_OUT = BETAT
      BETAP_OUT = BETAP
      PVOL_OUT  = PVOL
      RAAVE_OUT = RAAVE
      RIPX_OUT  = RIPX
      RETURN
      END

C     ------------------------------------------------------------------
C     Copy 1D profile samples (EQOUT2 / EQOUT3) into caller-provided
C     arrays sized at least NCOPY. NCOPY must be <= NPSMAX.
C     ------------------------------------------------------------------
      SUBROUTINE EQ_COMMON_GET_PROFILES_1D(NCOPY,
     &                                     PSIPS_OUT, PPPS_OUT,
     &                                     TTPS_OUT,  QQPS_OUT)
      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      INTEGER NCOPY
      REAL*8  PSIPS_OUT(*), PPPS_OUT(*), TTPS_OUT(*), QQPS_OUT(*)
      INTEGER I, LIMIT
      LIMIT = NCOPY
      IF (LIMIT .GT. NPSMAX) LIMIT = NPSMAX
      DO I = 1, LIMIT
         PSIPS_OUT(I) = PSIPS(I)
         PPPS_OUT(I)  = PPPS(I)
         TTPS_OUT(I)  = TTPS(I)
         QQPS_OUT(I)  = QQPS(I)
      END DO
      RETURN
      END

C     ------------------------------------------------------------------
C     Copy RZ grid coordinates (EQOUT1) into caller-provided arrays
C     sized at least NR_COPY / NZ_COPY. Limited to NRGMAX / NZGMAX.
C     ------------------------------------------------------------------
      SUBROUTINE EQ_COMMON_GET_RZ_GRID(NR_COPY, NZ_COPY,
     &                                 RG_OUT, ZG_OUT)
      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      INTEGER NR_COPY, NZ_COPY
      REAL*8  RG_OUT(*), ZG_OUT(*)
      INTEGER I, LIMR, LIMZ
      LIMR = NR_COPY
      IF (LIMR .GT. NRGMAX) LIMR = NRGMAX
      DO I = 1, LIMR
         RG_OUT(I) = RG(I)
      END DO
      LIMZ = NZ_COPY
      IF (LIMZ .GT. NZGMAX) LIMZ = NZGMAX
      DO I = 1, LIMZ
         ZG_OUT(I) = ZG(I)
      END DO
      RETURN
      END

C     ------------------------------------------------------------------
C     Scalar setter stub (Phase L-2: returns ok=0 unconditionally so
C     callers can exercise the plumbing without disturbing any actual
C     COMMON-block value). The real setter arrives in L-3 together
C     with eq_param_registry.
C     ------------------------------------------------------------------
      SUBROUTINE EQ_COMMON_SET_SCALAR(NAME, VALUE, OK)
      CHARACTER*(*) NAME
      REAL*8 VALUE
      INTEGER OK
C     Suppress unused-argument warnings (no INCLUDE: this routine does
C     not touch eqcomm.inc state).
      IF (LEN(NAME) .LT. 0) OK = 0
      IF (VALUE .NE. VALUE) OK = 0
C     L-2: stub. Real dispatch lands in eq_param_registry.f90 (L-3).
      OK = 0
      RETURN
      END
