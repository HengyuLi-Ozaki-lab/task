!     ****** Phase 2 submodule unit tests ******
!
!  Verifies each TRCOMM submodule's allocate/deallocate cycle works
!  in isolation (i.e. by calling the submodule routines directly,
!  without going through ALLOCATE_TRCOMM / DEALLOCATE_TRCOMM).
!
!  This catches regressions if future Phase L work changes a single
!  submodule independently and forgets to keep its allocate/deallocate
!  pair consistent.
!
!  STOP code 0 = all tests passed.  STOP code 1 = at least one failure.
!
PROGRAM test_trcomm_submodules
  USE bpsd_kinds, ONLY: rkind
  USE TRCOM0, ONLY: NSMAX, NRMAX, NSZMAX, NSNMAX, &
                    NSTM, NEQM, NEQMAXM, NVM, MWM, MLM, NRMP, NGLF, LDAB, &
                    NSM, NFM
  USE trcomm_const, ONLY: PI, AEE, AME, AMM, VC, RMU0, EPS0, RKEV
  USE trcomm_param, ONLY: RR, RA, BB, DT
  USE trcomm_ctrl,  ONLY: PNSS, NSS, NSV, NNS, NST, NEA, &
                          allocate_trcomm_ctrl, deallocate_trcomm_ctrl
  USE trcomm_mtx,   ONLY: XV, YV, AY, Y, ZV, AZ, Z, AX, X, &
                          allocate_trcomm_mtx, deallocate_trcomm_mtx
  USE trcomm_profile, ONLY: RG, RM, RN, RT, AJ, QP, ETA, &
                            allocate_trcomm_profile, deallocate_trcomm_profile
  USE trcomm_globals, ONLY: SPSCT, ANS0, TS0, WST, PRFVT, &
                            allocate_trcomm_globals, deallocate_trcomm_globals
  IMPLICIT NONE

  INTEGER :: failed_count, total_count

  failed_count = 0
  total_count  = 0

  CALL test_const_constants(failed_count, total_count)
  CALL test_param_inputs(failed_count, total_count)
  CALL test_ctrl_alloc_dealloc(failed_count, total_count)
  CALL test_mtx_alloc_dealloc(failed_count, total_count)
  CALL test_profile_alloc_dealloc(failed_count, total_count)
  CALL test_globals_alloc_dealloc(failed_count, total_count)
  CALL test_ctrl_idempotent(failed_count, total_count)
  CALL test_mtx_idempotent(failed_count, total_count)
  CALL test_profile_idempotent(failed_count, total_count)
  CALL test_globals_idempotent(failed_count, total_count)
  CALL test_ctrl_size_matches_param(failed_count, total_count)
  CALL test_mtx_size_matches_param(failed_count, total_count)
  CALL test_profile_size_matches_param(failed_count, total_count)
  CALL test_globals_size_matches_param(failed_count, total_count)

  IF (failed_count == 0) THEN
     WRITE(6,'(A,I0,A)') 'OK: all ', total_count, ' submodule tests passed'
     STOP 0
  ELSE
     WRITE(6,'(A,I0,A,I0,A)') 'FAIL: ', failed_count, ' of ', &
                              total_count, ' tests failed'
     STOP 1
  END IF

