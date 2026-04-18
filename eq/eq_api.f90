! eq_api.f90
!
! Phase L-2: C ABI entry points for libeqapi (scaffold layer).
!
! Five BIND(C) functions are exposed. In L-2 they are intentionally
! minimal scaffolding so that the C ABI surface (symbol names, arg
! layout, error-code enum) is fixed before L-3 wires them to real
! calculation drivers:
!
!   eq_init       -> marks the library as initialized (idempotent)
!                    and returns EQ_OK. Does NOT touch the legacy eq
!                    COMMON blocks so existing eq / pl / ak binaries
!                    keep bit-identical behavior.
!   eq_run        -> returns EQ_ERR_NOT_IMPL. Real dispatch (eqcalc /
!                    eqcalq / eq_bpsd_* etc.) arrives in L-3.
!   eq_set_param  -> delegates to eq_param_registry::eq_param_set
!                    which itself is an L-2 stub (always NOT_IMPL).
!   eq_get_state  -> reads grid dimensions and plasma scalars out of
!                    the legacy COMMON blocks via the F77 bridge
!                    routines in eq_api_common.f, then zeros the
!                    C struct and fills the scalars + 1D profiles
!                    up to the compile-time maxima in eq_state.
!   eq_finalize   -> clears the initialized flag. No COMMON cleanup
!                    yet (the legacy binaries rely on implicit
!                    static storage).
!
! Name-collision resolution: equnit.f already defines MODULE equnit
! with PUBLIC eq_init. The C-visible symbol also has to be named
! eq_init (per the design spec), so the BIND(C, NAME="eq_init")
! wrapper lives in this module as FUNCTION eq_api_init. When the
! wrapper needs to call equnit::eq_init it renames the import with
!   USE equnit, ONLY: equnit_eq_init => eq_init
! (done below), avoiding the name clash inside this module.
!
! See docs/superpowers/specs/2026-04-17-tr-library-design.md §4 for
! the overall C ABI shape; tr_api.f90 / ti_api.f90 are the L-3
! references.

MODULE eq_api
  USE, INTRINSIC :: ISO_C_BINDING
  USE eq_state, ONLY: eq_state_c, &
                      EQ_MAX_NRGM, EQ_MAX_NZGM, EQ_MAX_NPSM, &
                      EQ_MAX_NRM,  EQ_MAX_NTHM, EQ_MAX_NSUM
  USE eq_param_registry, ONLY: eq_param_set
  ! Rename equnit::eq_init away from the C-visible eq_init symbol.
  ! Not actually called in L-2 (eq_api_init is a no-op scaffold), but
  ! the USE line documents the resolution we will use in L-3 when
  ! eq_api_init starts delegating to the equnit initializer.
  USE equnit, ONLY: equnit_eq_init => eq_init
  IMPLICIT NONE
  PRIVATE
  PUBLIC :: eq_api_init, eq_api_run, eq_api_get_state, &
            eq_api_set_param, eq_api_finalize

  ! Error codes. Must match eq_api.h.
  INTEGER(C_INT), PARAMETER :: EQ_OK              = 0
  INTEGER(C_INT), PARAMETER :: EQ_ERR_INVALID     = 1
  INTEGER(C_INT), PARAMETER :: EQ_ERR_NOT_INIT    = 2
  INTEGER(C_INT), PARAMETER :: EQ_ERR_CALC_FAILED = 3
  INTEGER(C_INT), PARAMETER :: EQ_ERR_NOT_IMPL    = 4

  ! Lifecycle flag. Module-scope, single-instance (same pattern as tr / ti).
  LOGICAL, SAVE :: g_initialized = .FALSE.

