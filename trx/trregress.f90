! trregress.f90
!
! High-precision regression dump for Phase 0 regression tests.
! Emits tr_regress.dat (1PE24.16 format) when TR_REGRESS_DUMP=1.
! Otherwise does nothing; normal runs are unaffected.

MODULE trregress

  PRIVATE
  PUBLIC :: tr_regress_dump_if_enabled

CONTAINS

  SUBROUTINE tr_regress_dump_if_enabled
    USE TRCOMM, ONLY: &
         NRMAX, NSMAX, NT, T, &
         WPT, AJT, AJRFT, Q0, BETA0, BETAP0, BETAA, BETAN, &
         TAUE1, TAUE2, ZEFF0, ALI, RQ1, &
         RN, RT, AJ, QP
    IMPLICIT NONE
    INTEGER, PARAMETER :: UNIT_DUMP = 77
    CHARACTER(LEN=16) :: ENV_VAL
    INTEGER :: STAT, NR, NS, IOERR
    LOGICAL :: ENABLED

    CALL GET_ENVIRONMENT_VARIABLE('TR_REGRESS_DUMP', ENV_VAL, STATUS=STAT)
    ENABLED = (STAT == 0 .AND. TRIM(ENV_VAL) == '1')
    IF (.NOT. ENABLED) RETURN

    OPEN(UNIT=UNIT_DUMP, FILE='tr_regress.dat', &
         STATUS='REPLACE', ACTION='WRITE', IOSTAT=IOERR)
    IF (IOERR /= 0) THEN
       WRITE(6,*) 'XX trregress: cannot open tr_regress.dat, IOSTAT=', IOERR
       RETURN
    END IF

    WRITE(UNIT_DUMP, '(A)')         '# TASK/TR regression dump (format v1)'
    WRITE(UNIT_DUMP, '(A,I0)')      'NT=',     NT
    WRITE(UNIT_DUMP, '(A,I0)')      'NRMAX=',  NRMAX
    WRITE(UNIT_DUMP, '(A,I0)')      'NSMAX=',  NSMAX
    WRITE(UNIT_DUMP, '(A,1PE24.16)') 'T=',      T
    WRITE(UNIT_DUMP, '(A,1PE24.16)') 'WPT=',    WPT
    WRITE(UNIT_DUMP, '(A,1PE24.16)') 'AJT=',    AJT
    WRITE(UNIT_DUMP, '(A,1PE24.16)') 'AJRFT=',  AJRFT
    WRITE(UNIT_DUMP, '(A,1PE24.16)') 'Q0=',     Q0
    WRITE(UNIT_DUMP, '(A,1PE24.16)') 'BETA0=',  BETA0
    WRITE(UNIT_DUMP, '(A,1PE24.16)') 'BETAP0=', BETAP0
    WRITE(UNIT_DUMP, '(A,1PE24.16)') 'BETAA=',  BETAA
    WRITE(UNIT_DUMP, '(A,1PE24.16)') 'BETAN=',  BETAN
    WRITE(UNIT_DUMP, '(A,1PE24.16)') 'TAUE1=',  TAUE1
    WRITE(UNIT_DUMP, '(A,1PE24.16)') 'TAUE2=',  TAUE2
    WRITE(UNIT_DUMP, '(A,1PE24.16)') 'ZEFF0=',  ZEFF0
    WRITE(UNIT_DUMP, '(A,1PE24.16)') 'ALI=',    ALI
    WRITE(UNIT_DUMP, '(A,1PE24.16)') 'RQ1=',    RQ1

    WRITE(UNIT_DUMP, '(A)') '# profile columns: NR RN(NR,1:NSMAX) RT(NR,1:NSMAX) AJ(NR) QP(NR)'
    DO NR = 1, NRMAX
       WRITE(UNIT_DUMP, '(I5)', ADVANCE='NO') NR
       DO NS = 1, NSMAX
          WRITE(UNIT_DUMP, '(1X,1PE24.16)', ADVANCE='NO') RN(NR,NS)
       END DO
       DO NS = 1, NSMAX
          WRITE(UNIT_DUMP, '(1X,1PE24.16)', ADVANCE='NO') RT(NR,NS)
       END DO
       WRITE(UNIT_DUMP, '(1X,1PE24.16,1X,1PE24.16)') AJ(NR), QP(NR)
    END DO

    CLOSE(UNIT_DUMP)
  END SUBROUTINE tr_regress_dump_if_enabled

END MODULE trregress
