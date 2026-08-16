! trcomm_nf.f90
!
! State for the multi-reaction fusion path ported from trx (P1 Task 6).
!
! This module is deliberately separate from trcomm_profile so that the whole
! new-path state is one reviewable, removable unit and the dense allocate
! routine that serves the legacy MDLNF path is left untouched.
!
! Most of this is sized by `nnfmax`, which trcomm_ctrl defaults to 0, so at
! model_pnf = 0 those arrays come out zero-size.  The two _NSNR roll-ups are
! the exception: they are (NSTM,NRMAX) unconditionally and take real heap on
! every run.  No legacy behaviour changes either way -- nothing outside
! trpnf_multi reads any symbol declared here -- but the allocation is not
! free and it shifts every address allocated after it.
!
! Naming follows trx's own convention: the trailing `_NSNNFNR` / `_NNFNR` /
! `_NSNR` records the rank so the new arrays never collide with the legacy
! 1-D profiles of the same physical quantity (SNF, PNF, ...).
!
! One deliberate deviation from trx: trx keeps the name `TAUF` for its 2-D
! (NNFMAX,NRMAX) slowing-down time, which collides with tr's legacy 1-D
! TAUF(NRMAX) written by TRNFDT.  Here the new-path array is TAUF_NNFNR,
! matching the suffix convention trx applied to all its other fusion arrays
! but not to this one.

MODULE trcomm_nf

  USE TRCOM0, ONLY: rkind
  IMPLICIT NONE
  PUBLIC

  ! --- per-reaction caches, resolved once by tr_prep_pnf (nnfmax) ---
  INTEGER, DIMENSION(:), ALLOCATABLE :: &
       ns1_nnf, ns2_nnf, nsp_nnf
  REAL(rkind), DIMENSION(:), ALLOCATABLE :: &
       wgt_nnf, eng_nnf, enn_nnf

  ! --- (species, reaction, radius) ---
  REAL(rkind), DIMENSION(:,:,:), ALLOCATABLE :: &
       SNF_NSNNFNR, PNF_NSNNFNR, PNFCL_NSNNFNR

  ! --- (reaction, radius) ---
  REAL(rkind), DIMENSION(:,:), ALLOCATABLE :: &
       SNFNN_NNFNR, PNFNN_NNFNR, TAUF_NNFNR

  ! --- (species, radius) roll-ups consumed downstream ---
  REAL(rkind), DIMENSION(:,:), ALLOCATABLE :: &
       SNF_NSNR, PNFCL_NSNR

  ! --- dispatch guard (P1 Task 5 review, finding M8) ---
  !
  ! model_pnf > 0 is NOT sufficient to prove the new path is usable: the
  ! ported libnf returns a plausible-looking sigmav_nf even when its tables
  ! were never initialised, where upstream would have aborted.  A caller
  ! that gated only on model_pnf would therefore silently consume numbers
  ! from an uninitialised table.  tr_prep_pnf sets this .TRUE. as its last
  ! action; trcalc requires it before dispatching to tr_pnf.
  LOGICAL :: nf_multi_ready = .FALSE.

