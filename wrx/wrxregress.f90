! wrxregress.f90
!
! High-precision regression dump for WRX Phase L-0 regression tests.
! Emits wrx_regress.dat (1PE24.16 format) when WRX_REGRESS_DUMP=1.
! Otherwise does nothing; normal runs are unaffected.
!
! Module name is intentionally `wrxregress` (not `wrregress`) to avoid
! a Fortran module-name collision with `wr/wrregress.f90` if any future
! library build links both wr and wrx into the same image.

MODULE wrxregress

  PRIVATE
  PUBLIC :: wrx_regress_dump_if_enabled

CONTAINS

  SUBROUTINE wrx_regress_dump_if_enabled
    USE wrcomm, ONLY: &
         NRAYMAX, NSTPMAX, NRSMAX, NRLMAX, NSAMAX_WR, NSMAX, &
         MODELG, MDLWRQ, &
         pwr_tot, pwr_nray, pwr_nsa, pwr_nsa_nray, &
         pwr_nrs_nsa, pwr_nrl_nsa, &
         pos_nrs, pos_nrl, &
         pos_pwrmax_rs_nsa_nray, pwrmax_rs_nsa_nray, &
         pos_pwrmax_rl_nsa_nray, pwrmax_rl_nsa_nray, &
         NSTPMAX_NRAY, rkind
    IMPLICIT NONE
    INTEGER, PARAMETER :: UNIT_DUMP = 78
    CHARACTER(LEN=16) :: ENV_VAL
    INTEGER :: STAT, NRAY, NSA, NRS, NRL, IOERR
    LOGICAL :: ENABLED

    CALL GET_ENVIRONMENT_VARIABLE('WRX_REGRESS_DUMP', ENV_VAL, STATUS=STAT)
    ENABLED = (STAT == 0 .AND. TRIM(ENV_VAL) == '1')
    IF (.NOT. ENABLED) RETURN

    OPEN(UNIT=UNIT_DUMP, FILE='wrx_regress.dat', &
         STATUS='REPLACE', ACTION='WRITE', IOSTAT=IOERR)
    IF (IOERR /= 0) THEN
       WRITE(6,*) 'XX wrxregress: cannot open wrx_regress.dat, IOSTAT=', IOERR
       RETURN
    END IF

    WRITE(UNIT_DUMP,'(A)')         '# TASK/WRX regression dump (format v1)'
    WRITE(UNIT_DUMP,'(A,I0)')      'NRAYMAX=',  NRAYMAX
    WRITE(UNIT_DUMP,'(A,I0)')      'NSTPMAX=',  NSTPMAX
    WRITE(UNIT_DUMP,'(A,I0)')      'NRSMAX=',   NRSMAX
    WRITE(UNIT_DUMP,'(A,I0)')      'NRLMAX=',   NRLMAX
    WRITE(UNIT_DUMP,'(A,I0)')      'NSAMAX_WR=',NSAMAX_WR
    WRITE(UNIT_DUMP,'(A,I0)')      'NSMAX=',    NSMAX
    WRITE(UNIT_DUMP,'(A,I0)')      'MODELG=',   MODELG
    WRITE(UNIT_DUMP,'(A,I0)')      'MDLWRQ=',   MDLWRQ
    WRITE(UNIT_DUMP,'(A,1PE24.16)') 'pwr_tot=', pwr_tot

    WRITE(UNIT_DUMP,'(A,I0)') '# array NSTPMAX_NRAY n=', NRAYMAX
    DO NRAY = 1, NRAYMAX
       WRITE(UNIT_DUMP,'(I0)') NSTPMAX_NRAY(NRAY)
    END DO

    WRITE(UNIT_DUMP,'(A,I0)') '# array pwr_nray n=', NRAYMAX
    DO NRAY = 1, NRAYMAX
       WRITE(UNIT_DUMP,'(1PE24.16)') pwr_nray(NRAY)
    END DO

    WRITE(UNIT_DUMP,'(A,I0)') '# array pwr_nsa n=', NSAMAX_WR
    DO NSA = 1, NSAMAX_WR
       WRITE(UNIT_DUMP,'(1PE24.16)') pwr_nsa(NSA)
    END DO

    WRITE(UNIT_DUMP,'(A,I0)') '# array pos_nrs n=', NRSMAX
    DO NRS = 1, NRSMAX
       WRITE(UNIT_DUMP,'(1PE24.16)') pos_nrs(NRS)
    END DO

    WRITE(UNIT_DUMP,'(A,I0)') '# array pos_nrl n=', NRLMAX
    DO NRL = 1, NRLMAX
       WRITE(UNIT_DUMP,'(1PE24.16)') pos_nrl(NRL)
    END DO

    WRITE(UNIT_DUMP,'(A,I0,A,I0)') '# array2 pwr_nsa_nray rows=', NSAMAX_WR, ' cols=', NRAYMAX
    DO NSA = 1, NSAMAX_WR
       DO NRAY = 1, NRAYMAX
          WRITE(UNIT_DUMP,'(1PE24.16,1X)',ADVANCE='NO') pwr_nsa_nray(NSA,NRAY)
       END DO
       WRITE(UNIT_DUMP,'(A)') ''
    END DO

    WRITE(UNIT_DUMP,'(A,I0,A,I0)') '# array2 pwr_nrs_nsa rows=', NRSMAX, ' cols=', NSAMAX_WR
    DO NRS = 1, NRSMAX
       DO NSA = 1, NSAMAX_WR
          WRITE(UNIT_DUMP,'(1PE24.16,1X)',ADVANCE='NO') pwr_nrs_nsa(NRS,NSA)
       END DO
       WRITE(UNIT_DUMP,'(A)') ''
    END DO

    WRITE(UNIT_DUMP,'(A,I0,A,I0)') '# array2 pwr_nrl_nsa rows=', NRLMAX, ' cols=', NSAMAX_WR
    DO NRL = 1, NRLMAX
       DO NSA = 1, NSAMAX_WR
          WRITE(UNIT_DUMP,'(1PE24.16,1X)',ADVANCE='NO') pwr_nrl_nsa(NRL,NSA)
       END DO
       WRITE(UNIT_DUMP,'(A)') ''
    END DO

    WRITE(UNIT_DUMP,'(A,I0,A,I0)') '# array2 pos_pwrmax_rs_nsa_nray rows=', NSAMAX_WR, ' cols=', NRAYMAX
    DO NSA = 1, NSAMAX_WR
       DO NRAY = 1, NRAYMAX
          WRITE(UNIT_DUMP,'(1PE24.16,1X)',ADVANCE='NO') pos_pwrmax_rs_nsa_nray(NSA,NRAY)
       END DO
       WRITE(UNIT_DUMP,'(A)') ''
    END DO

    WRITE(UNIT_DUMP,'(A,I0,A,I0)') '# array2 pwrmax_rs_nsa_nray rows=', NSAMAX_WR, ' cols=', NRAYMAX
    DO NSA = 1, NSAMAX_WR
       DO NRAY = 1, NRAYMAX
          WRITE(UNIT_DUMP,'(1PE24.16,1X)',ADVANCE='NO') pwrmax_rs_nsa_nray(NSA,NRAY)
       END DO
       WRITE(UNIT_DUMP,'(A)') ''
    END DO

    WRITE(UNIT_DUMP,'(A,I0,A,I0)') '# array2 pos_pwrmax_rl_nsa_nray rows=', NSAMAX_WR, ' cols=', NRAYMAX
    DO NSA = 1, NSAMAX_WR
       DO NRAY = 1, NRAYMAX
          WRITE(UNIT_DUMP,'(1PE24.16,1X)',ADVANCE='NO') pos_pwrmax_rl_nsa_nray(NSA,NRAY)
       END DO
       WRITE(UNIT_DUMP,'(A)') ''
    END DO

    WRITE(UNIT_DUMP,'(A,I0,A,I0)') '# array2 pwrmax_rl_nsa_nray rows=', NSAMAX_WR, ' cols=', NRAYMAX
    DO NSA = 1, NSAMAX_WR
       DO NRAY = 1, NRAYMAX
          WRITE(UNIT_DUMP,'(1PE24.16,1X)',ADVANCE='NO') pwrmax_rl_nsa_nray(NSA,NRAY)
       END DO
       WRITE(UNIT_DUMP,'(A)') ''
    END DO

    CLOSE(UNIT_DUMP)
  END SUBROUTINE wrx_regress_dump_if_enabled

END MODULE wrxregress
