! equ_status.f90
!
! Failure record of EQU's solver, for the library interface
! (equ_api.f90; design docs/superpowers/specs/2026-11-22-equ-library-design.md,
! section 9.2).
!
! The places where the solver used to STOP call equ_fail instead, after
! printing what they printed before. Outside library mode equ_fail stops,
! so the program equ behaves as it always did. equ_init of the library
! sets library mode: equ_fail then records the failure and returns, the
! routine that called it returns, and each caller returns in turn when
! equ_failed() is true, up to the library, which reports the failure
! with the message instead of ending the process.
MODULE equ_status_mod
  IMPLICIT NONE
  PRIVATE
  PUBLIC :: equ_library_mode, equ_fail, equ_failed, equ_status_clear, &
            equ_status_message
  LOGICAL, SAVE :: equ_library_mode = .FALSE.
  LOGICAL, SAVE :: failed = .FALSE.
  CHARACTER(LEN=256), SAVE :: message = ' '
CONTAINS
  SUBROUTINE equ_fail(msg)
    CHARACTER(LEN=*), INTENT(IN) :: msg
    IF (.NOT. equ_library_mode) STOP
    ! The first failure is the cause; later ones follow from it.
    IF (.NOT. failed) message = msg
    failed = .TRUE.
  END SUBROUTINE equ_fail

  LOGICAL FUNCTION equ_failed()
    equ_failed = failed
  END FUNCTION equ_failed

  SUBROUTINE equ_status_clear
    failed = .FALSE.
    message = ' '
  END SUBROUTINE equ_status_clear

  FUNCTION equ_status_message() RESULT(m)
    CHARACTER(LEN=256) :: m
    m = message
  END FUNCTION equ_status_message
END MODULE equ_status_mod
