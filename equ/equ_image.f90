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
! as set.
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
                     ivtab, ivgrp
  USE cnt_mod, ONLY: ieqout, ieqrd, jeqrd, ieqwt, jeqwt
  IMPLICIT NONE
  PRIVATE
  PUBLIC :: image_save, image_restore, reset_run_state
  INTEGER, PARAMETER :: dp = KIND(1.0D0)

  CHARACTER(LEN=8), SAVE :: s_device
  CHARACTER(LEN=8), SAVE :: s_devnam
  CHARACTER(LEN=70), SAVE :: s_title
  INTEGER, SAVE :: s_nr
  INTEGER, SAVE :: s_nz
  INTEGER, SAVE :: s_nv
  INTEGER, SAVE :: s_nsumax
  INTEGER, SAVE :: s_iudsym
  REAL(dp), SAVE :: s_rwmn
  REAL(dp), SAVE :: s_rwmx
  REAL(dp), SAVE :: s_zwmx
  REAL(dp), SAVE :: s_btv
  REAL(dp), SAVE :: s_tcur
  REAL(dp), SAVE :: s_rmaj
  REAL(dp), SAVE :: s_rpla
  REAL(dp), SAVE :: s_zpla
  REAL(dp), SAVE :: s_elip
  REAL(dp), SAVE :: s_trig
  REAL(dp), SAVE :: s_elipup
  REAL(dp), SAVE :: s_trigup
  REAL(dp), SAVE :: s_yh
  REAL(dp), SAVE :: s_yd
  REAL(dp), SAVE :: s_qaxi
  REAL(dp), SAVE :: s_qsur
  REAL(dp), SAVE :: s_xxli
  INTEGER, SAVE :: s_icp(1:10)
  REAL(dp), SAVE :: s_cp(1:10)
  CHARACTER(LEN=80), SAVE :: s_knamcoil
  INTEGER, SAVE :: s_ivac(0:18)
  INTEGER, SAVE :: s_ncoil(0:18)
  REAL(dp), SAVE :: s_cvac(0:18)
  REAL(dp), SAVE :: s_cvacst(0:18)
  REAL(dp), SAVE :: s_cvacwg(0:18)
  REAL(dp), SAVE :: s_cvact(0:18)
  INTEGER, SAVE :: s_isvac
  INTEGER, SAVE :: s_msfx
  REAL(dp), SAVE :: s_rvac(0:30)
  REAL(dp), SAVE :: s_zvac(0:30)
  INTEGER, SAVE :: s_isep
  REAL(dp), SAVE :: s_dsep
  INTEGER, SAVE :: s_ilimt
  INTEGER, SAVE :: s_ivbnd
  REAL(dp), SAVE :: s_rloop
  REAL(dp), SAVE :: s_zloop
  INTEGER, SAVE :: s_msetup
  REAL(dp), SAVE :: s_esetup
  INTEGER, SAVE :: s_ieqmax
  REAL(dp), SAVE :: s_eeqmax
  INTEGER, SAVE :: s_iodmax
  REAL(dp), SAVE :: s_eodmax
  INTEGER, SAVE :: s_iadmax
  REAL(dp), SAVE :: s_eadmax
  REAL(dp), SAVE :: s_bavmax
  REAL(dp), SAVE :: s_bavmin
  INTEGER, SAVE :: s_ieqout(1:10)
  INTEGER, SAVE :: s_ieqrd
  INTEGER, SAVE :: s_ivp
  INTEGER, SAVE :: s_ivtab
  INTEGER, SAVE :: s_ivgrp
  INTEGER, SAVE :: s_jeqrd
  INTEGER, SAVE :: s_ieqwt
  INTEGER, SAVE :: s_jeqwt

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
  END SUBROUTINE image_restore

  SUBROUTINE reset_run_state(ierr)
    USE equ_mod, ONLY: iad, ieq, iod
    USE cnt_mod, ONLY: time, itime, iread
    USE par_mod, ONLY: btol
    USE vac_mod, ONLY: svac
    USE eqv_mod, ONLY: rbv
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
    empty%nrmax = 0
    empty%nsmax = 0
    empty%time = 0.0_dp
    CALL bpsd_put_plasmaf(empty, ierr)
  END SUBROUTINE reset_run_state

END MODULE equ_image_mod
