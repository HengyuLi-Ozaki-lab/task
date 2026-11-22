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
  INTEGER, PARAMETER :: COIL_UNIT = 18     ! the program's unit for the coil file

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
    USE eqinit_mod, ONLY: eqflin, eqchek
    USE eqsub_mod, ONLY: eqgrd, eqout
    USE eqset_mod, ONLY: eqset
    USE eqfct_mod, ONLY: eqfct
    USE equpl_mod, ONLY: eqpl_init, eqpl_prof, eqpl_get, eqpl_put
    USE trset_mod, ONLY: trset
    USE trpl_mod, ONLY: trpl_init, trpl_put
    INTEGER(C_INT), VALUE, INTENT(IN) :: mode
    INTEGER(C_INT) :: ierr
    INTEGER :: jerr
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
    CALL eqflin(COIL_UNIT, jerr)
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
  ! name and MODEFW set so that FWOPEN does not prompt: 0 overwrites,
  ! 3 refuses an existing file (lib/libfio.f90 FWOPEN).
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
    INTEGER :: save_mode, jerr
    INTEGER(8) :: fsize
    LOGICAL :: there

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
    INQUIRE(FILE=TRIM(fpath), EXIST=there)
    IF (there .AND. overwrite == 0) THEN
       CALL set_error('write_geqdsk: '//TRIM(fpath)//' exists (overwrite=0)')
       ierr = EQU_ERR_INVALID
       RETURN
    END IF
    save_name = KNAMEQ
    save_mode = MODEFW
    KNAMEQ = TRIM(fpath)
    IF (overwrite /= 0) THEN
       MODEFW = 0
    ELSE
       MODEFW = 3
    END IF
    CALL equ_eqdsk_write(jerr)
    KNAMEQ = save_name
    MODEFW = save_mode
    IF (jerr /= 0) THEN
       CALL set_error('write_geqdsk: '//TRIM(fpath)//' not written (ierr='// &
                      itoa(jerr)//')')
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
    USE equ_mod, ONLY: nsumax, isep, ieqmax, msetup, iodmax, iadmax
    USE par_mod, ONLY: rwmn, rwmx, zwmx, icp, rmaj, rpla, elip
    USE vac_mod, ONLY: msfx, ncoil, ilimt, isvac, ivac, rvac, zvac, ivbnd
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
    INTEGER :: n, nivac, ios, nmark
    REAL(dp) :: rrmax, rrmin, rm, rp, bx_rmin, bx_rmax, bx_z
    CHARACTER(LEN=128) :: why
    CHARACTER(LEN=40) :: rz

    ! --- bounds the arrays need (equcomm.f90) ---
    ! NR - 1 and NZ - 1 powers of two: the Buneman solver (eqgrd's csrz,
    ! eqpde's cyclic reduction) halves both directions.
    IF (nr < 3 .OR. nr > EQU_MAX_NR .OR. .NOT. pow2_plus_1(nr)) CALL report('NR', &
         EQU_DIAG_OUT_OF_RANGE, 'NR='//itoa(nr)//' must be 2**k+1 in 3..257 '// &
         '(3, 5, 9, 17, 33, 65, 129, 257): the Buneman solver')
    IF (nz < 3 .OR. nz > EQU_MAX_NZ .OR. .NOT. pow2_plus_1(nz)) CALL report('NZ', &
         EQU_DIAG_OUT_OF_RANGE, 'NZ='//itoa(nz)//' must be 2**k+1 in 3..257 '// &
         '(3, 5, 9, 17, 33, 65, 129, 257): the Buneman solver')
    ! NV >= 3: eqout prints rbv(nv-2), eqpfds reads pds0(nv-2).
    IF (nv < 3 .OR. nv > EQU_MAX_NV) CALL report('NV', EQU_DIAG_OUT_OF_RANGE, &
         'NV='//itoa(nv)//' is outside 3..101 (ivdm)')
    IF (nsumax < 3 .OR. nsumax > EQU_MAX_NSU) CALL report('NSUMAX', &
         EQU_DIAG_OUT_OF_RANGE, 'NSUMAX='//itoa(nsumax)//' is outside 3..1542 (isrzdm)')
    ! A positive MSFX is lowered by eqchek (to 17, or 9 when up-down
    ! symmetric); a negative one counts given markers RVAC/ZVAC(0:30).
    IF (msfx < -(nsfix - 1)) CALL report('MSFX', EQU_DIAG_OUT_OF_RANGE, &
         '|MSFX|='//itoa(ABS(msfx))//' is above 29 (the marker arrays)')
    DO n = 0, icvdm
       IF (ncoil(n) < 0 .OR. ncoil(n) > 100) CALL report('NCOIL['//itoa(n)//']', &
            EQU_DIAG_OUT_OF_RANGE, 'NCOIL='//itoa(ncoil(n))//' is outside 0..100 '// &
            '(filaments per coil group)')
    END DO
    IF (ilimt < 0 .OR. ilimt > 100) CALL report('ILIMT', EQU_DIAG_OUT_OF_RANGE, &
         'ILIMT='//itoa(ilimt)//' is outside 0..100 (limiter points)')
    ! eqlim reads IVBND points of RVBND, ZVBND(50), which no input sets.
    IF (ivbnd /= 0) CALL report('IVBND', EQU_DIAG_OUT_OF_RANGE, &
         'IVBND must be 0: the vacuum boundary points it counts (RVBND, ZVBND) '// &
         'are not inputs of &EQU')

    ! --- what eqchek refuses (equinit.f90), before the coil file is read ---
    IF (ieqrd /= 0) CALL report('IEQRD', EQU_DIAG_OUT_OF_RANGE, &
         'IEQRD must be 0 (eqchek refuses any other value)')
    nivac = -1
    DO n = 0, icvdm
       IF (ivac(n) >= 0) nivac = nivac + 1
    END DO
    ! With a positive MSFX the larger of eqchek's caps (17): eqchek itself
    ! refuses what this lets through (a run error, not a process exit).
    nmark = ABS(msfx)
    IF (msfx > 17) nmark = 17
    IF (nivac > nmark) CALL report('IVAC', EQU_DIAG_INCONSISTENT_PAIR, &
         itoa(nivac)//' coil groups are fitted (IVAC(i)>=0, i>0) but there are '// &
         itoa(nmark)//' marker points')

    ! --- the box, the profile and the switches ---
    IF (.NOT. (rwmn > 0.0_dp)) CALL report('RWMN', EQU_DIAG_OUT_OF_RANGE, &
         'RWMN must be > 0')
    IF (.NOT. (rwmx > rwmn)) CALL report('RWMX', EQU_DIAG_INCONSISTENT_PAIR, &
         'RWMX must be > RWMN')
    IF (.NOT. (zwmx > 0.0_dp)) CALL report('ZWMX', EQU_DIAG_OUT_OF_RANGE, &
         'ZWMX must be > 0')
    SELECT CASE (ABS(icp(1)))
    CASE (1, 2, 9, 11)
    CASE DEFAULT
       CALL report('ICP[1]', EQU_DIAG_OUT_OF_RANGE, &
            'ICP(1)='//itoa(icp(1))//': eqpds0 handles |ICP(1)| = 1, 2, 9, 11 only')
    END SELECT
    IF (isvac /= 0 .AND. isvac /= 1) CALL report('ISVAC', EQU_DIAG_OUT_OF_RANGE, &
         'ISVAC must be 0 or 1')
    ! The code takes ISEP's sign into account (iabs(isep), eqsep).
    IF (ABS(isep) > 4) CALL report('ISEP', EQU_DIAG_OUT_OF_RANGE, &
         'ISEP must be -4..4')
    IF (iudsym /= 0 .AND. iudsym /= 1) CALL report('IUDSYM', EQU_DIAG_OUT_OF_RANGE, &
         'IUDSYM must be 0 or 1')
    IF (ieqmax < 0) CALL report('IEQMAX', EQU_DIAG_OUT_OF_RANGE, 'IEQMAX must be >= 0')
    IF (msetup < 0) CALL report('MSETUP', EQU_DIAG_OUT_OF_RANGE, 'MSETUP must be >= 0')
    IF (iodmax < 0) CALL report('IODMAX', EQU_DIAG_OUT_OF_RANGE, 'IODMAX must be >= 0')
    IF (iadmax < 0) CALL report('IADMAX', EQU_DIAG_OUT_OF_RANGE, 'IADMAX must be >= 0')

    ! --- the box as eqchek sets it, and the marker points in it ---
    ! eqchek (equinit.f90) takes RMAJ, RPLA from the given markers when
    ! MSFX < 0 (those with R > 0), then widens the box to
    ! RMAJ -+ 1.2*RPLA and |Z| < 1.2*ELIP*RPLA. A marker outside that box
    ! indexes the vacuum field svac out of bounds in eqadj0 (QUEST with
    ! ZWMX = 0.6: index -177); eqadj0 uses marker 0 when MSFX = 0 too.
    IF (rwmn > 0.0_dp .AND. rwmx > rwmn .AND. zwmx > 0.0_dp .AND. &
        msfx >= -(nsfix - 1)) THEN
       rm = rmaj
       rp = rpla
       IF (msfx < 0) THEN
          rrmax = -1.0E10_dp
          rrmin = 1.0E10_dp
          DO n = 0, ABS(msfx)
             IF (rvac(n) > 0.0_dp .AND. rvac(n) > rrmax) rrmax = rvac(n)
             IF (rvac(n) > 0.0_dp .AND. rvac(n) < rrmin) rrmin = rvac(n)
          END DO
          rm = 0.5_dp * (rrmax + rrmin)
          rp = 0.5_dp * ABS(rrmax - rrmin)
       END IF
       bx_rmin = MIN(rwmn, rm - 1.2_dp * rp)
       bx_rmax = MAX(rwmx, rm + 1.2_dp * rp)
       bx_z = MAX(zwmx, 1.2_dp * elip * rp)
       IF (.NOT. (bx_rmin > 0.0_dp)) THEN
          WRITE(rz, '(ES10.3)', IOSTAT=ios) bx_rmin
          IF (ios /= 0) rz = '(not printable)'
          CALL report('RWMN', EQU_DIAG_OUT_OF_RANGE_AFTER_DEP, &
               'eqchek lowers the box''s inner edge to RMAJ - 1.2*RPLA ='//TRIM(rz)// &
               ' <= 0 (RMAJ, RPLA from the markers when MSFX < 0)')
       END IF
       IF (msfx <= 0) THEN
          DO n = 0, ABS(msfx)
             IF (.NOT. (rvac(n) > bx_rmin .AND. rvac(n) < bx_rmax .AND. &
                        ABS(zvac(n)) < bx_z)) THEN
                WRITE(rz, '(2(1X,ES10.3))', IOSTAT=ios) rvac(n), zvac(n)
                IF (ios /= 0) rz = ' (not printable)'
                CALL report('RVAC['//itoa(n)//']', EQU_DIAG_OUT_OF_RANGE_AFTER_DEP, &
                     'the marker point (R, Z) ='//TRIM(rz)//' is outside the box '// &
                     'as eqchek sets it')
             END IF
          END DO
       END IF
    END IF

    ! --- the coil file ---
    IF (TRIM(knamcoil) /= 'done') THEN
       why = ' '
       CALL scan_coil_file(TRIM(knamcoil), why)
       IF (LEN_TRIM(why) > 0) CALL report('KNAMCOIL', EQU_DIAG_FILE_MISSING, why)
    END IF
  END SUBROUTINE check_inputs

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
    USE vac_mod, ONLY: ncoil, ilimt
    USE aaa_mod, ONLY: icvdm
    CHARACTER(LEN=*), INTENT(IN) :: fname
    CHARACTER(LEN=*), INTENT(OUT) :: why
    INTEGER :: u, ios, n, nn
    CHARACTER(LEN=10) :: aname
    REAL(dp) :: a, b, c
    LOGICAL :: there

    why = ' '
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