CONTAINS

  !-------------------------------------------------------------------
  ! eq_init : L-2 scaffold. Flip the lifecycle flag and return EQ_OK.
  !-------------------------------------------------------------------
  FUNCTION eq_api_init() RESULT(ierr) BIND(C, NAME="eq_init")
    INTEGER(C_INT) :: ierr
    g_initialized = .TRUE.
    ierr = EQ_OK
    ! Touch the rename to keep the import "used" under strict checkers
    ! without actually running equnit::eq_init at L-2 (that would
    ! clobber COMMON defaults set up by the normal eq driver). The
    ! expression is a no-op: equnit_eq_init is a SUBROUTINE handle,
    ! and `.FALSE.` has no side effects.
    IF (.FALSE.) CALL equnit_eq_init
  END FUNCTION eq_api_init

  !-------------------------------------------------------------------
  ! eq_run : L-2 stub. Real dispatch lands in L-3.
  !-------------------------------------------------------------------
  FUNCTION eq_api_run(mode) RESULT(ierr) BIND(C, NAME="eq_run")
    INTEGER(C_INT), VALUE, INTENT(IN) :: mode
    INTEGER(C_INT) :: ierr
    ! Keep the arg meaningful: any non-negative mode is accepted by
    ! the stub so callers can exercise the path; negative modes are
    ! flagged as invalid so the enum contract is already visible.
    IF (mode < 0) THEN
       ierr = EQ_ERR_INVALID
       RETURN
    END IF
    IF (.NOT. g_initialized) THEN
       ierr = EQ_ERR_NOT_INIT
       RETURN
    END IF
    ierr = EQ_ERR_NOT_IMPL
  END FUNCTION eq_api_run

  !-------------------------------------------------------------------
  ! eq_set_param : delegate to the (L-2 stub) parameter registry.
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

    CALL eq_param_set(TRIM(fname), value, reg_ierr)
    IF (reg_ierr == 0) THEN
       ierr = EQ_OK
    ELSE IF (reg_ierr == 4) THEN
       ierr = EQ_ERR_NOT_IMPL
    ELSE
       ierr = EQ_ERR_INVALID
    END IF
  END FUNCTION eq_api_set_param

  !-------------------------------------------------------------------
  ! eq_get_state : fill the C-visible struct from the legacy COMMON
  ! state via the F77 bridge in eq_api_common.f.
  !-------------------------------------------------------------------
  FUNCTION eq_api_get_state(state) RESULT(ierr) BIND(C, NAME="eq_get_state")
    TYPE(eq_state_c), INTENT(OUT) :: state
    INTEGER(C_INT) :: ierr
    INTEGER :: nrgm_dim, nzgm_dim, npsm_dim, nrm_dim, nthm_dim, nsum_dim
    INTEGER :: nrgmax_c, nzgmax_c, npsmax_c
    INTEGER :: nrmax_c,  nthmax_c, nsumax_c
    REAL(C_DOUBLE) :: raxis_v, zaxis_v, psi0_v, psipa_v, psita_v
    REAL(C_DOUBLE) :: qaxis_v, qsurf_v, betat_v, betap_v
    REAL(C_DOUBLE) :: pvol_v,  raave_v, ripx_v
    INTEGER :: ncopy_ps, nr_copy, nz_copy

    ! Always zero the struct so callers never see uninitialized memory.
    state%nrgmax = 0
    state%nzgmax = 0
    state%npsmax = 0
    state%nrmax  = 0
    state%nthmax = 0
    state%nsumax = 0
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

    IF (.NOT. g_initialized) THEN
       ierr = EQ_ERR_NOT_INIT
       RETURN
    END IF

    ! Pull the compile-time PARAMETER dims (NRGM/NZGM/...) and the
    ! current runtime counters (NRGMAX/NZGMAX/...) via the F77 bridge.
    CALL EQ_COMMON_GET_GRID_DIMS(nrgm_dim, nzgm_dim, npsm_dim, &
                                 nrm_dim, nthm_dim, nsum_dim)
    CALL EQ_COMMON_GET_GRID_COUNTS(nrgmax_c, nzgmax_c, npsmax_c, &
                                   nrmax_c, nthmax_c, nsumax_c)

    state%nrgmax = nrgmax_c
    state%nzgmax = nzgmax_c
    state%npsmax = npsmax_c
    state%nrmax  = nrmax_c
    state%nthmax = nthmax_c
    state%nsumax = nsumax_c

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
    g_initialized = .FALSE.
    ierr = EQ_OK
  END FUNCTION eq_api_finalize

END MODULE eq_api
