! tiregress.f90
!
! High-precision regression dump for TI Phase L-0 regression tests.
! Emits ti_regress.dat (1PE24.16 format) when TI_REGRESS_DUMP=1.
! Otherwise does nothing; normal runs are unaffected.

MODULE tiregress

  PRIVATE
  PUBLIC :: ti_regress_dump_if_enabled

CONTAINS

  SUBROUTINE ti_regress_dump_if_enabled
    USE ticomm, ONLY: &
         NRMAX, NSMAX, nsa_max, NT, T, rkind, &
         residual_loop_max, icount_loop_max, icount_mat_max, &
         RNA, RTA, RUA, RBP, RQP, RJP, ZEFF, BETA, BETAP
    IMPLICIT NONE
    INTEGER, PARAMETER :: UNIT_DUMP = 78
    CHARACTER(LEN=16) :: ENV_VAL
    INTEGER :: STAT, NR, NSA, IOERR
    LOGICAL :: ENABLED

    CALL GET_ENVIRONMENT_VARIABLE('TI_REGRESS_DUMP', ENV_VAL, STATUS=STAT)
    ENABLED = (STAT == 0 .AND. TRIM(ENV_VAL) == '1')
    IF (.NOT. ENABLED) RETURN

    OPEN(UNIT=UNIT_DUMP, FILE='ti_regress.dat', &
         STATUS='REPLACE', ACTION='WRITE', IOSTAT=IOERR)
    IF (IOERR /= 0) THEN
       WRITE(6,*) 'XX tiregress: cannot open ti_regress.dat, IOSTAT=', IOERR
       RETURN
    END IF

    WRITE(UNIT_DUMP, '(A)')          '# TASK/TI regression dump (format v1)'
    WRITE(UNIT_DUMP, '(A,I0)')       'NT=',                NT
    WRITE(UNIT_DUMP, '(A,I0)')       'NRMAX=',             NRMAX
    WRITE(UNIT_DUMP, '(A,I0)')       'NSMAX=',             NSMAX
    WRITE(UNIT_DUMP, '(A,I0)')       'nsa_max=',           nsa_max
    WRITE(UNIT_DUMP, '(A,1PE24.16)') 'T=',                 T
    WRITE(UNIT_DUMP, '(A,1PE24.16)') 'residual_loop_max=', residual_loop_max
    WRITE(UNIT_DUMP, '(A,I0)')       'icount_loop_max=',   icount_loop_max
    WRITE(UNIT_DUMP, '(A,I0)')       'icount_mat_max=',    icount_mat_max

    WRITE(UNIT_DUMP, '(A)') &
         '# profile columns: NR RNA(1:nsa_max,NR) RTA(1:nsa_max,NR) RUA(1:nsa_max,NR) RBP RQP RJP ZEFF BETA BETAP'
    DO NR = 1, NRMAX
       WRITE(UNIT_DUMP, '(I5)', ADVANCE='NO') NR
       DO NSA = 1, nsa_max
          WRITE(UNIT_DUMP, '(1X,1PE24.16)', ADVANCE='NO') RNA(NSA,NR)
       END DO
       DO NSA = 1, nsa_max
          WRITE(UNIT_DUMP, '(1X,1PE24.16)', ADVANCE='NO') RTA(NSA,NR)
       END DO
       DO NSA = 1, nsa_max
          WRITE(UNIT_DUMP, '(1X,1PE24.16)', ADVANCE='NO') RUA(NSA,NR)
       END DO
       WRITE(UNIT_DUMP, '(6(1X,1PE24.16))') &
            RBP(NR), RQP(NR), RJP(NR), ZEFF(NR), BETA(NR), BETAP(NR)
    END DO

    CLOSE(UNIT_DUMP)
  END SUBROUTINE ti_regress_dump_if_enabled

END MODULE tiregress
