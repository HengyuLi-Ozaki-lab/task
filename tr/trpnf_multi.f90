! trpnf_multi.f90
!
! Multi-reaction fusion source, ported from trx/trpnf.f90 (P1 Task 6).
!
! FILE/MODULE NAMING: trx calls this `MODULE trpnf` in `trx/trpnf.f90`, but
! tr already has a `tr/trpnf.f90` -- a bare-externals file holding the legacy
! TRNFDT / SIGMAM / SIGMAB / TRNFDHe3.  Both would compile to `trpnf.o` in the
! same object directory, so the port lands here as `trpnf_multi`.
!
! SCOPE: the reaction sources and, since P1 Task 7, the slowing-down block
! and the publication of SNF/PNF/TAUF into the arrays the solver reads.
!
! STAGING: at model_pnf = 0 this path is inert and the legacy result is
! bit-exact -- that guarantee is unchanged, and the equivalence baselines
! rest on it.  At model_pnf /= 0 it is NOT additive: it drives the solve,
! and tr_prep refuses model_pnf together with MDLNF because both write the
! same three arrays.
!
! Only nnfmax == 1 publishes.  model_pnf >= 2 still evaluates every
! trcomm_nf array but publishes none of them, so it stays diagnostic-only --
! NOT refused, just not wired, because tr has one fusion fast-ion slot.
!
! NOT YET CORRECT PHYSICS FOR EVERY CHANNEL -- a Task 7 prerequisite, recorded
! here so validation starts from the right baseline.
!
! libnf indexes species through plcomm's NS_e..NS_He5.  trx resolves those
! against the run's composition in trx/trprep.f90's tr_prep_ns (zero them,
! then walk NS=1..NSMAX matching charge and mass), so an absent species comes
! out 0 and libnf's presence check refuses the run.  tr has no counterpart:
! NS_* keep pl/plinit.f90's defaults of 1..7 always: nothing in tr/ touches
! them, and pl/plprof_TOTAL.f90 reassigns four of them to those same values
! off tr's path, so no run here ever gets composition-resolved indices.
! Consequently libnf's presence check can never fire -- ierr_nf=3
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
    ! ONLY, not a bare USE: libnf does a module-level USE bpsd_constants, so
    ! a bare USE here puts bpsd's constants in scope alongside
    ! trcomm_const's.  libnf now carries PRIVATE :: AEE, AME, AMP, so the
    ! three that genuinely differ -- AMP by 1.7e-7, ~1700x the 1e-10 gate --
    ! are no longer re-exported and a bare USE could not pick them up.  PI
    ! still is, and is bit-identical between the two, so it only ever
    ! produces an ambiguous-reference error (which is how this was found).
    ! RKEV is not in bpsd_constants at all, so naming it without USE trcomm
    ! is a compile error, not a silent value.  The ONLY list is kept anyway:
    ! it is what makes the PRIVATE line unnecessary rather than load-bearing.
    USE libnf, ONLY: id_nf_nnf, ns1_idnf, ns2_idnf, nsp_idnf, &
         wgt_idnf, eng_idnf, enn_idnf
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

    USE TRCOM0, ONLY: rkind, NRMAX, NSMAX, NSTM
    USE trcomm_ctrl, ONLY: nnfmax
    USE trcomm_const, ONLY: PI, AME, AMM, RKEV
    USE trcomm_param, ONLY: PA, PZ
    ! Aliased: the local scalar SNF below is one reaction's rate, while these
    ! are the run-wide legacy profiles the solver reads.  The alias keeps the
    ! two apart at every use site rather than by declaration order.
    USE trcomm_profile, ONLY: RN, RT, &
         SNF_leg => SNF, PNF_leg => PNF, TAUF_leg => TAUF
    USE trlib, ONLY: COULOG, HY
    USE trcomm_nf
    USE libnf, ONLY: id_nf_nnf, sigmav_nf, nf_last_error   ! ONLY: see tr_prep_pnf
    IMPLICIT NONE
    INTEGER, INTENT(OUT):: ierr
    REAL(rkind):: PN1, PN2, PT1, RATE_NF, SNF
    REAL(rkind):: wgt, eng, enn
    REAL(rkind):: ANE, TE, P1, VC3, VCR, VF, HYF, TAUS
    INTEGER, PARAMETER:: NS_ELECTRON = 1   ! tr's convention; see TRNFDT
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

    ! Task 7 made these arrays load-bearing, so this now propagates.
    !
    ! A sigmav_nf failure returns 0, which without propagation would leave
    ! SNF and PNF zeroed across the whole radius while TAUF is still
    ! computed from the profiles: the step would proceed with fusion
    ! silently switched off, and since the summary latch is per-prepare a
    ! whole run would say so once.  Acceptable while nothing read these
    ! arrays; not now.  The durable record remains libnf's nf_error_count,
    ! which this routine does not clear.
    ! Always reported.  Whether it ABORTS the step is the caller's call --
    ! trcalc aborts only when this path is publishing, because at nnfmax > 1
    ! nothing here reaches the solver and a failed diagnostic must not kill
    ! a step whose consumed physics is fine.
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

    ! --- alpha slowing-down, and publication to the legacy arrays ---
    !
    ! Both are gated on nnfmax == 1.  tr carries exactly ONE fusion fast-ion
    ! slot -- RW is (NRMAX,NFM) with NFM a compile-time PARAMETER of 2, slot 1
    ! NB and slot 2 fusion (trcom0.f90) -- so a single reaction maps onto it
    ! and more than one does not.  Widening NFM is not local: it is the
    ! solver's state-vector dimension (YV/AY/Y, trcomm_mtx.f90), it sets the
    ! total stored energy (trrslt_globals.f90), and it is written into the
    ! binary dump header (trmenu.f90) that every regression baseline compares
    ! against.  Until that lands, model_pnf >= 2 still evaluates every
    ! trcomm_nf array but publishes none of them.  tr_prep does NOT refuse
    ! it -- its only refusal is MDLNF together with model_pnf.
    !
    ! The reference this is matched against is bpsi trx on branch
    ! ref/trx-regress-capture, with four corrections applied to its fusion
    ! path (a 1e6 cm^3/s->m^3/s error in the reaction rate, a doubled RKEV in
    ! the birth speed, a dead loop counter used as a species index, and
    ! PNF_NSNNFNR accumulated without reset).  See
    ! test_run/baselines/tr_fus_dt_hot/SOURCE.md.
    !
    ! AMM, not bpsd's AMP: the reference shadows AMP with kyoshimi's
    ! CODATA-2006 value (1.672621637D-27), so these are the same number.  Do
    ! not reach for libnf's re-exported AMP here -- that one is CODATA-2018
    ! and lands 1.7e-7 off, ~1700x the 1e-10 gate.

    IF(nnfmax /= 1) RETURN

    DO nr = 1, NRMAX
       ANE = RN(nr,NS_ELECTRON)
       TE  = RT(nr,NS_ELECTRON)
       P1  = 3.D0*SQRT(0.5D0*PI)*AME/ANE*(ABS(TE)*RKEV/AME)**1.5D0
       VC3 = 0.D0
       DO ns = 1, NSMAX
          IF(PZ(ns) > 0.D0) &                      ! sum over ions
               VC3 = VC3 + P1*RN(nr,ns)*PZ(ns)**2/(PA(ns)*AMM)
       END DO
       VCR = VC3**(1.D0/3.D0)

       nsp = nsp_nnf(1)
       VF  = SQRT(2.D0*eng_nnf(1)/(PA(nsp)*AMM))   ! eng_nnf is already in J
       HYF = HY(VF/VCR)
       TAUS = 0.2D0*PA(nsp)*ABS(TE)**1.5D0 &
            /(PZ(nsp)**2*ANE*COULOG(1,nsp,ANE,TE))
       TAUF_NNFNR(1,nr) = 0.5D0*TAUS*(1.D0-HYF)

       ! --- publish: these are what the solver actually reads ---
       !
       ! tr_prep refuses model_pnf /= 0 together with MDLNF /= 0, so nothing
       ! the legacy TRNFDT wrote is being overwritten here -- at MDLNF = 0
       ! TRCALC has already zeroed SNF and PNF and set TAUF to a placeholder
       ! 1.0, and this replaces all three.
       !
       ! NOT published, because the reference has no writer for them and
       ! inventing one would make this code the oracle rather than the thing
       ! under test: PFIN, PFCL, RNF, RTF.  In trx, PNFCL_NSNNFNR is zeroed
       ! and never assigned, so the alpha energy that leaves RW at rate
       ! 1/TAUF is discarded instead of heating the thermal species.  This
       ! oracle therefore does not exercise collisional transfer at all; that
       ! is recorded in the baseline's SOURCE.md, and closing it means adding
       ! the physics on BOTH sides, not here alone.
       TAUF_leg(nr) = TAUF_NNFNR(1,nr)
       SNF_leg(nr)  = SNF_NSNR(nsp,nr)
       PNF_leg(nr)  = PNF_NSNNFNR(nsp,1,nr)
    END DO

    RETURN
  END SUBROUTINE tr_pnf

END MODULE trpnf_multi
