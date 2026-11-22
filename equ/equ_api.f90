! equ_api.f90
!
! C ABI of EQU, the free-boundary equilibrium code (libequapi.so).
! Design: docs/superpowers/specs/2026-11-22-equ-library-design.md; the C
! declarations are in equ_api.h. EQ's interface (eq/eq_api.f90) is the
! pattern: the Fortran functions are equ_api_*, exported under the C names
! equ_* with BIND(C), so they do not clash with equunit_mod's equ_init and
! friends (which this module does not use: equunit_mod uses graphics).
!
! The run calls EQU's routines in the order the menu's R calls them
! (equmenu.f90: equ_prof, tr_prof, equ_calc; equunit.f90 and
! equtrunit.f90), checking each status: equ_prof drops them. The library
! comparison (python/equlib/tests/test_program_parity.py) holds this order
! to the program's.
!
! Library mode (equ_status_mod): the places where the solver used to STOP
! record a failure and return; equ_run returns EQU_ERR_CALC_FAILED with
! the message. Every run starts from the inputs as last set by init,
! read_parm or set_param (equ_image_mod).

MODULE equ_api
  USE, INTRINSIC :: ISO_C_BINDING
  USE equ_state, ONLY: EQU_STATE_ABI_VERSION, equ_state_c, equ_diag_entry_c, &
                       EQU_MAX_NR, EQU_MAX_NZ, EQU_MAX_NV, EQU_MAX_NSU, EQU_NCV, &
                       EQU_DIAG_PARAM_LEN, EQU_DIAG_MSG_LEN, &
                       EQU_DIAG_OUT_OF_RANGE, EQU_DIAG_INCONSISTENT_PAIR, &
                       EQU_DIAG_OUT_OF_RANGE_AFTER_DEP, EQU_DIAG_FILE_MISSING
  USE equ_param_registry, ONLY: equ_param_set, equ_param_set_str
  USE equ_image_mod, ONLY: image_save, image_restore, image_swap, &
                           stash_save, stash_restore, reset_run_state
  USE equ_status_mod, ONLY: equ_library_mode, equ_failed, equ_status_clear, &
                            equ_status_message
  IMPLICIT NONE
  PRIVATE
  PUBLIC :: equ_api_init, equ_api_read_parm, equ_api_set_param, &
            equ_api_set_param_str, equ_api_validate, equ_api_run, &
            equ_api_get_state, equ_api_get_psi_rz, equ_api_write_geqdsk, &
            equ_api_last_error, equ_api_finalize, &
            equ_api_state_abi_version, equ_api_state_size

  INTEGER(C_INT), PARAMETER :: EQU_OK              = 0
  INTEGER(C_INT), PARAMETER :: EQU_ERR_INVALID     = 1
  INTEGER(C_INT), PARAMETER :: EQU_ERR_NOT_INIT    = 2
  INTEGER(C_INT), PARAMETER :: EQU_ERR_CALC_FAILED = 3
  INTEGER(C_INT), PARAMETER :: EQU_ERR_NOT_IMPL    = 4

  INTEGER, PARAMETER :: dp = KIND(1.0D0)
  INTEGER, PARAMETER :: NAME_LEN = 63      ! names: at most 63 characters (equ_api.h)
  INTEGER, PARAMETER :: VALUE_LEN = 80     ! the longest CHARACTER of &EQU
  INTEGER, PARAMETER :: PATH_LEN = 1023    ! paths: at most 1023 characters

  LOGICAL, SAVE :: g_initialized = .FALSE.
  ! The fields hold the equilibrium of the last successful run.
  LOGICAL, SAVE :: g_has_equilibrium = .FALSE.
  ! A run has overwritten inputs since the image was taken: the module
  ! variables hold the solver's values (which get_state and the G-EQDSK
  ! writer read), the image the inputs. A check or a set swaps the two in
  ! for its time (image_swap); a run, or a set that succeeds, ends it.
  LOGICAL, SAVE :: g_dirty = .FALSE.
  INTEGER, SAVE :: g_mode = -1
  CHARACTER(LEN=256), SAVE :: g_errmsg = ' '

  ! equ_path.c: what a path names, for host_file_refusal.
  INTEGER(C_INT), PARAMETER :: PATH_ABSENT = 0, PATH_REGULAR = 1, PATH_OTHER = 2, &
                               PATH_STD_STREAM = 3
  INTERFACE
     FUNCTION c_path_kind(path) BIND(C, NAME='equ_path_kind') RESULT(k)
       IMPORT :: C_CHAR, C_INT
       CHARACTER(KIND=C_CHAR), INTENT(IN) :: path(*)
       INTEGER(C_INT) :: k
     END FUNCTION c_path_kind
  END INTERFACE

