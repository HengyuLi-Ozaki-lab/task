! trpnf_multi.f90
!
! Multi-reaction fusion source, ported from trx/trpnf.f90 (P1 Task 6).
!
! FILE/MODULE NAMING: trx calls this `MODULE trpnf` in `trx/trpnf.f90`, but
! tr already has a `tr/trpnf.f90` -- a bare-externals file holding the legacy
! TRNFDT / SIGMAM / SIGMAB / TRNFDHe3.  Both would compile to `trpnf.o` in the
! same object directory, so the port lands here as `trpnf_multi`.
!
! SCOPE: this ports the reaction-source half of trx's tr_pnf.  The
! slowing-down half (TAUF/WF/VC3) is deliberately NOT ported -- see the
! comment at the end of tr_pnf for the blocker and the evidence.
!
! STAGING: this path is additive.  trcalc keeps calling the legacy MDLNF
! block unchanged and calls tr_pnf afterwards, writing only trcomm_nf arrays
! that nothing else reads yet.  The legacy result is therefore bit-exact.
!
! NOT YET CORRECT PHYSICS FOR EVERY CHANNEL -- a Task 7 prerequisite, recorded
! here so validation starts from the right baseline.
!
! libnf indexes species through plcomm's NS_e..NS_He5.  trx resolves those
! against the run's composition in trx/trprep.f90's tr_prep_ns (zero them,
! then walk NS=1..NSMAX matching charge and mass), so an absent species comes
! out 0 and libnf's presence check refuses the run.  tr has no counterpart:
! NS_* keep pl/plinit.f90's defaults of 1..7 always, and nothing in tr/ or
! pl/ revises them.  So libnf's presence check can never fire here -- ierr_nf=3
! is unreachable and the reaction set is never validated against the
! composition.
!
! Which channels that actually breaks is narrower than it sounds.  Measured on
! tr_iter01 (e,D,T,He4) at model_pnf=4, PT=20 keV, dumping every slice of
! SNF_NSNNFNR:
!
!   slot            ns1  ns2  nsp   verdict
!   1  dt           D    T    He4   correct
!   2  dd1          D    D    T     correct
!   3  dd2          D    D    H     WRONG -- writes slot 6, not a species here
!   4  dd3          D    D    He4   see below, and not an NS_* problem
!   7  tt           T    T    He4   correct
!   5,6  dhe3*                      identically zero: ns2=NS_He3=5 is a slot
!   8-13 the3*                      the composition lacks, so RN reads 0
!
! Three of the five channels that evaluate are right, because e/D/T/He4 is the
! order plinit assumes.  dd2 is the only one depositing into a non-species.
! dd3 landing on He4 rather than He3 is the INVERTED REMAP documented at the
! nsp_idnf assignments in libnf -- a separate upstream defect with a separate
! cause, not a consequence of the missing resolution.
!
! Porting tr_prep_ns is not a drop-in:
!   * trx's tr_prep_ns does NOT cover NS_He5 -- it neither zeroes nor assigns
!     it, and its species walk has no mass-5 case -- so the NS_He5 term of the
!     CASE(4,14) presence check cannot fire even in trx, and the35 would still
!     write to a phantom slot after a verbatim port;
!   * with NS_* resolved the rest of the presence check does go live, and its
!     case labels then have to match what each model_pnf indexes rather than
!     what libnf's header table says.  model_pnf=12 reaches
!     nsp_idnf(dd3)=NS_He3 through the inverted remap while CASE(1,12) does not
!     require He3, so it would index 0.  Reasoned from the code and observed
!     once as a bounds trap on a working tree that carried the port; that tree
!     was discarded, so it is NOT reproducible from this commit;
!   * every dispatch test would need a composition supporting its model_pnf,
!     and building a 7-species tr run trips an unrelated NEA bounds error.
!
! Resolution, guard labels and multi-species fixtures are one unit of work and
! belong with the Task 7 validation, not with this dispatch.

MODULE trpnf_multi

  PRIVATE
  PUBLIC tr_prep_pnf
  PUBLIC tr_pnf

