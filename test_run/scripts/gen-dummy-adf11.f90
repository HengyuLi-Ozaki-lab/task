!
! Generate a structurally valid but synthetic ADF11-bin.data file.
!
! Why this exists:
!   The real ADAS data files are licensed and not redistributed in this
!   repo. ti_ar / ti_w regression tests only need an input that is
!   STRUCTURALLY valid (so LOAD_ADF11_bin succeeds and CALC_ADF11
!   returns finite values via SPL2DF) and STABLE across runs (so the
!   regression dump is bit-reproducible). Physical accuracy is not
!   required for the equivalence-test contract -- both the Fortran main
!   and libtiapi.so consume the same file and must produce identical
!   metrics.
!
! What it writes:
!   One ADF11-bin.data file containing 8 (Z, ICLASS) entries:
!     - Z=18 (Argon)  : ICLASS = 1 (acd), 2 (scd), 4 (prb), 8 (plt)
!     - Z=74 (Tungsten): same 4 classes
!   Each entry uses IDMAX=5 density points (log10(n) in 10..15) and
!   ITMAX=5 temperature points (log10(T) in -1..4 ; i.e. 0.1 eV..10 keV).
!   Charge-state coverage matches NZMIN_NS..NZMAX_NS in the test inputs
!   (Ar: 15..18, W: 20..45) so the file stays small (~400 KB) yet no
!   out-of-bounds clamp is needed inside CALC_ADF11 for the test runs.
!   DRCOFA is filled by a deterministic smooth analytic formula and
!   UDRCOFA is filled by the standard 2D natural-spline initializer
!   (libspl2d::SPL2D, identical to lib-adf11's READ_ADF11 path).
!
! Build (standalone in test_run/scripts/):
!   See test_run/scripts/Makefile.
!
PROGRAM gen_dummy_adf11

  USE ADF11
  USE libspl2d
  USE libfio
  IMPLICIT NONE

  INTEGER, PARAMETER :: NZS = 2     ! number of elements (Ar, W)
  INTEGER, PARAMETER :: NCLS = 4    ! 4 classes per element (acd, scd, prb, plt)
  INTEGER, PARAMETER :: NDMAX_LOC = NZS * NCLS  ! 8 entries
  INTEGER, PARAMETER :: IDMAX_LOC = 5
  INTEGER, PARAMETER :: ITMAX_LOC = 5

  INTEGER, DIMENSION(NZS),  PARAMETER :: IZ0_TBL  = (/ 18, 74 /)
  INTEGER, DIMENSION(NCLS), PARAMETER :: ICL_TBL  = (/ 1, 2, 4, 8 /)
  CHARACTER(LEN=3), DIMENSION(NCLS), PARAMETER :: ICL_NAME = &
       (/ 'acd', 'scd', 'prb', 'plt' /)
  ! Charge-state range per element. Chosen to cover the NZMIN_NS .. NZMAX_NS
  ! ranges in test_run/inputs/ti_ar.in (15..18) and ti_w.in (20..45) without
  ! over-allocating the dense 5D UDRCOFA table to all 75 W charge states.
  INTEGER, DIMENSION(NZS), PARAMETER :: IZMIN_TBL = (/ 15, 20 /)
  INTEGER, DIMENSION(NZS), PARAMETER :: IZMAX_TBL = (/ 18, 45 /)

  INTEGER :: ND, IZ, IC, ID, IT, IS, ISMAX_LOC
  INTEGER :: IERR
  REAL(dp) :: LOGN_LO, LOGN_HI, LOGT_LO, LOGT_HI
  REAL(dp), ALLOCATABLE :: DDENSL(:), DTEMPL(:), DRCOFL(:,:)
  REAL(dp), ALLOCATABLE :: FX(:,:), FY(:,:), FXY(:,:)
  REAL(dp), ALLOCATABLE :: U_LOC(:,:,:,:)
  CHARACTER(LEN=256) :: KFNAME
  CHARACTER(LEN=*), PARAMETER :: OUT_FILE = 'ADF11-bin.data'

  ! --- 1. Set module-level dimensions ---
  ! ISMAX = max(IZTOTA over all entries) where IZTOTA = NZMAX-NZMIN+1.
  ! NDMAX/IDMAX/ITMAX are scalar dimensions used by LOAD_ADF11_bin's ALLOCATE.
  ISMAX_LOC = MAXVAL(IZMAX_TBL - IZMIN_TBL + 1)   ! e.g. W: 45-20+1 = 26
  NDMAX = NDMAX_LOC
  ISMAX = ISMAX_LOC
  IDMAX = IDMAX_LOC
  ITMAX = ITMAX_LOC

  LOGN_LO = 10.0_dp   ! cm^-3 (log10)
  LOGN_HI = 15.0_dp
  LOGT_LO = -1.0_dp   ! eV (log10), 0.1 eV .. 10 keV
  LOGT_HI =  4.0_dp

  ! --- 2. Allocate module arrays ---
  ALLOCATE(IZ0A(NDMAX), IM0A(NDMAX), ICLASSA(NDMAX), KFNAMA(NDMAX))
  ALLOCATE(IDMAXA(NDMAX), ITMAXA(NDMAX), IZTOTA(NDMAX))
  ALLOCATE(IZMINA(NDMAX), IZMAXA(NDMAX))
  ALLOCATE(DDENSA(IDMAX, NDMAX))
  ALLOCATE(DTEMPA(ITMAX, NDMAX))
  ALLOCATE(DRCOFA(IDMAX, ITMAX, ISMAX, NDMAX))
  ALLOCATE(UDRCOFA(4, 4, IDMAX, ITMAX, ISMAX, NDMAX))

  DRCOFA  = 0.0_dp
  UDRCOFA = 0.0_dp

  ! Local spline workspace (one (ND,IS) slice at a time).
  ALLOCATE(DDENSL(IDMAX), DTEMPL(ITMAX))
  ALLOCATE(DRCOFL(IDMAX, ITMAX))
  ALLOCATE(FX(IDMAX, ITMAX), FY(IDMAX, ITMAX), FXY(IDMAX, ITMAX))
  ALLOCATE(U_LOC(4, 4, IDMAX, ITMAX))

  ! --- 3. Fill each (Z, class) entry ---
  ND = 0
  DO IZ = 1, NZS
     DO IC = 1, NCLS
        ND = ND + 1
        IZ0A(ND)    = IZ0_TBL(IZ)
        IM0A(ND)    = 0
        ICLASSA(ND) = ICL_TBL(IC)
        IZMINA(ND)  = IZMIN_TBL(IZ)
        IZMAXA(ND)  = IZMAX_TBL(IZ)
        IZTOTA(ND)  = IZMAX_TBL(IZ) - IZMIN_TBL(IZ) + 1
        IDMAXA(ND)  = IDMAX_LOC
        ITMAXA(ND)  = ITMAX_LOC

        WRITE(KFNAME,'(A,I0,A,A,A)') &
             'dummy_z', IZ0_TBL(IZ), '_', ICL_NAME(IC), '.dat'
        KFNAMA(ND) = KFNAME

        ! Density grid: equispaced in log10(n_cm-3).
        DO ID = 1, IDMAX_LOC
           DDENSA(ID, ND) = LOGN_LO &
                + (LOGN_HI - LOGN_LO) * REAL(ID - 1, dp) &
                  / REAL(IDMAX_LOC - 1, dp)
        END DO
        ! Temperature grid: equispaced in log10(T_eV).
        DO IT = 1, ITMAX_LOC
           DTEMPA(IT, ND) = LOGT_LO &
                + (LOGT_HI - LOGT_LO) * REAL(IT - 1, dp) &
                  / REAL(ITMAX_LOC - 1, dp)
        END DO

        ! Rate-coefficient surface (log10 cm^3 s^-1) for every charge
        ! state IS=1..IZTOTA. The formula is smooth, finite, and
        ! deterministic. CALC_ADF11 adds +14 to convert log10[cm3/s]
        ! -> log10[m-3/s] (the physically dimensioned value the rest
        ! of ti expects), so values around -15 produce sensible
        ! magnitudes around 10^-1 m-3/s after the offset.
        DO IS = 1, IZTOTA(ND)
           DO IT = 1, ITMAX_LOC
              DO ID = 1, IDMAX_LOC
                 DRCOFA(ID, IT, IS, ND) = &
                      -15.0_dp &
                      + 0.5_dp * DTEMPA(IT, ND) &
                      - 0.3_dp * (DDENSA(ID, ND) - 13.0_dp) &
                      + 0.01_dp * REAL(IS - 1, dp) &
                      + 0.05_dp * REAL(ICLASSA(ND), dp)
              END DO
           END DO
        END DO

        ! 2D spline init for every charge state. Mirrors READ_ADF11's
        ! natural-BC choice (IDX=3, IDY=3 with FX/FY/FXY at the four
        ! edges set to zero). UDRCOFA is the spline coefficient table
        ! consumed by CALC_ADF11's SPL2DF call.
        DDENSL = DDENSA(1:IDMAX_LOC, ND)
        DTEMPL = DTEMPA(1:ITMAX_LOC, ND)
        DO IS = 1, IZTOTA(ND)
           FX  = 0.0_dp
           FY  = 0.0_dp
           FXY = 0.0_dp
           DRCOFL = DRCOFA(1:IDMAX_LOC, 1:ITMAX_LOC, IS, ND)
           CALL SPL2D(DDENSL, DTEMPL, DRCOFL, &
                      FX, FY, FXY, U_LOC, &
                      IDMAX_LOC, IDMAX_LOC, ITMAX_LOC, 3, 3, IERR)
           IF (IERR /= 0) THEN
              WRITE(6,*) 'XX gen-dummy-adf11: SPL2D failed: IERR=', IERR, &
                   ' ND=', ND, ' IS=', IS
              STOP 1
           END IF
           UDRCOFA(1:4, 1:4, 1:IDMAX_LOC, 1:ITMAX_LOC, IS, ND) = &
                U_LOC(1:4, 1:4, 1:IDMAX_LOC, 1:ITMAX_LOC)
        END DO
     END DO
  END DO

  ! --- 4. Write the binary using the canonical lib-adf11 routine. ---
  ! SAVE_ADF11_bin is the inverse of LOAD_ADF11_bin so any future
  ! layout change in lib-adf11 is automatically picked up here.
  CALL SAVE_ADF11_bin(OUT_FILE, IERR)
  IF (IERR /= 0) THEN
     WRITE(6,*) 'XX gen-dummy-adf11: SAVE_ADF11_bin failed: IERR=', IERR
     STOP 2
  END IF

  WRITE(6,'(A,I0,A)') 'OK: dummy ADF11-bin.data written (', NDMAX, ' entries)'
  WRITE(6,'(A,A)') '  -> ', OUT_FILE

  ! --- 5. Cleanup ---
  DEALLOCATE(DDENSL, DTEMPL, DRCOFL, FX, FY, FXY, U_LOC)
  DEALLOCATE(IZ0A, IM0A, ICLASSA, KFNAMA)
  DEALLOCATE(IDMAXA, ITMAXA, IZTOTA, IZMINA, IZMAXA)
  DEALLOCATE(DDENSA, DTEMPA, DRCOFA, UDRCOFA)

  STOP 0
END PROGRAM gen_dummy_adf11
