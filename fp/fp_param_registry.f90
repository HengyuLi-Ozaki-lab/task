! fp_param_registry.f90
!
! Phase L-3: setter table for namelist (fpparm.f90 / &fp/) parameters.
!
! Implements a hand-written SELECT CASE dispatch that maps a parameter
! name (optionally with a 1-origin subscript in square brackets, e.g.
! "PN[1]") to an assignment into the matching fpcomm_parm / plcomm_parm
! variable.
!
! The initial set follows
! docs/superpowers/plans/2026-04-18-fp-library-L3-param-registry.md §"Module Survey":
!   - geometry/device scalars (RR, RA, RB, RKAP, RDLT, BB, RIP)
!   - mesh                    (NRMAX, NPMAX, NTHMAX, NTMAX, NAVMAX)
!   - species count           (NSMAX, NSAMAX, NSBMAX)
!   - species mapping arrays  (NS_NSA[i], NS_NSB[i])
!   - species real arrays     (PA[i], PZ[i], PN[i], PNS[i], PTPR[i],
!                              PTPP[i], PTS[i], PMAX[i])
!   - time evolution          (DELT, EPSFP, LMAXFP)
!   - radial mesh             (R1, DELR1, RMIN, RMAX, E0, ZEFF)
!   - wave heating            (PABS_EC, PABS_LH, PABS_FW, PABS_WR,
!                              PABS_WM, RF_WM)
!   - model switches scalar   (MODELG, MODELE, MODELR, MODELS, MODELD,
!                              MODEL_NBI, MODEL_WAVE, MODEL_DISRUPT,
!                              MODEL_BS, MODEL_LOSS, MODEL_SYNCH,
!                              MODEL_FOW)
!   - model switches arrays   (MODELC[i], MODELW[i])
!   - NBI source, bounce average (MODELA, NBEAMMAX, NSSPB[i], SPBTOT[i],
!                              SPBENG[i], SPBANG[i], SPBR0[i], SPBRW[i];
!                              task-web-client #232)
!
! 62 names (the CASEs below) cover more settable variables once array
! subscripts are counted. Additional namelist vars may be added
! in a later PR by extending the SELECT CASE list; the parser handles
! any "NAME" or "NAME[idx]" input unchanged.
!
! Mirrors tr/tr_param_registry.f90 (Phase L-3, PR #33).

MODULE fp_param_registry
  USE fpcomm_parm
  USE plcomm, ONLY: KNAMEQ
  IMPLICIT NONE
  PRIVATE
  PUBLIC :: fp_param_set
  PUBLIC :: fp_param_generation
  PUBLIC :: fp_param_set_str
  PUBLIC :: fp_param_check
  PUBLIC :: parse_array_subscript_pub   ! exported for unit-test only

  INTEGER, SAVE :: g_generation = 0

CONTAINS

  !-------------------------------------------------------------------
  ! Mutation counter (#253).
  !
  ! Every successful set through this registry, whoever calls it
  ! (fp_api_set_param, tot's "fp:" dispatcher, a future caller),
  ! advances g_generation. fp_api compares the value it saw when it
  ! last ran fp_prep with the current one and re-preps on a change,
  ! so the "prepared" state cannot go stale behind the C ABI's back.
  ! A set that fails leaves the counter alone: nothing changed.
  !-------------------------------------------------------------------
  FUNCTION fp_param_generation() RESULT(gen)
    INTEGER :: gen
    gen = g_generation
  END FUNCTION fp_param_generation

  FUNCTION fp_param_set(name, value) RESULT(ierr)
    CHARACTER(LEN=*), INTENT(IN) :: name
    REAL(rkind),      INTENT(IN) :: value
    INTEGER :: ierr
    ierr = fp_param_set_impl(name, value)
    IF (ierr == 0) g_generation = g_generation + 1
  END FUNCTION fp_param_set

  FUNCTION fp_param_set_str(name, value) RESULT(ierr)
    CHARACTER(LEN=*), INTENT(IN) :: name
    CHARACTER(LEN=*), INTENT(IN) :: value
    INTEGER :: ierr
    ierr = fp_param_set_str_impl(name, value)
    IF (ierr == 0) g_generation = g_generation + 1
  END FUNCTION fp_param_set_str

  FUNCTION fp_param_set_impl(name, value) RESULT(ierr)
    CHARACTER(LEN=*), INTENT(IN) :: name
    REAL(rkind),      INTENT(IN) :: value
    INTEGER :: ierr
    INTEGER :: idx
    CHARACTER(LEN=64) :: b

    ierr = 0
    CALL parse_array_subscript(name, b, idx)

    SELECT CASE (TRIM(b))
    ! --- geometry / device scalars (from plcomm_parm via fpcomm_parm) ---
    CASE ("RR");    RR    = value
    CASE ("RA");    RA    = value
    CASE ("RB");    RB    = value
    CASE ("RKAP");  RKAP  = value
    CASE ("RDLT");  RDLT  = value
    CASE ("BB");    BB    = value
    CASE ("RIP");   RIP   = value
    ! --- mesh ----------------------------------------------------
    CASE ("NRMAX");  NRMAX  = NINT(value)
    CASE ("NPMAX");  NPMAX  = NINT(value)
    CASE ("NTHMAX"); NTHMAX = NINT(value)
    CASE ("NTMAX");  NTMAX  = NINT(value)
    CASE ("NAVMAX"); NAVMAX = NINT(value)
    ! --- species count -------------------------------------------
    ! Early-reject out-of-range values so property-based / fuzz callers
    ! get a clean ierr=1 INVALID here instead of a later SEGV deep in
    ! fp_allocate. 100 = plcomm::NSM hard upper bound; 8 matches
    ! fp/fp_state.f90::FP_MAX_NSAMAX for the C ABI struct.
    CASE ("NSMAX")
       IF (NINT(value) < 1 .OR. NINT(value) > 100) THEN; ierr = 1; RETURN; END IF
       NSMAX  = NINT(value)
    CASE ("NSAMAX")
       IF (NINT(value) < 1 .OR. NINT(value) > 8) THEN; ierr = 1; RETURN; END IF
       NSAMAX = NINT(value)
    CASE ("NSBMAX")
       IF (NINT(value) < 1 .OR. NINT(value) > 8) THEN; ierr = 1; RETURN; END IF
       NSBMAX = NINT(value)
    ! --- species mapping arrays (1-origin, NSM-bound) ------------
    CASE ("NS_NSA")
       IF (idx < 1 .OR. idx > SIZE(NS_NSA)) THEN; ierr = 2; RETURN; END IF
       NS_NSA(idx) = NINT(value)
    CASE ("NS_NSB")
       IF (idx < 1 .OR. idx > SIZE(NS_NSB)) THEN; ierr = 2; RETURN; END IF
       NS_NSB(idx) = NINT(value)
    ! --- species real arrays (1-origin) --------------------------
    CASE ("PA")
       IF (idx < 1 .OR. idx > SIZE(PA))   THEN; ierr = 2; RETURN; END IF
       PA(idx)   = value
    CASE ("PZ")
       IF (idx < 1 .OR. idx > SIZE(PZ))   THEN; ierr = 2; RETURN; END IF
       PZ(idx)   = value
    CASE ("PN")
       IF (idx < 1 .OR. idx > SIZE(PN))   THEN; ierr = 2; RETURN; END IF
       PN(idx)   = value
    CASE ("PNS")
       IF (idx < 1 .OR. idx > SIZE(PNS))  THEN; ierr = 2; RETURN; END IF
       PNS(idx)  = value
    CASE ("PTPR")
       IF (idx < 1 .OR. idx > SIZE(PTPR)) THEN; ierr = 2; RETURN; END IF
       PTPR(idx) = value
    CASE ("PTPP")
       IF (idx < 1 .OR. idx > SIZE(PTPP)) THEN; ierr = 2; RETURN; END IF
       PTPP(idx) = value
    CASE ("PTS")
       IF (idx < 1 .OR. idx > SIZE(PTS))  THEN; ierr = 2; RETURN; END IF
       PTS(idx)  = value
    CASE ("PMAX")
       IF (idx < 1 .OR. idx > SIZE(PMAX)) THEN; ierr = 2; RETURN; END IF
       PMAX(idx) = value
    ! --- time evolution ------------------------------------------
    CASE ("DELT");   DELT   = value
    CASE ("EPSFP");  EPSFP  = value
    CASE ("LMAXFP"); LMAXFP = NINT(value)
    ! --- radial mesh / scalar physics ----------------------------
    CASE ("R1");    R1    = value
    CASE ("DELR1"); DELR1 = value
    CASE ("RMIN");  RMIN  = value
    CASE ("RMAX");  RMAX  = value
    CASE ("E0");    E0    = value
    CASE ("ZEFF");  ZEFF  = value
    ! --- wave heating --------------------------------------------
    CASE ("PABS_EC"); PABS_EC = value
    CASE ("PABS_LH"); PABS_LH = value
    CASE ("PABS_FW"); PABS_FW = value
    CASE ("PABS_WR"); PABS_WR = value
    CASE ("PABS_WM"); PABS_WM = value
    CASE ("RF_WM");   RF_WM   = value
    ! --- model switches (scalar int) -----------------------------
    CASE ("MODELG"); MODELG = NINT(value)
    CASE ("MODELE"); MODELE = NINT(value)
    CASE ("MODELR"); MODELR = NINT(value)
    CASE ("MODELS"); MODELS = NINT(value)
    CASE ("MODELD"); MODELD = NINT(value)
    CASE ("MODEL_NBI");      MODEL_NBI      = NINT(value)
    CASE ("MODEL_WAVE");     MODEL_WAVE     = NINT(value)
    CASE ("MODEL_DISRUPT");  MODEL_DISRUPT  = NINT(value)
    CASE ("MODEL_BS");       MODEL_BS       = NINT(value)
    CASE ("MODEL_LOSS");     MODEL_LOSS     = NINT(value)
    CASE ("MODEL_SYNCH");    MODEL_SYNCH    = NINT(value)
    CASE ("MODEL_FOW");      MODEL_FOW      = NINT(value)
    ! --- model switches (per-species int arrays) -----------------
    CASE ("MODELC")
       IF (idx < 1 .OR. idx > SIZE(MODELC)) THEN; ierr = 2; RETURN; END IF
       MODELC(idx) = NINT(value)
    CASE ("MODELW")
       IF (idx < 1 .OR. idx > SIZE(MODELW)) THEN; ierr = 2; RETURN; END IF
       MODELW(idx) = NINT(value)
    ! --- NBI source and bounce average (task-web-client #232) -----
    ! Units and defaults: fp/fpinit.f90 (NBEAMMAX has none). SPBPANG
    ! is not registered: no source under fp/ reads it.
    ! SPBTOT is in 1e20 particles/s (the source is normalised with RNFP0
    ! [1e20 m^-3]; fp/fpinit.f90's comment says [1/s]).
    CASE ("MODELA");   MODELA   = NINT(value)
    CASE ("NBEAMMAX"); NBEAMMAX = NINT(value)
    CASE ("NSSPB")
       IF (idx < 1 .OR. idx > SIZE(NSSPB))  THEN; ierr = 2; RETURN; END IF
       NSSPB(idx)  = NINT(value)
    CASE ("SPBTOT")
       IF (idx < 1 .OR. idx > SIZE(SPBTOT)) THEN; ierr = 2; RETURN; END IF
       SPBTOT(idx) = value
    CASE ("SPBENG")
       IF (idx < 1 .OR. idx > SIZE(SPBENG)) THEN; ierr = 2; RETURN; END IF
       SPBENG(idx) = value
    CASE ("SPBANG")
       IF (idx < 1 .OR. idx > SIZE(SPBANG)) THEN; ierr = 2; RETURN; END IF
       SPBANG(idx) = value
    CASE ("SPBR0")
       IF (idx < 1 .OR. idx > SIZE(SPBR0))  THEN; ierr = 2; RETURN; END IF
       SPBR0(idx)  = value
    CASE ("SPBRW")
       IF (idx < 1 .OR. idx > SIZE(SPBRW))  THEN; ierr = 2; RETURN; END IF
       SPBRW(idx)  = value
    CASE DEFAULT
       ierr = 1   ! unknown name
    END SELECT
  END FUNCTION fp_param_set_impl

  !-------------------------------------------------------------------
  ! fp_param_check : the counts a run cannot be made with, checked
  ! together before the run (issue #143) instead of being met deep in
  ! the solver as an array index out of bounds (an abort when the
  ! library is built with run-time checks, undefined without them), a
  ! process that ends, or a step that never ends (issue #142). Returns
  ! 0, or 1 after writing one line per violation to unit 6.
  !
  !   NRMAX          1 .. max_nrmax. Below 1 fp_mesh runs past an array
  !                  bound. max_nrmax is the caller's limit: fp_api
  !                  passes the surfaces its state layout holds
  !                  (fp/fp_state.f90), beyond which a run is made and
  !                  fp_get_state cannot return it.
  !   NPMAX, NTHMAX  2 or more: with fewer cells the solver runs past
  !                  an array bound.
  !   LMAXFP         0 .. HUGE-1. Below 0 no pass is made, and fp_loop
  !                  then tests an error flag that no pass has set (on
  !                  the build measured, mtx_abort ends the process).
  !                  At HUGE the iteration's exit at convergence,
  !                  N_IMPL = 1 + LMAXFP (fp/fploop.f90), overflows and
  !                  the step never ends.
  !   NSAMAX         at most NSBMAX: the collision arrays are sized by
  !                  NSBMAX in both species directions (fp/fpcomm.f90).
  !   NS_NSA(1..NSAMAX)  1 .. MIN(NSMAX, NSBMAX): a species has
  !                  profiles up to NSMAX, and its distribution is
  !                  copied into the background array at its species
  !                  number (fp/fpmpi.f90).
  !   NS_NSB(1..NSBMAX)  1 .. NSMAX.
  !   MODELA, NBEAMMAX and the beams (task-web-client #232): the block
  !                  at the end of the function says which and why.
  !
  ! A 0 in either map stands for the slot's own number, which
  ! fp_set_nsa_nsb substitutes when the run is prepared (fp/fpprep.f90).
  !-------------------------------------------------------------------
  FUNCTION fp_param_check(max_nrmax) RESULT(ierr)
    INTEGER, INTENT(IN) :: max_nrmax
    INTEGER :: ierr
    INTEGER :: i, ns, nsa, nsabeam, nsx, nsx_ns
    LOGICAL :: kinetic, electrons
    REAL(rkind) :: t, psp, pmax_eff, amfp, ptfp0
    REAL(rkind) :: amfp_e, ptfp0_e, amfp_b, pe, edge_e

    ierr = 0
    IF (NRMAX < 1 .OR. NRMAX > max_nrmax) THEN
       WRITE(6,'(A,I0,A,I0)') 'XX fp_run: NRMAX = ', NRMAX, &
            ' is outside 1 to ', max_nrmax
       ierr = 1
    END IF
    IF (NPMAX < 2) THEN
       WRITE(6,'(A,I0,A)') 'XX fp_run: NPMAX = ', NPMAX, ' is below 2'
       ierr = 1
    END IF
    IF (NTHMAX < 2) THEN
       WRITE(6,'(A,I0,A)') 'XX fp_run: NTHMAX = ', NTHMAX, ' is below 2'
       ierr = 1
    END IF
    IF (LMAXFP < 0 .OR. LMAXFP >= HUGE(LMAXFP)) THEN
       WRITE(6,'(A,I0,A,I0)') 'XX fp_run: LMAXFP = ', LMAXFP, &
            ' is outside 0 to ', HUGE(LMAXFP) - 1
       ierr = 1
    END IF
    IF (NSAMAX > NSBMAX) THEN
       WRITE(6,'(A,I0,A,I0)') 'XX fp_run: NSAMAX = ', NSAMAX, &
            ' is above NSBMAX = ', NSBMAX
       ierr = 1
    END IF
    DO i = 1, MIN(NSAMAX, SIZE(NS_NSA))
       ns = NS_NSA(i)
       IF (ns == 0) ns = i
       IF (ns < 1 .OR. ns > MIN(NSMAX, NSBMAX)) THEN
          WRITE(6,'(A,I0,A,I0,A,I0)') 'XX fp_run: NS_NSA(', i, ') = ', ns, &
               ' is outside 1 to MIN(NSMAX, NSBMAX) = ', MIN(NSMAX, NSBMAX)
          ierr = 1
       END IF
    END DO
    DO i = 1, MIN(NSBMAX, SIZE(NS_NSB))
       ns = NS_NSB(i)
       IF (ns == 0) ns = i
       IF (ns < 1 .OR. ns > NSMAX) THEN
          WRITE(6,'(A,I0,A,I0,A,I0)') 'XX fp_run: NS_NSB(', i, ') = ', ns, &
               ' is outside 1 to NSMAX = ', NSMAX
          ierr = 1
       END IF
    END DO
    ! --- NBI source and bounce average (task-web-client #232) -----
    ! MODELA: FP has only 0 and 1 (fp/fpparm.f90). NBEAMMAX: the beam
    ! loops run to it (fp/fpcoef.f90), and fp_init gives it no value
    ! (only the namelist does), so any start value outside 0 .. NBEAMM
    ! is refused here. With MODEL_NBI = 1, NBI_SOURCE_A0 takes every
    ! beam up to NBEAMMAX, whatever its source: SPBRW must be above 0
    ! for each (0 makes the source 0/0, NaN, even with SPBTOT = 0; a
    ! width below 0 means nothing). A beam with a source (SPBTOT /= 0)
    ! would deposit nothing, without a word, beyond NBEAMMAX, on no
    ! kinetic species (NSSPB is a namelist species, matched against
    ! NS_NSA, a 0 there read as the slot's number), with SPBANG outside
    ! 0 <= x < 180 (no pitch cell holds it) or with SPBENG < 0 (no
    ! momentum). Three more rules, added as a follow-up of #232:
    !  - NAVMAX is a divisor: in the bounce average of MODELA = 1
    !    (fp/fpbounce.f90: DELH = 2*ETAM/NAVMAX, DO NG = 1, NAVMAX) and
    !    in the wave terms whatever MODELA (MODEL_WAVE /= 0 calls FP_CALW,
    !    fp/fpcoef.f90, then FPSUMW, fp/fpcalw.f90: DELH = 2*ETA/NAVMAX,
    !    also fpcalwm.f90, fpcalwr.f90). NAVMAX = 0 divides by zero and
    !    the empty loop leaves SUM*DELH = 0*Inf = NaN, even with no wave
    !    power; a negative NAVMAX makes the averaging loop empty. So
    !    (MODELA = 1 .OR. MODEL_WAVE /= 0) .AND. NAVMAX < 1 is refused,
    !    whatever MODEL_NBI.
    !  - A beam beyond the ion momentum mesh. FP deposits ions only in
    !    the cell PG(NP) <= PSP < PG(NP+1), PSP = SQRT(2*SPBENG/(1000*T))
    !    (SPBENG in eV, T = (PTPR + 2*PTPP)/3 in keV of the beam's
    !    species; the mass cancels), and the mesh ends at PMAX(ns), or,
    !    when the sum of EMAX is not 0 and EMAX(ns) /= 0, at
    !    SQRT(2*EMAX/T) (fp/fpprep.f90; EMAX is not registered, so it
    !    keeps its default 0 unless a namelist file sets it). PSP at or
    !    beyond that edge deposits nothing in the beam's species; with
    !    kinetic electrons the electron branch still deposits electrons,
    !    so the source is unbalanced. The code computes the momentum and
    !    the edge with FP's own expressions, constants and order of
    !    operations (fpcoef.f90 ~535, fpprep.f90 ~40-55 and ~887-894:
    !    SQRT(2*amfp*SPBENG*AEE)/SQRT(T*1e3*AEE*amfp)), because the
    !    simplified form differs from FP's by 1 ulp for some inputs, which
    !    decides a beam at p = PMAX. A temperature not above 0 (or NaN)
    !    gives no momentum and nothing is deposited: refused.
    !  - The electron compensating source (fpcoef.f90 ~577-603) deposits
    !    the electrons, with the charge PZ(NSABEAM), only in the cell of
    !    the electron mesh that holds p_e = SQRT(2*amfp_e**2*SPBENG*AEE
    !    /amfp_b)/ptfp0_e. A beam whose p_e is not below the electron
    !    mesh edge is refused with its own line (its ions would be
    !    deposited with no electrons); only a beam inside the electron
    !    mesh reaches the PZ rule below.
    !  - The electron compensating source takes the wrong charge. With
    !    kinetic electrons and NSSPB(1) /= 1, NBI_SOURCE_A0 sets NSABEAM
    !    to the LAST kinetic slot whose species is NSSPB(beam), and adds
    !    PZ(NSABEAM)*SPBTOT: PZ is indexed by the namelist species, so
    !    the intended charge is PZ(NSSPB(beam)); the two agree only when
    !    slot and species numbers coincide or the charges are equal (the
    !    indices are compared first, so a NaN charge at the same index is
    !    not refused for PZ).
    !    That is an FP bug, reported to the lead (follow-up of
    !    task-web-client #232) and NOT changed here: the rule refuses the
    !    run where the two charges differ, so no result changes, and
    !    stands in until FP is fixed.
    ! Not checked: a source so narrow that EXP(-(RM-SPBR0)**2/SPBRW**2)
    ! is 0 at every radial point is 0/0.
    IF (MODELA < 0 .OR. MODELA > 1) THEN
       WRITE(6,'(A,I0,A)') 'XX fp_run: MODELA = ', MODELA, ' is neither 0 nor 1'
       ierr = 1
    END IF
    IF ((MODELA == 1 .OR. MODEL_WAVE /= 0) .AND. NAVMAX < 1) THEN
       WRITE(6,'(A,I0,A)') 'XX fp_run: NAVMAX = ', NAVMAX, &
            ' must be >= 1 with MODELA = 1 or MODEL_WAVE /= 0 (the bounce average and the wave diffusion divide by it and loop to it)'
       ierr = 1
    END IF
    IF (NBEAMMAX < 0 .OR. NBEAMMAX > NBEAMM) THEN
       WRITE(6,'(A,I0,A,I0)') 'XX fp_run: NBEAMMAX = ', NBEAMMAX, &
            ' is outside 0 to ', NBEAMM
       ierr = 1
    END IF
    IF (MODEL_NBI == 1) THEN
       ! Are electrons (species 1) a kinetic slot? NBI_SOURCE_A0's
       ! electron branch runs for that slot when NSSPB(1) /= 1.
       electrons = .FALSE.
       DO nsa = 1, MIN(NSAMAX, SIZE(NS_NSA))
          ns = NS_NSA(nsa)
          IF (ns == 0) ns = nsa
          IF (ns == 1) electrons = .TRUE.
       END DO
       electrons = electrons .AND. NSSPB(1) /= 1
       DO i = 1, NBEAMM
          IF (i <= NBEAMMAX .AND. .NOT. (SPBRW(i) > 0.0_rkind)) THEN
             WRITE(6,'(A,I0,A,ES12.4,A)') 'XX fp_run: SPBRW(', i, ') = ', SPBRW(i), &
                  ' is not above 0'
             ierr = 1
          END IF
          IF (SPBTOT(i) == 0.0_rkind) CYCLE
          IF (i > NBEAMMAX) THEN
             WRITE(6,'(A,I0,A,I0,A)') 'XX fp_run: SPBTOT(', i, &
                  ') is set, but NBEAMMAX = ', NBEAMMAX, ' leaves the beam out'
             ierr = 1
             CYCLE
          END IF
          kinetic = .FALSE.
          DO nsa = 1, MIN(NSAMAX, SIZE(NS_NSA))
             ns = NS_NSA(nsa)
             IF (ns == 0) ns = nsa
             IF (ns == NSSPB(i)) kinetic = .TRUE.
          END DO
          IF (.NOT. kinetic) THEN
             WRITE(6,'(A,I0,A,I0,A)') 'XX fp_run: NSSPB(', i, ') = ', NSSPB(i), &
                  ' is no kinetic species (NS_NSA)'
             ierr = 1
          END IF
          IF (.NOT. (SPBANG(i) >= 0.0_rkind .AND. SPBANG(i) < 180.0_rkind)) THEN
             WRITE(6,'(A,I0,A,ES12.4,A)') 'XX fp_run: SPBANG(', i, ') = ', SPBANG(i), &
                  ' is outside 0 to below 180'
             ierr = 1
          END IF
          IF (.NOT. (SPBENG(i) >= 0.0_rkind)) THEN
             WRITE(6,'(A,I0,A,ES12.4,A)') 'XX fp_run: SPBENG(', i, ') = ', SPBENG(i), &
                  ' is below 0'
             ierr = 1
          END IF
          ns = NSSPB(i)
          IF (ns < 1 .OR. ns > MIN(SIZE(PZ), SIZE(PA), SIZE(PTPR), SIZE(PTPP), SIZE(PMAX), SIZE(EMAX))) CYCLE
          IF (kinetic) THEN
             ! FP's own expressions, constants and order (fpprep.f90 ~887-894,
             ! fpcoef.f90 ~535), so that the verdict is FP's to the bit.
             t = (PTPR(ns) + 2.0_rkind*PTPP(ns))/3.0_rkind
             IF (.NOT. (t > 0.0_rkind)) THEN
                WRITE(6,'(A,I0,A,I0,A,ES12.4,A)') 'XX fp_run: beam ', i, &
                     ': the temperature of species ', ns, ' is not above 0 (T = ', t, &
                     '): no momentum, nothing is deposited'
                ierr = 1
             ELSE IF (SPBENG(i) >= 0.0_rkind) THEN
                amfp = PA(ns)*AMP
                ptfp0 = SQRT(t*1.0E3_rkind*AEE*amfp)
                psp = SQRT(2.0_rkind*amfp*SPBENG(i)*AEE)/ptfp0
                pmax_eff = fp_mesh_edge(ns)
                IF (.NOT. (psp < pmax_eff)) THEN
                   WRITE(6,'(A,I0,A,ES12.4,A,ES12.4,A,ES12.4,A,I0,A,ES12.4,A,I0,A)') &
                        'XX fp_run: SPBENG(', i, ') = ', SPBENG(i), ' eV needs p = ', psp, &
                        ' at T = ', t, ' keV of species ', ns, ', beyond its mesh edge (', &
                        pmax_eff, '): species ', ns, ' receives no deposit'
                   ierr = 1
                END IF
                ! The electron compensating source (fpcoef.f90 ~577-603): NSABEAM is the
                ! last kinetic slot of the beam's species; the electrons are deposited,
                ! with PZ(NSABEAM), only in the electron cell that holds the momentum pe.
                IF (electrons) THEN
                   nsabeam = 0
                   DO nsx = 1, MIN(NSAMAX, SIZE(NS_NSA))
                      nsx_ns = NS_NSA(nsx)
                      IF (nsx_ns == 0) nsx_ns = nsx
                      IF (nsx_ns == ns) nsabeam = nsx
                   END DO
                   IF (nsabeam >= 1 .AND. nsabeam <= SIZE(PZ)) THEN
                      amfp_e = PA(1)*AMP
                      amfp_b = PA(ns)*AMP
                      ptfp0_e = SQRT(((PTPR(1) + 2.0_rkind*PTPP(1))/3.0_rkind)*1.0E3_rkind*AEE*amfp_e)
                      pe = SQRT(2.0_rkind*amfp_e**2*SPBENG(i)*AEE/amfp_b)/ptfp0_e
                      edge_e = fp_mesh_edge(1)
                      IF (.NOT. (pe < edge_e)) THEN
                         WRITE(6,'(A,I0,A,ES12.4,A)') &
                              'XX fp_run: the electron compensating source of beam ', i, &
                              ' falls beyond the electron mesh edge (', edge_e, &
                              '): its ions are deposited with no electrons'
                         ierr = 1
                      ELSE IF (nsabeam /= ns .AND. .NOT. (PZ(nsabeam) == PZ(ns))) THEN
                         WRITE(6,'(A,I0,A,I0,A,I0,A,ES12.4,A,I0,A,ES12.4,A)') &
                              'XX fp_run: beam ', i, ' on species ', ns, &
                              ': FP''s electron source takes PZ(', nsabeam, ') = ', PZ(nsabeam), &
                              ', not PZ(', ns, ') = ', PZ(ns), ' (fp/fpcoef.f90, NBI_SOURCE_A0)'
                         ierr = 1
                      END IF
                   END IF
                END IF
             END IF
          END IF
       END DO
    END IF
    IF (ierr /= 0) FLUSH(6)
  END FUNCTION fp_param_check

  !-------------------------------------------------------------------
  ! The momentum mesh's upper edge of species ns, as fp_prep makes it
  ! (fp/fpprep.f90): PMAX(ns), or, only when the sum of EMAX over
  ! 1..NSMAX is not 0 and EMAX(ns) /= 0, from EMAX(ns), with fp_prep's
  ! constants, names and order of operations (so the verdict matches FP's
  ! to the bit). PG(NPMAX+1) is set to exactly this value.
  !-------------------------------------------------------------------
  FUNCTION fp_mesh_edge(ns) RESULT(edge)
    INTEGER, INTENT(IN) :: ns
    REAL(rkind) :: edge
    REAL(rkind) :: sumemax, rmass, rrtfp, rptfp
    INTEGER :: k

    sumemax = 0.0_rkind
    DO k = 1, MIN(NSMAX, SIZE(EMAX))
       sumemax = sumemax + EMAX(k)
    END DO
    edge = PMAX(ns)
    IF (sumemax /= 0.0_rkind .AND. EMAX(ns) /= 0.0_rkind) THEN
       rmass = PA(ns)*AMP
       rrtfp = (PTPR(ns) + 2.0_rkind*PTPP(ns))/3.0_rkind
       rptfp = SQRT(rrtfp*1.0E3_rkind*AEE*rmass)
       edge = SQRT(2.0_rkind*AEE*rmass*1.0E3_rkind*EMAX(ns))/rptfp
    END IF
  END FUNCTION fp_mesh_edge

  !-------------------------------------------------------------------
  ! fp_param_set_str : string-valued parameter setter.
  !
  ! Mirrors tr/tr_param_registry.f90::tr_param_set_str (PR #103).
  ! Required because the FP namelist /FP/ inherits KNAMEQ from
  ! plcomm (the equilibrium-data file name used by the MODELG=3
  ! eq_load path on fp_iter01). Without this entry point the
  ! Layer 1 fixture cannot point at a real EQDSK; the default
  ! KNAMEQ='eqdata' (from pl_init) is missing in cwd, so eq_load
  ! fails silently and downstream BESEKNX trips with NCALC=-2.
  !-------------------------------------------------------------------
  FUNCTION fp_param_set_str_impl(name, value) RESULT(ierr)
    CHARACTER(LEN=*), INTENT(IN) :: name
    CHARACTER(LEN=*), INTENT(IN) :: value
    INTEGER :: ierr

    ierr = 0
    SELECT CASE (TRIM(ADJUSTL(name)))
    CASE ("KNAMEQ"); KNAMEQ = TRIM(value)
    CASE DEFAULT
       ierr = 1   ! unknown string-valued name
    END SELECT
  END FUNCTION fp_param_set_str_impl

  !-------------------------------------------------------------------
  ! Split "NAME" or "NAME[N]" into (base, idx).
  !
  !   "RR"      -> base="RR",  idx=0       (scalar form)
  !   "PN[1]"   -> base="PN",  idx=1       (1-origin subscript)
  !   "MODELC[2]" -> base="MODELC", idx=2
  !   malformed -> base=<full>, idx=-1     (caller returns ierr=1)
  !-------------------------------------------------------------------
  SUBROUTINE parse_array_subscript(full_name, base, idx)
    CHARACTER(LEN=*), INTENT(IN)  :: full_name
    CHARACTER(LEN=*), INTENT(OUT) :: base
    INTEGER,          INTENT(OUT) :: idx
    INTEGER :: lb, rb, ios
    base = ' '
    idx  = 0
    lb = INDEX(full_name, '[')
    rb = INDEX(full_name, ']', BACK=.TRUE.)
    IF (lb == 0 .AND. rb == 0) THEN
       base = TRIM(ADJUSTL(full_name))
       RETURN
    END IF
    IF (lb == 0 .OR. rb == 0 .OR. rb <= lb + 1) THEN
       base = TRIM(ADJUSTL(full_name))   ! malformed; caller returns ierr=1
       idx  = -1
       RETURN
    END IF
    base = full_name(1:lb-1)
    READ(full_name(lb+1:rb-1), *, IOSTAT=ios) idx
    IF (ios /= 0) idx = -1
  END SUBROUTINE parse_array_subscript

  ! Public alias for unit testing only.
  SUBROUTINE parse_array_subscript_pub(full_name, base, idx)
    CHARACTER(LEN=*), INTENT(IN)  :: full_name
    CHARACTER(LEN=*), INTENT(OUT) :: base
    INTEGER,          INTENT(OUT) :: idx
    CALL parse_array_subscript(full_name, base, idx)
  END SUBROUTINE parse_array_subscript_pub

END MODULE fp_param_registry