CONTAINS

  !-------------------------------------------------------------------
  ! equ_init : the program's start (equmain.f90: equ_init, tr_init),
  ! library mode, the run state reset, the image of the defaults.
  !-------------------------------------------------------------------
  FUNCTION equ_api_init() RESULT(ierr) BIND(C, NAME="equ_init")
    USE aaa_mod, ONLY: ft05, ft06, out
    USE eqsub_mod, ONLY: flxtab
    USE eqinit_mod, ONLY: eqinit
    USE trpl_mod, ONLY: trpl_init
    USE vac_mod, ONLY: rvac, zvac, rcoil, zcoil, ccoil
    INTEGER(C_INT) :: ierr
    INTEGER :: jerr
    ft05 = 5
    ft06 = 6
    out = 0
    CALL flxtab
    CALL eqinit
    ! What eqinit leaves as it is and a fresh process has as zero: the
    ! marker points, and the filaments of coil groups 5..18 (eqinit sets
    ! the JT-60U groups 1..4; with KNAMCOIL = 'done' a group's filaments
    ! are whatever is in memory).
    rvac = 0.0_dp
    zvac = 0.0_dp
    rcoil(:, 5:) = 0.0_dp
    zcoil(:, 5:) = 0.0_dp
    ccoil(:, 5:) = 0.0_dp
    CALL trpl_init
    equ_library_mode = .TRUE.
    CALL equ_status_clear
    CALL reset_run_state(jerr)
    CALL image_save
    g_initialized = .TRUE.
    g_has_equilibrium = .FALSE.
    g_dirty = .FALSE.
    g_mode = -1
    g_errmsg = ' '
    ierr = EQU_OK
  END FUNCTION equ_api_init

  !-------------------------------------------------------------------
  ! equ_read_parm : an &EQU namelist file, read by EQU's own eqnlin as
  ! the program's start-up read does (task_parm mode 1: open, eqnlin,
  ! close). A failed read is undone: a namelist read stops at the bad
  ! item with the earlier ones already assigned.
  !-------------------------------------------------------------------
  FUNCTION equ_api_read_parm(path) RESULT(ierr) BIND(C, NAME="equ_read_parm")
    USE eqinit_mod, ONLY: eqnlin
    CHARACTER(KIND=C_CHAR), DIMENSION(*), INTENT(IN) :: path
    INTEGER(C_INT) :: ierr
    CHARACTER(LEN=PATH_LEN) :: fpath
    INTEGER :: u, ios, ist, jerr
    LOGICAL :: was_dirty
    CHARACTER(LEN=80) :: why

    IF (.NOT. g_initialized) THEN
       ierr = EQU_ERR_NOT_INIT
       RETURN
    END IF
    IF (.NOT. c_to_f(path, fpath)) THEN
       CALL set_error('read_parm: the path is longer than 1023 characters')
       ierr = EQU_ERR_INVALID
       RETURN
    END IF
    IF (LEN_TRIM(fpath) == 0) THEN
       CALL set_error('read_parm: the path is blank')
       ierr = EQU_ERR_INVALID
       RETURN
    END IF
    ! Only a regular file that is not the process's standard input,
    ! output or error, which a stdio MCP server owns (host_file_refusal).
    why = host_file_refusal(fpath)
    IF (LEN_TRIM(why) > 0) THEN
       CALL set_error('read_parm: '//TRIM(fpath)//' '//TRIM(why))
       ierr = EQU_ERR_INVALID
       RETURN
    END IF
    ! A positive unit: eqnlin writes the namelist to unit -NID when NID is
    ! negative, and NEWUNIT= gives negative numbers.
    u = free_unit()
    IF (u < 0) THEN
       CALL set_error('read_parm: no free Fortran unit in 30..99')
       ierr = EQU_ERR_INVALID
       RETURN
    END IF
    OPEN(UNIT=u, FILE=TRIM(fpath), STATUS='OLD', ACTION='READ', &
         FORM='FORMATTED', IOSTAT=ios)
    IF (ios /= 0) THEN
       CALL set_error('read_parm: cannot open '//TRIM(fpath))
       ierr = EQU_ERR_INVALID
       RETURN
    END IF
    ! The read goes into the inputs; a failed one is undone and, after a
    ! run, leaves the run's values in place.
    was_dirty = g_dirty
    IF (was_dirty) CALL image_swap
    CALL stash_save
    CALL eqnlin(u, ist, jerr)
    CLOSE(u)
    IF (jerr /= 0) THEN
       CALL stash_restore
       IF (was_dirty) CALL image_swap
       IF (jerr == 9) THEN
          CALL set_error('read_parm: no &EQU namelist in '//TRIM(fpath))
       ELSE
          CALL set_error('read_parm: the &EQU namelist of '//TRIM(fpath)// &
                         ' could not be read (iostat='//itoa(ist)// &
                         '): an unknown name or a bad value')
       END IF
       ierr = EQU_ERR_INVALID
       RETURN
    END IF
    CALL image_save
    g_dirty = .FALSE.
    g_has_equilibrium = .FALSE.
    g_errmsg = ' '
    ierr = EQU_OK
  END FUNCTION equ_api_read_parm

  !-------------------------------------------------------------------
  ! equ_set_param : one numeric parameter through the registry.
  !-------------------------------------------------------------------
  FUNCTION equ_api_set_param(name, value) RESULT(ierr) &
           BIND(C, NAME="equ_set_param")
    CHARACTER(KIND=C_CHAR), DIMENSION(*), INTENT(IN) :: name
    REAL(C_DOUBLE), VALUE, INTENT(IN) :: value
    INTEGER(C_INT) :: ierr
    CHARACTER(LEN=NAME_LEN) :: fname
    INTEGER :: jerr
    LOGICAL :: was_dirty

    IF (.NOT. g_initialized) THEN
       ierr = EQU_ERR_NOT_INIT
       RETURN
    END IF
    IF (.NOT. c_to_f(name, fname)) THEN
       CALL set_error('set_param: a name longer than 63 characters')
       ierr = EQU_ERR_INVALID
       RETURN
    END IF
    ! The set goes into the inputs (the registry assigns nothing when it
    ! refuses); a refused one, after a run, leaves the run's values.
    was_dirty = g_dirty
    IF (was_dirty) CALL image_swap
    CALL equ_param_set(TRIM(fname), REAL(value, dp), jerr)
    IF (jerr == 0) THEN
       CALL image_save
       g_dirty = .FALSE.
       g_has_equilibrium = .FALSE.
       ierr = EQU_OK
       RETURN
    END IF
    IF (was_dirty) CALL image_swap
    IF (jerr == 2) THEN
       CALL set_error('set_param: '//TRIM(fname)//' is accepted by the &EQU '// &
                      'namelist but not used by EQU')
       ierr = EQU_ERR_INVALID
    ELSE
       CALL set_error('set_param: '//TRIM(fname)//': unknown name, malformed '// &
                      'or out-of-range subscript, or a value it does not take')
       ierr = EQU_ERR_INVALID
    END IF
  END FUNCTION equ_api_set_param

  !-------------------------------------------------------------------
  ! equ_set_param_str : DEVICE, DEVNAM, TITLE, KNAMCOIL.
  !-------------------------------------------------------------------
  FUNCTION equ_api_set_param_str(name, value) RESULT(ierr) &
           BIND(C, NAME="equ_set_param_str")
    CHARACTER(KIND=C_CHAR), DIMENSION(*), INTENT(IN) :: name
    CHARACTER(KIND=C_CHAR), DIMENSION(*), INTENT(IN) :: value
    INTEGER(C_INT) :: ierr
    CHARACTER(LEN=NAME_LEN) :: fname
    CHARACTER(LEN=VALUE_LEN) :: fvalue
    INTEGER :: jerr
    LOGICAL :: was_dirty

    IF (.NOT. g_initialized) THEN
       ierr = EQU_ERR_NOT_INIT
       RETURN
    END IF
    IF (.NOT. c_to_f(name, fname)) THEN
       CALL set_error('set_param_str: a name longer than 63 characters')
       ierr = EQU_ERR_INVALID
       RETURN
    END IF
    IF (.NOT. c_to_f(value, fvalue)) THEN
       CALL set_error('set_param_str: '//TRIM(fname)//': a value longer than '// &
                      '80 characters')
       ierr = EQU_ERR_INVALID
       RETURN
    END IF
    was_dirty = g_dirty
    IF (was_dirty) CALL image_swap
    CALL equ_param_set_str(TRIM(fname), TRIM(fvalue), jerr)
    IF (jerr == 0) THEN
       CALL image_save
       g_dirty = .FALSE.
       g_has_equilibrium = .FALSE.
       ierr = EQU_OK
    ELSE
       IF (was_dirty) CALL image_swap
       CALL set_error('set_param_str: '//TRIM(fname)//': unknown string name, '// &
                      'or a value longer than the variable')
       ierr = EQU_ERR_INVALID
    END IF
  END FUNCTION equ_api_set_param_str

  !-------------------------------------------------------------------
  ! equ_validate : the checks of the inputs, in one batch (design,
  ! section 8). Read-only: after a run it swaps the inputs in for the
  ! checks and the run's values back afterwards.
  !-------------------------------------------------------------------
  FUNCTION equ_api_validate(diag, diag_cap, ndiag_out) RESULT(ierr) &
           BIND(C, NAME="equ_validate")
    TYPE(equ_diag_entry_c), DIMENSION(*), INTENT(INOUT) :: diag
    INTEGER(C_INT), VALUE, INTENT(IN) :: diag_cap
    INTEGER(C_INT), INTENT(OUT) :: ndiag_out
    INTEGER(C_INT) :: ierr
    INTEGER :: nlocal

    ndiag_out = 0
    IF (.NOT. g_initialized) THEN
       ierr = EQU_ERR_NOT_INIT
       RETURN
    END IF
    IF (g_dirty) CALL image_swap
    nlocal = 0
    CALL check_inputs(push)
    IF (g_dirty) CALL image_swap
    ndiag_out = nlocal
    IF (nlocal > 0) THEN
       ierr = EQU_ERR_INVALID
    ELSE
       ierr = EQU_OK
    END IF

  CONTAINS

    SUBROUTINE push(pname, code, msg)
      CHARACTER(LEN=*), INTENT(IN) :: pname, msg
      INTEGER(C_INT), INTENT(IN) :: code
      INTEGER :: i, n
      nlocal = nlocal + 1
      IF (nlocal > diag_cap) RETURN
      diag(nlocal)%param = C_NULL_CHAR
      n = MIN(LEN_TRIM(pname), EQU_DIAG_PARAM_LEN - 1)
      DO i = 1, n
         diag(nlocal)%param(i) = pname(i:i)
      END DO
      diag(nlocal)%msg = C_NULL_CHAR
      n = MIN(LEN_TRIM(msg), EQU_DIAG_MSG_LEN - 1)
      DO i = 1, n
         diag(nlocal)%msg(i) = msg(i:i)
      END DO
      diag(nlocal)%code = code
    END SUBROUTINE push

  END FUNCTION equ_api_validate

  !-------------------------------------------------------------------
  ! equ_run : mode 1 = the menu's R; mode 0 = its first step (equ_prof).
  !-------------------------------------------------------------------
  FUNCTION equ_api_run(mode) RESULT(ierr) BIND(C, NAME="equ_run")
    USE eqinit_mod, ONLY: eqflin, eqchek, knamcoil
    USE eqsub_mod, ONLY: eqgrd, eqout
    USE eqset_mod, ONLY: eqset
    USE eqfct_mod, ONLY: eqfct
    USE equpl_mod, ONLY: eqpl_init, eqpl_prof, eqpl_get, eqpl_put
    USE trset_mod, ONLY: trset
    USE trpl_mod, ONLY: trpl_init, trpl_put
    USE equ_mod, ONLY: ieq
    INTEGER(C_INT), VALUE, INTENT(IN) :: mode
    INTEGER(C_INT) :: ierr
    INTEGER :: jerr, ucoil
    CHARACTER(LEN=256) :: first

    IF (.NOT. g_initialized) THEN
       ierr = EQU_ERR_NOT_INIT
       RETURN
    END IF
    IF (mode < 0) THEN
       CALL set_error('run: mode must be 0 or 1')
       ierr = EQU_ERR_INVALID
       RETURN
    END IF
    IF (mode > 1) THEN
       CALL set_error('run: mode '//itoa(INT(mode))//' is not implemented '// &
                      '(0: equ_prof; 1: the menu''s R)')
       ierr = EQU_ERR_NOT_IMPL
       RETURN
    END IF
    CALL restore_if_dirty
    g_has_equilibrium = .FALSE.
    g_mode = -1
    g_errmsg = ' '

    ! The checks of equ_validate, the first one in the message.
    first = ' '
    CALL check_inputs(note_first)
    IF (LEN_TRIM(first) > 0) THEN
       CALL set_error('run: refused: '//TRIM(first))
       ierr = EQU_ERR_INVALID
       RETURN
    END IF

    CALL equ_status_clear
    CALL reset_run_state(jerr)
    IF (jerr /= 0) THEN
       CALL set_error('run: bpsd_put_plasmaf failed (ierr='//itoa(jerr)//')')
       ierr = EQU_ERR_CALC_FAILED
       RETURN
    END IF
    ! From here on the solver overwrites inputs.
    g_dirty = .TRUE.

    ! --- equ_prof (equunit.f90:58-73) ---
    ! eqflin takes its unit as an argument: a free one, not the program's
    ! 18, which a host may have open.
    IF (TRIM(knamcoil) /= 'done') THEN
       ucoil = free_unit()
       IF (ucoil < 0) THEN
          CALL set_error('run: no free Fortran unit in 30..99 for the coil file')
          GOTO 900
       END IF
    ELSE
       ucoil = 18          ! eqflin opens no file with 'done'
    END IF
    CALL eqflin(ucoil, jerr)
    IF (failed_step('eqflin', jerr)) GOTO 900
    CALL eqchek(jerr)
    IF (failed_step('eqchek', jerr)) GOTO 900
    CALL eqgrd
    CALL eqset
    IF (failed_step('eqset', 0)) GOTO 900
    CALL eqout
    IF (failed_step('eqout', 0)) GOTO 900
    CALL eqpl_init(jerr)
    IF (failed_step('eqpl_init', jerr)) GOTO 900
    CALL eqpl_prof(jerr)
    IF (failed_step('eqpl_prof', jerr)) GOTO 900

    IF (mode == 1) THEN
       ! --- tr_prof (equtrunit.f90:28-39) ---
       CALL trset
       CALL trpl_init
       CALL trpl_put(jerr)
       IF (failed_step('trpl_put', jerr)) GOTO 900
       ! --- equ_calc (equunit.f90:77-89) ---
       CALL eqpl_get(jerr)
       IF (failed_step('eqpl_get', jerr)) GOTO 900
       ! The state reports this loop's steps: with IEQMAX = 0 it runs none,
       ! and ieq would otherwise show eqset's ten.
       ieq = 0
       CALL eqfct
       IF (failed_step('eqfct', 0)) GOTO 900
       CALL eqout
       IF (failed_step('eqout', 0)) GOTO 900
       CALL eqpl_put(jerr)
       IF (failed_step('eqpl_put', jerr)) GOTO 900
    END IF

    g_has_equilibrium = .TRUE.
    g_mode = mode
    ierr = EQU_OK
    RETURN

900 CONTINUE
    ierr = EQU_ERR_CALC_FAILED

  CONTAINS

    SUBROUTINE note_first(pname, code, msg)
      CHARACTER(LEN=*), INTENT(IN) :: pname, msg
      INTEGER(C_INT), INTENT(IN) :: code
      IF (LEN_TRIM(first) == 0) first = TRIM(pname)//': '//TRIM(msg)
    END SUBROUTINE note_first

  END FUNCTION equ_api_run

  !-------------------------------------------------------------------
  ! failed_step : .TRUE. (with the message set) when a step returned a
  ! status or recorded a failure through equ_fail.
  !-------------------------------------------------------------------
  LOGICAL FUNCTION failed_step(step, jerr)
    CHARACTER(LEN=*), INTENT(IN) :: step
    INTEGER, INTENT(IN) :: jerr
    failed_step = .FALSE.
    IF (equ_failed()) THEN
       CALL set_error('run: '//TRIM(equ_status_message()))
       ! Reported: the flag is cleared, so a later check or run starts clean.
       CALL equ_status_clear
       failed_step = .TRUE.
    ELSE IF (jerr /= 0) THEN
       CALL set_error('run: '//step//' failed (ierr='//itoa(jerr)//')')
       failed_step = .TRUE.
    END IF
  END FUNCTION failed_step

  !-------------------------------------------------------------------
  ! equ_get_state : the result of the last run (design, section 7).
  !-------------------------------------------------------------------
  FUNCTION equ_api_get_state(st) RESULT(ierr) BIND(C, NAME="equ_get_state")
    USE geo_mod, ONLY: nr, nz, rg, zg
    USE eqv_mod, ONLY: nv, siv, hiv, prv, qqv, rbv, vlv, rpv, rtv, elv, dlv
    USE equ_mod, ONLY: nsu, rsu, zsu, ieq, erreq, raxis, zaxis, saxis, &
                       iisep, irsep, izsep, psep, ttcu, btv, beta, bets, &
                       betj, zzli, qsurf, q95, qqj, el95
    USE par_mod, ONLY: tcur, rmaj, rpla, elip, trig
    USE vac_mod, ONLY: cvac
    TYPE(equ_state_c), INTENT(OUT) :: st
    INTEGER(C_INT) :: ierr
    INTEGER :: n, m

    st%nr = 0; st%nz = 0; st%nv = 0; st%nsu = 0
    st%mode = -1; st%fct_steps = 0; st%fct_converged = 0; st%xpoint_status = 0
    st%erreq = 0; st%raxis = 0; st%zaxis = 0; st%psi_axis = 0
    st%rsep = 0; st%zsep = 0; st%psi_sep = 0
    st%ip = 0; st%ip_target = 0; st%rbt = 0
    st%beta_t = 0; st%beta_s = 0; st%beta_j = 0; st%li = 0
    st%q_axis = 0; st%q_surf = 0; st%q95 = 0; st%qqj = 0
    st%rmaj = 0; st%rpla = 0; st%elip = 0; st%trig = 0; st%el95 = 0
    st%volume = 0
    st%cvac = 0; st%rg = 0; st%zg = 0
    st%psi = 0; st%psit = 0; st%pressure = 0; st%q = 0; st%f = 0
    st%vol = 0; st%rminor = 0; st%rcentre = 0; st%kappa = 0; st%delta = 0
    st%rsu = 0; st%zsu = 0

    IF (.NOT. g_initialized) THEN
       ierr = EQU_ERR_NOT_INIT
       RETURN
    END IF
    ierr = EQU_OK
    IF (.NOT. g_has_equilibrium) RETURN

    st%nr = MIN(nr, EQU_MAX_NR)
    st%nz = MIN(nz, EQU_MAX_NZ)
    st%nv = MIN(nv, EQU_MAX_NV)
    st%nsu = MIN(nsu, EQU_MAX_NSU)
    st%mode = g_mode
    st%fct_steps = ABS(ieq)
    IF (ieq < 0) st%fct_converged = 1
    st%xpoint_status = iisep
    st%erreq = erreq
    st%raxis = raxis
    st%zaxis = zaxis
    st%psi_axis = saxis
    ! As eqout prints them (equsub.f90, after its call of eqsep).
    ! Only when an X point was found (iisep > 0): irsep and izsep are
    ! otherwise left from eqsol's guess.
    IF (iisep > 0 .AND. irsep > 1 .AND. irsep < nr) st%rsep = rg(irsep)
    IF (iisep > 0 .AND. izsep > 1 .AND. izsep < nz) st%zsep = zg(izsep)
    st%psi_sep = psep
    st%ip = ttcu
    st%ip_target = tcur
    st%rbt = btv
    st%beta_t = beta
    st%beta_s = bets
    st%beta_j = betj
    st%li = zzli
    ! q on axis as eqout prints it and the G-EQDSK writer writes it
    ! (qqv(1)); the module variable qaxis is set again afterwards by the
    ! eqaxi that eqout's call of eqsep makes, with another estimate.
    st%q_axis = qqv(1)
    st%q_surf = qsurf
    st%q95 = q95
    st%qqj = qqj
    st%rmaj = rmaj
    st%rpla = rpla
    st%elip = elip
    st%trig = trig
    st%el95 = el95
    st%volume = vlv(nv)
    st%cvac(1:EQU_NCV) = cvac(0:EQU_NCV-1)
    n = st%nr
    st%rg(1:n) = rg(1:n)
    n = st%nz
    st%zg(1:n) = zg(1:n)
    n = st%nv
    st%psi(1:n) = siv(1:n)
    st%psit(1:n) = hiv(1:n)
    ! prv holds MPa after eqout (prv = muv*hdv**gam/cnmu0, equsub.f90).
    st%pressure(1:n) = prv(1:n) * 1.0E6_dp
    st%q(1:n) = qqv(1:n)
    st%f(1:n) = rbv(1:n)
    st%vol(1:n) = vlv(1:n)
    st%rminor(1:n) = rpv(1:n)
    st%rcentre(1:n) = rtv(1:n)
    st%kappa(1:n) = elv(1:n)
    st%delta(1:n) = dlv(1:n)
    m = st%nsu
    st%rsu(1:m) = rsu(1:m)
    st%zsu(1:m) = zsu(1:m)
  END FUNCTION equ_api_get_state

  !-------------------------------------------------------------------
  ! equ_get_psi_rz : psi on the R-Z grid, psi[(iz-1)*nr + ir - 1] in C.
  ! EQU stores psi the same way (equ_mod psi(ir + nr*(iz-1))).
  !-------------------------------------------------------------------
  FUNCTION equ_api_get_psi_rz(nr_in, nz_in, out) RESULT(ierr) &
           BIND(C, NAME="equ_get_psi_rz")
    USE geo_mod, ONLY: nr, nz
    USE equ_mod, ONLY: psi
    INTEGER(C_INT), VALUE, INTENT(IN) :: nr_in, nz_in
    REAL(C_DOUBLE), DIMENSION(*), INTENT(OUT) :: out
    INTEGER(C_INT) :: ierr
    INTEGER :: i
    IF (.NOT. g_initialized) THEN
       ierr = EQU_ERR_NOT_INIT
       RETURN
    END IF
    IF (.NOT. g_has_equilibrium) THEN
       CALL set_error('get_psi_rz: no equilibrium (run first)')
       ierr = EQU_ERR_INVALID
       RETURN
    END IF
    IF (nr_in /= nr .OR. nz_in /= nz) THEN
       CALL set_error('get_psi_rz: the sizes differ from the state''s nr, nz')
       ierr = EQU_ERR_INVALID
       RETURN
    END IF
    DO i = 1, nr * nz
       out(i) = psi(i)
    END DO
    ierr = EQU_OK
  END FUNCTION equ_api_get_psi_rz

  !-------------------------------------------------------------------
  ! equ_write_geqdsk : EQU's own writer (the program's E), with the file
  ! name and MODEFW = 0 so that FWOPEN does not prompt (lib/libfio.f90
  ! FWOPEN); a new file is created first, so overwrite = 0 refuses a file
  ! there before the call and one made meanwhile.
  !-------------------------------------------------------------------
  FUNCTION equ_api_write_geqdsk(path, overwrite) RESULT(ierr) &
           BIND(C, NAME="equ_write_geqdsk")
    USE plcomm, ONLY: KNAMEQ, MODEFW
    USE equ_eqdsk, ONLY: equ_eqdsk_write
    CHARACTER(KIND=C_CHAR), DIMENSION(*), INTENT(IN) :: path
    INTEGER(C_INT), VALUE, INTENT(IN) :: overwrite
    INTEGER(C_INT) :: ierr
    CHARACTER(LEN=PATH_LEN) :: fpath
    CHARACTER(LEN=LEN(KNAMEQ)) :: save_name
    INTEGER :: save_mode, jerr, u, ios
    INTEGER(8) :: fsize
    LOGICAL :: there, created
    CHARACTER(LEN=8) :: wr
    CHARACTER(LEN=56) :: note
    CHARACTER(LEN=80) :: why
    CHARACTER(LEN=200) :: msg

    IF (.NOT. g_initialized) THEN
       ierr = EQU_ERR_NOT_INIT
       RETURN
    END IF
    IF (.NOT. g_has_equilibrium) THEN
       CALL set_error('write_geqdsk: no equilibrium (run first)')
       ierr = EQU_ERR_INVALID
       RETURN
    END IF
    IF (.NOT. c_to_f(path, fpath)) THEN
       CALL set_error('write_geqdsk: the path is longer than 80 characters')
       ierr = EQU_ERR_INVALID
       RETURN
    END IF
    IF (LEN_TRIM(fpath) == 0) THEN
       CALL set_error('write_geqdsk: the path is blank')
       ierr = EQU_ERR_INVALID
       RETURN
    END IF
    IF (LEN_TRIM(fpath) > LEN(KNAMEQ)) THEN
       CALL set_error('write_geqdsk: the path is longer than 80 characters')
       ierr = EQU_ERR_INVALID
       RETURN
    END IF
    why = host_file_refusal(fpath)
    IF (LEN_TRIM(why) > 0) THEN
       CALL set_error('write_geqdsk: '//TRIM(fpath)//' '//TRIM(why))
       ierr = EQU_ERR_INVALID
       RETURN
    END IF
    ! EQU's writer uses unit 21 (equ_eqdsk.f90); one the host has open
    ! would be taken over and closed.
    INQUIRE(UNIT=21, OPENED=there)
    IF (there) THEN
       CALL set_error('write_geqdsk: Fortran unit 21, which EQU''s writer uses, '// &
                      'is open in this process')
       ierr = EQU_ERR_CALC_FAILED
       RETURN
    END IF
    INQUIRE(FILE=TRIM(fpath), EXIST=there)
    IF (there .AND. overwrite == 0) THEN
       CALL set_error('write_geqdsk: '//TRIM(fpath)//' exists (overwrite=0)')
       ierr = EQU_ERR_INVALID
       RETURN
    END IF
    IF (there) THEN
       ! An existing file the process may not write: FWOPEN would open it
       ! read-only and the first WRITE fail.
       INQUIRE(FILE=TRIM(fpath), WRITE=wr)
       IF (wr == 'NO') THEN
          CALL set_error('write_geqdsk: '//TRIM(fpath)//' exists and is not writable')
          ierr = EQU_ERR_INVALID
          RETURN
       END IF
    ELSE
       ! A new file is created here with STATUS='NEW' (O_EXCL: a name taken
       ! meanwhile, or a dangling link, is refused, not opened), so that a
       ! failed write removes only a file this call made.
       u = free_unit()
       IF (u < 0) THEN
          CALL set_error('write_geqdsk: no free Fortran unit in 30..99')
          ierr = EQU_ERR_CALC_FAILED
          RETURN
       END IF
       msg = ' '
       OPEN(UNIT=u, FILE=TRIM(fpath), STATUS='NEW', ACTION='WRITE', FORM='FORMATTED', &
            IOSTAT=ios, IOMSG=msg)
       IF (ios /= 0) THEN
          CALL set_error('write_geqdsk: '//TRIM(fpath)//' cannot be created: '//TRIM(msg))
          ierr = EQU_ERR_INVALID
          RETURN
       END IF
       CLOSE(u)
    END IF
    created = .NOT. there
    ! The file exists now (the host's, or the empty one made above):
    ! FWOPEN opens it for writing without a prompt.
    save_name = KNAMEQ
    save_mode = MODEFW
    KNAMEQ = TRIM(fpath)
    MODEFW = 0
    CALL equ_eqdsk_write(jerr)
    KNAMEQ = save_name
    MODEFW = save_mode
    ! gfortran's runtime does not report every failed write (past
    ! RLIMIT_FSIZE the file is cut and IOSTAT stays 0): the file must end
    ! with the writer's last record.
    IF (jerr == 0) THEN
       IF (.NOT. ends_with_last_record(TRIM(fpath))) jerr = 13
    END IF
    IF (jerr /= 0) THEN
       ! The file this call created is removed, so that a part-written one
       ! is not loaded later; a file that was there is left as it is.
       IF (created) THEN
          note = '; the part-written file could not be removed'
          u = free_unit()
          IF (u > 0) THEN
             OPEN(UNIT=u, FILE=TRIM(fpath), STATUS='OLD', IOSTAT=ios)
             IF (ios == 0) CLOSE(u, STATUS='DELETE', IOSTAT=ios)
             IF (ios == 0) note = '; the part-written file was removed'
          END IF
       ELSE
          note = '; the file that was there may be incomplete'
       END IF
       IF (jerr == 13) THEN
          CALL set_error('write_geqdsk: '//TRIM(fpath)//' not written (ierr=13: '// &
                         'it ends before its last record)'//TRIM(note))
       ELSE
          CALL set_error('write_geqdsk: '//TRIM(fpath)//' not written (ierr='// &
                         itoa(jerr)//')'//TRIM(note))
       END IF
       ierr = EQU_ERR_CALC_FAILED
       RETURN
    END IF
    INQUIRE(FILE=TRIM(fpath), EXIST=there, SIZE=fsize)
    IF (.NOT. there .OR. fsize <= 0) THEN
       CALL set_error('write_geqdsk: '//TRIM(fpath)//' is missing or empty '// &
                      'after the write')
       ierr = EQU_ERR_CALC_FAILED
       RETURN
    END IF
    ierr = EQU_OK
  END FUNCTION equ_api_write_geqdsk

  !-------------------------------------------------------------------
  ! equ_last_error : the reason of the last failure (EQ's eq_last_error).
  !-------------------------------------------------------------------
  FUNCTION equ_api_last_error(buf, buflen) RESULT(ierr) &
           BIND(C, NAME="equ_last_error")
    CHARACTER(KIND=C_CHAR), DIMENSION(*), INTENT(INOUT) :: buf
    INTEGER(C_INT), VALUE, INTENT(IN) :: buflen
    INTEGER(C_INT) :: ierr
    INTEGER :: i, n
    IF (.NOT. g_initialized) THEN
       ierr = EQU_ERR_NOT_INIT
       RETURN
    END IF
    IF (buflen < 1) THEN
       ierr = EQU_ERR_INVALID
       RETURN
    END IF
    n = MIN(LEN_TRIM(g_errmsg), buflen - 1)
    DO i = 1, n
       buf(i) = g_errmsg(i:i)
    END DO
    buf(n + 1) = C_NULL_CHAR
    ierr = EQU_OK
  END FUNCTION equ_api_last_error

  FUNCTION equ_api_finalize() RESULT(ierr) BIND(C, NAME="equ_finalize")
    INTEGER(C_INT) :: ierr
    g_initialized = .FALSE.
    g_has_equilibrium = .FALSE.
    g_dirty = .FALSE.
    g_mode = -1
    g_errmsg = ' '
    ierr = EQU_OK
  END FUNCTION equ_api_finalize

  FUNCTION equ_api_state_abi_version() RESULT(v) &
           BIND(C, NAME="equ_state_abi_version")
    INTEGER(C_INT) :: v
    v = EQU_STATE_ABI_VERSION
  END FUNCTION equ_api_state_abi_version

  FUNCTION equ_api_state_size() RESULT(n) BIND(C, NAME="equ_state_size")
    INTEGER(C_SIZE_T) :: n
    TYPE(equ_state_c) :: probe
    n = C_SIZEOF(probe)
  END FUNCTION equ_api_state_size

  ! ===================================================================
  ! Helpers
  ! ===================================================================

  !-------------------------------------------------------------------
  ! check_inputs : the checks of design section 8, each reported through
  ! REPORT(name, code, message). Shared by equ_validate and equ_run.
  !-------------------------------------------------------------------
  SUBROUTINE check_inputs(report)
    USE geo_mod, ONLY: nr, nz
    USE eqv_mod, ONLY: nv
    USE equ_mod, ONLY: nsumax, isep, ieqmax, msetup, iodmax, iadmax, eodmax
    USE par_mod, ONLY: rwmn, rwmx, zwmx, icp
    USE vac_mod, ONLY: msfx, ncoil, ilimt, isvac, ivbnd, rcoil, zcoil, ccoil
    USE, INTRINSIC :: ieee_arithmetic, ONLY: ieee_is_finite
    USE aaa_mod, ONLY: iudsym, icvdm, nsfix
    USE cnt_mod, ONLY: ieqrd
    USE eqinit_mod, ONLY: knamcoil
    INTERFACE
       SUBROUTINE report(pname, code, msg)
         IMPORT :: C_INT
         CHARACTER(LEN=*), INTENT(IN) :: pname, msg
         INTEGER(C_INT), INTENT(IN) :: code
       END SUBROUTINE report
    END INTERFACE
    INTEGER :: n, nivac, ios, nmark, jerr, nrep
    REAL(dp) :: bx_rmin, bx_rmax, bx_z, rv(0:30), zv(0:30)
    CHARACTER(LEN=128) :: why
    CHARACTER(LEN=40) :: rz

    nrep = 0

    ! --- bounds the arrays need (equcomm.f90) ---
    ! NR - 1 and NZ - 1 powers of two: the Buneman solver (eqgrd's csrz,
    ! eqpde's cyclic reduction) halves both directions.
    ! NR, NZ >= 5: with 3, eqgrd's csrz recursion writes csrz(0) or loops.
    IF (nr < 5 .OR. nr > EQU_MAX_NR .OR. .NOT. pow2_plus_1(nr)) CALL rep('NR', &
         EQU_DIAG_OUT_OF_RANGE, 'NR='//itoa(nr)//' must be 2**k+1 in 5..257 '// &
         '(5, 9, 17, 33, 65, 129, 257): the Buneman solver')
    IF (nz < 5 .OR. nz > EQU_MAX_NZ .OR. .NOT. pow2_plus_1(nz)) CALL rep('NZ', &
         EQU_DIAG_OUT_OF_RANGE, 'NZ='//itoa(nz)//' must be 2**k+1 in 5..257 '// &
         '(5, 9, 17, 33, 65, 129, 257): the Buneman solver')
    ! NV >= 3: eqout prints rbv(nv-2), eqpfds reads pds0(nv-2).
    IF (nv < 3 .OR. nv > EQU_MAX_NV) CALL rep('NV', EQU_DIAG_OUT_OF_RANGE, &
         'NV='//itoa(nv)//' is outside 3..101 (ivdm)')
    IF (nsumax < 3 .OR. nsumax > EQU_MAX_NSU) CALL rep('NSUMAX', &
         EQU_DIAG_OUT_OF_RANGE, 'NSUMAX='//itoa(nsumax)//' is outside 3..1542 (isrzdm)')
    ! A positive MSFX is lowered by eqchek (to 17, or 9 when up-down
    ! symmetric); a negative one counts given markers RVAC/ZVAC(0:30).
    IF (msfx < -(nsfix - 1)) CALL rep('MSFX', EQU_DIAG_OUT_OF_RANGE, &
         '|MSFX|='//itoa(ABS(msfx))//' is above 29 (the marker arrays)')
    DO n = 0, icvdm
       IF (ncoil(n) < 0 .OR. ncoil(n) > 100) CALL rep('NCOIL['//itoa(n)//']', &
            EQU_DIAG_OUT_OF_RANGE, 'NCOIL='//itoa(ncoil(n))//' is outside 0..100 '// &
            '(filaments per coil group)')
    END DO
    ! The limiter branch of eqlim reads locals it never sets (rzla, za,
    ! rzla2): a question for the code's lead; refused in the library.
    IF (ilimt /= 0) CALL rep('ILIMT', EQU_DIAG_OUT_OF_RANGE, &
         'ILIMT must be 0: eqlim''s limiter branch reads variables it never sets')
    ! eqlim reads IVBND points of RVBND, ZVBND(50), which no input sets.
    IF (ivbnd /= 0) CALL rep('IVBND', EQU_DIAG_OUT_OF_RANGE, &
         'IVBND must be 0: the vacuum boundary points it counts (RVBND, ZVBND) '// &
         'are not inputs of &EQU')

    ! --- what eqchek refuses outright (equinit.f90) ---
    IF (ieqrd /= 0) CALL rep('IEQRD', EQU_DIAG_OUT_OF_RANGE, &
         'IEQRD must be 0 (eqchek refuses any other value)')

    ! --- the box, the profile and the switches ---
    IF (.NOT. (rwmn > 0.0_dp)) CALL rep('RWMN', EQU_DIAG_OUT_OF_RANGE, &
         'RWMN must be > 0')
    IF (.NOT. (rwmx > rwmn)) CALL rep('RWMX', EQU_DIAG_INCONSISTENT_PAIR, &
         'RWMX must be > RWMN')
    IF (.NOT. (zwmx > 0.0_dp)) CALL rep('ZWMX', EQU_DIAG_OUT_OF_RANGE, &
         'ZWMX must be > 0')
    ! |ICP(1)| = 9: eqpfds reads pds0(3) before it sets it when NV = 3.
    IF (ABS(icp(1)) == 9 .AND. nv < 4) CALL rep('NV', EQU_DIAG_INCONSISTENT_PAIR, &
         'NV must be >= 4 with |ICP(1)| = 9 (eqpfds)')
    SELECT CASE (ABS(icp(1)))
    CASE (1, 2, 9, 11)
    CASE DEFAULT
       CALL rep('ICP[1]', EQU_DIAG_OUT_OF_RANGE, &
            'ICP(1)='//itoa(icp(1))//': eqpds0 handles |ICP(1)| = 1, 2, 9, 11 only')
    END SELECT
    IF (isvac /= 0 .AND. isvac /= 1) CALL rep('ISVAC', EQU_DIAG_OUT_OF_RANGE, &
         'ISVAC must be 0 or 1')
    ! The code takes ISEP's sign into account (iabs(isep), eqsep).
    IF (ABS(isep) > 4) CALL rep('ISEP', EQU_DIAG_OUT_OF_RANGE, &
         'ISEP must be -4..4')
    IF (iudsym /= 0 .AND. iudsym /= 1) CALL rep('IUDSYM', EQU_DIAG_OUT_OF_RANGE, &
         'IUDSYM must be 0 or 1')
    IF (ieqmax < 0) CALL rep('IEQMAX', EQU_DIAG_OUT_OF_RANGE, 'IEQMAX must be >= 0')
    IF (msetup < 0) CALL rep('MSETUP', EQU_DIAG_OUT_OF_RANGE, 'MSETUP must be >= 0')
    ! eqode's loop must run once: it starts with errod = 1, and the
    ! derivatives it uses after the loop are set only inside it.
    IF (iodmax < 1) CALL rep('IODMAX', EQU_DIAG_OUT_OF_RANGE, 'IODMAX must be >= 1')
    IF (.NOT. (eodmax < 1.0_dp)) CALL rep('EODMAX', EQU_DIAG_OUT_OF_RANGE, &
         'EODMAX must be < 1 (eqode''s first error is 1)')
    IF (iadmax < 0) CALL rep('IADMAX', EQU_DIAG_OUT_OF_RANGE, 'IADMAX must be >= 0')

    ! --- the coil file, or with 'done' the coils in memory ---
    IF (TRIM(knamcoil) /= 'done') THEN
       why = ' '
       CALL scan_coil_file(TRIM(knamcoil), why)
       IF (LEN_TRIM(why) > 0) CALL rep('KNAMCOIL', EQU_DIAG_FILE_MISSING, why)
    ELSE
       ! The inputs' coils: after init the JT-60U groups 1..4, zeros in the
       ! others (a coil file a run read is not kept). A group with NCOIL > 0
       ! and filaments at R = 0 has no flux, its current's fit fails and
       ! eqtrc started off the grid (QUEST's namelist with 'done'); R < 0
       ! indexes flxfun's table below its bounds, as in a file.
       DO n = 1, icvdm
          IF (ncoil(n) <= 0 .OR. ncoil(n) > 100) CYCLE
          IF (.NOT. ALL(rcoil(1:ncoil(n), n) > 0.0_dp .AND. &
                        ieee_is_finite(rcoil(1:ncoil(n), n)) .AND. &
                        ieee_is_finite(zcoil(1:ncoil(n), n)) .AND. &
                        ieee_is_finite(ccoil(1:ncoil(n), n)))) &
             CALL rep('NCOIL['//itoa(n)//']', EQU_DIAG_INCONSISTENT_PAIR, &
                  'KNAMCOIL = ''done'' and the coils in memory of group '//itoa(n)// &
                  ' have R <= 0 or values that are not finite (after init only '// &
                  'the JT-60U groups 1..4 are set)')
       END DO
    END IF

    ! --- the box and the marker points as eqchek leaves them ---
    ! eqchek (after eqflin, as in a run) takes RMAJ, RPLA from the given
    ! markers when MSFX < 0, generates the markers from the shape when
    ! MSFX > 0 (lowering MSFX to 17, or 9 when symmetric), widens the box
    ! to RMAJ -+ 1.2*RPLA and |Z| < 1.2*ELIP*RPLA, and refuses more fitted
    ! coil groups than markers. The checks below run eqflin and eqchek on
    ! a copy (eqchek_preview) and look at what they leave: a marker
    ! outside the box indexes the vacuum field svac out of bounds in
    ! eqadj0 (QUEST with ZWMX = 0.6: index -177; the defaults with
    ! ELIPUP = 1.5 or ZPLA = 0.4 generate markers above the box). Only
    ! when nothing above was reported: eqchek indexes by these inputs.
    IF (nrep == 0) THEN
       CALL eqchek_preview(jerr, bx_rmin, bx_rmax, bx_z, nmark, nivac, rv, zv)
       IF (jerr == 3) CALL rep('IVAC', EQU_DIAG_INCONSISTENT_PAIR, &
            itoa(nivac)//' coil groups are fitted (IVAC(i)>=0, i>0) but there are '// &
            itoa(nmark)//' marker points (MSFX as eqchek leaves it)')
       ! Backstops: with the checks above in place, scan_coil_file has
       ! refused a file eqflin cannot read, and the IEQRD and NR, NZ, NV
       ! checks what eqchek refuses (ierr 1, 2); these two report only if
       ! eqflin or eqchek come to refuse more, or (-1) when the host holds
       ! every Fortran unit of 30..99 open.
       IF (jerr == -1) CALL rep('KNAMCOIL', EQU_DIAG_FILE_MISSING, &
            'eqflin could not read the coil file '//TRIM(knamcoil)// &
            ' (or no Fortran unit of 30..99 was free)')
       IF (jerr /= 0 .AND. jerr /= 3 .AND. jerr /= -1) CALL rep('IEQRD', &
            EQU_DIAG_OUT_OF_RANGE, 'eqchek refuses the inputs (ierr='//itoa(jerr)//')')
       ! ierr 3 comes after the box is widened; -1 (eqflin) before it.
       IF (jerr == -1) RETURN
       IF (.NOT. (bx_rmin > 0.0_dp)) THEN
          WRITE(rz, '(ES10.3)', IOSTAT=ios) bx_rmin
          IF (ios /= 0) rz = '(not printable)'
          CALL rep('RWMN', EQU_DIAG_OUT_OF_RANGE_AFTER_DEP, &
               'eqchek lowers the box''s inner edge to RMAJ - 1.2*RPLA ='//TRIM(rz)// &
               ' <= 0 (RMAJ, RPLA from the markers when MSFX < 0)')
       END IF
       ! eqadj scales the markers about (RVAC(0) + RVAC(1))/2 by a ratio
       ! with RVAC(1) - RVAC(0) below: equal radii give 0/0 and NaN indices.
       IF (.NOT. (ABS(rv(1) - rv(0)) > 0.0_dp)) CALL rep('RVAC[1]', &
            EQU_DIAG_INCONSISTENT_PAIR, 'markers 0 and 1 must have different R '// &
            '(eqadj divides by RVAC(1) - RVAC(0))')
       DO n = 0, nmark
          IF (.NOT. (rv(n) > bx_rmin .AND. rv(n) < bx_rmax .AND. ABS(zv(n)) < bx_z)) THEN
             WRITE(rz, '(2(1X,ES10.3))', IOSTAT=ios) rv(n), zv(n)
             IF (ios /= 0) rz = ' (not printable)'
             CALL rep('RVAC['//itoa(n)//']', EQU_DIAG_OUT_OF_RANGE_AFTER_DEP, &
                  'the marker point (R, Z) ='//TRIM(rz)//' is outside the box as '// &
                  'eqchek sets it (given when MSFX <= 0, generated when MSFX > 0)')
          END IF
       END DO
    END IF

  CONTAINS

    SUBROUTINE rep(pname, code, msg)
      CHARACTER(LEN=*), INTENT(IN) :: pname, msg
      INTEGER(C_INT), INTENT(IN) :: code
      nrep = nrep + 1
      CALL report(pname, code, msg)
    END SUBROUTINE rep

  END SUBROUTINE check_inputs

  !-------------------------------------------------------------------
  ! eqchek_preview : run eqflin (unless KNAMCOIL is 'done') and eqchek as
  ! a run does, read the box, MSFX and the marker points they leave, and
  ! put back everything they changed: the image's variables (the stash:
  ! the &EQU variables and the coil and limiter arrays eqflin reads), the
  ! Solovev constants and nivac eqchek sets. eqchek prints its notes on
  ! unit 6, as in a run.
  !-------------------------------------------------------------------
  SUBROUTINE eqchek_preview(jerr, bx_rmin, bx_rmax, bx_z, nmark, nivac_out, rv, zv)
    USE eqinit_mod, ONLY: eqflin, eqchek, knamcoil
    USE equ_mod, ONLY: asol, esol, ssol, qsol
    USE vac_mod, ONLY: nivac, msfx, rvac, zvac
    USE par_mod, ONLY: rwmn, rwmx, zwmx
    INTEGER, INTENT(OUT) :: jerr, nmark, nivac_out
    REAL(dp), INTENT(OUT) :: bx_rmin, bx_rmax, bx_z, rv(0:30), zv(0:30)
    REAL(dp) :: a_asol, a_esol, a_ssol, a_qsol
    INTEGER :: a_nivac, ferr, ucoil

    a_asol = asol; a_esol = esol; a_ssol = ssol; a_qsol = qsol; a_nivac = nivac
    CALL stash_save
    ferr = 0
    IF (TRIM(knamcoil) /= 'done') THEN
       ucoil = free_unit()
       IF (ucoil < 0) THEN
          ferr = -1
       ELSE
          CALL eqflin(ucoil, ferr)
       END IF
    END IF
    IF (ferr == 0 .AND. .NOT. equ_failed()) THEN
       CALL eqchek(jerr)
    ELSE
       jerr = -1
    END IF
    IF (equ_failed()) CALL equ_status_clear
    bx_rmin = rwmn
    bx_rmax = rwmx
    bx_z = zwmx
    nmark = MIN(ABS(msfx), 30)
    nivac_out = nivac
    rv = rvac
    zv = zvac
    CALL stash_restore
    asol = a_asol; esol = a_esol; ssol = a_ssol; qsol = a_qsol; nivac = a_nivac
  END SUBROUTINE eqchek_preview

  LOGICAL FUNCTION pow2_plus_1(n)
    INTEGER, INTENT(IN) :: n
    INTEGER :: m
    m = n - 1
    pow2_plus_1 = m > 0 .AND. IAND(m, m - 1) == 0
  END FUNCTION pow2_plus_1

  !-------------------------------------------------------------------
  ! scan_coil_file : does the file hold what eqflin will read (equinit.f90,
  ! eqflin): for each group n = 1..18 with NCOIL(n) > 0 a header line and
  ! NCOIL(n) lines of (3d10.3); then, if ILIMT > 0, a header line and
  ! ILIMT lines of (2d10.3)? WHY is blank when it does.
  !-------------------------------------------------------------------
  SUBROUTINE scan_coil_file(fname, why)
    USE, INTRINSIC :: ieee_arithmetic, ONLY: ieee_is_finite
    USE vac_mod, ONLY: ncoil, ilimt
    USE aaa_mod, ONLY: icvdm
    CHARACTER(LEN=*), INTENT(IN) :: fname
    CHARACTER(LEN=*), INTENT(OUT) :: why
    INTEGER :: u, ios, n, nn
    CHARACTER(LEN=10) :: aname
    CHARACTER(LEN=80) :: r
    REAL(dp) :: a, b, c
    LOGICAL :: there

    why = ' '
    r = host_file_refusal(fname)
    IF (LEN_TRIM(r) > 0) THEN
       why = 'the coil file '//fname//' '//TRIM(r)
       RETURN
    END IF
    INQUIRE(FILE=fname, EXIST=there)
    IF (.NOT. there) THEN
       why = 'no coil file '//fname//' (relative to the working directory)'
       RETURN
    END IF
    OPEN(NEWUNIT=u, FILE=fname, STATUS='OLD', ACTION='READ', FORM='FORMATTED', &
         IOSTAT=ios)
    IF (ios /= 0) THEN
       why = 'cannot open the coil file '//fname
       RETURN
    END IF
    DO n = 1, icvdm
       IF (ncoil(n) <= 0) CYCLE
       READ(u, '(a10)', IOSTAT=ios) aname
       IF (ios /= 0) GOTO 800
       DO nn = 1, ncoil(n)
          READ(u, '(3d10.3)', IOSTAT=ios) a, b, c
          IF (ios /= 0) GOTO 800
          ! flxfun indexes its table by the radius: a filament at R <= 0
          ! reads it below its bounds (QUEST with -0.1545: index -25).
          IF (.NOT. (a > 0.0_dp .AND. ieee_is_finite(a) .AND. ieee_is_finite(b) &
                     .AND. ieee_is_finite(c))) THEN
             why = 'the coil file '//fname//', group '//itoa(n)//', filament '// &
                   itoa(nn)//': R must be > 0 and R, Z, weight finite'
             CLOSE(u)
             RETURN
          END IF
       END DO
    END DO
    IF (ilimt > 0) THEN
       READ(u, '(a10)', IOSTAT=ios) aname
       IF (ios /= 0) GOTO 810
       DO nn = 1, ilimt
          READ(u, '(2d10.3)', IOSTAT=ios) a, b
          IF (ios /= 0) GOTO 810
       END DO
    END IF
    CLOSE(u)
    RETURN
800 why = 'the coil file '//fname//' ends or fails before group '//itoa(n)// &
          ' (NCOIL='//itoa(ncoil(n))//')'
    CLOSE(u)
    RETURN
810 why = 'the coil file '//fname//' ends or fails in the limiter points '// &
          '(ILIMT='//itoa(ilimt)//')'
    CLOSE(u)
  END SUBROUTINE scan_coil_file

  !-------------------------------------------------------------------
  ! ends_with_last_record : the G-EQDSK file p ends with the record
  ! equ_eqdsk_write writes last (format 2024: 0, 0.D0, 0) and a newline.
  ! Without a free unit it is not checked (.TRUE.).
  !-------------------------------------------------------------------
  LOGICAL FUNCTION ends_with_last_record(p)
    CHARACTER(LEN=*), INTENT(IN) :: p
    CHARACTER(LEN=26) :: last
    CHARACTER(LEN=27) :: tail
    INTEGER :: u, ios
    INTEGER(8) :: n
    ends_with_last_record = .FALSE.
    WRITE(last, '(i5,e16.9,i5)') 0, 0.0_dp, 0
    INQUIRE(FILE=p, SIZE=n)
    IF (n < LEN(tail)) RETURN
    u = free_unit()
    IF (u < 0) THEN
       ends_with_last_record = .TRUE.
       RETURN
    END IF
    OPEN(UNIT=u, FILE=p, STATUS='OLD', ACTION='READ', ACCESS='STREAM', &
         FORM='UNFORMATTED', IOSTAT=ios)
    IF (ios /= 0) RETURN
    READ(u, POS=n-LEN(tail)+1, IOSTAT=ios) tail
    CLOSE(u)
    IF (ios /= 0) RETURN
    ends_with_last_record = tail == last//ACHAR(10)
  END FUNCTION ends_with_last_record

  !-------------------------------------------------------------------
  ! host_file_refusal : why the library does not open path p, blank if it
  ! may. p is taken as OPEN takes it (trailing blanks dropped, leading
  ! ones kept). A name under /dev or /proc is refused as written; through
  ! any name (a link, "..", /dev/fd/0, a named FIFO) a file that exists
  ! must be a regular file and not one of the process's standard input,
  ! output or error, which a stdio MCP server owns (equ_path.c: stat(2)
  ! follows the links). A name that does not exist is left to the caller.
  !-------------------------------------------------------------------
  FUNCTION host_file_refusal(p) RESULT(why)
    CHARACTER(LEN=*), INTENT(IN) :: p
    CHARACTER(LEN=80) :: why
    CHARACTER(LEN=LEN_TRIM(p)) :: q
    q = p(1:LEN_TRIM(p))
    why = ' '
    IF (q == '/dev' .OR. q == '/proc' .OR. q(1:MIN(5, LEN(q))) == '/dev/' .OR. &
        q(1:MIN(6, LEN(q))) == '/proc/') THEN
       why = 'is under /dev or /proc'
       RETURN
    END IF
    SELECT CASE (c_path_kind(q//C_NULL_CHAR))
    CASE (PATH_ABSENT, PATH_REGULAR)
    CASE (PATH_OTHER)
       why = 'is not a regular file (a directory, pipe, FIFO, terminal or device)'
    CASE (PATH_STD_STREAM)
       why = 'is the standard input, output or error of this process'
    CASE DEFAULT
       why = 'cannot be checked (stat failed: a loop of links, no access, ...)'
    END SELECT
  END FUNCTION host_file_refusal

  !-------------------------------------------------------------------
  ! free_unit : the first unit of 30..99 that is not open, or -1.
  !-------------------------------------------------------------------
  INTEGER FUNCTION free_unit()
    INTEGER :: k
    LOGICAL :: used
    DO k = 30, 99
       INQUIRE(UNIT=k, OPENED=used)
       IF (.NOT. used) THEN
          free_unit = k
          RETURN
       END IF
    END DO
    free_unit = -1
  END FUNCTION free_unit

  SUBROUTINE restore_if_dirty
    IF (g_dirty) THEN
       CALL image_restore
       g_dirty = .FALSE.
    END IF
  END SUBROUTINE restore_if_dirty

  SUBROUTINE set_error(msg)
    CHARACTER(LEN=*), INTENT(IN) :: msg
    g_errmsg = msg
  END SUBROUTINE set_error

  FUNCTION itoa(i) RESULT(s)
    INTEGER, INTENT(IN) :: i
    CHARACTER(LEN=:), ALLOCATABLE :: s
    CHARACTER(LEN=16) :: b
    WRITE(b, '(I0)') i
    s = TRIM(b)
  END FUNCTION itoa

  !-------------------------------------------------------------------
  ! c_to_f : copy a NUL-terminated C string into F (blank-padded).
  ! .FALSE. when it does not fit; trailing blanks beyond F do not count
  ! (EQ's c_str_overflows rule, with the same 4096-character scan).
  !-------------------------------------------------------------------
  LOGICAL FUNCTION c_to_f(s, f)
    CHARACTER(KIND=C_CHAR), DIMENSION(*), INTENT(IN) :: s
    CHARACTER(LEN=*), INTENT(OUT) :: f
    INTEGER :: i, j
    f = ' '
    c_to_f = .TRUE.
    DO i = 1, LEN(f)
       IF (s(i) == C_NULL_CHAR) RETURN
       f(i:i) = s(i)
    END DO
    ! F is full: what follows must be blanks up to the NUL.
    DO j = LEN(f) + 1, LEN(f) + 4096
       IF (s(j) == C_NULL_CHAR) RETURN
       IF (s(j) /= ' ') EXIT
    END DO
    c_to_f = .FALSE.
  END FUNCTION c_to_f

END MODULE equ_api
