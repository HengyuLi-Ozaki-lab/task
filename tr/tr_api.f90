! tr_api.f90
!
! Phase L-3: C ABI entry points for libtrapi (functional layer).
!
! All five functions are now wired to the real TRCOMM state:
!
!   tr_init       -> pl_init + eq_init + tr_init (Fortran) + ALLOCATE_TRCOMM
!                    populates TRCOMM default values including NRMAX=50,
!                    NSMAX=2, DT, NTSTEP, etc.
!   tr_set_param  -> dispatches to tr_param_registry::tr_param_set which
!                    handles ~34 namelist scalars/arrays.
!   tr_run        -> tr_prep (first call only) + tr_loop with NTMAX set to
!                    the requested step count; NTMAX is restored after
!                    the loop.
!   tr_get_state  -> populates the tr_state_c struct from the same set of
!                    TRCOMM scalars/arrays that trregress.f90 dumps.
!   tr_finalize   -> DEALLOCATE_TRCOMM + clears g_* flags.
!
! The Fortran-side names are tr_api_* to avoid colliding with the existing
! SUBROUTINE tr_init in trinit.f90 (and friends); the C-side public names
! tr_init, tr_run, tr_set_param, tr_get_state, tr_finalize are bound
! through BIND(C, NAME=...) so external callers see the spec'd symbols.
!
! See docs/superpowers/specs/2026-04-17-tr-library-design.md §4.