CONTAINS

  ! *** resolve the per-reaction species/weight/energy caches ***
  !
  ! Called once after the libnf tables are initialised.  Sets
  ! nf_multi_ready as its last action -- see trcomm_nf for why the
  ! model_pnf gate alone is not a sufficient guard.

  SUBROUTINE tr_prep_pnf(ierr)

    USE trcomm_ctrl, ONLY: nnfmax
    USE trcomm_nf
    USE libnf
    IMPLICIT NONE
    INTEGER, INTENT(OUT):: ierr
    INTEGER:: nnf, id_nf

    ierr = 0
    nf_multi_ready = .FALSE.

    ! libnf owns id_nf_nnf and allocates it from nnfmax; if that has not
    ! happened there is nothing to resolve and the caller must not dispatch.
    IF(.NOT.ALLOCATED(id_nf_nnf)) THEN
       ierr = 1
       RETURN
    END IF
    IF(nnfmax <= 0) THEN
       ierr = 2
       RETURN
    END IF
    ! ns1_nnf needs its own ALLOCATED test -- SIZE() of an unallocated
    ! allocatable is undefined -- and the comparison is /=, not <: an
    ! array left oversized by a previous, wider nnfmax is just as wrong as
    ! an undersized one, and `<` would wave it through.
    IF(.NOT.ALLOCATED(ns1_nnf)) THEN
       ierr = 3
       RETURN
    END IF
    IF(SIZE(id_nf_nnf) /= nnfmax .OR. SIZE(ns1_nnf) /= nnfmax) THEN
       ierr = 3
       RETURN
    END IF

    DO nnf = 1, nnfmax
       id_nf = id_nf_nnf(nnf)
       ns1_nnf(nnf) = ns1_idnf(id_nf)
       ns2_nnf(nnf) = ns2_idnf(id_nf)
       nsp_nnf(nnf) = nsp_idnf(id_nf)
       wgt_nnf(nnf) = wgt_idnf(id_nf)
       eng_nnf(nnf) = eng_idnf(id_nf)
       enn_nnf(nnf) = enn_idnf(id_nf)
    END DO

    nf_multi_ready = .TRUE.

    RETURN
  END SUBROUTINE tr_prep_pnf

  ! *** calculate the fusion reaction sources ***

  SUBROUTINE tr_pnf(ierr)

    USE TRCOM0, ONLY: rkind, NRMAX, NSTM
    USE trcomm_ctrl, ONLY: nnfmax
    USE trcomm_profile, ONLY: RN, RT
    USE trcomm_nf
    USE libnf
    IMPLICIT NONE
    INTEGER, INTENT(OUT):: ierr
    REAL(rkind):: PN1, PN2, PT1, RATE_NF, SNF
    REAL(rkind):: wgt, eng, enn
    INTEGER:: nnf, nr, id_nf, ns1, ns2, nsp, ns

    ierr = 0
    IF(.NOT.nf_multi_ready) RETURN

    ! Zeroed over the full NSTM extent, not 1:NSMAX.
    !
    ! trx bounds these loops by NSMAX because its arrays are NSMAX-
    ! dimensioned. Here they are NSTM-dimensioned, and the species indices
    ! written below are plcomm's NS_* constants -- fixed at 2..7 by
    ! pl/plinit.f90 and never re-resolved against the run's composition --
    ! so nothing keeps them at or below NSMAX. A 4-species case at
    ! model_pnf=2 writes ns=NS_H=6; bounding the reset at NSMAX=4 would
    ! leave that slot accumulating `+` on every step, for the whole run.
    ! That is the same unbounded growth the PNF_NSNNFNR note below
    ! describes, reintroduced by the NSMAX->NSTM widening rather than
    ! inherited from trx.
    SNF_NSNNFNR(1:NSTM,1:nnfmax,1:NRMAX)   = 0.D0 ! particle source
    PNFCL_NSNNFNR(1:NSTM,1:nnfmax,1:NRMAX) = 0.D0 ! collisional transfer in
    SNFNN_NNFNR(1:nnfmax,1:NRMAX)          = 0.D0 ! neutron number
    PNFNN_NNFNR(1:nnfmax,1:NRMAX)          = 0.D0 ! neutron power
    ! DEVIATION FROM trx (upstream defect): trx zeroes the four arrays above
    ! but not PNF_NSNNFNR, which it then accumulates into with `+`.  Left as
    ! upstream, the fusion power would grow without bound across timesteps.
    PNF_NSNNFNR(1:NSTM,1:nnfmax,1:NRMAX)   = 0.D0 ! fusion power

    ! sigmav_nf reports out-of-band (its signature is pinned by a ctypes
    ! binding). Clear once here, check once after the loop.
    nf_last_error = 0

    DO nnf = 1, nnfmax
       id_nf = id_nf_nnf(nnf)
       ns1 = ns1_nnf(nnf)
       ns2 = ns2_nnf(nnf)
       nsp = nsp_nnf(nnf)
       wgt = wgt_nnf(nnf)
       eng = eng_nnf(nnf)
       enn = enn_nnf(nnf)
       DO nr = 1, NRMAX
          PN1 = RN(nr,ns1)
          PN2 = RN(nr,ns2)
          PT1 = RT(nr,ns1)
          RATE_NF = sigmav_nf(id_nf,PT1)
          SNF = wgt*PN1*PN2*1.D20*RATE_NF
          SNF_NSNNFNR(ns1,nnf,nr) = SNF_NSNNFNR(ns1,nnf,nr) - SNF
          SNF_NSNNFNR(ns2,nnf,nr) = SNF_NSNNFNR(ns2,nnf,nr) - SNF
          SNF_NSNNFNR(nsp,nnf,nr) = SNF_NSNNFNR(nsp,nnf,nr) + SNF
          PNF_NSNNFNR(nsp,nnf,nr) = PNF_NSNNFNR(nsp,nnf,nr) + eng*SNF*1.D20
          IF(enn > 0.D0) THEN
             SNFNN_NNFNR(nnf,nr) = SNFNN_NNFNR(nnf,nr) + SNF
             PNFNN_NNFNR(nnf,nr) = PNFNN_NNFNR(nnf,nr) + enn*SNF*1.D20
          END IF
       END DO
    END DO

    ! Reported through ierr, but the caller deliberately does not abandon
    ! the step on it: everything this routine writes is a diagnostic that
    ! nothing else reads yet, so returning early from trcalc would skip
    ! TRAJOH and the SSIN/PIN assembly and kill a solve whose consumed
    ! physics is fine.  When Task 7 makes these arrays load-bearing, the
    ! caller starts propagating; the value is set here either way, so the
    ! argument is not decorative and a future `ierr = <code>` cannot go
    ! nowhere unnoticed.  The durable record is libnf's nf_error_count,
    ! which this routine does not clear.
    IF(nf_last_error.NE.0) ierr = 100 + nf_last_error

    ! --- roll-ups over reactions, as consumed downstream in trx ---
    !
    ! 1:NSTM, not 1:NSMAX, for the same reason the resets above are: the
    ! contributing species indices are not bounded by NSMAX.

    DO nr = 1, NRMAX
       DO ns = 1, NSTM
          SNF_NSNR(ns,nr)   = SUM(SNF_NSNNFNR(ns,1:nnfmax,nr))
          PNFCL_NSNR(ns,nr) = SUM(PNFCL_NSNNFNR(ns,1:nnfmax,nr))
       END DO
    END DO

    ! --- NOT PORTED: the slowing-down block (TAUF_NNFNR stays zero) ---
    !
    ! trx computes a per-reaction slowing-down time from the fast-ion stored
    ! energy `RW(NR,NNBMAX+nnf)` -- one fast-ion slot per reaction.  tr cannot
    ! express that: RW is dimensioned (NRMAX,NFM) with NFM a compile-time
    ! PARAMETER equal to 2 (trcom0.f90:12), slot 1 = NB and slot 2 = fusion.
    !
    ! Raising NFM is not a local change.  It is the solver's state-vector
    ! dimension (YV/AY/Y(NFM,NRMAX), trcomm_mtx.f90:27, looped in trexec.f90
    ! at 117/147 and divided at 104), it sets the total stored energy
    ! (SUM(RW(NR,1:NFM)), trrslt_globals.f90:69), and it is written into the
    ! binary dump header (trmenu.f90:137) that every regression baseline is
    ! compared against.  Widening the fast-ion species dimension is therefore
    ! its own task, not a side effect of porting the reaction sources.
    !
    ! Until then the legacy MDLNF path keeps computing the 1-D TAUF(NRMAX) it
    ! always has, and this routine leaves TAUF_NNFNR at zero rather than
    ! filling it from a single-slot RW it cannot correctly attribute.
    !
    ! When that task lands, port trx/trpnf.f90:94-113, and note that its
    ! slowing-down loop reads PA(ns)/PZ(ns)/COULOG(1,ns,...) where `ns` is the
    ! leftover DO-variable from the preceding VC3 loop (so NSMAX+1, an
    ! unwritten slot) and never uses the `nsp` it assigns one line earlier.

    RETURN
  END SUBROUTINE tr_pnf

END MODULE trpnf_multi