CONTAINS

  !---------------------------------------------------------------------
  !  Setup helper: replicate the size-derivation logic from
  !  ALLOCATE_TRCOMM so each submodule allocate routine has the
  !  TRCOM0 sizing variables it needs.
  !---------------------------------------------------------------------
  SUBROUTINE setup_sizes
    NSMAX  = 2
    NSZMAX = 0
    NSNMAX = 2
    NRMAX  = 50

    ! Same derivations as ALLOCATE_TRCOMM in trcomm.f90
    NEQMAXM = 3 * (NSMAX + NSZMAX + NSNMAX) + 1
    NVM     = NEQMAXM
    MWM     = 4 * NEQMAXM - 1
    MLM     = NEQMAXM * NRMAX
    NRMP    = NRMAX + 1
    NGLF    = NRMAX
    LDAB    = 6 * NEQMAXM
  END SUBROUTINE setup_sizes

  !---------------------------------------------------------------------
  !  trcomm_const: smoke check that physical constants are accessible
  !  and within expected ranges.
  !---------------------------------------------------------------------
  SUBROUTINE test_const_constants(fc, tc)
    INTEGER, INTENT(INOUT) :: fc, tc
    LOGICAL :: ok
    tc = tc + 1
    ok = (PI   > 3.14_rkind .AND. PI   < 3.15_rkind)             .AND. &
         (AEE  > 1.0e-19_rkind .AND. AEE  < 2.0e-19_rkind)       .AND. &
         (AME  > 9.0e-31_rkind .AND. AME  < 1.0e-30_rkind)       .AND. &
         (AMM  > 1.6e-27_rkind .AND. AMM  < 1.7e-27_rkind)       .AND. &
         (VC   > 2.99e8_rkind  .AND. VC   < 3.00e8_rkind)        .AND. &
         (RMU0 > 1.0e-6_rkind  .AND. RMU0 < 2.0e-6_rkind)        .AND. &
         (EPS0 > 8.0e-12_rkind .AND. EPS0 < 9.0e-12_rkind)       .AND. &
         (RKEV > 1.0e-16_rkind .AND. RKEV < 2.0e-16_rkind)
    IF (.NOT. ok) THEN
       fc = fc + 1
       WRITE(6,'(A)') '  FAIL: test_const_constants (value out of range)'
    END IF
  END SUBROUTINE test_const_constants

  !---------------------------------------------------------------------
  !  trcomm_param: smoke check that namelist input variables are
  !  writable scalars (no allocate cycle to verify).
  !---------------------------------------------------------------------
  SUBROUTINE test_param_inputs(fc, tc)
    INTEGER, INTENT(INOUT) :: fc, tc
    REAL(rkind) :: rr_save, ra_save, bb_save, dt_save
    LOGICAL :: ok
    tc = tc + 1
    rr_save = RR ; ra_save = RA ; bb_save = BB ; dt_save = DT
    RR = 3.0_rkind
    RA = 1.2_rkind
    BB = 3.0_rkind
    DT = 0.01_rkind
    ok = (RR == 3.0_rkind) .AND. (RA == 1.2_rkind) .AND. &
         (BB == 3.0_rkind) .AND. (DT == 0.01_rkind)
    IF (.NOT. ok) THEN
       fc = fc + 1
       WRITE(6,'(A)') '  FAIL: test_param_inputs (assignment readback failed)'
    END IF
    RR = rr_save ; RA = ra_save ; BB = bb_save ; DT = dt_save
  END SUBROUTINE test_param_inputs

  !---------------------------------------------------------------------
  !  trcomm_ctrl: allocate / deallocate cycle.
  !---------------------------------------------------------------------
  SUBROUTINE test_ctrl_alloc_dealloc(fc, tc)
    INTEGER, INTENT(INOUT) :: fc, tc
    INTEGER :: ierr
    LOGICAL :: ok_alloc, ok_dealloc
    tc = tc + 1
    CALL setup_sizes
    CALL allocate_trcomm_ctrl(ierr)
    ok_alloc = (ierr == 0)            .AND. &
               ALLOCATED(PNSS)        .AND. &
               ALLOCATED(NSS)         .AND. &
               ALLOCATED(NSV)         .AND. &
               ALLOCATED(NNS)         .AND. &
               ALLOCATED(NST)         .AND. &
               ALLOCATED(NEA)
    IF (.NOT. ok_alloc) THEN
       fc = fc + 1
       WRITE(6,'(A,I0)') '  FAIL: test_ctrl_alloc_dealloc (allocate) ierr=', ierr
       RETURN
    END IF
    CALL deallocate_trcomm_ctrl
    ok_dealloc = (.NOT. ALLOCATED(PNSS)) .AND. &
                 (.NOT. ALLOCATED(NSS )) .AND. &
                 (.NOT. ALLOCATED(NSV )) .AND. &
                 (.NOT. ALLOCATED(NNS )) .AND. &
                 (.NOT. ALLOCATED(NST )) .AND. &
                 (.NOT. ALLOCATED(NEA ))
    IF (.NOT. ok_dealloc) THEN
       fc = fc + 1
       WRITE(6,'(A)') '  FAIL: test_ctrl_alloc_dealloc (deallocate)'
    END IF
  END SUBROUTINE test_ctrl_alloc_dealloc

  !---------------------------------------------------------------------
  !  trcomm_mtx: allocate / deallocate cycle.
  !---------------------------------------------------------------------
  SUBROUTINE test_mtx_alloc_dealloc(fc, tc)
    INTEGER, INTENT(INOUT) :: fc, tc
    INTEGER :: ierr
    LOGICAL :: ok_alloc, ok_dealloc
    tc = tc + 1
    CALL setup_sizes
    CALL allocate_trcomm_mtx(ierr)
    ok_alloc = (ierr == 0)        .AND. &
               ALLOCATED(XV)      .AND. &
               ALLOCATED(YV)      .AND. ALLOCATED(AY) .AND. ALLOCATED(Y) .AND. &
               ALLOCATED(ZV)      .AND. ALLOCATED(AZ) .AND. ALLOCATED(Z) .AND. &
               ALLOCATED(AX)      .AND. ALLOCATED(X)
    IF (.NOT. ok_alloc) THEN
       fc = fc + 1
       WRITE(6,'(A,I0)') '  FAIL: test_mtx_alloc_dealloc (allocate) ierr=', ierr
       RETURN
    END IF
    CALL deallocate_trcomm_mtx
    ok_dealloc = (.NOT. ALLOCATED(XV)) .AND. &
                 (.NOT. ALLOCATED(YV)) .AND. (.NOT. ALLOCATED(AY)) .AND. &
                 (.NOT. ALLOCATED(Y))  .AND. (.NOT. ALLOCATED(ZV)) .AND. &
                 (.NOT. ALLOCATED(AZ)) .AND. (.NOT. ALLOCATED(Z))  .AND. &
                 (.NOT. ALLOCATED(AX)) .AND. (.NOT. ALLOCATED(X))
    IF (.NOT. ok_dealloc) THEN
       fc = fc + 1
       WRITE(6,'(A)') '  FAIL: test_mtx_alloc_dealloc (deallocate)'
    END IF
  END SUBROUTINE test_mtx_alloc_dealloc

  !---------------------------------------------------------------------
  !  trcomm_profile: allocate / deallocate cycle.
  !  Spot-check a handful of representative arrays from each
  !  sub-section (TRVAR / TRSRC / TRCEF / TRADD).
  !---------------------------------------------------------------------
  SUBROUTINE test_profile_alloc_dealloc(fc, tc)
    INTEGER, INTENT(INOUT) :: fc, tc
    INTEGER :: ierr
    LOGICAL :: ok_alloc, ok_dealloc
    tc = tc + 1
    CALL setup_sizes
    CALL allocate_trcomm_profile(ierr)
    ok_alloc = (ierr == 0)       .AND. &
               ALLOCATED(RG)     .AND. ALLOCATED(RM)  .AND. &
               ALLOCATED(RN)     .AND. ALLOCATED(RT)  .AND. &
               ALLOCATED(AJ)     .AND. ALLOCATED(QP)  .AND. &
               ALLOCATED(ETA)
    IF (.NOT. ok_alloc) THEN
       fc = fc + 1
       WRITE(6,'(A,I0)') '  FAIL: test_profile_alloc_dealloc (allocate) ierr=', ierr
       RETURN
    END IF
    CALL deallocate_trcomm_profile
    ok_dealloc = (.NOT. ALLOCATED(RG))  .AND. (.NOT. ALLOCATED(RM)) .AND. &
                 (.NOT. ALLOCATED(RN))  .AND. (.NOT. ALLOCATED(RT)) .AND. &
                 (.NOT. ALLOCATED(AJ))  .AND. (.NOT. ALLOCATED(QP)) .AND. &
                 (.NOT. ALLOCATED(ETA))
    IF (.NOT. ok_dealloc) THEN
       fc = fc + 1
       WRITE(6,'(A)') '  FAIL: test_profile_alloc_dealloc (deallocate)'
    END IF
  END SUBROUTINE test_profile_alloc_dealloc

  !---------------------------------------------------------------------
  !  trcomm_globals: allocate / deallocate cycle.
  !---------------------------------------------------------------------
  SUBROUTINE test_globals_alloc_dealloc(fc, tc)
    INTEGER, INTENT(INOUT) :: fc, tc
    INTEGER :: ierr
    LOGICAL :: ok_alloc, ok_dealloc
    tc = tc + 1
    CALL setup_sizes
    CALL allocate_trcomm_globals(ierr)
    ok_alloc = (ierr == 0)         .AND. &
               ALLOCATED(SPSCT)    .AND. &
               ALLOCATED(ANS0)     .AND. &
               ALLOCATED(TS0)      .AND. &
               ALLOCATED(WST)      .AND. &
               ALLOCATED(PRFVT)
    IF (.NOT. ok_alloc) THEN
       fc = fc + 1
       WRITE(6,'(A,I0)') '  FAIL: test_globals_alloc_dealloc (allocate) ierr=', ierr
       RETURN
    END IF
    CALL deallocate_trcomm_globals
    ok_dealloc = (.NOT. ALLOCATED(SPSCT)) .AND. &
                 (.NOT. ALLOCATED(ANS0))  .AND. &
                 (.NOT. ALLOCATED(TS0))   .AND. &
                 (.NOT. ALLOCATED(WST))   .AND. &
                 (.NOT. ALLOCATED(PRFVT))
    IF (.NOT. ok_dealloc) THEN
       fc = fc + 1
       WRITE(6,'(A)') '  FAIL: test_globals_alloc_dealloc (deallocate)'
    END IF
  END SUBROUTINE test_globals_alloc_dealloc

  !---------------------------------------------------------------------
  !  Idempotency: cycle allocate/deallocate 3 times for each submodule.
  !  Final state must be deallocated; no run-time crash is the
  !  primary success criterion (gfortran with -fcheck=all would
  !  abort if double-free or use-after-free occurred).
  !---------------------------------------------------------------------
  SUBROUTINE test_ctrl_idempotent(fc, tc)
    INTEGER, INTENT(INOUT) :: fc, tc
    INTEGER :: ierr, k
    tc = tc + 1
    CALL setup_sizes
    DO k = 1, 3
       CALL allocate_trcomm_ctrl(ierr)
       IF (ierr /= 0) THEN
          fc = fc + 1
          WRITE(6,'(A,I0,A,I0)') '  FAIL: test_ctrl_idempotent cycle=', k, ' ierr=', ierr
          RETURN
       END IF
       CALL deallocate_trcomm_ctrl
    END DO
    IF (ALLOCATED(PNSS)) THEN
       fc = fc + 1
       WRITE(6,'(A)') '  FAIL: test_ctrl_idempotent (PNSS still allocated)'
    END IF
  END SUBROUTINE test_ctrl_idempotent

  SUBROUTINE test_mtx_idempotent(fc, tc)
    INTEGER, INTENT(INOUT) :: fc, tc
    INTEGER :: ierr, k
    tc = tc + 1
    CALL setup_sizes
    DO k = 1, 3
       CALL allocate_trcomm_mtx(ierr)
       IF (ierr /= 0) THEN
          fc = fc + 1
          WRITE(6,'(A,I0,A,I0)') '  FAIL: test_mtx_idempotent cycle=', k, ' ierr=', ierr
          RETURN
       END IF
       CALL deallocate_trcomm_mtx
    END DO
    IF (ALLOCATED(XV)) THEN
       fc = fc + 1
       WRITE(6,'(A)') '  FAIL: test_mtx_idempotent (XV still allocated)'
    END IF
  END SUBROUTINE test_mtx_idempotent

  SUBROUTINE test_profile_idempotent(fc, tc)
    INTEGER, INTENT(INOUT) :: fc, tc
    INTEGER :: ierr, k
    tc = tc + 1
    CALL setup_sizes
    DO k = 1, 3
       CALL allocate_trcomm_profile(ierr)
       IF (ierr /= 0) THEN
          fc = fc + 1
          WRITE(6,'(A,I0,A,I0)') '  FAIL: test_profile_idempotent cycle=', k, ' ierr=', ierr
          RETURN
       END IF
       CALL deallocate_trcomm_profile
    END DO
    IF (ALLOCATED(RG)) THEN
       fc = fc + 1
       WRITE(6,'(A)') '  FAIL: test_profile_idempotent (RG still allocated)'
    END IF
  END SUBROUTINE test_profile_idempotent

  SUBROUTINE test_globals_idempotent(fc, tc)
    INTEGER, INTENT(INOUT) :: fc, tc
    INTEGER :: ierr, k
    tc = tc + 1
    CALL setup_sizes
    DO k = 1, 3
       CALL allocate_trcomm_globals(ierr)
       IF (ierr /= 0) THEN
          fc = fc + 1
          WRITE(6,'(A,I0,A,I0)') '  FAIL: test_globals_idempotent cycle=', k, ' ierr=', ierr
          RETURN
       END IF
       CALL deallocate_trcomm_globals
    END DO
    IF (ALLOCATED(SPSCT)) THEN
       fc = fc + 1
       WRITE(6,'(A)') '  FAIL: test_globals_idempotent (SPSCT still allocated)'
    END IF
  END SUBROUTINE test_globals_idempotent

  !---------------------------------------------------------------------
  !  Shape checks: verify that allocated arrays have the expected
  !  extents based on the sizing variables in trcom0.
  !---------------------------------------------------------------------
  SUBROUTINE test_ctrl_size_matches_param(fc, tc)
    INTEGER, INTENT(INOUT) :: fc, tc
    INTEGER :: ierr
    LOGICAL :: ok
    tc = tc + 1
    CALL setup_sizes
    CALL allocate_trcomm_ctrl(ierr)
    IF (ierr /= 0) THEN
       fc = fc + 1
       WRITE(6,'(A,I0)') '  FAIL: test_ctrl_size_matches_param (allocate) ierr=', ierr
       RETURN
    END IF
    ok = (SIZE(PNSS) == NSTM)              .AND. &
         (SIZE(NSS)  == NEQMAXM)           .AND. &
         (SIZE(NSV)  == NEQMAXM)           .AND. &
         (SIZE(NNS)  == NEQMAXM)           .AND. &
         (SIZE(NST)  == NEQMAXM)           .AND. &
         (SIZE(NEA,1) == NSTM + 1)         .AND. &
         (SIZE(NEA,2) == 4)
    IF (.NOT. ok) THEN
       fc = fc + 1
       WRITE(6,'(A)') '  FAIL: test_ctrl_size_matches_param (shape mismatch)'
    END IF
    CALL deallocate_trcomm_ctrl
  END SUBROUTINE test_ctrl_size_matches_param

  SUBROUTINE test_mtx_size_matches_param(fc, tc)
    INTEGER, INTENT(INOUT) :: fc, tc
    INTEGER :: ierr
    LOGICAL :: ok
    tc = tc + 1
    CALL setup_sizes
    CALL allocate_trcomm_mtx(ierr)
    IF (ierr /= 0) THEN
       fc = fc + 1
       WRITE(6,'(A,I0)') '  FAIL: test_mtx_size_matches_param (allocate) ierr=', ierr
       RETURN
    END IF
    ok = (SIZE(XV,1) == NEQMAXM) .AND. (SIZE(XV,2) == NRMAX) .AND. &
         (SIZE(YV,1) == NFM)     .AND. (SIZE(YV,2) == NRMAX) .AND. &
         (SIZE(ZV,1) == NSM)     .AND. (SIZE(ZV,2) == NRMAX) .AND. &
         (SIZE(AX,1) == 6*NEQMAXM) .AND. (SIZE(AX,2) == NEQMAXM*NRMAX) .AND. &
         (SIZE(X)    == NEQMAXM*NRMAX)
    IF (.NOT. ok) THEN
       fc = fc + 1
       WRITE(6,'(A)') '  FAIL: test_mtx_size_matches_param (shape mismatch)'
    END IF
    CALL deallocate_trcomm_mtx
  END SUBROUTINE test_mtx_size_matches_param

  SUBROUTINE test_profile_size_matches_param(fc, tc)
    INTEGER, INTENT(INOUT) :: fc, tc
    INTEGER :: ierr
    LOGICAL :: ok
    tc = tc + 1
    CALL setup_sizes
    CALL allocate_trcomm_profile(ierr)
    IF (ierr /= 0) THEN
       fc = fc + 1
       WRITE(6,'(A,I0)') '  FAIL: test_profile_size_matches_param (allocate) ierr=', ierr
       RETURN
    END IF
    ok = (SIZE(RG)   == NRMAX) .AND. &
         (SIZE(RM)   == NRMAX) .AND. &
         (SIZE(RN,1) == NRMAX) .AND. (SIZE(RN,2) == NSTM) .AND. &
         (SIZE(RT,1) == NRMAX) .AND. (SIZE(RT,2) == NSTM) .AND. &
         (SIZE(AJ)   == NRMAX) .AND. &
         (SIZE(QP)   == NRMAX) .AND. &
         (SIZE(ETA)  == NRMAX)
    IF (.NOT. ok) THEN
       fc = fc + 1
       WRITE(6,'(A)') '  FAIL: test_profile_size_matches_param (shape mismatch)'
    END IF
    CALL deallocate_trcomm_profile
  END SUBROUTINE test_profile_size_matches_param

  SUBROUTINE test_globals_size_matches_param(fc, tc)
    INTEGER, INTENT(INOUT) :: fc, tc
    INTEGER :: ierr
    LOGICAL :: ok
    tc = tc + 1
    CALL setup_sizes
    CALL allocate_trcomm_globals(ierr)
    IF (ierr /= 0) THEN
       fc = fc + 1
       WRITE(6,'(A,I0)') '  FAIL: test_globals_size_matches_param (allocate) ierr=', ierr
       RETURN
    END IF
    ok = (SIZE(SPSCT)   == NSM)  .AND. &
         (SIZE(ANS0)    == NSTM) .AND. &
         (SIZE(TS0)     == NSTM) .AND. &
         (SIZE(WST)     == NSTM) .AND. &
         (SIZE(PRFVT,1) == NSTM) .AND. (SIZE(PRFVT,2) == 3)
    IF (.NOT. ok) THEN
       fc = fc + 1
       WRITE(6,'(A)') '  FAIL: test_globals_size_matches_param (shape mismatch)'
    END IF
    CALL deallocate_trcomm_globals
  END SUBROUTINE test_globals_size_matches_param

END PROGRAM test_trcomm_submodules