MODULE tr_api
  USE, INTRINSIC :: ISO_C_BINDING
  USE, INTRINSIC :: IEEE_ARITHMETIC, ONLY: IEEE_IS_FINITE
  USE tr_state, ONLY: TR_STATE_ABI_VERSION
  USE tr_state, ONLY: tr_state_c, TR_MAX_NRMAX, TR_MAX_NSMAX, &
                      tr_diag_entry_c, &
                      TR_DIAG_PARAM_LEN, TR_DIAG_MSG_LEN, &
                      TR_DIAG_OUT_OF_RANGE, TR_DIAG_FILE_MISSING, &
                      TR_DIAG_OUT_OF_RANGE_AFTER_DEP
  USE TRCOM0,   ONLY: NSM
  USE trcomm,   ONLY: rkind, &
       NRMAX, NSMAX, NT, T, NTMAX, MODELG, KNAMEQ, &
       MDLUF, PN, PNS, PT, PTS, &
       WPT, AJT, Q0, BETA0, BETAP0, BETAA, BETAN, &
       TAUE1, TAUE2, ZEFF0, ALI, RQ1, RN, RT, AJ, QP, &
       AJRFT, &
       EXTERNAL_DRIVEN_I, EXTERNAL_DRIVEN_RW, &
       ALLOCATE_TRCOMM, DEALLOCATE_TRCOMM
  USE tr_param_registry, ONLY: tr_param_set, tr_param_set_str, tr_param_generation, &
       tr_param_note_external_set
  USE eq_param_registry, ONLY: eq_param_set, eq_param_set_str
  ! EQ's mesh sizes and the compile-time maxima of its arrays (the ones eq_validate checks, eq/eq_api.f90). Renamed:
  ! TRCOMM has an NRMAX of its own.
  USE eqcom0_mod, ONLY: eq_NRGM => NRGM, eq_NZGM => NZGM, eq_NPSM => NPSM, eq_NSGM => NSGM, eq_NTGM => NTGM, &
                        eq_NUGM => NUGM, eq_NRM => NRM, eq_NTHM => NTHM, eq_NSUM => NSUM, eq_NRVM => NRVM
  USE eqcom1_mod, ONLY: eq_NSGMAX => NSGMAX, eq_NTGMAX => NTGMAX, eq_NUGMAX => NUGMAX, eq_NRGMAX => NRGMAX, &
                        eq_NZGMAX => NZGMAX, eq_NPSMAX => NPSMAX, eq_NRMAX => NRMAX, eq_NTHMAX => NTHMAX, &
                        eq_NSUMAX => NSUMAX, eq_NRVMAX => NRVMAX
  USE libnf,             ONLY: nf_finalize
  USE plinit,            ONLY: pl_init
  USE equnit,            ONLY: eq_init
  USE trinit,            ONLY: trinit_fortran => tr_init
  USE trprep,            ONLY: tr_prep
  USE trloop,            ONLY: tr_loop
  USE trbpsd,            ONLY: tr_eq_init
  USE trfailure
  IMPLICIT NONE
  PRIVATE
  PUBLIC :: tr_api_init, tr_api_run, tr_api_get_state, tr_api_history_get, &
            tr_api_set_param, tr_api_set_param_str, tr_api_finalize, tr_api_history_name, &
            tr_api_validate, tr_api_history_length, tr_api_history_full, tr_api_history_count, &
            tr_check_bpsd_pull, tr_api_last_error, tr_api_scalar_count, tr_api_scalar_name, tr_api_get_scalar

  ! Error codes (must match tr_api.h enum):
  !   0 = OK
  !   1 = invalid parameter name / value
  !   2 = not initialized
  !   3 = calculation / initialization failed
  !   4 = (reserved, used in L-2 for "not implemented")
  INTEGER(C_INT), PARAMETER :: TR_OK              = 0
  INTEGER(C_INT), PARAMETER :: TR_ERR_INVALID     = 1
  INTEGER(C_INT), PARAMETER :: TR_ERR_NOT_INIT    = 2
  INTEGER(C_INT), PARAMETER :: TR_ERR_CALC_FAILED = 3

  ! Lifecycle flags (module-scope state, single instance only at L-3).
  ! #189: at most 3 findings per active species (density sign / zero
  ! density / temperature), species bounded by TR_MAX_NSMAX.
  ! + RIPS, RIPE (current_for_eq); + the equation switches, NPSCMAX and three per particle source
  ! (source_and_equation_violations; NPSCM = 10, tr/trcomm_const.f90); + NRMAX (mesh_violation); + the ten EQ mesh sizes
  ! (eq_mesh_violation)
  INTEGER, PARAMETER :: SPC_MAX_VIOL = 3 * TR_MAX_NSMAX + 2 + 6 + 3 * 10 + 1 + 10

  LOGICAL, SAVE :: g_initialized = .FALSE.
  LOGICAL, SAVE :: g_prepared    = .FALSE.
  ! Registry mutation counter seen by the last successful prep (#253).
  ! -1 = never prepared. See tr_param_generation in the registry.
  INTEGER, SAVE :: g_prep_generation = -1
  ! NRMAX of this process's first tr_prep attempt; 0 = none yet. Kept across
  ! tr_finalize and tr_init, as bpsd's splines are (see mesh_violation).
  INTEGER, SAVE :: g_first_nrmax = 0
  ! The same fact seen from the eq: names: once this process has made a preparation attempt (g_first_nrmax /= 0), an
  ! eq: set is refused (eq_name_refused), for the same bpsd reason. Both come off together with 61ff3cdf's guard.
  ! The sizes of the scalar table and of the history table (the constructors below must match them).
  INTEGER, PARAMETER :: N_SCALARS = 31, N_HISTORY = 47

  ! #246: layout query, callable before tr_init.
  PUBLIC :: tr_api_state_abi_version, tr_api_state_size

CONTAINS

  !-------------------------------------------------------------------
  ! tr_init : allocate TRCOMM and populate default parameter values.
  !-------------------------------------------------------------------
  FUNCTION tr_api_init() RESULT(ierr) BIND(C, NAME="tr_init")
    INTEGER(C_INT) :: ierr
    INTEGER :: alloc_ierr, ios_close

    IF (g_initialized) THEN
       ! Idempotent: already initialized, just return OK.
       ierr = TR_OK
       RETURN
    END IF

    ! Initialize parameter defaults through the standard stack used by
    ! trmain.f90: pl_init, eq_init, tr_init (Fortran) all set their own
    ! namelist defaults.
    CALL pl_init
    CALL eq_init
    ! Mirror trmain.f90:57 — open the scratch unit that tr_set_metric
    ! and friends use for inline namelist (eq_parm(2,'nrmax= 51',...))
    ! buffering. lib/libkio.f90:248-258 hard-codes WRITE(7)/REWIND(7),
    ! so NEWUNIT= is not viable; this matches the legacy convention
    ! used by trmain/eqmain. Without it, the C ABI path computes
    ! initial profiles with junk geometry and trcalc produces
    ! NEGATIVE TEMPERATURE at step 0 (Layer 1 repro: tr_tst2 MODELG=3).
    BLOCK
       INTEGER :: ios
       OPEN(7, STATUS='SCRATCH', FORM='FORMATTED', IOSTAT=ios)
       IF (ios /= 0) THEN
          ierr = TR_ERR_CALC_FAILED
          RETURN
       END IF
    END BLOCK
    CALL trinit_fortran

    ! Allocate TRCOMM arrays using NRMAX / NSMAX (etc.) defaults set by
    ! trinit_fortran.
    CALL ALLOCATE_TRCOMM(alloc_ierr)
    IF (alloc_ierr /= 0) THEN
       ! Pair the OPEN(7) above so a failed init does not leak the
       ! scratch unit (Bugbot MED on PR #103).
       CLOSE(7, IOSTAT=ios_close)
       ierr = TR_ERR_CALC_FAILED
       RETURN
    END IF

    ! The MODELG=9 flag "adopt EQ's psi_p" is saved module state that a
    ! run clears; a new lifecycle starts from its initial value (#228).
    tr_eq_init    = .TRUE.
    g_initialized = .TRUE.
    g_prepared    = .FALSE.
    ! Library mode: tr_loop, tr_set_metric and tr_exec record their failures and
    ! tr_loop tests the periodic equilibrium solve. Only this entry sets it.
    tr_library_mode = .TRUE.
    CALL tr_failure_clear()      ! a new lifecycle starts with no failure on record
    ierr = TR_OK
  END FUNCTION tr_api_init

  !-------------------------------------------------------------------
  ! tr_set_param : dispatch to the parameter registry.
  !-------------------------------------------------------------------
  FUNCTION tr_api_set_param(name, value) RESULT(ierr) BIND(C, NAME="tr_set_param")
    CHARACTER(KIND=C_CHAR), DIMENSION(*), INTENT(IN) :: name
    REAL(C_DOUBLE), VALUE,                INTENT(IN) :: value
    INTEGER(C_INT) :: ierr
    CHARACTER(LEN=64) :: fname
    INTEGER :: i, n, eq_rc

    IF (.NOT. g_initialized) THEN
       ierr = TR_ERR_NOT_INIT
       RETURN
    END IF

    ! Convert C string (NUL-terminated) to Fortran string.
    fname = ' '
    n = 0
    DO i = 1, LEN(fname)
       IF (name(i) == C_NULL_CHAR) EXIT
       fname(i:i) = name(i)
       n = i
    END DO
    ! A name longer than the buffer is refused, not cut: what the cut
    ! leaves can be another parameter's name ("RR", blanks, anything).
    IF (i > LEN(fname)) THEN
       IF (c_str_overflows(name, LEN(fname) + 1)) THEN
          ierr = TR_ERR_INVALID
          RETURN
       END IF
    END IF

    ! An "eq:" name belongs to EQ's registry (the same one tot's "eq:"
    ! names reach). A set that EQ takes changes what the next preparation
    ! reads, so TR prepares again before its next run.
    IF (n > 3) THEN
       IF (fname(1:3) == 'eq:') THEN
          IF (eq_name_refused('tr_set_param', fname(4:n))) THEN
             ierr = TR_ERR_INVALID
             RETURN
          END IF
          CALL eq_param_set(fname(4:n), REAL(value, rkind), eq_rc)
          IF (eq_rc /= 0) THEN
             ierr = TR_ERR_INVALID
          ELSE
             CALL tr_param_note_external_set()
             ierr = TR_OK
          END IF
          RETURN
       END IF
    END IF

    ! NRMAX is settable. Changing the mesh between preparations in one
    ! process needs a bpsd with the spline-resize fix (see the README).
    IF (tr_param_set(TRIM(fname), value) /= 0) THEN
       ierr = TR_ERR_INVALID
    ELSE
       ! A successful set advances the registry's mutation counter;
       ! tr_run compares it with g_prep_generation and re-runs tr_prep
       ! (#253: the same holds for sets that reach the registry without
       ! passing through here, such as tot's "tr:" dispatcher).
       ierr = TR_OK
    END IF
  END FUNCTION tr_api_set_param

  !-------------------------------------------------------------------
  ! tr_set_param_str : string-valued parameter setter (KNAMEQ, ...).
  !
  ! Accepts two NUL-terminated C strings. Neither is cut: a name that
  ! does not fit the 64-character buffer is refused, and so is a value
  ! that does not fit the 128-character one or, in the registry, the
  ! 80 characters of KNAMEQ (trailing blanks are not counted).
  !-------------------------------------------------------------------
  FUNCTION tr_api_set_param_str(name, value) RESULT(ierr) BIND(C, NAME="tr_set_param_str")
    CHARACTER(KIND=C_CHAR), DIMENSION(*), INTENT(IN) :: name
    CHARACTER(KIND=C_CHAR), DIMENSION(*), INTENT(IN) :: value
    INTEGER(C_INT) :: ierr
    CHARACTER(LEN=64)  :: fname
    CHARACTER(LEN=128) :: fvalue
    INTEGER :: i

    IF (.NOT. g_initialized) THEN
       ierr = TR_ERR_NOT_INIT
       RETURN
    END IF

    ! Convert both C strings (NUL-terminated) to Fortran strings.
    fname = ' '
    DO i = 1, LEN(fname)
       IF (name(i) == C_NULL_CHAR) EXIT
       fname(i:i) = name(i)
    END DO
    ! A name longer than the buffer is refused, not cut: what the cut
    ! leaves can be another parameter's name ("RR", blanks, anything).
    IF (i > LEN(fname)) THEN
       IF (c_str_overflows(name, LEN(fname) + 1)) THEN
          ierr = TR_ERR_INVALID
          RETURN
       END IF
    END IF
    fvalue = ' '
    DO i = 1, LEN(fvalue)
       IF (value(i) == C_NULL_CHAR) EXIT
       fvalue(i:i) = value(i)
    END DO
    ! As for the name: a value longer than the buffer is refused, not cut.
    IF (i > LEN(fvalue)) THEN
       IF (c_str_overflows(value, LEN(fvalue) + 1)) THEN
          ierr = TR_ERR_INVALID
          RETURN
       END IF
    END IF

    ! "eq:" names go to EQ's string setter, as in tr_api_set_param.
    IF (LEN_TRIM(fname) > 3) THEN
       IF (fname(1:3) == 'eq:') THEN
          IF (eq_name_refused('tr_set_param_str', fname(4:LEN_TRIM(fname)))) THEN
             ierr = TR_ERR_INVALID
             RETURN
          END IF
          IF (eq_param_set_str(fname(4:LEN_TRIM(fname)), TRIM(fvalue)) /= 0) THEN
             ierr = TR_ERR_INVALID
          ELSE
             CALL tr_param_note_external_set()
             ierr = TR_OK
          END IF
          RETURN
       END IF
    END IF

    IF (tr_param_set_str(TRIM(fname), TRIM(fvalue)) /= 0) THEN
       ierr = TR_ERR_INVALID
    ELSE
       ! Changing KNAMEQ (equilibrium data file) alters the tr_prep
       ! inputs; the registry's mutation counter makes the next tr_run
       ! rebuild (see tr_api_set_param).
       ierr = TR_OK
    END IF
  END FUNCTION tr_api_set_param_str

  !-------------------------------------------------------------------
  ! tr_run : advance the simulation by ntmax_in steps.
  !
  ! NOTE: the dummy arg is `ntmax_in` (not `ntmax`) to avoid case-
  ! insensitive collision with the TRCOMM global `NTMAX` imported above.
  ! BIND(C, NAME="tr_run") keeps the external symbol as `tr_run`.
  !-------------------------------------------------------------------
  FUNCTION tr_api_run(ntmax_in) RESULT(ierr) BIND(C, NAME="tr_run")
    INTEGER(C_INT), VALUE, INTENT(IN) :: ntmax_in
    INTEGER(C_INT) :: ierr
    INTEGER :: ntmax_save, calc_ierr, prep_ierr
    INTEGER :: nviol, i
    CHARACTER(LEN=TR_DIAG_PARAM_LEN) :: vnames(SPC_MAX_VIOL)
    INTEGER(C_INT)                   :: vcodes(SPC_MAX_VIOL)
    CHARACTER(LEN=TR_DIAG_MSG_LEN)   :: vmsgs(SPC_MAX_VIOL)

    CALL tr_failure_clear()      ! the record of the last failure belongs to one tr_run
    IF (.NOT. g_initialized) THEN
       ierr = TR_ERR_NOT_INIT
       RETURN
    END IF
    IF (ntmax_in < 0) THEN
       ierr = TR_ERR_INVALID
       RETURN
    END IF

    ! tr_prep builds the initial profile, metric and bpsd state. It must
    ! run before the first tr_loop call and any time a parameter was set
    ! since the last prep: the registry counts every successful set
    ! (tr_param_generation), from tr_api_set_param or from tot's "tr:"
    ! dispatcher alike (#253), and a changed count means re-prep.
    IF (.NOT. g_prepared .OR. g_prep_generation /= tr_param_generation()) THEN
       ! NSMAX above the solver's compile-time NSM: tr_api_validate
       ! reports it, but a caller that skips validate must not reach
       ! tr_prep with it (the registry accepts up to TR_MAX_NSMAX=8).
       IF (NSMAX > NSM) THEN
          WRITE(6, '(A,I0,A,I0)') 'XX tr_run: NSMAX=', NSMAX, &
               ' exceeds the compile-time maximum NSM=', NSM
          ierr = TR_ERR_INVALID
          RETURN
       END IF
       ! #189: refuse, before any work, an active species whose namelist
       ! profile the solver cannot evolve (see species_profile_violations).
       ! Same contract as fp_run (#242): one line per violation on unit 6,
       ! TR_ERR_INVALID returned, handle stays usable.
       CALL species_profile_violations(nviol, vnames, vcodes, vmsgs)
       CALL source_and_equation_violations(nviol, vnames, vcodes, vmsgs)
       CALL mesh_violation(nviol, vnames, vcodes, vmsgs)
       CALL eq_mesh_violation(nviol, vnames, vcodes, vmsgs)
       IF (nviol > 0) THEN
          DO i = 1, nviol
             WRITE(6, '(A)') 'XX tr_run: '//TRIM(vnames(i))//': '//TRIM(vmsgs(i))
          END DO
          ierr = TR_ERR_INVALID
          RETURN
       END IF
       ! The first attempt fixes the mesh, failed or not: tr_prep can size
       ! bpsd's splines (tr_set_metric) and then fail later (tr_prof_impurity).
       IF (g_first_nrmax == 0) g_first_nrmax = NRMAX
       ! Not prepared until tr_prep succeeds: a preparation that fails before it starts the history again
       ! (NGT = 0) leaves the rows of the run before, which are not this run's (history_rows gives 0).
       g_prepared = .FALSE.
       CALL tr_prep(prep_ierr)
       IF (prep_ierr /= 0) THEN
          CALL tr_failure_record(TRF_PREP_FAILED, prep_ierr, NT, T, 'tr_prep failed')
          ierr = TR_ERR_CALC_FAILED
          RETURN
       END IF
       g_prepared = .TRUE.
       g_prep_generation = tr_param_generation()
    END IF

    ! Override NTMAX for this call so tr_loop steps exactly ntmax_in
    ! times. tr_loop increments NT internally; restoring NTMAX afterwards
    ! leaves the namelist-configured value intact for subsequent calls.
    ntmax_save = NTMAX
    NTMAX      = NT + ntmax_in
    CALL tr_loop(calc_ierr)
    NTMAX      = ntmax_save
    IF (calc_ierr /= 0) THEN
       ! A failure that tr_loop's callees did not record is kept as OTHER.
       CALL tr_failure_record(TRF_OTHER, calc_ierr, NT, T, 'tr_loop returned a non-zero status')
       ierr = TR_ERR_CALC_FAILED
       RETURN
    END IF

    ierr = TR_OK
  END FUNCTION tr_api_run

  !-------------------------------------------------------------------
  ! tr_get_state : populate the C-visible state struct.
  !
  ! The scalar / profile set matches trregress.f90 so that Layer-1 tests
  ! (L-6) can diff a C-driven run against a Fortran-driven run.
  !-------------------------------------------------------------------
  FUNCTION tr_api_get_state(state) RESULT(ierr) BIND(C, NAME="tr_get_state")
    TYPE(tr_state_c), INTENT(OUT) :: state
    INTEGER(C_INT) :: ierr
    INTEGER :: nr, ns

    ! Always zero the struct so callers never see uninitialized memory.
    state%nt     = 0
    state%nrmax  = 0
    state%nsmax  = 0
    state%T      = 0.0_C_DOUBLE
    state%WPT    = 0.0_C_DOUBLE
    state%AJT    = 0.0_C_DOUBLE
    state%Q0     = 0.0_C_DOUBLE
    state%BETA0  = 0.0_C_DOUBLE
    state%BETAP0 = 0.0_C_DOUBLE
    state%BETAA  = 0.0_C_DOUBLE
    state%BETAN  = 0.0_C_DOUBLE
    state%TAUE1  = 0.0_C_DOUBLE
    state%TAUE2  = 0.0_C_DOUBLE
    state%ZEFF0  = 0.0_C_DOUBLE
    state%ALI    = 0.0_C_DOUBLE
    state%RQ1    = 0.0_C_DOUBLE
    state%RN     = 0.0_C_DOUBLE
    state%RT     = 0.0_C_DOUBLE
    state%AJ     = 0.0_C_DOUBLE
    state%QP     = 0.0_C_DOUBLE
    state%AJRFT  = 0.0_C_DOUBLE     ! L-7b-i

    IF (.NOT. g_initialized) THEN
       ierr = TR_ERR_NOT_INIT
       RETURN
    END IF

    IF (NRMAX > TR_MAX_NRMAX .OR. NSMAX > TR_MAX_NSMAX) THEN
       ! Refusing rather than silently truncating: the static layout
       ! cannot hold the requested grid, the caller needs to rebuild
       ! libtrapi with a larger TR_MAX_* constant.
       ierr = TR_ERR_CALC_FAILED
       RETURN
    END IF

    ! Scalars (match trregress.f90 dump set).
    state%nt     = NT
    state%nrmax  = NRMAX
    state%nsmax  = NSMAX
    state%T      = T
    state%WPT    = WPT
    state%AJT    = AJT
    state%Q0     = Q0
    state%BETA0  = BETA0
    state%BETAP0 = BETAP0
    state%BETAA  = BETAA
    state%BETAN  = BETAN
    state%TAUE1  = TAUE1
    state%TAUE2  = TAUE2
    state%ZEFF0  = ZEFF0
    state%ALI    = ALI
    state%RQ1    = RQ1
    state%AJRFT  = AJRFT             ! L-7b-i: includes EXTERNAL_DRIVEN_I contribution

    ! Profiles: only populate when TRCOMM arrays are allocated (they are
    ! after ALLOCATE_TRCOMM succeeds during tr_api_init). The transpose
    ! state%RN(ns, nr) = RN(nr, ns) takes care of the Fortran column-major
    ! vs C row-major layout (see §4.2 of the design doc).
    IF (ALLOCATED(RN) .AND. ALLOCATED(RT) .AND. &
        ALLOCATED(AJ) .AND. ALLOCATED(QP)) THEN
       DO nr = 1, NRMAX
          DO ns = 1, NSMAX
             state%RN(ns, nr) = RN(nr, ns)
             state%RT(ns, nr) = RT(nr, ns)
          END DO
          state%AJ(nr) = AJ(nr)
          state%QP(nr) = QP(nr)
       END DO
    END IF

    ierr = TR_OK
  END FUNCTION tr_api_get_state

  !-------------------------------------------------------------------
  ! tr_finalize : release TRCOMM arrays and clear the lifecycle flags.
  !-------------------------------------------------------------------
  FUNCTION tr_api_finalize() RESULT(ierr) BIND(C, NAME="tr_finalize")
    INTEGER(C_INT) :: ierr

    IF (.NOT. g_initialized) THEN
       ! Idempotent: nothing to free, but not an error either.
       ierr = TR_OK
       RETURN
    END IF

    CALL DEALLOCATE_TRCOMM
    ! libnf's id_nf_nnf is per-session state that DEALLOCATE_TRCOMM cannot
    ! reach (module cycle -- see nf_finalize).  Without this it survives
    ! into the next init, where tr_prep_pnf's ALLOCATED guard reads .TRUE.
    ! for a table the new session never built.
    CALL nf_finalize
    ! Pair with the OPEN(7) in tr_api_init so re-init after finalize
    ! does not try to OPEN an already-open unit (SCRATCH would auto-
    ! delete on program exit but a same-process re-init would fail).
    CLOSE(7, IOSTAT=ierr)
    tr_eq_init    = .TRUE.
    g_initialized = .FALSE.
    g_prepared    = .FALSE.
    ierr = TR_OK
  END FUNCTION tr_api_finalize

  !-------------------------------------------------------------------
  ! Issue #143 pilot: pre-run cross-parameter validation.
  !
  ! Returns up to diag_cap diagnostics in diag(0..ndiag-1). Read-only:
  ! does NOT modify any tr state. Caller workflow:
  !   tr_init -> tr_set_param(...) -> tr_validate -> fix -> tr_run
  !
  ! Categories covered at L-3 pilot:
  !   OUT_OF_RANGE: NSMAX overflow vs TRCOM0 compile-time NSM=4. The
  !                 registry accepts NSMAX in [2, 8] (matching the C
  !                 ABI TR_MAX_NSMAX capacity); values 5..8 then
  !                 overflow the TRCOM0::NSM compile-time maximum used
  !                 by several pl/ak imports, so trip this check
  !                 before tr_run lets the mesh hit the mismatch.
  !   FILE_MISSING: MODELG in {3,5,7,8} requires non-blank KNAMEQ. This
  !                 mirrors the eq_api::eq_api_validate guard — without
  !                 it, tr_run -> pl_prof_init -> equnit::eq_load opens
  !                 "" silently and fills the post-load grid with garbage.
  !
  !   OUT_OF_RANGE / OUT_OF_RANGE_AFTER_DEP (#189): per-species namelist
  !                 profile (PN/PNS/PT/PTS) that the solver cannot evolve,
  !                 and RIPS or RIPE < 0 with MODELG 9; tr_run refuses the
  !                 same findings (see species_profile_violations).
  !
  !   OUT_OF_RANGE / INCONSISTENT_PAIR: the equation switches and the
  !                 particle sources (see source_and_equation_violations).
  !   OUT_OF_RANGE_AFTER_DEP: an NRMAX other than the process's first
  !                 (see mesh_violation).
  !
  ! Future category (a follow-up PR): MISSING_REQUIRED.
  !
  ! Note: NSZMAX / NSNMAX are NOT settable via tr_set_param, so they stay
  ! at their tr_init defaults. NRMAX is settable, and the registry refuses
  ! a value outside 3 .. TR_MAX_NRMAX, so it never exceeds the state
  ! struct.
  !-------------------------------------------------------------------
  FUNCTION tr_api_validate(diag, diag_cap, ndiag) &
           RESULT(ierr) BIND(C, NAME="tr_validate")
    TYPE(tr_diag_entry_c), INTENT(OUT) :: diag(diag_cap)
    INTEGER(C_INT), VALUE, INTENT(IN)  :: diag_cap
    INTEGER(C_INT),        INTENT(OUT) :: ndiag
    INTEGER(C_INT) :: ierr
    INTEGER :: nlocal
    INTEGER :: nviol, i
    CHARACTER(LEN=TR_DIAG_PARAM_LEN) :: vnames(SPC_MAX_VIOL)
    INTEGER(C_INT)                   :: vcodes(SPC_MAX_VIOL)
    CHARACTER(LEN=TR_DIAG_MSG_LEN)   :: vmsgs(SPC_MAX_VIOL)

    IF (.NOT. g_initialized) THEN
       ndiag = 0
       ierr  = TR_ERR_NOT_INIT
       RETURN
    END IF

    nlocal = 0

    ! ---- OUT_OF_RANGE: NSMAX overflow vs TRCOM0::NSM=4. -----------
    CALL push_oor("NSMAX", NSMAX, NSM)

    ! ---- FILE_MISSING: MODELG in {3,5,7,8} requires non-blank KNAMEQ.
    !      Without it, a subsequent tr_run path opens "" silently and
    !      fills the post-load grid with garbage:
    !        - MODELG 3/5/8: tr_run -> pl_prof_init -> equnit::eq_load
    !        - MODELG 7:     tr_set_metric -> pl_vmec (VMEC reader,
    !                        also takes KNAMEQ as the input filename)
    !      --------------------------------------------------------
    IF (MODELG == 3 .OR. MODELG == 5 .OR. MODELG == 7 .OR. MODELG == 8) THEN
       IF (LEN_TRIM(KNAMEQ) == 0) THEN
          CALL push_diag("KNAMEQ", TR_DIAG_FILE_MISSING, &
               "MODELG=3/5/7/8 requires non-blank KNAMEQ (eq/VMEC file)")
       END IF
    END IF

    ! ---- #189: per-species namelist profile sanity (every MDLUF outside
    !      the UFILE modes 1/2/3). Same
    !      findings that make tr_run refuse; here they are diagnostics.
    CALL species_profile_violations(nviol, vnames, vcodes, vmsgs)
    ! ---- The equation switches and the particle source (see
    !      source_and_equation_violations), also refused by tr_run.
    CALL source_and_equation_violations(nviol, vnames, vcodes, vmsgs)
    CALL mesh_violation(nviol, vnames, vcodes, vmsgs)
    CALL eq_mesh_violation(nviol, vnames, vcodes, vmsgs)
    DO i = 1, nviol
       CALL push_diag(TRIM(vnames(i)), vcodes(i), TRIM(vmsgs(i)))
    END DO

    ! ---- L-7b-i: OUT_OF_RANGE: EXTERNAL_DRIVEN_I requires positive width.
    !      Non-zero I with non-positive RW would silently normalize to zero
    !      in trprf, leaving AJRF unchanged. Surface this so callers know
    !      their setting was no-op rather than physically applied.
    IF (EXTERNAL_DRIVEN_I /= 0.D0 .AND. EXTERNAL_DRIVEN_RW <= 0.D0) THEN
       CALL push_diag("EXTERNAL_DRIVEN_RW", TR_DIAG_OUT_OF_RANGE, &
            "non-positive width with non-zero EXTERNAL_DRIVEN_I; profile cannot be normalized (silent no-op)")
    END IF

    ndiag = nlocal
    IF (nlocal == 0) THEN
       ierr = TR_OK
    ELSE
       ierr = TR_ERR_INVALID
    END IF

  CONTAINS

    !---------------------------------------------------------------
    ! Emit an OUT_OF_RANGE diagnostic if requested > max_value.
    !---------------------------------------------------------------
    SUBROUTINE push_oor(name_str, requested, max_value)
      CHARACTER(LEN=*), INTENT(IN) :: name_str
      INTEGER, INTENT(IN)          :: requested, max_value
      CHARACTER(LEN=TR_DIAG_MSG_LEN) :: m
      IF (requested <= max_value) RETURN
      WRITE(m, '(A,I0,A,I0)') &
           "value ", requested, " exceeds compile-time maximum ", max_value
      CALL push_diag(name_str, TR_DIAG_OUT_OF_RANGE, m)
    END SUBROUTINE push_oor

    !---------------------------------------------------------------
    ! Append (param, code, msg) to diag(). Skips storage if diag_cap
    ! is exhausted but still increments nlocal so the caller can
    ! detect truncation via ndiag_out > diag_cap.
    !---------------------------------------------------------------
    SUBROUTINE push_diag(name_str, code_in, msg_in)
      CHARACTER(LEN=*), INTENT(IN) :: name_str, msg_in
      INTEGER(C_INT),   INTENT(IN) :: code_in
      INTEGER :: i, n
      nlocal = nlocal + 1
      IF (nlocal > diag_cap) RETURN
      ! Zero-fill, then copy + NUL-terminate.
      DO i = 1, TR_DIAG_PARAM_LEN
         diag(nlocal)%param(i) = C_NULL_CHAR
      END DO
      n = MIN(LEN_TRIM(name_str), TR_DIAG_PARAM_LEN - 1)
      DO i = 1, n
         diag(nlocal)%param(i) = name_str(i:i)
      END DO
      DO i = 1, TR_DIAG_MSG_LEN
         diag(nlocal)%msg(i) = C_NULL_CHAR
      END DO
      n = MIN(LEN_TRIM(msg_in), TR_DIAG_MSG_LEN - 1)
      DO i = 1, n
         diag(nlocal)%msg(i) = msg_in(i:i)
      END DO
      diag(nlocal)%code = code_in
    END SUBROUTINE push_diag

  END FUNCTION tr_api_validate

  ! ----- L-7b-ii: BPSD broker round-trip verification -------------
  ! Non-mutating: pulls the 3 eq-pushed BPSD slots (device, equ1D,
  ! metric1D) into LOCAL discardable types and reports ok = 1 iff
  ! all three per-slot ierr == 0. plasmaf is intentionally NOT
  ! checked; it is tr's own BPSD output (tr_bpsd_put), absent on a
  ! fresh eq->tr pipeline. Each local %nrmax is set to 0 to trigger
  ! BPSD's self-allocation path (per ../../bpsd/bpsd_equ1D.f90:143).
  SUBROUTINE tr_check_bpsd_pull(ok) BIND(C, NAME="tr_check_bpsd_pull")
    USE iso_c_binding, ONLY: c_int
    USE bpsd, ONLY: bpsd_get_data
    USE bpsd_types, ONLY: bpsd_device_type, bpsd_equ1D_type, &
                          bpsd_metric1D_type
    INTEGER(c_int), INTENT(OUT) :: ok
    TYPE(bpsd_device_type)    :: dev_local
    TYPE(bpsd_equ1D_type)     :: eq_local
    TYPE(bpsd_metric1D_type)  :: met_local
    INTEGER :: ierr_dev, ierr_eq, ierr_met

    ! Initialize size fields to 0 so BPSD allocates internally
    ! (mode=0 path in bpsd_get_*). bpsd_device_type has no nrmax.
    eq_local%nrmax  = 0
    met_local%nrmax = 0

    CALL bpsd_get_data(dev_local, ierr_dev)
    CALL bpsd_get_data(eq_local,  ierr_eq)
    CALL bpsd_get_data(met_local, ierr_met)

    IF (ierr_dev == 0 .AND. ierr_eq == 0 .AND. ierr_met == 0) THEN
      ok = 1
    ELSE
      ok = 0
    END IF
  END SUBROUTINE tr_check_bpsd_pull

  !-------------------------------------------------------------------
  ! c_str_overflows : .TRUE. when the C string S holds, from position
  ! FIRST on (the first one the caller's buffer has no room for), a
  ! character other than a blank. Trailing blanks are no part of a
  ! name or a value, so a blank-padded string that is longer than the
  ! buffer only by blanks loses nothing when it is copied. Call it
  ! only when no NUL was met before FIRST. A string with no NUL within
  ! C_STR_SCAN characters from FIRST is refused as well.
  !-------------------------------------------------------------------
  PURE FUNCTION c_str_overflows(s, first) RESULT(over)
    CHARACTER(KIND=C_CHAR), DIMENSION(*), INTENT(IN) :: s
    INTEGER,                              INTENT(IN) :: first
    LOGICAL :: over
    INTEGER, PARAMETER :: C_STR_SCAN = 4096
    INTEGER :: j

    over = .TRUE.
    DO j = first, first + C_STR_SCAN - 1
       IF (s(j) == C_NULL_CHAR) THEN
          over = .FALSE.
          RETURN
       END IF
       IF (s(j) /= ' ') RETURN
    END DO
  END FUNCTION c_str_overflows

  ! ----- #189: namelist profile sanity per active species -----------
  ! With MDLUF=0 (no UFILE data; every fixture and sample input in the
  ! repo) tr_prof builds RN/RT for ns = 1..NSMAX from the namelist pairs
  ! PN/PNS (centre / edge density) and PT/PTS (centre / edge
  ! temperature). The transport step then divides by the density and
  ! temperature of every active species, so a species whose profile is
  ! identically zero or negative turns the whole state into NaN after
  ! the first step (reproduced with the tst2 fixture: NSMAX=3 leaves
  ! species 3 at the tr_init defaults PN(3)=PNS(3)=0 -> WPT/BETA*/TAUE*
  ! = NaN; the same with PT(3)=0, PTS(3)=0 or PN(3)<0). PN(ns)=0 with
  ! PNS(ns)>0 is refused as well (task-web-client #190): the profile
  ! then falls to zero at the axis (RN = 1e-7 at the first grid point
  ! of the tst2 case with PN(2)=0, PNS(2)=1e-3), and the run fails
  ! (tr_prep's impurity dilution goes negative; a negative temperature
  ! at step 0, or at step 9 for species 3 of tst2, which a 2-step run
  ! missed) or ends with WPT, Q0, the betas and TAUE NaN (TR's defaults
  ! with PN(2)=0). A zero edge density of
  ! species 1 or 2 is refused: the edge transport divides by it (PNSS(1),
  ! PNSS(2), trcalc.f90). Non-finite values (the C setter accepts any
  ! double) are reported too. With MODELG 9, RIPS or RIPE < 0 is
  ! reported as well (current_for_eq, below).
  !
  ! Scope: tr_prof's `case default` branch, i.e. every MDLUF outside
  ! {1,2,3}, builds all species from the namelist and is checked in
  ! full. The UFILE modes MDLUF=1/2/3 take most profiles from the
  ! RNU/RTU arrays but still read PN/PNS (and PT/PTS) for some species,
  ! selected by MDNI / MODEP / RHOA inside tr_prof; that subset is not
  ! mirrored here (no UFILE fixture in the repo to verify it against) and
  ! is tracked as a follow-up.
  !
  ! Returns one (param, code, message) triple per finding; param uses
  ! the registry's "PN[ns]" spelling so a caller can set it directly.
  ! Species are bounded by the array extents: NSMAX above NSM is
  ! reported separately by tr_api_validate's OUT_OF_RANGE check.
  SUBROUTINE species_profile_violations(nviol, vnames, vcodes, vmsgs)
    INTEGER,                          INTENT(OUT) :: nviol
    CHARACTER(LEN=TR_DIAG_PARAM_LEN), INTENT(OUT) :: vnames(SPC_MAX_VIOL)
    INTEGER(C_INT),                   INTENT(OUT) :: vcodes(SPC_MAX_VIOL)
    CHARACTER(LEN=TR_DIAG_MSG_LEN),   INTENT(OUT) :: vmsgs(SPC_MAX_VIOL)
    INTEGER :: ns, nsa

    nviol = 0
    IF (MDLUF == 1 .OR. MDLUF == 2 .OR. MDLUF == 3) RETURN
    ! With MODELG 9 TR has EQ solve the equilibrium with TR's own current (equnit's eq_calc, from
    ! tr_set_metric and every NTEQIT steps), and EQ's analytic solve does not treat the sign of the
    ! current (eq_run refuses a negative one: eq_api.f90): refuse it here, before the run. After the
    ! UFILE modes' return above: there the current comes from the UFILE, not from RIPS and RIPE.
    CALL current_for_eq
    nsa = MIN(NSMAX, SIZE(PN), SIZE(PNS), SIZE(PT), SIZE(PTS), TR_MAX_NSMAX)
    DO ns = 1, nsa
       IF (.NOT. (IEEE_IS_FINITE(PN(ns)) .AND. IEEE_IS_FINITE(PNS(ns)) &
            .AND. IEEE_IS_FINITE(PT(ns)) .AND. IEEE_IS_FINITE(PTS(ns)))) THEN
          CALL add("PN", ns, TR_DIAG_OUT_OF_RANGE, &
               "non-finite PN, PNS, PT or PTS for active species: the run produces NaN")
          CYCLE
       END IF
       IF (PN(ns) < 0.D0 .OR. PNS(ns) < 0.D0) THEN
          CALL add("PN", ns, TR_DIAG_OUT_OF_RANGE, &
               "negative density (PN or PNS) for active species: the run produces NaN")
       ELSE IF (PN(ns) == 0.D0 .AND. PNS(ns) == 0.D0) THEN
          CALL add("PN", ns, TR_DIAG_OUT_OF_RANGE_AFTER_DEP, &
               "PN and PNS both 0 for a species <= NSMAX: zero density everywhere, NaN after one step; set PN/PNS or lower NSMAX")
       ELSE IF (PN(ns) == 0.D0) THEN
          ! PNS > 0 here: the profile falls to zero at the axis, where the transport divides by it
          ! (task-web-client #190; see the header).
          CALL add("PN", ns, TR_DIAG_OUT_OF_RANGE, &
               "zero centre density (PN = 0, PNS > 0) for active species: the density vanishes at the axis; " // &
               "the run fails or produces NaN")
       ELSE IF (ns <= 2 .AND. PNS(ns) == 0.D0) THEN
          ! The edge terms of the transport divide by the edge density of the electrons and of the
          ! bulk ions (PNSS(1), PNSS(2) in trcalc.f90): the run ends with WPT, the betas and TAUE NaN.
          CALL add("PNS", ns, TR_DIAG_OUT_OF_RANGE, &
               "zero edge density of species 1 or 2 (the electrons, the bulk ions), which the edge " // &
               "transport divides by: the run produces NaN")
       END IF
       IF (PT(ns) <= 0.D0) THEN
          CALL add("PT", ns, TR_DIAG_OUT_OF_RANGE, &
               "non-positive centre temperature for active species: the run produces NaN")
       END IF
       IF (PTS(ns) <= 0.D0) THEN
          CALL add("PTS", ns, TR_DIAG_OUT_OF_RANGE, &
               "non-positive edge temperature for active species: the run produces NaN")
       END IF
    END DO

  CONTAINS

    SUBROUTINE current_for_eq
      USE TRCOMM, ONLY : RIPE, RIPS          ! MODELG comes with the module's own USE
      IF (MODELG /= 9) RETURN
      IF (RIPS < 0.D0) CALL scalar("RIPS")
      IF (RIPE < 0.D0) CALL scalar("RIPE")
    END SUBROUTINE current_for_eq

    SUBROUTINE scalar(name)
      CHARACTER(LEN=*), INTENT(IN) :: name
      IF (nviol >= SPC_MAX_VIOL) RETURN
      nviol = nviol + 1
      vnames(nviol) = name
      vcodes(nviol) = TR_DIAG_OUT_OF_RANGE
      vmsgs(nviol)  = "negative plasma current with MODELG 9: EQ's analytic solve, which MODELG 9 runs, " // &
           "does not treat its sign"
    END SUBROUTINE scalar

    SUBROUTINE add(base, idx, code_in, msg_in)
      CHARACTER(LEN=*), INTENT(IN) :: base, msg_in
      INTEGER,          INTENT(IN) :: idx
      INTEGER(C_INT),   INTENT(IN) :: code_in
      IF (nviol >= SPC_MAX_VIOL) RETURN
      nviol = nviol + 1
      WRITE(vnames(nviol), '(A,"[",I0,"]")') base, idx
      vcodes(nviol) = code_in
      vmsgs(nviol)  = msg_in
    END SUBROUTINE add

  END SUBROUTINE species_profile_violations

  ! ----- The equation switches and the particle source ---------------
  ! Appends to the findings already in vnames(1:nviol) (those of
  ! species_profile_violations) the values of these names that the
  ! solver cannot take; tr_run refuses them, tr_validate reports them.
  ! The registry made them settable for the PLATO case (NCLASS, the
  ! density equations, the gas puff); the namelist took them before.
  !
  !   - MDLEQB, MDLEQN, MDLPSC outside {0, 1}, MDLEQE outside {0, 1, 2}:
  !     TR_EQS_SELECT (trprep.f90) and TRPSC (trpsc.f90) test for these
  !     values only, and run any other as one of them without a word
  !     (measured: MDLEQN 2 runs with the densities fixed, MDLPSC 2
  !     with no source); MDLEQB 2 stopped inside tr_prep (equations
  !     without a species).
  !   - MDLEQE 1 or 2 with MDLEQN 0: TR_EQS_SELECT refuses it inside
  !     tr_prep (#142); here it is refused before the run, as #143 asks.
  !   - MDLEQE 2 (the bulk-ion density from quasi-neutrality) unless
  !     NSMAX is 2, species 2 is hydrogen or deuterium of charge 1, there
  !     is no impurity density (MDLIMP 0, or MDLIMP 1..4 with PNC and PNFE
  !     0: trprof.f90 scales ANC and ANFE by them) and no UFILE (MDLUF 0, where
  !     TR_EQS_SELECT may add a carbon species in tr_prep): trexec.f90
  !     sets the density of species 2 to the sum of |PZ| n over every
  !     other species and the impurities, which is quasi-neutrality only
  !     for the electrons alone; it adds the other ions instead of
  !     subtracting them, and a species 2 of another class (TR_TABLE's
  !     NSS 3 or 4) is never filled.
  !   - With MDLPSC 1, TRPSCA deposits NPSCMAX Gaussians in RA*rho,
  !     S = S0 exp(-((RA*rho - PSCR0)/PSCRW)**2) with S0 = PSCTOT over
  !     the volume integral of the exponential, into ion species NSPSC
  !     and the electrons:
  !       NPSCMAX outside 0..NPSCM: PSCTOT, PSCR0, PSCRW and NSPSC are
  !         read beyond their NPSCM elements;
  !       NSPSC[i] outside 2..NSMAX: SPSC(:, NSPSC) and PZ(NSPSC) are
  !         indexed out of bounds (0, above NSM), or the source adds no
  !         particle (1: the electrons, PZ(1) + 1 = 0; a species above
  !         NSMAX is not evolved). With a UFILE (MDLUF /= 0) TR_EQS_SELECT
  !         may change NSMAX in tr_prep, and only species 2 is sure to
  !         be evolved: the bound is 2 there, a deliberate restriction
  !         (the species TR_EQS_SELECT resolves are known only in tr_prep);
  !       PSCRW[i] <= 0: the exponent divides by it (NaN at 0); a negative
  !         width gives the same Gaussian as its absolute value and is
  !         refused so that the sign means nothing;
  !       PSCRW[i] below 1e-10 m or |PSCR0[i]| above 1e10 m: no device's
  !         source, and ((RA*rho - PSCR0)/PSCRW)**2 could overflow.
  !     A source many widths from every mesh point needs no check:
  !     TRPSCA normalises the exponential by its largest value first.
  ! Stops adding when the arrays are full: tr_run still refuses.
  SUBROUTINE source_and_equation_violations(nviol, vnames, vcodes, vmsgs)
    USE tr_state, ONLY : TR_DIAG_INCONSISTENT_PAIR
    USE trcomm, ONLY : MDLEQB, MDLEQN, MDLEQE, MDLPSC, NPSCMAX, &
                       NPSCM, PSCR0, PSCRW, NSPSC, PA, PZ, MDLIMP, PNC, PNFE
    INTEGER,                          INTENT(INOUT) :: nviol
    CHARACTER(LEN=TR_DIAG_PARAM_LEN), INTENT(INOUT) :: vnames(:)
    INTEGER(C_INT),                   INTENT(INOUT) :: vcodes(:)
    CHARACTER(LEN=TR_DIAG_MSG_LEN),   INTENT(INOUT) :: vmsgs(:)
    INTEGER :: i, nsup
    LOGICAL :: hydrogenic, impurity

    IF (MDLEQB /= 0 .AND. MDLEQB /= 1) CALL add("MDLEQB", 0, TR_DIAG_OUT_OF_RANGE, &
         "MDLEQB takes 0 or 1 (B_theta fixed or evolved)")
    IF (MDLEQN /= 0 .AND. MDLEQN /= 1) CALL add("MDLEQN", 0, TR_DIAG_OUT_OF_RANGE, &
         "MDLEQN takes 0 or 1 (densities fixed or evolved); another value runs as 0")
    IF (MDLEQE < 0 .OR. MDLEQE > 2) THEN
       CALL add("MDLEQE", 0, TR_DIAG_OUT_OF_RANGE, &
            "MDLEQE takes 0, 1 or 2 (electrons from quasi-neutrality, both solved, bulk ions from quasi-neutrality)")
    ELSE IF (MDLEQE /= 0 .AND. MDLEQN == 0) THEN
       CALL add("MDLEQE", 0, TR_DIAG_INCONSISTENT_PAIR, &
            "MDLEQE 1 or 2 needs MDLEQN 1 (the densities evolved)")
    ELSE IF (MDLEQE == 2) THEN
       hydrogenic = PA(2) == 1.D0 .OR. ABS(PA(2) - 2.D0) < 0.5D0
       ! MDLIMP 1..4 scale ANC and ANFE by PNC and PNFE; any other non-zero mode
       ! assigns them nothing in tr_prof_impurity, so they keep an earlier run's.
       impurity = MDLIMP /= 0 .AND. (MDLIMP < 1 .OR. MDLIMP > 4 .OR. PNC /= 0.D0 .OR. PNFE /= 0.D0)
       IF (MDLUF /= 0 .OR. NSMAX /= 2 .OR. .NOT. hydrogenic .OR. PZ(2) /= 1.D0 .OR. impurity) &
            CALL add("MDLEQE", 0, TR_DIAG_INCONSISTENT_PAIR, &
            "MDLEQE 2 only with NSMAX 2, species 2 H or D of PZ 1, no impurity, no UFILE: its quasi-neutrality adds the others")
    END IF
    IF (MDLPSC /= 0 .AND. MDLPSC /= 1) CALL add("MDLPSC", 0, TR_DIAG_OUT_OF_RANGE, &
         "MDLPSC takes 0 or 1 (no particle source, Gaussian sources); another value runs as 0")
    IF (MDLPSC /= 1) RETURN
    IF (NPSCMAX < 0 .OR. NPSCMAX > NPSCM) CALL add("NPSCMAX", 0, TR_DIAG_OUT_OF_RANGE, &
         "NPSCMAX outside 0..10 (NPSCM, the size of the source arrays PSCTOT, PSCR0, PSCRW, NSPSC)")
    nsup = NSMAX
    IF (MDLUF /= 0) nsup = 2
    DO i = 1, MIN(NPSCMAX, NPSCM)
       IF (NSPSC(i) < 2 .OR. NSPSC(i) > nsup) CALL add("NSPSC", i, TR_DIAG_OUT_OF_RANGE, &
            "NSPSC outside 2..NSMAX (only 2 with a UFILE): no evolved ion species takes the source (0 or above NSM: " // &
            "out of the arrays)")
       IF (PSCRW(i) < 1.D-10) CALL add("PSCRW", i, TR_DIAG_OUT_OF_RANGE, &
            "PSCRW below 1e-10 m: 0 ends in NaN, a negative width means nothing, a narrower one can overflow the exponent")
       IF (ABS(PSCR0(i)) > 1.D10) CALL add("PSCR0", i, TR_DIAG_OUT_OF_RANGE, &
            "|PSCR0| above 1e10 m: no source sits there (PSCR0 is in metres), and the exponent can overflow")
    END DO

  CONTAINS

    SUBROUTINE add(base, idx, code_in, msg_in)
      CHARACTER(LEN=*), INTENT(IN) :: base, msg_in
      INTEGER,          INTENT(IN) :: idx
      INTEGER(C_INT),   INTENT(IN) :: code_in
      IF (nviol >= MIN(SIZE(vnames), SIZE(vcodes), SIZE(vmsgs))) RETURN
      nviol = nviol + 1
      IF (idx > 0) THEN
         WRITE(vnames(nviol), '(A,"[",I0,"]")') base, idx
      ELSE
         vnames(nviol) = base
      END IF
      vcodes(nviol) = code_in
      vmsgs(nviol)  = msg_in
    END SUBROUTINE add

  END SUBROUTINE source_and_equation_violations

  ! ----- One TR mesh per process -------------------------------------
  ! bpsd sizes its equilibrium and metric splines at the first get and keeps
  ! that size (bpsd_get_equ1D, bpsd_get_metric1D): a later preparation on a
  ! larger mesh in the same process writes past them (measured under MODELG
  ! 3: NaN everywhere, or SIGSEGV), across tr_finalize and tr_init too.
  ! Until the pinned bpsd resizes them (k-yoshimi/bpsd#7), an NRMAX that
  ! differs from the one of this process's first tr_prep attempt (failed or
  ! not: tr_prep sizes the splines before steps that can fail) is refused,
  ! for every MODELG (MODELG 3 was measured to break; the others are held to
  ! the same rule rather than measured one by one); a task-web job, or a test
  ! under --forked, is a process of its own.
  SUBROUTINE mesh_violation(nviol, vnames, vcodes, vmsgs)
    INTEGER,                          INTENT(INOUT) :: nviol
    CHARACTER(LEN=TR_DIAG_PARAM_LEN), INTENT(INOUT) :: vnames(:)
    INTEGER(C_INT),                   INTENT(INOUT) :: vcodes(:)
    CHARACTER(LEN=TR_DIAG_MSG_LEN),   INTENT(INOUT) :: vmsgs(:)

    IF (g_first_nrmax == 0 .OR. NRMAX == g_first_nrmax) RETURN
    IF (nviol >= MIN(SIZE(vnames), SIZE(vcodes), SIZE(vmsgs))) RETURN
    nviol = nviol + 1
    vnames(nviol) = "NRMAX"
    vcodes(nviol) = TR_DIAG_OUT_OF_RANGE_AFTER_DEP
    WRITE(vmsgs(nviol), '(A,I0,A,I0,A)') "NRMAX ", NRMAX, " differs from ", g_first_nrmax, &
         ", this process's first: bpsd keeps its first mesh (k-yoshimi/bpsd#7); one NRMAX per process"
  END SUBROUTINE mesh_violation

  !-------------------------------------------------------------------
  ! tr_state_abi_version / tr_state_size : layout query (#246).
  !
  ! No lifecycle check and no side effect; callable before tr_init.
  ! A caller compares both with its own sizeof(tr_state_t) and its copy
  ! of TR_STATE_ABI_VERSION before passing a struct to tr_get_state;
  ! python/trlib/_ffi.py refuses the library when either differs.
  !-------------------------------------------------------------------
  FUNCTION tr_api_state_abi_version() RESULT(v) BIND(C, NAME="tr_state_abi_version")
    INTEGER(C_INT) :: v
    v = TR_STATE_ABI_VERSION
  END FUNCTION tr_api_state_abi_version

  FUNCTION tr_api_state_size() RESULT(n) BIND(C, NAME="tr_state_size")
    INTEGER(C_SIZE_T) :: n
    TYPE(tr_state_c) :: probe
    n = C_SIZEOF(probe)
  END FUNCTION tr_api_state_size

  !-------------------------------------------------------------------
  ! tr_last_error : the first failure of the last tr_run.
  !
  ! param = the kind (NONE, EQ_FAILED, NONFINITE, TR_CHECK, PREP_FAILED,
  ! OTHER; REFUSED is reserved for tr_continue and not recorded yet), code =
  ! the Fortran status, msg = "nt=<step> t=<time> s: <what failed>" (for
  ! EQ_FAILED the text ends with EQ's EQ_ERRMSG). Cleared at the start of every tr_run. Always TR_OK.
  !-------------------------------------------------------------------
  FUNCTION tr_api_last_error(e) RESULT(ierr) BIND(C, NAME="tr_last_error")
    TYPE(tr_diag_entry_c), INTENT(OUT) :: e
    INTEGER(C_INT) :: ierr
    INTEGER :: kind, code, nt_rec, i, n
    REAL(rkind) :: time
    CHARACTER(LEN=TR_FAILURE_DETAIL_LEN) :: detail
    INTEGER :: ios
    CHARACTER(LEN=TR_FAILURE_DETAIL_LEN + 40) :: full
    CHARACTER(LEN=TR_DIAG_PARAM_LEN) :: pname
    CHARACTER(LEN=TR_DIAG_MSG_LEN) :: msg
    CALL tr_failure_get(kind, code, nt_rec, time, detail)
    SELECT CASE (kind)
    CASE (TRF_NONE);        pname = 'NONE'
    CASE (TRF_EQ_FAILED);   pname = 'EQ_FAILED'
    CASE (TRF_NONFINITE);   pname = 'NONFINITE'
    CASE (TRF_TR_CHECK);    pname = 'TR_CHECK'
    CASE (TRF_PREP_FAILED); pname = 'PREP_FAILED'
    CASE (TRF_REFUSED);     pname = 'REFUSED'
    CASE DEFAULT;           pname = 'OTHER'
    END SELECT
    msg = ''
    ! The message is cut at the C buffer (TR_DIAG_MSG_LEN - 1 characters), and the write cannot abort on a long detail.
    IF (kind /= TRF_NONE) THEN
       WRITE(full, '(A,I0,A,ES14.7,A,A)', IOSTAT=ios) 'nt=', nt_rec, ' t=', time, ' s: ', TRIM(detail)
       IF (ios /= 0) full = 'a failure whose record does not fit'
       msg = full                    ! cut to the C buffer by the assignment
    END IF
    ! Zero-fill, then copy and NUL-terminate, as tr_validate's push_diag does.
    DO i = 1, TR_DIAG_PARAM_LEN
       e%param(i) = C_NULL_CHAR
    END DO
    n = MIN(LEN_TRIM(pname), TR_DIAG_PARAM_LEN - 1)
    DO i = 1, n
       e%param(i) = pname(i:i)
    END DO
    DO i = 1, TR_DIAG_MSG_LEN
       e%msg(i) = C_NULL_CHAR
    END DO
    n = MIN(LEN_TRIM(msg), TR_DIAG_MSG_LEN - 1)
    DO i = 1, n
       e%msg(i) = msg(i:i)
    END DO
    e%code = INT(code, C_INT)
    ierr = TR_OK
  END FUNCTION tr_api_last_error

  !-------------------------------------------------------------------
  ! eq_name_refused : true (and one line on unit 6) when an "eq:" name must not be set through TR.
  !
  ! nm is the name without its "eq:" prefix, who the calling routine.
  !  - EQ's RR, RA, RKAP, RDLT, BB, RIP and KNAMEQ do nothing here: under MODELG 9 eq_bpsd_get overwrites the first
  !    six from TR's device, and TR passes its own KNAMEQ to eq_load (tr/trmetric.f90); under MODELG 3/5/8
  !    tr_set_metric sets EQ's NRMAX, NTHMAX and NSUMAX. The message names TR's own parameter.
  !  - Once the process has made its first preparation attempt (g_first_nrmax /= 0) every eq: name is refused: a
  !    change of EQ's grid writes past bpsd's splines until the pinned bpsd has k-yoshimi/bpsd#7 (see mesh_violation).
  !-------------------------------------------------------------------
  FUNCTION eq_name_refused(who, nm) RESULT(refused)
    CHARACTER(LEN=*), INTENT(IN) :: who, nm
    LOGICAL :: refused
    CHARACTER(LEN=LEN(nm)) :: up
    INTEGER :: i, k
    up = nm
    DO i = 1, LEN(up)
       k = IACHAR(up(i:i))
       IF (k >= IACHAR('a') .AND. k <= IACHAR('z')) up(i:i) = ACHAR(k - 32)
    END DO
    refused = .TRUE.
    SELECT CASE (TRIM(up))
    CASE ('RIP')
       WRITE(6, '(A)') 'XX '//who//': eq:'//TRIM(nm)//" is not settable through TR: set RIPS and RIPE (TR's), "// &
            'which TR passes to EQ as RIP'
       RETURN
    CASE ('RR', 'RA', 'RKAP', 'RDLT', 'BB', 'KNAMEQ')
       WRITE(6, '(A)') 'XX '//who//': eq:'//TRIM(nm)//' is not settable through TR: set '//TRIM(up)// &
            " (TR's), which TR passes to EQ"
       RETURN
    END SELECT
    IF (g_first_nrmax /= 0) THEN
       WRITE(6, '(A)') 'XX '//who//': eq:'//TRIM(nm)//' refused: until the pinned bpsd has k-yoshimi/bpsd#7 an EQ '// &
            "grid change in one process corrupts memory, so eq: names are set before the process's first run"
       RETURN
    END IF
    refused = .FALSE.
  END FUNCTION eq_name_refused

  !-------------------------------------------------------------------
  ! eq_mesh_violation : EQ's mesh sizes (set through "eq:" names) against the compile-time maxima of EQ's arrays.
  !
  ! The same ten bounds as eq_validate (eq/eq_api.f90, push_oor), which the TR route to EQ did not apply: with
  ! MODELG 9, eq:NSGMAX=129 reached EQMESH, which wrote SIGM(129) past SIGM(NSGM=128) (eq/eqcalc.f90:63). The
  ! limits are EQ's own parameters (eqcom0_mod), not copies. Which of them matter depends on MODELG:
  !  - MODELG 9 solves the equilibrium itself (tr_set_metric: eq_prof, eq_calc): all ten.
  !  - MODELG 3, 5, 8 load a file (eq_load); tr_set_metric sets EQ's NRMAX, NTHMAX and NSUMAX there, so the other
  !    seven are held to their maxima.
  !  - Any other MODELG does not use EQ's grid: nothing is checked.
  ! Same contract as mesh_violation: appends (name, code, message) to the lists; the name carries the "eq:" prefix.
  !-------------------------------------------------------------------
  SUBROUTINE eq_mesh_violation(nviol, vnames, vcodes, vmsgs)
    INTEGER,                          INTENT(INOUT) :: nviol
    CHARACTER(LEN=TR_DIAG_PARAM_LEN), INTENT(INOUT) :: vnames(:)
    INTEGER(C_INT),                   INTENT(INOUT) :: vcodes(:)
    CHARACTER(LEN=TR_DIAG_MSG_LEN),   INTENT(INOUT) :: vmsgs(:)
    LOGICAL :: file_load, solve

    solve     = (MODELG == 9)
    file_load = (MODELG == 3 .OR. MODELG == 5 .OR. MODELG == 8)
    IF (.NOT. (solve .OR. file_load)) RETURN

    CALL check('eq:NSGMAX', eq_NSGMAX, eq_NSGM)
    CALL check('eq:NTGMAX', eq_NTGMAX, eq_NTGM)
    CALL check('eq:NUGMAX', eq_NUGMAX, eq_NUGM)
    CALL check('eq:NRGMAX', eq_NRGMAX, eq_NRGM)
    CALL check('eq:NZGMAX', eq_NZGMAX, eq_NZGM)
    CALL check('eq:NPSMAX', eq_NPSMAX, eq_NPSM)
    CALL check('eq:NRVMAX', eq_NRVMAX, eq_NRVM)
    IF (solve) THEN
       CALL check('eq:NRMAX',  eq_NRMAX,  eq_NRM)
       CALL check('eq:NTHMAX', eq_NTHMAX, eq_NTHM)
       CALL check('eq:NSUMAX', eq_NSUMAX, eq_NSUM)
    END IF

  CONTAINS

    SUBROUTINE check(name_str, requested, max_value)
      CHARACTER(LEN=*), INTENT(IN) :: name_str
      INTEGER, INTENT(IN)          :: requested, max_value
      IF (requested <= max_value) RETURN
      IF (nviol >= MIN(SIZE(vnames), SIZE(vcodes), SIZE(vmsgs))) RETURN
      nviol = nviol + 1
      vnames(nviol) = name_str
      vcodes(nviol) = TR_DIAG_OUT_OF_RANGE
      WRITE(vmsgs(nviol), '(A,I0,A,I0)') 'value ', requested, ' exceeds the compile-time maximum of EQ: ', max_value
    END SUBROUTINE check

  END SUBROUTINE eq_mesh_violation

  !-------------------------------------------------------------------
  ! Outputs by name (PR 2 of #96): the scalar table.
  !
  ! The names are TRCOMM's; each one is the value TRGLOB last computed
  ! (tr/trrslt_globals.f90; TRGLOB runs on output steps and on a run's
  ! last step, tr/trexec.f90 tr_eval), in the unit TRGLOB gives it:
  !   T s; WPT, WPDOT MJ and MW; AJT, AJRFT, AJOHT, AJNBT, AJBST, RIP MA;
  !   POHT, PNBT, PNFT, PRFST, PEXST, PRLT, POUT MW (PNFT is the charged fusion
  !   products' power: alpha for D-T, MDLNF 1-4; alpha and proton for D-He3,
  !   MDLNF 5, 6, trpnf.f90; QF = 5 PNFT / input is TRGLOB's D-T gain);
  !   PINT MW and includes PNFT (POHT+PNBT+PRFST+PNFT+PEXST);
  !   VLOOP V; TAUE1, TAUE2, TAUE98 s; RQ1 m; the rest have no unit.
  ! The order here is the order tr_scalar_name enumerates. RIP is the
  ! equilibrium's boundary current under MODELG 3, 5 and 8 (tr_bpsd_get,
  ! trbpsd.f90), the experimental data's under MDLUF 1 and 3 (tr_exec), the
  ! current set (RIPS to RIPE) otherwise. A tr_run of 0 steps evaluates no step
  ! (tr_loop returns before tr_eval): what the preparation sets is new (T 0,
  ! RIP = RIPS, Q0 under MODELG 2), what only a step computes is not.
  !-------------------------------------------------------------------
  PURE FUNCTION scalar_table() RESULT(names)
    CHARACTER(LEN=8) :: names(N_SCALARS)
    names = [ CHARACTER(LEN=8) :: &
         'T', 'WPT', 'AJT', 'Q0', 'BETA0', 'BETAP0', 'BETAA', 'BETAN', &
         'TAUE1', 'TAUE2', 'ZEFF0', 'ALI', 'RQ1', 'AJRFT', &
         'PNFT', 'QF', 'PINT', 'POHT', 'PNBT', 'PRFST', 'PEXST', 'PRLT', 'POUT', &
         'AJOHT', 'AJNBT', 'AJBST', 'RIP', 'VLOOP', 'WPDOT', 'H98Y2', 'TAUE98' ]
  END FUNCTION scalar_table

  ! The value of the scalar NAME (exact, upper case); FOUND is .FALSE. for a name not in the table.
  SUBROUTINE scalar_value(name, v, found)
    USE trcomm, ONLY: AJOHT, AJNBT, AJBST, PNFT, QF, PINT, POHT, PNBT, PRFST, PEXST, &
         PRLT, POUT, RIP, VLOOP, WPDOT, H98Y2, TAUE98
    CHARACTER(LEN=*), INTENT(IN)  :: name
    REAL(rkind),      INTENT(OUT) :: v
    LOGICAL,          INTENT(OUT) :: found

    found = .TRUE.
    SELECT CASE (name)
    CASE ('T');      v = T
    CASE ('WPT');    v = WPT
    CASE ('AJT');    v = AJT
    CASE ('Q0');     v = Q0
    CASE ('BETA0');  v = BETA0
    CASE ('BETAP0'); v = BETAP0
    CASE ('BETAA');  v = BETAA
    CASE ('BETAN');  v = BETAN
    CASE ('TAUE1');  v = TAUE1
    CASE ('TAUE2');  v = TAUE2
    CASE ('ZEFF0');  v = ZEFF0
    CASE ('ALI');    v = ALI
    CASE ('RQ1');    v = RQ1
    CASE ('AJRFT');  v = AJRFT
    CASE ('PNFT');   v = PNFT
    CASE ('QF');     v = QF
    CASE ('PINT');   v = PINT
    CASE ('POHT');   v = POHT
    CASE ('PNBT');   v = PNBT
    CASE ('PRFST');  v = PRFST
    CASE ('PEXST');  v = PEXST
    CASE ('PRLT');   v = PRLT
    CASE ('POUT');   v = POUT
    CASE ('AJOHT');  v = AJOHT
    CASE ('AJNBT');  v = AJNBT
    CASE ('AJBST');  v = AJBST
    CASE ('RIP');    v = RIP
    CASE ('VLOOP');  v = VLOOP
    CASE ('WPDOT');  v = WPDOT
    CASE ('H98Y2');  v = H98Y2
    CASE ('TAUE98'); v = TAUE98
    CASE DEFAULT
       v = 0.0_rkind
       found = .FALSE.
    END SELECT
  END SUBROUTINE scalar_value

  ! Copy the NUL-terminated C string S into FNAME (blank padded). OK is .FALSE. when it has no NUL within
  ! LEN(FNAME) characters, or is empty, or holds a blank: no name of this API is that long, empty or has one.
  SUBROUTINE c_name_to_fortran(s, fname, ok)
    CHARACTER(KIND=C_CHAR), DIMENSION(*), INTENT(IN)  :: s
    CHARACTER(LEN=*),                     INTENT(OUT) :: fname
    LOGICAL,                              INTENT(OUT) :: ok
    INTEGER :: i

    fname = ' '
    ok = .FALSE.
    DO i = 1, LEN(fname)
       IF (s(i) == C_NULL_CHAR) THEN
          ok = (i > 1)
          RETURN
       END IF
       IF (s(i) == ' ' .OR. s(i) < ' ') RETURN
       fname(i:i) = s(i)
    END DO
  END SUBROUTINE c_name_to_fortran

  ! Copy NAME into the C buffer BUF of BUFLEN characters with its NUL: 0, or TR_ERR_INVALID when it does not fit.
  FUNCTION name_to_c_buffer(name, buf, buflen) RESULT(ierr)
    CHARACTER(LEN=*),                     INTENT(IN)    :: name
    CHARACTER(KIND=C_CHAR), DIMENSION(*), INTENT(INOUT) :: buf
    INTEGER(C_INT),                       INTENT(IN)    :: buflen
    INTEGER(C_INT) :: ierr
    INTEGER :: i, n

    n = LEN_TRIM(name)
    IF (buflen < n + 1) THEN
       ierr = TR_ERR_INVALID
       RETURN
    END IF
    DO i = 1, n
       buf(i) = name(i:i)
    END DO
    buf(n + 1) = C_NULL_CHAR
    ierr = TR_OK
  END FUNCTION name_to_c_buffer

  ! tr_scalar_count : the number of named scalars.
  FUNCTION tr_api_scalar_count() RESULT(n) BIND(C, NAME="tr_scalar_count")
    INTEGER(C_INT) :: n
    n = INT(SIZE(scalar_table()), C_INT)
  END FUNCTION tr_api_scalar_count

  ! tr_scalar_name : the I-th name (1-based) as a NUL-terminated string in BUF of BUFLEN characters.
  ! TR_ERR_INVALID past either end or when the name and its NUL do not fit.
  FUNCTION tr_api_scalar_name(i, buf, buflen) RESULT(ierr) BIND(C, NAME="tr_scalar_name")
    INTEGER(C_INT), VALUE,                INTENT(IN)    :: i
    CHARACTER(KIND=C_CHAR), DIMENSION(*), INTENT(INOUT) :: buf
    INTEGER(C_INT), VALUE,                INTENT(IN)    :: buflen
    INTEGER(C_INT) :: ierr
    CHARACTER(LEN=8) :: tab(N_SCALARS)

    tab = scalar_table()
    IF (i < 1 .OR. i > SIZE(tab)) THEN
       ierr = TR_ERR_INVALID
       RETURN
    END IF
    ierr = name_to_c_buffer(tab(i), buf, buflen)
  END FUNCTION tr_api_scalar_name

  ! tr_get_scalar : the value of one named scalar, as of the last step TRGLOB ran on.
  ! TR_ERR_NOT_INIT before tr_init; TR_ERR_INVALID for a name not in the table (value is left alone).
  FUNCTION tr_api_get_scalar(name, value) RESULT(ierr) BIND(C, NAME="tr_get_scalar")
    CHARACTER(KIND=C_CHAR), DIMENSION(*), INTENT(IN)  :: name
    REAL(C_DOUBLE),                       INTENT(INOUT) :: value   ! left as it was for an error
    INTEGER(C_INT) :: ierr
    CHARACTER(LEN=16) :: fname
    REAL(rkind) :: v
    LOGICAL :: ok, found

    IF (.NOT. g_initialized) THEN
       ierr = TR_ERR_NOT_INIT
       RETURN
    END IF
    CALL c_name_to_fortran(name, fname, ok)
    IF (.NOT. ok) THEN
       ierr = TR_ERR_INVALID
       RETURN
    END IF
    CALL scalar_value(TRIM(fname), v, found)
    IF (.NOT. found) THEN
       ierr = TR_ERR_INVALID
       RETURN
    END IF
    value = v
    ierr = TR_OK
  END FUNCTION tr_api_get_scalar

  !-------------------------------------------------------------------
  ! Time history by name (PR 2 of #96, Task 5b).
  !
  ! TR records a row every NGTSTP steps (tr_eval, trexec.f90): GT(NGT) is
  ! the time and GVT(NGT, 1:NCTM) the globals, both single precision
  ! (GUCLIP), written by TRATOT in trrslt_globals.f90 (the column numbers
  ! below are TRATOT's). NTM rows (trcom0.f90); TRATOT stops recording
  ! when they are full. tr_prep sets NGT to 0 (trprep.f90), so a run starts a
  ! history and a re-preparation starts it again. In library mode tr_eval does not
  ! record the step a call of tr_run starts on when the call before it ended on
  ! it (the same T twice), nor the failed iterate of a TRCHCK failure (tr_exec),
  ! and tr_loop takes back the row of a step it finds not finite (NONFINITE).
  ! A failed preparation leaves no rows (g_prepared is false until tr_prep succeeds).
  ! Under MODELG 9 tr_loop records a step before it re-solves EQ on it (a
  ! multiple of NTEQIT) and then recomputes Q0 on the new metric: that row
  ! holds the Q0 of before the re-solve, tr_get_scalar the one after it.
  ! Columns 89 to 88 + 4 NGPST are also the sawtooth record's (TRATOTN, its
  ! own row count NGST) once MDLST /= 0 and T >= TSST (1e9 s); tr_eval does not
  ! call TRATOTN in library mode, so there they are always TRATOT's.
  !
  ! COL = 0: GT (the time); COL > 0: GVT column; BETAN and PRFST have no
  ! column of their own and are computed from columns of the same row:
  ! BETAN = 100 BETAA / (RIP / (RA BB)) (cols 85, 88, 98, 99, as TRGLOB),
  ! PRFST = PRFT(1) + ... + PRFT(4) (cols 42 to 45; NSM = 4 = the
  ! species TRGLOB sums). PEXST has no such columns (GVT holds PEXT(1:2) only).
  !-------------------------------------------------------------------
  SUBROUTINE history_table(names, cols)
    CHARACTER(LEN=8), INTENT(OUT) :: names(N_HISTORY)
    INTEGER,          INTENT(OUT) :: cols(N_HISTORY)
    names = [ CHARACTER(LEN=8) :: &
         'T', 'NE0', 'NEAV', 'TE0', 'TI0', 'TEAV', 'TIAV', 'WPT', &
         'AJT', 'AJOHT', 'AJNBT', 'AJRFT', 'AJBST', 'PINT', 'POHT', 'PNBT', &
         'PRFE', 'PRFD', 'PNFT', 'POUT', 'VLOOP', 'ALI', 'RQ1', 'Q0', &
         'WPDOT', 'TAUE1', 'TAUE2', 'BETAP0', 'BETA0', 'BETAA', 'ZEFF0', 'QF', &
         'RIP', 'PEXE', 'PEXI', 'PECE', 'PECI', 'PLHE', 'PLHI', 'PICE', &
         'PICI', 'TAUE98', 'H98Y2', 'NLAV', 'PRLT', &
         'BETAN', 'PRFST' ]
    cols = [ INTEGER :: &
         0, 1, 5, 9, 10, 13, 14, 33, 34, 35, 36, 37, 38, 39, 40, 41, &
         42, 43, 46, 57, 74, 75, 76, 77, 78, 79, 80, 82, 84, 85, 86, 87, &
         88, 89, 90, 91, 92, 93, 94, 95, 96, 102, 103, 104, 110, &
         -1, -2 ]
  END SUBROUTINE history_table

  ! Rows recorded since the last tr_prep: 0 when TR is not prepared.
  FUNCTION history_rows() RESULT(n)
    USE trcomm, ONLY: NGT, NTM
    INTEGER :: n
    IF (.NOT. g_prepared) THEN
       n = 0
    ELSE
       n = MAX(0, MIN(NGT, NTM))
    END IF
  END FUNCTION history_rows

  ! Row I of column COL (see history_table), in double precision.
  FUNCTION history_cell(col, i) RESULT(v)
    USE trcomm, ONLY: GT, GVT
    INTEGER, INTENT(IN) :: col, i
    REAL(rkind) :: v
    IF (col == 0) THEN
       v = REAL(GT(i), rkind)
    ELSE IF (col == -1) THEN
       v = 1.0E2_rkind * REAL(GVT(i, 85), rkind) / (REAL(GVT(i, 88), rkind) &
            / (REAL(GVT(i, 98), rkind) * REAL(GVT(i, 99), rkind)))
    ELSE IF (col == -2) THEN
       v = REAL(GVT(i, 42), rkind) + REAL(GVT(i, 43), rkind) + REAL(GVT(i, 44), rkind) + REAL(GVT(i, 45), rkind)
    ELSE
       v = REAL(GVT(i, col), rkind)
    END IF
  END FUNCTION history_cell

  ! tr_history_length : rows recorded since the last preparation (0 before one).
  FUNCTION tr_api_history_length() RESULT(n) BIND(C, NAME="tr_history_length")
    INTEGER(C_INT) :: n
    n = INT(history_rows(), C_INT)
  END FUNCTION tr_api_history_length

  ! tr_history_full : 1 when the history holds NTM rows and recording has stopped, else 0.
  FUNCTION tr_api_history_full() RESULT(full) BIND(C, NAME="tr_history_full")
    USE trcomm, ONLY: NTM
    INTEGER(C_INT) :: full
    full = 0
    IF (history_rows() >= NTM) full = 1
  END FUNCTION tr_api_history_full

  ! tr_history_count : the number of named columns.
  FUNCTION tr_api_history_count() RESULT(n) BIND(C, NAME="tr_history_count")
    INTEGER(C_INT) :: n
    n = N_HISTORY
  END FUNCTION tr_api_history_count

  ! tr_history_name : the I-th column name (1-based), as tr_scalar_name does.
  FUNCTION tr_api_history_name(i, buf, buflen) RESULT(ierr) BIND(C, NAME="tr_history_name")
    INTEGER(C_INT), VALUE,                INTENT(IN)    :: i
    CHARACTER(KIND=C_CHAR), DIMENSION(*), INTENT(INOUT) :: buf
    INTEGER(C_INT), VALUE,                INTENT(IN)    :: buflen
    INTEGER(C_INT) :: ierr
    CHARACTER(LEN=8) :: names(N_HISTORY)
    INTEGER :: cols(N_HISTORY)

    IF (i < 1 .OR. i > N_HISTORY) THEN
       ierr = TR_ERR_INVALID
       RETURN
    END IF
    CALL history_table(names, cols)
    ierr = name_to_c_buffer(names(i), buf, buflen)
  END FUNCTION tr_api_history_name

  ! tr_history_get : copy the first min(n, rows) rows of the column NAME ("T" is the time) into BUF;
  ! *got is the number copied. TR_ERR_NOT_INIT before tr_init; TR_ERR_INVALID for an unknown name or n < 0.
  FUNCTION tr_api_history_get(name, buf, n, got) RESULT(ierr) BIND(C, NAME="tr_history_get")
    CHARACTER(KIND=C_CHAR), DIMENSION(*), INTENT(IN)  :: name
    REAL(C_DOUBLE),                       INTENT(OUT) :: buf(*)
    INTEGER(C_INT), VALUE,                INTENT(IN)  :: n
    INTEGER(C_INT),                       INTENT(OUT) :: got
    INTEGER(C_INT) :: ierr
    CHARACTER(LEN=16) :: fname
    CHARACTER(LEN=8) :: names(N_HISTORY)
    INTEGER :: cols(N_HISTORY)
    INTEGER :: j, k, m
    LOGICAL :: ok

    got = 0
    IF (.NOT. g_initialized) THEN
       ierr = TR_ERR_NOT_INIT
       RETURN
    END IF
    CALL c_name_to_fortran(name, fname, ok)
    IF (.NOT. ok .OR. n < 0) THEN
       ierr = TR_ERR_INVALID
       RETURN
    END IF
    CALL history_table(names, cols)
    k = 0
    DO j = 1, N_HISTORY
       IF (TRIM(fname) == TRIM(names(j))) k = j
    END DO
    IF (k == 0) THEN
       ierr = TR_ERR_INVALID
       RETURN
    END IF
    m = MIN(INT(n), history_rows())
    DO j = 1, m
       buf(j) = history_cell(cols(k), j)
    END DO
    got = INT(m, C_INT)
    ierr = TR_OK
  END FUNCTION tr_api_history_get

END MODULE tr_api
