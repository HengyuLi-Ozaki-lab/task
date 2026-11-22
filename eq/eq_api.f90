! eq_api.f90
!
! Phase L-2/L-3: C ABI entry points for libeqapi.
!
! Eleven BIND(C) functions are exposed (eq_validate, eq_save and the layout
! queries eq_state_abi_version / eq_state_size are described where they
! are defined, at the end of the module):
!
!   eq_init           -> marks the library as initialized (idempotent)
!                        and returns EQ_OK. Does NOT touch the legacy
!                        eq COMMON blocks so existing eq / pl / ak
!                        binaries keep bit-identical behavior.
!   eq_run            -> mode=0 solves the fixed-boundary Grad-Shafranov
!                        equation numerically from the parameters
!                        (EQCALC, then EQCALQ; no file).
!                        mode=1 loads the equilibrium file via
!                        equnit::eq_load using the current MODELG +
!                        KNAMEQ (MODELG=15 reads the fixed eqdb.dat).
!                        A mode above 1 returns EQ_ERR_NOT_IMPL, a
!                        negative one EQ_ERR_INVALID.
!   eq_set_param      -> delegates to eq_param_registry::eq_param_set
!                        (Phase L-3 real dispatch).
!   eq_set_param_str  -> delegates to eq_param_registry::eq_param_set_str
!                        for file-name parameters (KNAMEQ, KNAMWR, ...).
!   eq_get_state      -> reads grid dimensions and plasma scalars out of
!                        the legacy COMMON blocks via the F77 bridge
!                        routines in eq_api_common.f, then zeros the
!                        C struct and fills the scalars + 1D profiles
!                        up to the compile-time maxima in eq_state.
!   eq_finalize       -> clears the initialized flag. No COMMON cleanup
!                        yet (the legacy binaries rely on implicit
!                        static storage).
!   eq_last_error     -> copies the reason the most recent eq_run failed
!                        (eqcom1_mod::EQ_ERRMSG) into a C buffer.
!
! Name-collision resolution: equnit.f already defines MODULE equnit
! with PUBLIC eq_init. The C-visible symbol also has to be named
! eq_init (per the design spec), so the BIND(C, NAME="eq_init")
! wrapper lives in this module as FUNCTION eq_api_init. When the
! wrapper needs to call equnit::eq_init / eq_load it renames the
! import with
!   USE equnit, ONLY: equnit_eq_init => eq_init, equnit_eq_load => eq_load
! avoiding the name clash inside this module.
!
! See docs/superpowers/specs/2026-04-17-tr-library-design.md §4 for
! the overall C ABI shape; tr_api.f90 / ti_api.f90 are the L-3
! references.

MODULE eq_api
  USE, INTRINSIC :: ISO_C_BINDING
  USE eq_state, ONLY: EQ_STATE_ABI_VERSION
  USE eq_state, ONLY: eq_state_c, &
                      EQ_MAX_NRGM, EQ_MAX_NZGM, EQ_MAX_NPSM, &
                      EQ_MAX_NRM,  EQ_MAX_NTHM, EQ_MAX_NSUM, &
                      eq_diag_entry_c, &
                      EQ_DIAG_PARAM_LEN, EQ_DIAG_MSG_LEN, &
                      EQ_DIAG_OUT_OF_RANGE, EQ_DIAG_FILE_MISSING, &
                      EQ_DIAG_INCONSISTENT_PAIR, EQ_DIAG_OUT_OF_RANGE_AFTER_DEP
  USE eq_param_registry, ONLY: eq_param_set, eq_param_set_str
  ! Rename equnit::eq_init / eq_load away from the C-visible eq_init /
  ! eq_run symbols.
  USE equnit, ONLY: equnit_eq_init => eq_init, &
                    equnit_eq_load => eq_load
  ! Pull MODELG + KNAMEQ directly from plcomm so eq_api_run can forward
  ! them to equnit_eq_load without going through a COMMON-block bridge.
  ! MODEFW: eq_api_save looks at it before it lets EQSAVE open a file.
  USE plcomm, ONLY: MODELG, KNAMEQ, MODEFW
  ! QQPS provenance flag and the failure reason eq_last_error returns.
  USE eqcom1_mod, ONLY: QQPS_FROM_FILE, EQ_ERRMSG
  IMPLICIT NONE
  PRIVATE
  PUBLIC :: eq_api_init, eq_api_run, eq_api_get_state, &
            eq_api_set_param, eq_api_set_param_str, eq_api_finalize, &
            eq_api_validate, eq_api_save, eq_api_last_error

  ! Error codes. Must match eq_api.h.
  INTEGER(C_INT), PARAMETER :: EQ_OK              = 0
  INTEGER(C_INT), PARAMETER :: EQ_ERR_INVALID     = 1
  INTEGER(C_INT), PARAMETER :: EQ_ERR_NOT_INIT    = 2
  INTEGER(C_INT), PARAMETER :: EQ_ERR_CALC_FAILED = 3
  INTEGER(C_INT), PARAMETER :: EQ_ERR_NOT_IMPL    = 4

  ! Lifecycle flag. Module-scope, single-instance (same pattern as tr / ti).
  LOGICAL, SAVE :: g_initialized = .FALSE.
  ! .TRUE. while the fields hold the equilibrium that the last eq_run
  ! computed or loaded for the present parameters: what eq_save writes.
  ! Cleared by eq_init and eq_finalize, when an eq_run starts (one that
  ! fails leaves the fields part-way), and by a successful eq_set_param
  ! of anything but the two file modes (EQSAVE writes the parameters and
  ! counts as they stand, over fields computed for the old ones).
  LOGICAL, SAVE :: g_has_equilibrium = .FALSE.

  ! #246: layout query, callable before eq_init.
  PUBLIC :: eq_api_state_abi_version, eq_api_state_size

