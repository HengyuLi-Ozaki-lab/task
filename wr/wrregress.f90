! wrregress.f90
!
! High-precision regression dump for Phase L-0 regression tests.
! Emits wr_regress.dat (1PE24.16 format) when WR_REGRESS_DUMP=1.
! Otherwise does nothing; normal runs are unaffected.

MODULE wrregress

  PRIVATE
  PUBLIC :: wr_regress_dump_if_enabled

CONTAINS

  SUBROUTINE wr_regress_dump_if_enabled(nstat)
    ! Dumps deterministic, fully initialized state only. The per-ray
    ! pwrmax_rs_nray / pos_pwrmax_rl_nray / pwrmax_rl_nray arrays are
    ! deliberately omitted: pwrmax_rs_nray is left uninitialized in the
    ! locmax<=1 / locmax>=nrsmax branches of wr_calc_pwr and the rl_nray
    ! variants are never assigned anywhere (pre-existing in wr/wrexecr.f90).
    ! These will be re-included in L-6 once that bug is fixed.
    USE wrcomm, ONLY: rkind, &
         RF, RPI, ZPI, PHII, RNZI, RNPHII, RKR0, UUI, &
         NRAYMAX, NSTPMAX, NRSMAX, NRLMAX, NEQ, &
         MDLWRI, MDLWRQ, mode_beam, &
         NSTPMAX_NRAY, RAYS, &
         pos_nrs, pwr_nrs, pos_nrl, pwr_nrl, &
         pos_pwrmax_rs, pwrmax_rs, pos_pwrmax_rl, pwrmax_rl, &
         pos_pwrmax_rs_nray
    USE plcomm, ONLY: MODELG
    IMPLICIT NONE
    INTEGER, INTENT(IN) :: nstat
    INTEGER, PARAMETER :: UNIT_DUMP = 78
    CHARACTER(LEN=16) :: ENV_VAL
    INTEGER :: STAT, NRAY, NRS, NRL, NSTP_END, IOERR, I
    LOGICAL :: ENABLED

    CALL GET_ENVIRONMENT_VARIABLE('WR_REGRESS_DUMP', ENV_VAL, STATUS=STAT)
    ENABLED = (STAT == 0 .AND. TRIM(ENV_VAL) == '1')
    IF (.NOT. ENABLED) RETURN

    ! Dump only for ray tracing path (nstat==1). Beam path (nstat==2) is
    ! intentionally out of scope for L-0; will be re-evaluated in L-6.
    IF (nstat /= 1) RETURN

    OPEN(UNIT=UNIT_DUMP, FILE='wr_regress.dat', &
         STATUS='REPLACE', ACTION='WRITE', IOSTAT=IOERR)
    IF (IOERR /= 0) THEN
       WRITE(6,*) 'XX wrregress: cannot open wr_regress.dat, IOSTAT=', IOERR
       RETURN
    END IF

    WRITE(UNIT_DUMP, '(A)')          '# TASK/WR regression dump (format v1)'
    WRITE(UNIT_DUMP, '(A,I0)')       'NRAYMAX=', NRAYMAX
    WRITE(UNIT_DUMP, '(A,I0)')       'NSTPMAX=', NSTPMAX
    WRITE(UNIT_DUMP, '(A,I0)')       'NRSMAX=',  NRSMAX
    WRITE(UNIT_DUMP, '(A,I0)')       'NRLMAX=',  NRLMAX
    WRITE(UNIT_DUMP, '(A,I0)')       'MODELG=',  MODELG
    WRITE(UNIT_DUMP, '(A,I0)')       'MDLWRI=',  MDLWRI
    WRITE(UNIT_DUMP, '(A,I0)')       'MDLWRQ=',  MDLWRQ
    WRITE(UNIT_DUMP, '(A,I0)')       'mode_beam=', mode_beam
    WRITE(UNIT_DUMP, '(A,1PE24.16)') 'RF=',     RF
    WRITE(UNIT_DUMP, '(A,1PE24.16)') 'RPI=',    RPI
    WRITE(UNIT_DUMP, '(A,1PE24.16)') 'ZPI=',    ZPI
    WRITE(UNIT_DUMP, '(A,1PE24.16)') 'PHII=',   PHII
    WRITE(UNIT_DUMP, '(A,1PE24.16)') 'RNZI=',   RNZI
    WRITE(UNIT_DUMP, '(A,1PE24.16)') 'RNPHII=', RNPHII
    WRITE(UNIT_DUMP, '(A,1PE24.16)') 'RKR0=',   RKR0
    WRITE(UNIT_DUMP, '(A,1PE24.16)') 'UUI=',    UUI
    WRITE(UNIT_DUMP, '(A,1PE24.16)') 'pos_pwrmax_rs=', pos_pwrmax_rs
    WRITE(UNIT_DUMP, '(A,1PE24.16)') 'pwrmax_rs=',     pwrmax_rs
    WRITE(UNIT_DUMP, '(A,1PE24.16)') 'pos_pwrmax_rl=', pos_pwrmax_rl
    WRITE(UNIT_DUMP, '(A,1PE24.16)') 'pwrmax_rl=',     pwrmax_rl

    WRITE(UNIT_DUMP, '(A)') &
         '# rays: NRAY NSTP_END pos_pwrmax_rs_nray RAYS(0:8,end)'
    DO NRAY = 1, NRAYMAX
       NSTP_END = NSTPMAX_NRAY(NRAY)
       ! Defensive clamp: RAYS is allocated 0:NSTPMAX in second dim.
       ! Some integrator paths can leave NSTPMAX_NRAY out of range; treat
       ! that as "no terminal sample" rather than going OOB.
       IF (NSTP_END < 0 .OR. NSTP_END > NSTPMAX) THEN
          WRITE(UNIT_DUMP, '(I5,1X,I7,A)') NRAY, NSTP_END, &
               '   ! NSTP_END out of range; ray-end values omitted'
          CYCLE
       END IF
       WRITE(UNIT_DUMP, '(I5,1X,I7)', ADVANCE='NO') NRAY, NSTP_END
       WRITE(UNIT_DUMP, '(1X,1PE24.16)', ADVANCE='NO') pos_pwrmax_rs_nray(NRAY)
       DO I = 0, NEQ   ! NEQ=8 (wrcomm.f90) => 9 elements (RAYS first dim is 0:NEQ)
          WRITE(UNIT_DUMP, '(1X,1PE24.16)', ADVANCE='NO') RAYS(I, NSTP_END, NRAY)
       END DO
       WRITE(UNIT_DUMP, '(A)') ''
    END DO

    WRITE(UNIT_DUMP, '(A)') '# minor radius profile: NRS pos_nrs pwr_nrs'
    DO NRS = 1, NRSMAX
       WRITE(UNIT_DUMP, '(I5,1X,1PE24.16,1X,1PE24.16)') NRS, pos_nrs(NRS), pwr_nrs(NRS)
    END DO

    WRITE(UNIT_DUMP, '(A)') '# major radius profile: NRL pos_nrl pwr_nrl'
    DO NRL = 1, NRLMAX
       WRITE(UNIT_DUMP, '(I5,1X,1PE24.16,1X,1PE24.16)') NRL, pos_nrl(NRL), pwr_nrl(NRL)
    END DO

    CLOSE(UNIT_DUMP)
  END SUBROUTINE wr_regress_dump_if_enabled

END MODULE wrregress
