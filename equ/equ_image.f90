! equ_image.f90
!
! The inputs of the EQU library interface as the caller set them, and the
! reset of the solver's state before a run (design 2026-11-22, sections 5
! and 9.3).
!
! The solver overwrites some of its inputs: eqout sets RMAJ, RPLA, ELIP,
! TRIG; eqchek enlarges RWMN, RWMX, ZWMX and makes CVAC and CVACST agree;
! eqsol changes BTV and ZPLA; eqflin sets KNAMCOIL to 'done'; eqadj moves
! RVAC and ZVAC. The library keeps an image of every &EQU variable, taken
! after each init, read_parm and set_param, and puts it back before a run
! and before a set that follows a run, so each run starts from the inputs
! as set. The coil and limiter arrays are part of the image too: with
! KNAMCOIL = 'done' they are inputs (after init the JT-60U set), and a run
! with IUDSYM = 1 folds zcoil below the midplane in eqvac0.
!
! reset_run_state clears what eqinit does not set and a run reads: the
! iteration counters iad, ieq, iod, the time counters, iread (eqset's
! restart branch), btol (read by eqsol, set nowhere), the vacuum fields
! svac, the profile rbv (F = R*B_t: with ICP(2) = 2 the setup loop of
! eqequ starts from it, and takes BTV where it is not positive, as in a
! fresh process; a previous run's F would be a different start), and
! bpsd's plasmaf (eqpl_prof reads it before the TR interface puts the
! run's own): an empty one is put, which eqpl_prof reads as the first
! run in a process does. Found by restoring each module variable to its
! value before a first run and comparing the second run's G-EQDSK
! (QUEST, 2026-11-22): rbv alone made the difference.

MODULE equ_image_mod
  USE aaa_mod, ONLY: device, devnam, title, iudsym, ivp
  USE geo_mod, ONLY: nr, nz
  USE eqv_mod, ONLY: nv
  USE equ_mod, ONLY: nsumax, btv, isep, dsep, rloop, zloop, &
                     msetup, esetup, ieqmax, eeqmax, iodmax, eodmax, &
                     iadmax, eadmax, bavmax, bavmin
  USE par_mod, ONLY: rwmn, rwmx, zwmx, tcur, rmaj, rpla, &
                     zpla, elip, trig, elipup, trigup, yh, &
                     yd, qaxi, qsur, xxli, icp, cp
  USE eqinit_mod, ONLY: knamcoil
  USE vac_mod, ONLY: ivac, ncoil, cvac, cvacst, cvacwg, cvact, &
                     isvac, msfx, rvac, zvac, ilimt, ivbnd, &
                     ivtab, ivgrp, rcoil, zcoil, ccoil, rlimt, &
                     zlimt
  USE cnt_mod, ONLY: ieqout, ieqrd, jeqrd, ieqwt, jeqwt
  IMPLICIT NONE
  PRIVATE
  PUBLIC :: image_save, image_restore, image_swap, stash_save, stash_restore, &
            reset_run_state
  INTEGER, PARAMETER :: dp = KIND(1.0D0)

  CHARACTER(LEN=8), SAVE :: s_device, t_device
  CHARACTER(LEN=8), SAVE :: s_devnam, t_devnam
  CHARACTER(LEN=70), SAVE :: s_title, t_title
  INTEGER, SAVE :: s_nr, t_nr
  INTEGER, SAVE :: s_nz, t_nz
  INTEGER, SAVE :: s_nv, t_nv
  INTEGER, SAVE :: s_nsumax, t_nsumax
  INTEGER, SAVE :: s_iudsym, t_iudsym
  REAL(dp), SAVE :: s_rwmn, t_rwmn
  REAL(dp), SAVE :: s_rwmx, t_rwmx
  REAL(dp), SAVE :: s_zwmx, t_zwmx
  REAL(dp), SAVE :: s_btv, t_btv
  REAL(dp), SAVE :: s_tcur, t_tcur
  REAL(dp), SAVE :: s_rmaj, t_rmaj
  REAL(dp), SAVE :: s_rpla, t_rpla
  REAL(dp), SAVE :: s_zpla, t_zpla
  REAL(dp), SAVE :: s_elip, t_elip
  REAL(dp), SAVE :: s_trig, t_trig
  REAL(dp), SAVE :: s_elipup, t_elipup
  REAL(dp), SAVE :: s_trigup, t_trigup
  REAL(dp), SAVE :: s_yh, t_yh
  REAL(dp), SAVE :: s_yd, t_yd
  REAL(dp), SAVE :: s_qaxi, t_qaxi
  REAL(dp), SAVE :: s_qsur, t_qsur
  REAL(dp), SAVE :: s_xxli, t_xxli
  INTEGER, SAVE :: s_icp(1:10), t_icp(1:10)
  REAL(dp), SAVE :: s_cp(1:10), t_cp(1:10)
  CHARACTER(LEN=80), SAVE :: s_knamcoil, t_knamcoil
  INTEGER, SAVE :: s_ivac(0:18), t_ivac(0:18)
  INTEGER, SAVE :: s_ncoil(0:18), t_ncoil(0:18)
  REAL(dp), SAVE :: s_cvac(0:18), t_cvac(0:18)
  REAL(dp), SAVE :: s_cvacst(0:18), t_cvacst(0:18)
  REAL(dp), SAVE :: s_cvacwg(0:18), t_cvacwg(0:18)
  REAL(dp), SAVE :: s_cvact(0:18), t_cvact(0:18)
  INTEGER, SAVE :: s_isvac, t_isvac
  INTEGER, SAVE :: s_msfx, t_msfx
  REAL(dp), SAVE :: s_rvac(0:30), t_rvac(0:30)
  REAL(dp), SAVE :: s_zvac(0:30), t_zvac(0:30)
  INTEGER, SAVE :: s_isep, t_isep
  REAL(dp), SAVE :: s_dsep, t_dsep
  INTEGER, SAVE :: s_ilimt, t_ilimt
  INTEGER, SAVE :: s_ivbnd, t_ivbnd
  REAL(dp), SAVE :: s_rloop, t_rloop
  REAL(dp), SAVE :: s_zloop, t_zloop
  INTEGER, SAVE :: s_msetup, t_msetup
  REAL(dp), SAVE :: s_esetup, t_esetup
  INTEGER, SAVE :: s_ieqmax, t_ieqmax
  REAL(dp), SAVE :: s_eeqmax, t_eeqmax
  INTEGER, SAVE :: s_iodmax, t_iodmax
  REAL(dp), SAVE :: s_eodmax, t_eodmax
  INTEGER, SAVE :: s_iadmax, t_iadmax
  REAL(dp), SAVE :: s_eadmax, t_eadmax
  REAL(dp), SAVE :: s_bavmax, t_bavmax
  REAL(dp), SAVE :: s_bavmin, t_bavmin
  INTEGER, SAVE :: s_ieqout(1:10), t_ieqout(1:10)
  INTEGER, SAVE :: s_ieqrd, t_ieqrd
  INTEGER, SAVE :: s_ivp, t_ivp
  INTEGER, SAVE :: s_ivtab, t_ivtab
  INTEGER, SAVE :: s_ivgrp, t_ivgrp
  INTEGER, SAVE :: s_jeqrd, t_jeqrd
  INTEGER, SAVE :: s_ieqwt, t_ieqwt
  INTEGER, SAVE :: s_jeqwt, t_jeqwt
  REAL(dp), SAVE :: s_rcoil(100,18), t_rcoil(100,18)
  REAL(dp), SAVE :: s_zcoil(100,18), t_zcoil(100,18)
  REAL(dp), SAVE :: s_ccoil(100,18), t_ccoil(100,18)
  REAL(dp), SAVE :: s_rlimt(100), t_rlimt(100)
  REAL(dp), SAVE :: s_zlimt(100), t_zlimt(100)

CONTAINS

  SUBROUTINE image_save
    s_device = device
    s_devnam = devnam
    s_title = title
    s_nr = nr
    s_nz = nz
    s_nv = nv
    s_nsumax = nsumax
    s_iudsym = iudsym
    s_rwmn = rwmn
    s_rwmx = rwmx
    s_zwmx = zwmx
    s_btv = btv
    s_tcur = tcur
    s_rmaj = rmaj
    s_rpla = rpla
    s_zpla = zpla
    s_elip = elip
    s_trig = trig
    s_elipup = elipup
    s_trigup = trigup
    s_yh = yh
    s_yd = yd
    s_qaxi = qaxi
    s_qsur = qsur
    s_xxli = xxli
    s_icp = icp
    s_cp = cp
    s_knamcoil = knamcoil
    s_ivac = ivac
    s_ncoil = ncoil
    s_cvac = cvac
    s_cvacst = cvacst
    s_cvacwg = cvacwg
    s_cvact = cvact
    s_isvac = isvac
    s_msfx = msfx
    s_rvac = rvac
    s_zvac = zvac
    s_isep = isep
    s_dsep = dsep
    s_ilimt = ilimt
    s_ivbnd = ivbnd
    s_rloop = rloop
    s_zloop = zloop
    s_msetup = msetup
    s_esetup = esetup
    s_ieqmax = ieqmax
    s_eeqmax = eeqmax
    s_iodmax = iodmax
    s_eodmax = eodmax
    s_iadmax = iadmax
    s_eadmax = eadmax
    s_bavmax = bavmax
    s_bavmin = bavmin
    s_ieqout = ieqout
    s_ieqrd = ieqrd
    s_ivp = ivp
    s_ivtab = ivtab
    s_ivgrp = ivgrp
    s_jeqrd = jeqrd
    s_ieqwt = ieqwt
    s_jeqwt = jeqwt
    s_rcoil = rcoil
    s_zcoil = zcoil
    s_ccoil = ccoil
    s_rlimt = rlimt
    s_zlimt = zlimt
  END SUBROUTINE image_save

  SUBROUTINE image_restore
    device = s_device
    devnam = s_devnam
    title = s_title
    nr = s_nr
    nz = s_nz
    nv = s_nv
    nsumax = s_nsumax
    iudsym = s_iudsym
    rwmn = s_rwmn
    rwmx = s_rwmx
    zwmx = s_zwmx
    btv = s_btv
    tcur = s_tcur
    rmaj = s_rmaj
    rpla = s_rpla
    zpla = s_zpla
    elip = s_elip
    trig = s_trig
    elipup = s_elipup
    trigup = s_trigup
    yh = s_yh
    yd = s_yd
    qaxi = s_qaxi
    qsur = s_qsur
    xxli = s_xxli
    icp = s_icp
    cp = s_cp
    knamcoil = s_knamcoil
    ivac = s_ivac
    ncoil = s_ncoil
    cvac = s_cvac
    cvacst = s_cvacst
    cvacwg = s_cvacwg
    cvact = s_cvact
    isvac = s_isvac
    msfx = s_msfx
    rvac = s_rvac
    zvac = s_zvac
    isep = s_isep
    dsep = s_dsep
    ilimt = s_ilimt
    ivbnd = s_ivbnd
    rloop = s_rloop
    zloop = s_zloop
    msetup = s_msetup
    esetup = s_esetup
    ieqmax = s_ieqmax
    eeqmax = s_eeqmax
    iodmax = s_iodmax
    eodmax = s_eodmax
    iadmax = s_iadmax
    eadmax = s_eadmax
    bavmax = s_bavmax
    bavmin = s_bavmin
    ieqout = s_ieqout
    ieqrd = s_ieqrd
    ivp = s_ivp
    ivtab = s_ivtab
    ivgrp = s_ivgrp
    jeqrd = s_jeqrd
    ieqwt = s_ieqwt
    jeqwt = s_jeqwt
    rcoil = s_rcoil
    zcoil = s_zcoil
    ccoil = s_ccoil
    rlimt = s_rlimt
    zlimt = s_zlimt
  END SUBROUTINE image_restore

  ! Exchange the module variables and the image: after a run the module
  ! variables hold what the solver left (which get_state and the G-EQDSK
  ! writer read) and the image holds the inputs; a swap puts the inputs
  ! in place for a check or a set, a second swap puts the run's values
  ! back. Uses the stash as its temporary.
  SUBROUTINE image_swap
    t_device = device
    device = s_device
    s_device = t_device
    t_devnam = devnam
    devnam = s_devnam
    s_devnam = t_devnam
    t_title = title
    title = s_title
    s_title = t_title
    t_nr = nr
    nr = s_nr
    s_nr = t_nr
    t_nz = nz
    nz = s_nz
    s_nz = t_nz
    t_nv = nv
    nv = s_nv
    s_nv = t_nv
    t_nsumax = nsumax
    nsumax = s_nsumax
    s_nsumax = t_nsumax
    t_iudsym = iudsym
    iudsym = s_iudsym
    s_iudsym = t_iudsym
    t_rwmn = rwmn
    rwmn = s_rwmn
    s_rwmn = t_rwmn
    t_rwmx = rwmx
    rwmx = s_rwmx
    s_rwmx = t_rwmx
    t_zwmx = zwmx
    zwmx = s_zwmx
    s_zwmx = t_zwmx
    t_btv = btv
    btv = s_btv
    s_btv = t_btv
    t_tcur = tcur
    tcur = s_tcur
    s_tcur = t_tcur
    t_rmaj = rmaj
    rmaj = s_rmaj
    s_rmaj = t_rmaj
    t_rpla = rpla
    rpla = s_rpla
    s_rpla = t_rpla
    t_zpla = zpla
    zpla = s_zpla
    s_zpla = t_zpla
    t_elip = elip
    elip = s_elip
    s_elip = t_elip
    t_trig = trig
    trig = s_trig
    s_trig = t_trig
    t_elipup = elipup
    elipup = s_elipup
    s_elipup = t_elipup
    t_trigup = trigup
    trigup = s_trigup
    s_trigup = t_trigup
    t_yh = yh
    yh = s_yh
    s_yh = t_yh
    t_yd = yd
    yd = s_yd
    s_yd = t_yd
    t_qaxi = qaxi
    qaxi = s_qaxi
    s_qaxi = t_qaxi
    t_qsur = qsur
    qsur = s_qsur
    s_qsur = t_qsur
    t_xxli = xxli
    xxli = s_xxli
    s_xxli = t_xxli
    t_icp = icp
    icp = s_icp
    s_icp = t_icp
    t_cp = cp
    cp = s_cp
    s_cp = t_cp
    t_knamcoil = knamcoil
    knamcoil = s_knamcoil
    s_knamcoil = t_knamcoil
    t_ivac = ivac
    ivac = s_ivac
    s_ivac = t_ivac
    t_ncoil = ncoil
    ncoil = s_ncoil
    s_ncoil = t_ncoil
    t_cvac = cvac
    cvac = s_cvac
    s_cvac = t_cvac
    t_cvacst = cvacst
    cvacst = s_cvacst
    s_cvacst = t_cvacst
    t_cvacwg = cvacwg
    cvacwg = s_cvacwg
    s_cvacwg = t_cvacwg
    t_cvact = cvact
    cvact = s_cvact
    s_cvact = t_cvact
    t_isvac = isvac
    isvac = s_isvac
    s_isvac = t_isvac
    t_msfx = msfx
    msfx = s_msfx
    s_msfx = t_msfx
    t_rvac = rvac
    rvac = s_rvac
    s_rvac = t_rvac
    t_zvac = zvac
    zvac = s_zvac
    s_zvac = t_zvac
    t_isep = isep
    isep = s_isep
    s_isep = t_isep
    t_dsep = dsep
    dsep = s_dsep
    s_dsep = t_dsep
    t_ilimt = ilimt
    ilimt = s_ilimt
    s_ilimt = t_ilimt
    t_ivbnd = ivbnd
    ivbnd = s_ivbnd
    s_ivbnd = t_ivbnd
    t_rloop = rloop
    rloop = s_rloop
    s_rloop = t_rloop
    t_zloop = zloop
    zloop = s_zloop
    s_zloop = t_zloop
    t_msetup = msetup
    msetup = s_msetup
    s_msetup = t_msetup
    t_esetup = esetup
    esetup = s_esetup
    s_esetup = t_esetup
    t_ieqmax = ieqmax
    ieqmax = s_ieqmax
    s_ieqmax = t_ieqmax
    t_eeqmax = eeqmax
    eeqmax = s_eeqmax
    s_eeqmax = t_eeqmax
    t_iodmax = iodmax
    iodmax = s_iodmax
    s_iodmax = t_iodmax
    t_eodmax = eodmax
    eodmax = s_eodmax
    s_eodmax = t_eodmax
    t_iadmax = iadmax
    iadmax = s_iadmax
    s_iadmax = t_iadmax
    t_eadmax = eadmax
    eadmax = s_eadmax
    s_eadmax = t_eadmax
    t_bavmax = bavmax
    bavmax = s_bavmax
    s_bavmax = t_bavmax
    t_bavmin = bavmin
    bavmin = s_bavmin
    s_bavmin = t_bavmin
    t_ieqout = ieqout
    ieqout = s_ieqout
    s_ieqout = t_ieqout
    t_ieqrd = ieqrd
    ieqrd = s_ieqrd
    s_ieqrd = t_ieqrd
    t_ivp = ivp
    ivp = s_ivp
    s_ivp = t_ivp
    t_ivtab = ivtab
    ivtab = s_ivtab
    s_ivtab = t_ivtab
    t_ivgrp = ivgrp
    ivgrp = s_ivgrp
    s_ivgrp = t_ivgrp
    t_jeqrd = jeqrd
    jeqrd = s_jeqrd
    s_jeqrd = t_jeqrd
    t_ieqwt = ieqwt
    ieqwt = s_ieqwt
    s_ieqwt = t_ieqwt
    t_jeqwt = jeqwt
    jeqwt = s_jeqwt
    s_jeqwt = t_jeqwt
    t_rcoil = rcoil
    rcoil = s_rcoil
    s_rcoil = t_rcoil
    t_zcoil = zcoil
    zcoil = s_zcoil
    s_zcoil = t_zcoil
    t_ccoil = ccoil
    ccoil = s_ccoil
    s_ccoil = t_ccoil
    t_rlimt = rlimt
    rlimt = s_rlimt
    s_rlimt = t_rlimt
    t_zlimt = zlimt
    zlimt = s_zlimt
    s_zlimt = t_zlimt
  END SUBROUTINE image_swap

  ! A second copy, to undo a namelist read that fails part-way.
  SUBROUTINE stash_save
    t_device = device
    t_devnam = devnam
    t_title = title
    t_nr = nr
    t_nz = nz
    t_nv = nv
    t_nsumax = nsumax
    t_iudsym = iudsym
    t_rwmn = rwmn
    t_rwmx = rwmx
    t_zwmx = zwmx
    t_btv = btv
    t_tcur = tcur
    t_rmaj = rmaj
    t_rpla = rpla
    t_zpla = zpla
    t_elip = elip
    t_trig = trig
    t_elipup = elipup
    t_trigup = trigup
    t_yh = yh
    t_yd = yd
    t_qaxi = qaxi
    t_qsur = qsur
    t_xxli = xxli
    t_icp = icp
    t_cp = cp
    t_knamcoil = knamcoil
    t_ivac = ivac
    t_ncoil = ncoil
    t_cvac = cvac
    t_cvacst = cvacst
    t_cvacwg = cvacwg
    t_cvact = cvact
    t_isvac = isvac
    t_msfx = msfx
    t_rvac = rvac
    t_zvac = zvac
    t_isep = isep
    t_dsep = dsep
    t_ilimt = ilimt
    t_ivbnd = ivbnd
    t_rloop = rloop
    t_zloop = zloop
    t_msetup = msetup
    t_esetup = esetup
    t_ieqmax = ieqmax
    t_eeqmax = eeqmax
    t_iodmax = iodmax
    t_eodmax = eodmax
    t_iadmax = iadmax
    t_eadmax = eadmax
    t_bavmax = bavmax
    t_bavmin = bavmin
    t_ieqout = ieqout
    t_ieqrd = ieqrd
    t_ivp = ivp
    t_ivtab = ivtab
    t_ivgrp = ivgrp
    t_jeqrd = jeqrd
    t_ieqwt = ieqwt
    t_jeqwt = jeqwt
    t_rcoil = rcoil
    t_zcoil = zcoil
    t_ccoil = ccoil
    t_rlimt = rlimt
    t_zlimt = zlimt
  END SUBROUTINE stash_save

  SUBROUTINE stash_restore
    device = t_device
    devnam = t_devnam
    title = t_title
    nr = t_nr
    nz = t_nz
    nv = t_nv
    nsumax = t_nsumax
    iudsym = t_iudsym
    rwmn = t_rwmn
    rwmx = t_rwmx
    zwmx = t_zwmx
    btv = t_btv
    tcur = t_tcur
    rmaj = t_rmaj
    rpla = t_rpla
    zpla = t_zpla
    elip = t_elip
    trig = t_trig
    elipup = t_elipup
    trigup = t_trigup
    yh = t_yh
    yd = t_yd
    qaxi = t_qaxi
    qsur = t_qsur
    xxli = t_xxli
    icp = t_icp
    cp = t_cp
    knamcoil = t_knamcoil
    ivac = t_ivac
    ncoil = t_ncoil
    cvac = t_cvac
    cvacst = t_cvacst
    cvacwg = t_cvacwg
    cvact = t_cvact
    isvac = t_isvac
    msfx = t_msfx
    rvac = t_rvac
    zvac = t_zvac
    isep = t_isep
    dsep = t_dsep
    ilimt = t_ilimt
    ivbnd = t_ivbnd
    rloop = t_rloop
    zloop = t_zloop
    msetup = t_msetup
    esetup = t_esetup
    ieqmax = t_ieqmax
    eeqmax = t_eeqmax
    iodmax = t_iodmax
    eodmax = t_eodmax
    iadmax = t_iadmax
    eadmax = t_eadmax
    bavmax = t_bavmax
    bavmin = t_bavmin
    ieqout = t_ieqout
    ieqrd = t_ieqrd
    ivp = t_ivp
    ivtab = t_ivtab
    ivgrp = t_ivgrp
    jeqrd = t_jeqrd
    ieqwt = t_ieqwt
    jeqwt = t_jeqwt
    rcoil = t_rcoil
    zcoil = t_zcoil
    ccoil = t_ccoil
    rlimt = t_rlimt
    zlimt = t_zlimt
  END SUBROUTINE stash_restore

  SUBROUTINE reset_run_state(ierr)
    USE equ_mod, ONLY: iad, ieq, iod
    USE cnt_mod, ONLY: time, itime, iread
    USE par_mod, ONLY: btol
    USE vac_mod, ONLY: svac
    USE eqv_mod, ONLY: rbv
    USE equ_mod, ONLY: psep, iisep, irsep, izsep
    USE bpsd, ONLY: bpsd_plasmaf_type, bpsd_put_plasmaf
    INTEGER, INTENT(OUT) :: ierr
    TYPE(bpsd_plasmaf_type) :: empty
    iad = 0
    ieq = 0
    iod = 0
    time = 0.0_dp
    itime = 0
    iread = 0
    btol = 0.0_dp
    svac = 0.0_dp
    rbv = 0.0_dp
    ! The separatrix of the previous run: eqsep sets none of it when
    ! ISEP = 0 (a fresh process has zeros).
    psep = 0.0_dp
    iisep = 0
    irsep = 0
    izsep = 0
    empty%nrmax = 0
    empty%nsmax = 0
    empty%time = 0.0_dp
    CALL bpsd_put_plasmaf(empty, ierr)
  END SUBROUTINE reset_run_state

END MODULE equ_image_mod
