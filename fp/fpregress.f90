! fpregress.f90
!
! High-precision regression dump for Phase L-0 regression tests.
! Emits fp_regress.dat (1PE24.16 format) when FP_REGRESS_DUMP=1.
! Otherwise does nothing; normal runs are unaffected.
!
! Only nrank == 0 writes the dump (MPI-safe).

MODULE fpregress

  PRIVATE
  PUBLIC :: fp_regress_dump_if_enabled

CONTAINS

  SUBROUTINE fp_regress_dump_if_enabled
    USE fpcomm, ONLY: &
         NRMAX, NSAMAX, NPMAX, NTHMAX, NTG2, TIMEFP, &
         RNT, RWT, RTT, RJT, RPCT, RPWT, &
         nrank
    IMPLICIT NONE
    INTEGER, PARAMETER :: UNIT_DUMP = 87
    CHARACTER(LEN=16) :: ENV_VAL
    INTEGER :: STAT, NR, NSA, IOERR, NTG_LAST
    LOGICAL :: ENABLED

    IF (nrank /= 0) RETURN

    CALL GET_ENVIRONMENT_VARIABLE('FP_REGRESS_DUMP', ENV_VAL, STATUS=STAT)
    ENABLED = (STAT == 0 .AND. TRIM(ENV_VAL) == '1')
    IF (.NOT. ENABLED) RETURN

    NTG_LAST = MAX(NTG2, 1)   ! defensive: in case loop did not advance NTG2

    OPEN(UNIT=UNIT_DUMP, FILE='fp_regress.dat', &
         STATUS='REPLACE', ACTION='WRITE', IOSTAT=IOERR)
    IF (IOERR /= 0) THEN
       WRITE(6,*) 'XX fpregress: cannot open fp_regress.dat, IOSTAT=', IOERR
       RETURN
    END IF

    WRITE(UNIT_DUMP, '(A)')         '# TASK/FP regression dump (format v1)'
    WRITE(UNIT_DUMP, '(A,I0)')      'NRMAX=',  NRMAX
    WRITE(UNIT_DUMP, '(A,I0)')      'NSAMAX=', NSAMAX
    WRITE(UNIT_DUMP, '(A,I0)')      'NPMAX=',  NPMAX
    WRITE(UNIT_DUMP, '(A,I0)')      'NTHMAX=', NTHMAX
    WRITE(UNIT_DUMP, '(A,I0)')      'NTG2=',   NTG2
    WRITE(UNIT_DUMP, '(A,1PE24.16)') 'TIMEFP=', TIMEFP

    WRITE(UNIT_DUMP, '(A)') &
         '# profile columns: NR NSA RNT RWT RTT RJT RPCT RPWT (at NTG=NTG2)'
    DO NSA = 1, NSAMAX
       DO NR = 1, NRMAX
          WRITE(UNIT_DUMP, '(I5,1X,I3,6(1X,1PE24.16))') &
               NR, NSA, &
               RNT (NR, NSA, NTG_LAST), &
               RWT (NR, NSA, NTG_LAST), &
               RTT (NR, NSA, NTG_LAST), &
               RJT (NR, NSA, NTG_LAST), &
               RPCT(NR, NSA, NTG_LAST), &
               RPWT(NR, NSA, NTG_LAST)
       END DO
    END DO

    CLOSE(UNIT_DUMP)
  END SUBROUTINE fp_regress_dump_if_enabled

END MODULE fpregress