CONTAINS

  !-------------------------------------------------------------------
  ! eq_init : L-2 scaffold. Flip the lifecycle flag and return EQ_OK.
  !-------------------------------------------------------------------
  FUNCTION eq_api_init() RESULT(ierr) BIND(C, NAME="eq_init")
    INTEGER(C_INT) :: ierr
    ! Populate the eq COMMON defaults (NRMAX=50, NTHMAX=64, NSUMAX=65,
    ! MODELG=2, KNAMEQ='eqdata', ...). The C-ABI is the SOLE entry
    ! point in the libeqapi.so context (no eq menu driver runs), so
    ! these defaults MUST be set here -- otherwise NRMAX/NTHMAX stay 0
    ! and equnit::eq_load's save/restore of those counters around
    ! eqload() leaves the post-load grid sized 0, which then corrupts
    ! the heap inside SPL2D in eqcalq (the SPL2D calls sized by NTHMAX and NRMAX, eqcalq.f90:1164 and :1168). Callers can
    ! still override MODELG / KNAMEQ / etc. afterwards via
    ! eq_set_param / eq_set_param_str.
    CALL equnit_eq_init
    ! A new session starts without a g-eqdsk q column or a failure.
    QQPS_FROM_FILE = .FALSE.
    EQ_ERRMSG = ' '
    g_initialized = .TRUE.
    g_has_equilibrium = .FALSE.
    ierr = EQ_OK
  END FUNCTION eq_api_init

  !-------------------------------------------------------------------
  ! eq_run : dispatch on `mode` to the Grad-Shafranov solve or the file load.
  ! Before the dispatch below, an uninitialised library returns
  ! EQ_ERR_NOT_INIT and a negative mode EQ_ERR_INVALID.
  !
  !   mode == 0 : solve the fixed-boundary Grad-Shafranov equation
  !               numerically, without an equilibrium file: EQCALC
  !               iterates until the relative change of PSI is below
  !               EPSEQ (at most NLPMAX times, else EQ_ERR_CALC_FAILED),
  !               then EQCALQ computes the flux-surface quantities.
  !               Mirrors the legacy `eqx2` CLI's `R` command and is
  !               the natural run path when MODELG=2 (the default,
  !               toroidal geometry). EQCALC reads
  !               PP*/PJ*/FF*/PT*/PV* coefficients from the EQCOMM
  !               module and solves the fixed-boundary Grad-Shafranov
  !               problem; callers set those via eq_set_param
  !               beforehand.
  !   mode == 1 : load equilibrium from the file pointed to by KNAMEQ,
  !               then run eq_bpsd_init / eqcalq / eq_bpsd_put via
  !               equnit::eq_load. Mirrors the legacy `L` command.
  !               Requires a file format, MODELG ∈ {3, 5, 8, 9, 25}
  !               with a valid KNAMEQ (and KNAMEQ2 for 8), or 15 with
  !               the fixed eqdb.dat.
  !   mode > 1  : EQ_ERR_NOT_IMPL (reserved for future modes);
  !   mode < 0  : EQ_ERR_INVALID.
  !-------------------------------------------------------------------
  FUNCTION eq_api_run(mode) RESULT(ierr) BIND(C, NAME="eq_run")
    USE plcomm, ONLY: RIP
    INTEGER(C_INT), VALUE, INTENT(IN) :: mode
    INTEGER(C_INT) :: ierr
    INTEGER :: calc_ierr, load_ierr, ios
    CHARACTER(LEN=80) :: knameq_local
    ! Contract: NOT_INIT takes precedence over INVALID (mirrors tr_api_run).
    ! So callers that hit an uninitialised library always see the same
    ! NOT_INIT error regardless of what other arguments they passed.
    IF (.NOT. g_initialized) THEN
       ierr = EQ_ERR_NOT_INIT
       RETURN
    END IF
    ! eq_last_error reports on this run only.
    EQ_ERRMSG = ' '
    IF (mode < 0) THEN
       WRITE(EQ_ERRMSG, '(A,I0)', IOSTAT=ios) &
            'eq_run: mode must be 0 or 1, got ', mode
       ierr = EQ_ERR_INVALID
       RETURN
    END IF

    SELECT CASE (mode)
    CASE (0)
       ! A negative plasma current: the solve converges, but QAXIS and QSURF come out as the wall's q
       ! (FNPSIP, eqsplf.f90, clamps PSIT as if it grew outward), BETAT and BETAP 0, PVOL negative and
       ! RAAVE NaN, without a message; clamping both ways leaves most of it wrong, so the solve does not
       ! treat the sign. Refused here, before any work. EQCALC itself, and the coupled path (equnit's
       ! eq_calc, TR's MODELG 9, which TR refuses itself), are left as they are.
       IF (RIP < 0.D0) THEN
          WRITE(EQ_ERRMSG, '(A,1PE11.4,A)', IOSTAT=ios) 'eq_run: RIP =', RIP, &
               ' MA is negative; the analytic solve does not treat the sign of the current: give its magnitude'
          ierr = EQ_ERR_INVALID
          RETURN
       END IF
       ! The Grad-Shafranov solve via EQCALC, then post-process
       ! via EQCALQ to populate the ψ-surface profile + scalar
       ! diagnostics (qaxis/qsurf/betat/betap/pvol). EQCALC alone
       ! solves the fixed-boundary GS equation but doesn't compute the
       ! flux-surface averaged quantities; EQCALQ (also called by the
       ! `L` path after EQ_READ) computes the metric and reduces the
       ! 2D ψ-grid to 1D ψ-surface arrays. Mirrors the legacy CLI's
       ! `R` then `F` workflow.
       g_has_equilibrium = .FALSE.
       CALL EQCALC(calc_ierr)
       IF (calc_ierr /= 0) THEN
          CALL note_failure('EQCALC', calc_ierr)
          ierr = EQ_ERR_CALC_FAILED
          RETURN
       END IF
       CALL EQCALQ(calc_ierr)
       IF (calc_ierr /= 0) THEN
          CALL note_failure('EQCALQ', calc_ierr)
          ierr = EQ_ERR_CALC_FAILED
          RETURN
       END IF
       g_has_equilibrium = .TRUE.
       ierr = EQ_OK
    CASE (1)
       ! Equilibrium-file load via equnit::eq_load(MODELG, KNAMEQ, ierr).
       ! MODELG and KNAMEQ come from plcomm_parm; callers are expected
       ! to set them via eq_set_param / eq_set_param_str beforehand.
       knameq_local = KNAMEQ
       g_has_equilibrium = .FALSE.
       CALL equnit_eq_load(MODELG, knameq_local, load_ierr)
       IF (load_ierr /= 0) THEN
          CALL note_failure('equnit::eq_load', load_ierr)
          ierr = EQ_ERR_CALC_FAILED
          RETURN
       END IF
       g_has_equilibrium = .TRUE.
       ierr = EQ_OK
    CASE DEFAULT
       WRITE(EQ_ERRMSG, '(A,I0,A)', IOSTAT=ios) &
            'eq_run: mode ', mode, ' is not implemented (0 or 1)'
       ierr = EQ_ERR_NOT_IMPL
    END SELECT
  END FUNCTION eq_api_run

  !-------------------------------------------------------------------
  ! note_failure : give a failed eq_run a reason if the failing step
  ! did not set one (EQ_READ / EQCALQ set specific ones).
  !-------------------------------------------------------------------
  SUBROUTINE note_failure(step, code)
    CHARACTER(LEN=*), INTENT(IN) :: step
    INTEGER, INTENT(IN) :: code
    INTEGER :: ios
    IF (LEN_TRIM(EQ_ERRMSG) > 0) RETURN
    WRITE(EQ_ERRMSG, '(2A,I0,A)', IOSTAT=ios) &
         TRIM(step), ' failed (ierr=', code, ')'
  END SUBROUTINE note_failure

  !-------------------------------------------------------------------
  ! eq_set_param : delegate to the L-3 parameter registry.
  !-------------------------------------------------------------------
  FUNCTION eq_api_set_param(name, value) RESULT(ierr) &
           BIND(C, NAME="eq_set_param")
    CHARACTER(KIND=C_CHAR), DIMENSION(*), INTENT(IN) :: name
    REAL(C_DOUBLE), VALUE,                INTENT(IN) :: value
    INTEGER(C_INT) :: ierr
    CHARACTER(LEN=64) :: fname
    INTEGER :: i, reg_ierr

    IF (.NOT. g_initialized) THEN
       ierr = EQ_ERR_NOT_INIT
       RETURN
    END IF

    ! Convert C string (NUL-terminated) to Fortran string.
    fname = ' '
    DO i = 1, LEN(fname)
       IF (name(i) == C_NULL_CHAR) EXIT
       fname(i:i) = name(i)
    END DO
    ! A name longer than the buffer is refused, not cut: what the cut
    ! leaves can be another parameter's name ("RR", blanks, anything).
    IF (i > LEN(fname)) THEN
       IF (c_str_overflows(name, LEN(fname) + 1)) THEN
          ierr = EQ_ERR_INVALID
          RETURN
       END IF
    END IF

    CALL eq_param_set(TRIM(fname), value, reg_ierr)
    IF (reg_ierr == 0) THEN
       ! MODEFR and MODEFW say how a file is opened, not what the
       ! equilibrium is: they leave eq_save's precondition as it was.
       IF (TRIM(fname) /= 'MODEFW' .AND. TRIM(fname) /= 'MODEFR') &
          g_has_equilibrium = .FALSE.
       ierr = EQ_OK
    ELSE
       ierr = EQ_ERR_INVALID
    END IF
  END FUNCTION eq_api_set_param

  !-------------------------------------------------------------------
  ! eq_set_param_str : string-valued parameter setter (KNAMEQ, ...).
  !
  ! Mirrors the pattern in tr_api::tr_api_set_param_str.
  !-------------------------------------------------------------------
  FUNCTION eq_api_set_param_str(name, value) RESULT(ierr) &
           BIND(C, NAME="eq_set_param_str")
    CHARACTER(KIND=C_CHAR), DIMENSION(*), INTENT(IN) :: name
    CHARACTER(KIND=C_CHAR), DIMENSION(*), INTENT(IN) :: value
    INTEGER(C_INT) :: ierr
    CHARACTER(LEN=64) :: fname
    CHARACTER(LEN=80) :: fvalue
    INTEGER :: i, reg_ierr

    IF (.NOT. g_initialized) THEN
       ierr = EQ_ERR_NOT_INIT
       RETURN
    END IF

    fname = ' '
    DO i = 1, LEN(fname)
       IF (name(i) == C_NULL_CHAR) EXIT
       fname(i:i) = name(i)
    END DO
    ! A name longer than the buffer is refused, not cut: what the cut
    ! leaves can be another parameter's name ("RR", blanks, anything).
    IF (i > LEN(fname)) THEN
       IF (c_str_overflows(name, LEN(fname) + 1)) THEN
          ierr = EQ_ERR_INVALID
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
          ierr = EQ_ERR_INVALID
          RETURN
       END IF
    END IF

    reg_ierr = eq_param_set_str(TRIM(fname), TRIM(fvalue))
    ! g_has_equilibrium is left as it is, unlike in eq_api_set_param: the
    ! strings are file names (KNAMEQ and the other KNAM*). The analytic
    ! solve reads none of them; a load (eq_run(1)) reads its file and sets
    ! the flag itself; and KNAMEQ is where eq_save writes, so setting it
    ! must not invalidate what is to be saved.
    IF (reg_ierr == 0) THEN
       ierr = EQ_OK
    ELSE
       ierr = EQ_ERR_INVALID
    END IF
  END FUNCTION eq_api_set_param_str

  !-------------------------------------------------------------------
  ! eq_get_state : fill the C-visible struct from the legacy COMMON
  ! state via the F77 bridge in eq_api_common.f.
  !-------------------------------------------------------------------
  FUNCTION eq_api_get_state(state) RESULT(ierr) BIND(C, NAME="eq_get_state")
    TYPE(eq_state_c), INTENT(OUT) :: state
    INTEGER(C_INT) :: ierr
    INTEGER :: nrgmax_c, nzgmax_c, npsmax_c
    INTEGER :: nrmax_c,  nthmax_c, nsumax_c
    INTEGER :: nrvmax_c, nsgmax_c, ntgmax_c
    REAL(C_DOUBLE) :: raxis_v, zaxis_v, psi0_v, psipa_v, psita_v
    REAL(C_DOUBLE) :: qaxis_v, qsurf_v, betat_v, betap_v
    REAL(C_DOUBLE) :: pvol_v,  raave_v, ripx_v
    INTEGER :: ncopy_ps, nr_copy, nz_copy, nprof_copy

    ! Always zero the struct so callers never see uninitialized memory.
    state%nrgmax = 0
    state%nzgmax = 0
    state%npsmax = 0
    state%nrmax  = 0
    state%nthmax = 0
    state%nsumax = 0
    state%nrvmax = 0
    state%nsgmax = 0
    state%ntgmax = 0
    state%raxis  = 0.0_C_DOUBLE
    state%zaxis  = 0.0_C_DOUBLE
    state%psi0   = 0.0_C_DOUBLE
    state%psipa  = 0.0_C_DOUBLE
    state%psita  = 0.0_C_DOUBLE
    state%qaxis  = 0.0_C_DOUBLE
    state%qsurf  = 0.0_C_DOUBLE
    state%betat  = 0.0_C_DOUBLE
    state%betap  = 0.0_C_DOUBLE
    state%pvol   = 0.0_C_DOUBLE
    state%raave  = 0.0_C_DOUBLE
    state%ripx   = 0.0_C_DOUBLE
    state%psips  = 0.0_C_DOUBLE
    state%ppps   = 0.0_C_DOUBLE
    state%ttps   = 0.0_C_DOUBLE
    state%qqps   = 0.0_C_DOUBLE
    state%rg     = 0.0_C_DOUBLE
    state%zg     = 0.0_C_DOUBLE
    state%profile_psip = 0.0_C_DOUBLE
    state%profile_psit = 0.0_C_DOUBLE
    state%profile_pps  = 0.0_C_DOUBLE
    state%profile_tts  = 0.0_C_DOUBLE
    state%profile_qps  = 0.0_C_DOUBLE
    state%profile_vps  = 0.0_C_DOUBLE
    state%profile_rst  = 0.0_C_DOUBLE

    IF (.NOT. g_initialized) THEN
       ierr = EQ_ERR_NOT_INIT
       RETURN
    END IF

    ! Pull the current runtime counters (NRGMAX/NZGMAX/...) via the F77 bridge.
    ! Compile-time PARAMETER dims (NRGM/NZGM/...) are hard-encoded as
    ! EQ_MAX_* in eq_state.f90 and do not need a runtime fetch.
    CALL EQ_COMMON_GET_GRID_COUNTS(nrgmax_c, nzgmax_c, npsmax_c, &
                                   nrmax_c, nthmax_c, nsumax_c)

    state%nrgmax = nrgmax_c
    state%nzgmax = nzgmax_c
    state%npsmax = npsmax_c
    state%nrmax  = nrmax_c
    state%nthmax = nthmax_c
    state%nsumax = nsumax_c

    ! Secondary counters (NRVMAX/NSGMAX/NTGMAX) needed to mirror the
    ! Phase 0 baseline metrics for MODELG=3 EQRTSK loads.
    CALL EQ_COMMON_GET_AUX_GRID_COUNTS(nrvmax_c, nsgmax_c, ntgmax_c)
    state%nrvmax = nrvmax_c
    state%nsgmax = nsgmax_c
    state%ntgmax = ntgmax_c

    ! Per-NR flux-surface profile (NR=1..NRMAX) — mirrors the 7
    ! columns the Phase 0 baseline writes via eqregress.f. Indexed
    ! 1..NRMAX is the active runtime slice; trailing entries up to
    ! EQ_MAX_NRM stay zero from the initialisation above.
    !
    ! Bounds cap: the C-side state%profile_* arrays are sized
    ! EQ_MAX_NRM (1001) and the Fortran-side NRMAX (== nrmax_c) is
    ! nominally bounded by the same compile-time NRM=1001. Cap
    ! defensively with MIN(nrmax_c, EQ_MAX_NRM) anyway so a future
    ! resize of NRM (or stale eqcom1_mod state) cannot overflow the
    ! C buffer. Mirrors the same MIN(...) pattern used for the 1D
    ! profiles (npsmax_c) and the RZ grid (nrgmax_c/nzgmax_c) below.
    nprof_copy = MIN(nrmax_c, EQ_MAX_NRM)
    IF (nprof_copy > 0) THEN
       CALL EQ_COMMON_GET_PROFILE(nprof_copy, &
            state%profile_psip, state%profile_psit, &
            state%profile_pps,  state%profile_tts,  &
            state%profile_qps,  state%profile_vps,  &
            state%profile_rst)
    END IF

    ! Pull scalar plasma parameters.
    CALL EQ_COMMON_GET_SCALARS(raxis_v, zaxis_v, psi0_v, psipa_v, &
                               psita_v, qaxis_v, qsurf_v,         &
                               betat_v, betap_v, pvol_v,          &
                               raave_v, ripx_v)
    state%raxis = raxis_v
    state%zaxis = zaxis_v
    state%psi0  = psi0_v
    state%psipa = psipa_v
    state%psita = psita_v
    state%qaxis = qaxis_v
    state%qsurf = qsurf_v
    state%betat = betat_v
    state%betap = betap_v
    state%pvol  = pvol_v
    state%raave = raave_v
    state%ripx  = ripx_v

    ! 1D profile copy. NPSMAX can be zero before the first calc runs
    ! (L-2); cap at the compile-time maximum to avoid overruns.
    ncopy_ps = MIN(npsmax_c, EQ_MAX_NPSM)
    IF (ncopy_ps > 0) THEN
       CALL EQ_COMMON_GET_PROFILES_1D(ncopy_ps, state%psips, &
                                      state%ppps, state%ttps, &
                                      state%qqps)
    END IF

    ! RZ grid copy.
    nr_copy = MIN(nrgmax_c, EQ_MAX_NRGM)
    nz_copy = MIN(nzgmax_c, EQ_MAX_NZGM)
    IF (nr_copy > 0 .OR. nz_copy > 0) THEN
       CALL EQ_COMMON_GET_RZ_GRID(nr_copy, nz_copy, state%rg, state%zg)
    END IF

    ierr = EQ_OK
  END FUNCTION eq_api_get_state

  !-------------------------------------------------------------------
  ! eq_finalize : L-2 scaffold. Clear the flag, no COMMON cleanup.
  !-------------------------------------------------------------------
  FUNCTION eq_api_finalize() RESULT(ierr) BIND(C, NAME="eq_finalize")
    INTEGER(C_INT) :: ierr
    QQPS_FROM_FILE = .FALSE.
    EQ_ERRMSG = ' '
    g_initialized = .FALSE.
    g_has_equilibrium = .FALSE.
    ierr = EQ_OK
  END FUNCTION eq_api_finalize

  !-------------------------------------------------------------------
  ! eq_last_error : the reason the most recent eq_run failed, e.g. the
  ! file that could not be loaded or why the psi-surface grid was
  ! rejected. Copies at most buflen-1 characters of EQ_ERRMSG into buf
  ! and NUL-terminates it. Empty after a successful eq_run (eq_run
  ! clears it on entry) and after eq_init / eq_finalize.
  !-------------------------------------------------------------------
  FUNCTION eq_api_last_error(buf, buflen) RESULT(ierr) &
           BIND(C, NAME="eq_last_error")
    CHARACTER(KIND=C_CHAR), DIMENSION(*), INTENT(INOUT) :: buf
    INTEGER(C_INT), VALUE, INTENT(IN) :: buflen
    INTEGER(C_INT) :: ierr
    INTEGER :: i, n
    IF (.NOT. g_initialized) THEN
       ierr = EQ_ERR_NOT_INIT
       RETURN
    END IF
    IF (buflen < 1) THEN
       ierr = EQ_ERR_INVALID
       RETURN
    END IF
    n = MIN(LEN_TRIM(EQ_ERRMSG), buflen - 1)
    DO i = 1, n
       buf(i) = EQ_ERRMSG(i:i)
    END DO
    buf(n + 1) = C_NULL_CHAR
    ierr = EQ_OK
  END FUNCTION eq_api_last_error

  !-------------------------------------------------------------------
  ! Issue #143 pilot: pre-run cross-parameter validation.
  !
  ! Returns up to diag_cap diagnostics in diag(0..ndiag-1). Read-only:
  ! does NOT modify any eq state. Caller workflow:
  !   eq_init -> eq_set_param(...) -> eq_validate -> fix -> eq_run
  !
  ! Categories covered:
  !   OUT_OF_RANGE  : 10 EQCHEK overflow guards (NSGMAX/NTGMAX/NUGMAX/
  !                   NRGMAX/NZGMAX/NPSMAX/NRMAX/NTHMAX/NSUMAX/NRVMAX
  !                   vs the eqcom0_mod compile-time maxima), and a
  !                   negative RIP for an analytic solve (see below).
  !   FILE_MISSING  : the files a load reads: KNAMEQ blank or not there
  !                   for MODELG 3/5/8/9/25, KNAMEQ2 too for MODELG 8;
  !                   for MODELG 15 the fixed file eqdb.dat not there.
  !   INCONSISTENT_PAIR      : wall radius RB < minor radius RA, for an
  !                   analytic solve (the solver can abort or give a
  !                   wrong equilibrium).
  !   OUT_OF_RANGE_AFTER_DEP : the box RGMIN..ZGMAX leaves out RR or
  !                   Z = 0, or RGMAX is below RR+RA: where the solver
  !                   fails or cuts the plasma. Checked for an analytic
  !                   solve with MDLEQF >= 10 only; the file loads also
  !                   read the box then and are not checked (see the
  !                   long comment at the check): their failure says
  !                   where the axis search ended and the box
  !                   (eq_last_error).
  !
  ! validate() does not know the mode of the run to come, and goes by
  ! MODELG. The file formats (MODELG 3/5/8/9/15/25, what EQ_READ reads:
  ! eq/eqfile.f90:186-221) are taken to be loaded, run(1): they bring
  ! their own geometry (EQRTSK reads RA/RKAP/RDLT/RB from the TASK-native
  ! file; EQDSKR reconstructs RB = 1.1*RA), so their pre-run
  ! RR/RA/RB/RKAP say nothing about the run and are not checked. Any
  ! other MODELG can only be solved, run(0), and is the analytic solve:
  ! EQCALC does not read MODELG (0, 1, 2, 4, 6, 7, 26 and -1 give the
  ! same equilibrium, bit for bit). A file format solved with run(0) is
  ! the analytic solve too, and goes unchecked.
  !
  ! Future categories (left for follow-up PRs as the validation surface
  ! grows): MISSING_REQUIRED.
  !-------------------------------------------------------------------
  FUNCTION eq_api_validate(diag, diag_cap, ndiag) &
           RESULT(ierr) BIND(C, NAME="eq_validate")
    USE eqcom0_mod, ONLY: NRGM, NZGM, NPSM, NSGM, NTGM, NUGM, &
                          NRM, NTHM, NSUM, NRVM
    USE eqcom1_mod, ONLY: NSGMAX, NTGMAX, NUGMAX, NRGMAX, NZGMAX, &
                          NPSMAX, NRMAX, NTHMAX, NSUMAX, NRVMAX, &
                          RGMIN, RGMAX, ZGMIN, ZGMAX, MDLEQF
    USE plcomm, ONLY: rkind, RR, RA, RB, RKAP, RIP, KNAMEQ2
    USE equ_params, ONLY: eqfile
    TYPE(eq_diag_entry_c), INTENT(OUT) :: diag(diag_cap)
    INTEGER(C_INT), VALUE, INTENT(IN)  :: diag_cap
    INTEGER(C_INT),        INTENT(OUT) :: ndiag
    INTEGER(C_INT) :: ierr
    INTEGER :: nlocal
    INTEGER :: ios
    LOGICAL :: analytic
    CHARACTER(LEN=EQ_DIAG_MSG_LEN - 1) :: msgbuf   ! the C field keeps 127 characters + NUL

    IF (.NOT. g_initialized) THEN
       ndiag = 0
       ierr  = EQ_ERR_NOT_INIT
       RETURN
    END IF

    nlocal = 0
    ! The analytic solve: every MODELG but the file formats (see the header).
    analytic = .NOT. (MODELG == 3 .OR. MODELG == 5 .OR. MODELG == 8 .OR. &
                      MODELG == 9 .OR. MODELG == 15 .OR. MODELG == 25)

    ! ---- OUT_OF_RANGE: grid-overflow guards (port from EQCHEK in
    !      eqinit.f90:509-548; same checks the binary path runs at
    !      EQPARM time, missing from libeqapi.so callers). ---------
    CALL push_oor("NSGMAX", NSGMAX, NSGM)
    CALL push_oor("NTGMAX", NTGMAX, NTGM)
    CALL push_oor("NUGMAX", NUGMAX, NUGM)
    CALL push_oor("NRGMAX", NRGMAX, NRGM)
    CALL push_oor("NZGMAX", NZGMAX, NZGM)
    CALL push_oor("NPSMAX", NPSMAX, NPSM)
    CALL push_oor("NRMAX",  NRMAX,  NRM)
    CALL push_oor("NTHMAX", NTHMAX, NTHM)
    CALL push_oor("NSUMAX", NSUMAX, NSUM)
    CALL push_oor("NRVMAX", NRVMAX, NRVM)

    ! ---- FILE_MISSING: the files a load, run(1), reads (EQ_READ,
    !      eq/eqfile.f90): KNAMEQ for MODELG 3, 5, 8, 9 and 25, and for
    !      MODELG 8 KNAMEQ2 too (EQJAEAR, eq/eq-qst.f90), reported when
    !      blank or naming no file; for MODELG 15 the fixed file
    !      eqdb.dat (equ_params' eqfile: EQDSK in eq/equread.f90 does not
    !      read KNAMEQ), reported as MODELG when it is not there. The load
    !      fails on each of them too, and says which file, but only once
    !      the run is made. A name is looked up as the load opens it,
    !      relative to the working directory of the process at the time
    !      of validate(). (task-web-client #191)
    IF (MODELG == 3 .OR. MODELG == 5 .OR. MODELG == 8 .OR. &
        MODELG == 9 .OR. MODELG == 25) THEN
       IF (LEN_TRIM(KNAMEQ) == 0) THEN
          WRITE(msgbuf, '(A,I0,A)', IOSTAT=ios) "MODELG=", MODELG, &
               " loads the file KNAMEQ names, and KNAMEQ is blank"
          CALL push_diag("KNAMEQ", EQ_DIAG_FILE_MISSING, msgbuf)
       ELSE IF (.NOT. file_there(KNAMEQ)) THEN
          WRITE(msgbuf, '(3A,I0,A)', IOSTAT=ios) "KNAMEQ='", TRIM(KNAMEQ), &
               "' not found: MODELG=", MODELG, " loads it"
          IF (ios /= 0) WRITE(msgbuf, '(A,I0,A)', IOSTAT=ios) &
               "KNAMEQ not found: MODELG=", MODELG, " loads it (name unprintable)"
          CALL push_diag("KNAMEQ", EQ_DIAG_FILE_MISSING, msgbuf)
       END IF
       IF (MODELG == 8) THEN
          IF (LEN_TRIM(KNAMEQ2) == 0) THEN
             msgbuf = "MODELG=8 loads the file KNAMEQ2 names too, and KNAMEQ2 is blank"
             CALL push_diag("KNAMEQ2", EQ_DIAG_FILE_MISSING, msgbuf)
          ELSE IF (.NOT. file_there(KNAMEQ2)) THEN
             WRITE(msgbuf, '(3A)', IOSTAT=ios) "KNAMEQ2='", TRIM(KNAMEQ2), &
                  "' not found: MODELG=8 loads it too"
             IF (ios /= 0) msgbuf = "KNAMEQ2 not found: MODELG=8 loads it too (name unprintable)"
             CALL push_diag("KNAMEQ2", EQ_DIAG_FILE_MISSING, msgbuf)
          END IF
       END IF
    ELSE IF (MODELG == 15) THEN
       IF (.NOT. file_there(eqfile)) THEN
          WRITE(msgbuf, '(5A)', IOSTAT=ios) "MODELG=15 loads the fixed file '", &
               TRIM(eqfile), "', not KNAMEQ, and '", TRIM(eqfile), "' is not there"
          IF (ios /= 0) msgbuf = "MODELG=15 loads a fixed file, not KNAMEQ, and it is not there"
          CALL push_diag("MODELG", EQ_DIAG_FILE_MISSING, msgbuf)
       END IF
    END IF

    ! ---- INCONSISTENT_PAIR: the wall must enclose the plasma (RB >=
    !      RA) in an analytic solve. Measured: a large device (RR=6.2,
    !      RA=2.0) run through MODELG=2 mode=0 with RB left at the
    !      small-tokamak default (1.2) fails the run (EQMAGS cannot trace
    !      a surface; EQCALQP returns ierr=111 and eq_last_error says so;
    !      before that it read YA(:,0) in zminmax and ended the process);
    !      RB=0.8 with RA=1.0 runs but gives a different equilibrium
    !      than an enclosing wall (PVOL 57.97 against 59.16, the same for
    !      every MODELG solved), because the solve and its R-Z grid use the
    !      smaller RB (EQCALQ's RB=RA clamp comes after EQCALC in a mode-0
    !      run). Not for a file load, which brings its own RB: the TASK
    !      file eqdata.TST-2 (MODELG=3) loads the same equilibrium with
    !      RA=2.0 > RB=1.2 as with RA=0.2 (measured 2026-11-15).
    IF (analytic .AND. RB < RA) THEN
       ! IOSTAT guard (all three diagnostic WRITEs): RR/RA/RB/RKAP are
       ! externally settable, and an extreme value (e.g. RR=1e30,
       ! live-reproduced) makes the F0.3 rendering overflow the
       ! CHARACTER(127) internal file -> gfortran "End of record"
       ! ABORTS the process without IOSTAT — a library-reachable abort
       ! inside the function whose whole purpose is returning
       ! diagnostics instead of crashing. On overflow substitute a
       ! static message (kept LEN-safe and still naming the check).
       WRITE(msgbuf, '(A,F0.3,A,F0.3,A)', IOSTAT=ios) &
            "wall radius RB=", RB, " < minor radius RA=", RA, &
            " (the solver can abort or give a wrong equilibrium)"
       IF (ios /= 0) msgbuf = &
            "wall radius RB < minor radius RA (the solver can abort or give a wrong equilibrium; values unprintable)"
       CALL push_diag("RB", EQ_DIAG_INCONSISTENT_PAIR, msgbuf)
    END IF

    ! ---- OUT_OF_RANGE_AFTER_DEP: the box RGMIN/RGMAX/ZGMIN/ZGMAX,
    !      where the solver reads it: an analytic solve with MDLEQF >= 10.
    !      It is read in one place, EQAXIS (eq/eqsub.f90:58-121, from
    !      EQSETP and EQCALV; otherwise its window is RR +/- RB,
    !      +/- RKAP*RB), which asks two things of it: the magnetic axis
    !      must lie inside it (or the run fails, ierr=103), and RGMAX
    !      bounds the search for the outer edge (beyond it the plasma is
    !      cut at RGMAX). The axis starts at (RR, 0) (NEWTN steps from
    !      there) and moves as the solve goes on (outward with the
    !      Shafranov shift: RAXIS 3.070 for RR=3.0 at the defaults; inward
    !      with triangularity: 2.976 at RDLT=0.4), and the outer edge at
    !      Z=0 is RR+RA whatever RKAP and RDLT. So three things are flagged,
    !      each failing or cutting the plasma whatever the shift (measured
    !      2026-11-15, the defaults with MDLEQF=10, box [1.5, 4.5] x [-2, 2]):
    !        RR outside RGMIN..RGMAX (RGMIN=3.001 fails, 2.999 runs);
    !        RGMAX below RR+RA (3.999 cuts the plasma, PVOL 59.07 against
    !        59.16; 3.5 gives 11.7; below the axis, 3.05, the run fails;
    !        4.0 runs, every scalar within 4e-9 of the default box's, the
    !        edge search's tolerance). The solve's own edge lies 3.3e-4
    !        inside RR+RA (REDGE 3.99967 with the default box), so an RGMAX
    !        between the two is flagged though the run is the default
    !        box's (3.9998: PVOL within 1e-8);
    !        a Z range that leaves out Z=0, the axis of the up-down
    !        symmetric plasma (ZGMIN=0.5 and ZGMAX=-0.5 fail; ZGMAX=0.01
    !        runs). At ZGMIN=0 or ZGMAX=0 exactly, flagged too, the run
    !        turns on rounding: the axis's Z starts at exactly 0 and ends
    !        1e-12 (1e-10 on an ITER-sized case) to one side; both fail
    !        here (macOS arm64, -O0).
    !      What else the box leaves out of the plasma changes nothing:
    !      ZGMAX=0.01 (the plasma +/-1.0), RGMIN=2.999 (its inner edge at
    !      2.0) and RKAP=1.8 with ZGMAX=0.3 run with every scalar as with
    !      the default box. Not seen before the run: an axis that leaves
    !      the box as it moves (RDLT=0.4 with RGMIN=RR fails, ierr=103),
    !      and a Z bound inside the axis's rounding (ZGMIN=-1e-14 fails).
    !      After the solve EQCALQP overwrites the four with the traced
    !      plasma extent for any MDLEQF (eqcalq.f90:630-640; EQCALQV
    !      again for MDLEQF < 10, 1026-1037), so for MDLEQF < 10 they are
    !      outputs only. With MDLEQF >= 10 a validate() after a run reads
    !      the traced RGMAX, 3e-4 below RR+RA at the defaults: the edge is
    !      flagged, rightly once an input has changed, since the next
    !      run(0) of the same instance reads that box too (RR=3.4 then:
    !      PVOL 20.81 against 67.05 in a new instance), and needlessly for
    !      a run of the same input again (PVOL equal to 1.4e-13, the other
    !      scalars to 1e-11).
    !      The box is not the grid psi is tabulated on (EQTORZ: RR +/- RB).
    !      A file load (EQ_READ dispatch,
    !      eq/eqfile.f90:186-221: MODELG=3/9 -> EQRTSK, a TASK-native file
    !      carrying its own RG/ZG grids AND RA/RKAP/RDLT/RB; MODELG=5/25
    !      -> EQDSKR, grid rebuilt from the file's rdim/zdim; MODELG=8 ->
    !      EQJAEAR; MODELG=15 -> equread::eqdsk) sets the geometry itself,
    !      so the pre-run values say nothing about the loaded plasma. Not
    !      checked, hence a false negative for a load with MDLEQF >= 10,
    !      which reads the box too (EQAXIS: run(1) fails, ierr=103, and
    !      eq_last_error says where the axis search ended and the box,
    !      task-web-client #187): the axis it is held to is the one found
    !      in the file's psi, known only once the file is read. The
    !      eq_mcp ITER01 fixture (RR=6.2, RA=2.0, MODELG=3,
    !      test_server.py::test_init_set_run_get_state_cycle_iter01) is far
    !      outside the default box yet clean: validate() must return [].
    IF (analytic .AND. MDLEQF >= 10) THEN
       IF (RR < RGMIN .OR. RR > RGMAX) THEN
          WRITE(msgbuf, '(A,F0.3,A,F0.3,A,F0.3,A)', IOSTAT=ios) &
               "RR=", RR, " outside RGMIN..RGMAX [", RGMIN, ", ", RGMAX, &
               "]: the magnetic axis starts at RR, and must lie in the box (MDLEQF >= 10)"
          IF (ios /= 0) msgbuf = &
               "RR outside RGMIN..RGMAX: the magnetic axis starts at RR, and must lie in the box (MDLEQF >= 10; values unprintable)"
          CALL push_diag("RR", EQ_DIAG_OUT_OF_RANGE_AFTER_DEP, msgbuf)
       ELSE IF (RR + RA > RGMAX) THEN
          WRITE(msgbuf, '(A,F0.3,A,1PE9.3,A,0PF0.3,A)', IOSTAT=ios) &
               "outer edge RR+RA=", RR + RA, " lies ", RR + RA - RGMAX, " beyond RGMAX=", RGMAX, &
               ": the solve cuts the plasma at RGMAX, or fails (MDLEQF >= 10)"
          IF (ios /= 0) msgbuf = &
               "outer edge RR+RA beyond RGMAX: the solve cuts the plasma at RGMAX, or fails" // &
               " (MDLEQF >= 10; values unprintable)"
          CALL push_diag("RR", EQ_DIAG_OUT_OF_RANGE_AFTER_DEP, msgbuf)
       END IF

       IF (ZGMIN >= 0.D0 .OR. ZGMAX <= 0.D0) THEN
          WRITE(msgbuf, '(A,F0.3,A,F0.3,A)', IOSTAT=ios) &
               "ZGMIN..ZGMAX [", ZGMIN, ", ", ZGMAX, &
               "] leaves out Z=0, where the magnetic axis lies (MDLEQF >= 10)"
          IF (ios /= 0) msgbuf = &
               "ZGMIN..ZGMAX leaves out Z=0, where the magnetic axis lies (MDLEQF >= 10; values unprintable)"
          IF (ZGMIN >= 0.D0) THEN
             CALL push_diag("ZGMIN", EQ_DIAG_OUT_OF_RANGE_AFTER_DEP, msgbuf)
          ELSE
             CALL push_diag("ZGMAX", EQ_DIAG_OUT_OF_RANGE_AFTER_DEP, msgbuf)
          END IF
       END IF
    END IF

    ! ---- OUT_OF_RANGE: a negative plasma current, which eq_run(0) refuses (see there).
    IF (analytic .AND. RIP < 0.D0) THEN
       WRITE(msgbuf, '(A,1PE11.4,A)', IOSTAT=ios) "plasma current RIP=", RIP, &
            " MA is negative: the analytic solve does not treat its sign; give its magnitude"
       IF (ios /= 0) msgbuf = "plasma current RIP is negative: the analytic solve does not treat its sign"
       CALL push_diag("RIP", EQ_DIAG_OUT_OF_RANGE, msgbuf)
    END IF

    ndiag = nlocal
    IF (nlocal == 0) THEN
       ierr = EQ_OK
    ELSE
       ierr = EQ_ERR_INVALID
    END IF

  CONTAINS

    !---------------------------------------------------------------
    ! Helper: emit a single OUT_OF_RANGE diagnostic if requested
    ! grid count exceeds the compile-time maximum. Idempotent w.r.t.
    ! diag_cap exhaustion (extra diagnostics are silently dropped).
    !---------------------------------------------------------------
    SUBROUTINE push_oor(name_str, requested, max_value)
      CHARACTER(LEN=*), INTENT(IN) :: name_str
      INTEGER, INTENT(IN)          :: requested, max_value
      CHARACTER(LEN=EQ_DIAG_MSG_LEN) :: m
      IF (requested <= max_value) RETURN
      WRITE(m, '(A,I0,A,I0)') &
           "value ", requested, " exceeds compile-time maximum ", max_value
      CALL push_diag(name_str, EQ_DIAG_OUT_OF_RANGE, m)
    END SUBROUTINE push_oor

    !---------------------------------------------------------------
    ! Helper: append (param, code, msg) to diag(). Skips if diag_cap
    ! is exhausted but still increments nlocal so caller can detect
    ! truncation by ndiag > diag_cap (NOTE: callers should size
    ! diag_cap >= EQ_DIAG_CAP_HINT == 32 to avoid this).
    !---------------------------------------------------------------
    SUBROUTINE push_diag(name_str, code_in, msg_in)
      CHARACTER(LEN=*), INTENT(IN) :: name_str, msg_in
      INTEGER(C_INT),   INTENT(IN) :: code_in
      INTEGER :: i, n
      nlocal = nlocal + 1
      IF (nlocal > diag_cap) RETURN
      ! Zero-fill, then copy + NUL-terminate.
      DO i = 1, EQ_DIAG_PARAM_LEN
         diag(nlocal)%param(i) = C_NULL_CHAR
      END DO
      n = MIN(LEN_TRIM(name_str), EQ_DIAG_PARAM_LEN - 1)
      DO i = 1, n
         diag(nlocal)%param(i) = name_str(i:i)
      END DO
      DO i = 1, EQ_DIAG_MSG_LEN
         diag(nlocal)%msg(i) = C_NULL_CHAR
      END DO
      n = MIN(LEN_TRIM(msg_in), EQ_DIAG_MSG_LEN - 1)
      DO i = 1, n
         diag(nlocal)%msg(i) = msg_in(i:i)
      END DO
      diag(nlocal)%code = code_in
    END SUBROUTINE push_diag

    !---------------------------------------------------------------
    ! Helper: .TRUE. when a file of this name exists (relative to the
    ! working directory), as the load would open it.
    !---------------------------------------------------------------
    LOGICAL FUNCTION file_there(fname)
      CHARACTER(LEN=*), INTENT(IN) :: fname
      INTEGER :: ios_q
      file_there = .FALSE.
      INQUIRE(FILE=TRIM(fname), EXIST=file_there, IOSTAT=ios_q)
      IF (ios_q /= 0) file_there = .FALSE.
    END FUNCTION file_there

  END FUNCTION eq_api_validate

  !=====================================================================
  ! eq_save : C-ABI wrapper around EQSAVE_IERR (eq/eqfile.f90).
  !
  !   - Writes the current EQ state (PSIRZ, profiles, scalars) to the
  !     TASK-internal binary file at the path stored in module-level
  !     KNAMEQ. Caller MUST set KNAMEQ via eq_set_param_str before
  !     calling this.
  !   - EQ_ERR_INVALID, before any file is touched: the fields do not
  !     hold the equilibrium of the present parameters (no successful
  !     eq_run since eq_init, a later solve or load that failed, or
  !     eq_set_param of anything but MODEFR and MODEFW since; what EQSAVE
  !     would write then can end the process that loads it); a blank
  !     KNAMEQ; MODEFW
  !     other than 0 (overwrite an existing file) or 3 (refuse one):
  !     with 1, 2 and 4 to 7 FWOPEN can read unit 5, for a Y/N or for
  !     the file name.
  !   - EQ_ERR_CALC_FAILED when EQSAVE_IERR reports that the file could
  !     not be opened (a directory that is missing or not writable,
  !     MODEFW=3 and an existing file), that a write failed (an existing
  !     file without write permission) or that the file is shorter than
  !     what was written, or when no non-empty file exists afterwards.
  !   - EQ_OK otherwise.
  !=====================================================================
  FUNCTION eq_api_save() RESULT(ierr) BIND(C, NAME="eq_save")
    INTEGER(C_INT) :: ierr
    LOGICAL :: file_exists
    INTEGER :: file_size, ierr_save
    IF (.NOT. g_initialized) THEN
       ierr = EQ_ERR_NOT_INIT
       RETURN
    END IF
    IF (.NOT. g_has_equilibrium) THEN
       WRITE(6,*) 'XX eq_save: no equilibrium of the present parameters:', &
                  ' call eq_run first'
       ierr = EQ_ERR_INVALID
       RETURN
    END IF
    IF (LEN_TRIM(KNAMEQ) == 0) THEN
       ierr = EQ_ERR_INVALID
       RETURN
    END IF
    IF (MODEFW /= 0 .AND. MODEFW /= 3) THEN
       WRITE(6,*) 'XX eq_save: MODEFW must be 0 or 3 here: MODEFW=', MODEFW
       ierr = EQ_ERR_INVALID
       RETURN
    END IF
    ! #227 item 3: a save that wrote nothing must not return EQ_OK.
    ! EQSAVE_IERR (the body of EQSAVE, which keeps its argument-less
    ! entry for the menu) reports a failed open or write through its
    ! argument. Looking for the file afterwards is not enough on its own:
    ! a save to a path that already holds an earlier, non-empty file would
    ! pass for a success.
    CALL EQSAVE_IERR(ierr_save)
    IF (ierr_save /= 0) THEN
       ierr = EQ_ERR_CALC_FAILED
       RETURN
    END IF
    ! The open succeeded; also confirm that a non-empty file is there.
    INQUIRE(FILE=TRIM(KNAMEQ), EXIST=file_exists, SIZE=file_size)
    IF ((.NOT. file_exists) .OR. (file_size <= 0)) THEN
       ierr = EQ_ERR_CALC_FAILED
       RETURN
    END IF
    ierr = EQ_OK
  END FUNCTION eq_api_save

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

  !-------------------------------------------------------------------
  ! eq_state_abi_version / eq_state_size : layout query (#246).
  !
  ! No lifecycle check and no side effect; callable before eq_init.
  ! A caller compares both with its own sizeof(eq_state_t) and its copy
  ! of EQ_STATE_ABI_VERSION before passing a struct to eq_get_state;
  ! python/eqlib/_ffi.py refuses the library when either differs.
  !-------------------------------------------------------------------
  FUNCTION eq_api_state_abi_version() RESULT(v) BIND(C, NAME="eq_state_abi_version")
    INTEGER(C_INT) :: v
    v = EQ_STATE_ABI_VERSION
  END FUNCTION eq_api_state_abi_version

  FUNCTION eq_api_state_size() RESULT(n) BIND(C, NAME="eq_state_size")
    INTEGER(C_SIZE_T) :: n
    TYPE(eq_state_c) :: probe
    n = C_SIZEOF(probe)
  END FUNCTION eq_api_state_size

END MODULE eq_api
