! trfailure.f90 -- library mode and the last failure of a TR run.
!
! tr_library_mode is set by tr_init in tr_api.f90 only; the tr2 program never sets it, so
! every library-only behaviour of tr_loop, tr_set_metric and tr_exec is gated on it.
! The record holds the first failure of a run (a later one is its consequence). tr_api.f90
! clears it at the start of every tr_run and hands it out through tr_last_error.
MODULE trfailure
  USE bpsd_kinds, ONLY: rkind
  IMPLICIT NONE
  PRIVATE
  PUBLIC :: tr_library_mode, tr_failure_clear, tr_failure_record, tr_failure_get
  PUBLIC :: TRF_NONE, TRF_EQ_FAILED, TRF_NONFINITE, TRF_TR_CHECK, TRF_PREP_FAILED, &
            TRF_REFUSED, TRF_OTHER
  INTEGER, PARAMETER :: TRF_NONE = 0, TRF_EQ_FAILED = 1, TRF_NONFINITE = 2, &
                        TRF_TR_CHECK = 3, TRF_PREP_FAILED = 4, TRF_REFUSED = 5, &
                        TRF_OTHER = 6
  LOGICAL, SAVE :: tr_library_mode = .FALSE.
  INTEGER, SAVE :: g_kind = TRF_NONE, g_code = 0, g_nt = 0
  REAL(rkind), SAVE :: g_time = 0.0_rkind
  CHARACTER(LEN=96), SAVE :: g_detail = ''
CONTAINS
  SUBROUTINE tr_failure_clear()
    g_kind = TRF_NONE; g_code = 0; g_nt = 0; g_time = 0.0_rkind; g_detail = ''
  END SUBROUTINE tr_failure_clear

  ! The first failure of a run is kept.
  SUBROUTINE tr_failure_record(kind, code, nt, time, detail)
    INTEGER, INTENT(IN) :: kind, code, nt
    REAL(rkind), INTENT(IN) :: time
    CHARACTER(LEN=*), INTENT(IN) :: detail
    IF (g_kind /= TRF_NONE) RETURN
    g_kind = kind; g_code = code; g_nt = nt; g_time = time; g_detail = detail
  END SUBROUTINE tr_failure_record

  SUBROUTINE tr_failure_get(kind, code, nt, time, detail)
    INTEGER, INTENT(OUT) :: kind, code, nt
    REAL(rkind), INTENT(OUT) :: time
    CHARACTER(LEN=*), INTENT(OUT) :: detail
    kind = g_kind; code = g_code; nt = g_nt; time = g_time; detail = g_detail
  END SUBROUTINE tr_failure_get
END MODULE trfailure