CONTAINS

  ! Idempotent and self-resizing.
  !
  ! ALLOCATE_TRCOMM guards itself with "have nrmax/nsmax/nszmax/nsnmax
  ! changed?" and returns early when they have not.  nnfmax is not in that
  ! set and moves independently of it -- set_usigmav_nf derives it from
  ! model_pnf -- so a caller can legitimately change nnfmax while every
  ! dimension the guard watches stays put, and these arrays would keep a
  ! stale size.  Checking our own sizes here makes that safe no matter how
  ! we are reached, so tr_prep can also call it directly after the guard.
  SUBROUTINE allocate_trcomm_nf(ierr)
    USE TRCOM0, ONLY: NRMAX, NSTM
    USE trcomm_ctrl, ONLY: nnfmax
    INTEGER, INTENT(OUT) :: ierr
    ierr = 0

    ! All three ALLOCATED tests are needed, not just the first: an earlier call
    ! can fail between the two ALLOCATEs and RETURN, and tr_prep's direct
    ! call does not clean up on failure the way ALLOCATE_TRCOMM's GOTO 900
    ! path does.  SIZE() of an unallocated allocatable is undefined.  SNF_NSNR
    ! is the last array allocated, so testing it is what proves the previous
    ! attempt ran to completion; ns1_nnf and SNF_NSNNFNR alone would early-
    ! return on a run that failed at TAUF_NNFNR, leaving tr_pnf to write an
    ! unallocated SNF_NSNR.  The caller cleanups are the primary defence;
    ! this is defence in depth.
    IF(ALLOCATED(ns1_nnf) .AND. ALLOCATED(SNF_NSNNFNR) .AND. &
       ALLOCATED(SNF_NSNR)) THEN
       IF(SIZE(ns1_nnf) == nnfmax .AND. &
          SIZE(SNF_NSNNFNR,1) == NSTM .AND. &
          SIZE(SNF_NSNNFNR,2) == nnfmax .AND. &
          SIZE(SNF_NSNNFNR,3) == NRMAX) RETURN
    END IF
    CALL deallocate_trcomm_nf

    ! At nnfmax == 0 (model_pnf == 0) the nnfmax-sized arrays below come out
    ! zero-size -- allocated, so ALLOCATED() guards and whole-array
    ! assignments stay well defined, but iterated over zero times.
    !
    ! The last ALLOCATE is NOT one of them: SNF_NSNR and PNFCL_NSNR are
    ! (NSTM,NRMAX) with no nnfmax dependence, so they take real heap on
    ! every run -- 6.4 KB at NRMAX=50 -- and every allocation issued after
    ! this routine lands at a different address than it did before Task 6.
    ! That is why the bit-exactness evidence for the legacy path has to be a
    ! measurement and not an argument, and why the measurement has to be
    ! repeated on Linux: the hazard it must exclude is glibc handing back a
    ! just-freed chunk, which the macOS allocator does not reproduce.
    ALLOCATE(ns1_nnf(nnfmax),ns2_nnf(nnfmax),nsp_nnf(nnfmax),STAT=ierr)
      IF(ierr /= 0) RETURN
    ALLOCATE(wgt_nnf(nnfmax),eng_nnf(nnfmax),enn_nnf(nnfmax),STAT=ierr)
      IF(ierr /= 0) RETURN
    ALLOCATE(SNF_NSNNFNR(NSTM,nnfmax,NRMAX),STAT=ierr)
      IF(ierr /= 0) RETURN
    ALLOCATE(PNF_NSNNFNR(NSTM,nnfmax,NRMAX),STAT=ierr)
      IF(ierr /= 0) RETURN
    ALLOCATE(PNFCL_NSNNFNR(NSTM,nnfmax,NRMAX),STAT=ierr)
      IF(ierr /= 0) RETURN
    ALLOCATE(SNFNN_NNFNR(nnfmax,NRMAX),PNFNN_NNFNR(nnfmax,NRMAX),STAT=ierr)
      IF(ierr /= 0) RETURN
    ALLOCATE(TAUF_NNFNR(nnfmax,NRMAX),STAT=ierr)
      IF(ierr /= 0) RETURN
    ALLOCATE(SNF_NSNR(NSTM,NRMAX),PNFCL_NSNR(NSTM,NRMAX),STAT=ierr)
      IF(ierr /= 0) RETURN

    ! Zero-init for the same reason trcomm_profile zero-inits BP/RDP/RPSI:
    ! after a finalize+init cycle glibc can hand back the chunk the previous
    ! run just freed, so "fresh" memory holds the old run's values.
    ns1_nnf(:) = 0;      ns2_nnf(:) = 0;      nsp_nnf(:) = 0
    wgt_nnf(:) = 0.D0;   eng_nnf(:) = 0.D0;   enn_nnf(:) = 0.D0
    SNF_NSNNFNR(:,:,:)   = 0.D0
    PNF_NSNNFNR(:,:,:)   = 0.D0
    PNFCL_NSNNFNR(:,:,:) = 0.D0
    SNFNN_NNFNR(:,:)     = 0.D0
    PNFNN_NNFNR(:,:)     = 0.D0
    TAUF_NNFNR(:,:)      = 0.D0
    SNF_NSNR(:,:)        = 0.D0
    PNFCL_NSNR(:,:)      = 0.D0

    ! Not ready until tr_prep_pnf has resolved the reaction tables.
    nf_multi_ready = .FALSE.

    RETURN
  END SUBROUTINE allocate_trcomm_nf

  ! Delegates to the guarded form.  The sibling submodules issue bare
  ! DEALLOCATEs here and rely on ALLOCATE_TRCOMM's PNSS sentinel to prove
  ! they ran; this module cannot borrow that proof, because it is also
  ! reached from allocate_trcomm_nf's own resize path and from tr_prep.
  SUBROUTINE deallocate_trcomm_nf
    CALL deallocate_err_trcomm_nf
    RETURN
  END SUBROUTINE deallocate_trcomm_nf

  ! Tolerates any subset being allocated: allocate_trcomm_nf can RETURN
  ! mid-way on an allocation failure, and this is also the resize path.
  SUBROUTINE deallocate_err_trcomm_nf
    nf_multi_ready = .FALSE.
    IF(ALLOCATED(ns1_nnf      )) DEALLOCATE(ns1_nnf      )
    IF(ALLOCATED(ns2_nnf      )) DEALLOCATE(ns2_nnf      )
    IF(ALLOCATED(nsp_nnf      )) DEALLOCATE(nsp_nnf      )
    IF(ALLOCATED(wgt_nnf      )) DEALLOCATE(wgt_nnf      )
    IF(ALLOCATED(eng_nnf      )) DEALLOCATE(eng_nnf      )
    IF(ALLOCATED(enn_nnf      )) DEALLOCATE(enn_nnf      )
    IF(ALLOCATED(SNF_NSNNFNR  )) DEALLOCATE(SNF_NSNNFNR  )
    IF(ALLOCATED(PNF_NSNNFNR  )) DEALLOCATE(PNF_NSNNFNR  )
    IF(ALLOCATED(PNFCL_NSNNFNR)) DEALLOCATE(PNFCL_NSNNFNR)
    IF(ALLOCATED(SNFNN_NNFNR  )) DEALLOCATE(SNFNN_NNFNR  )
    IF(ALLOCATED(PNFNN_NNFNR  )) DEALLOCATE(PNFNN_NNFNR  )
    IF(ALLOCATED(TAUF_NNFNR   )) DEALLOCATE(TAUF_NNFNR   )
    IF(ALLOCATED(SNF_NSNR     )) DEALLOCATE(SNF_NSNR     )
    IF(ALLOCATED(PNFCL_NSNR   )) DEALLOCATE(PNFCL_NSNR   )
    RETURN
  END SUBROUTINE deallocate_err_trcomm_nf

END MODULE trcomm_nf
