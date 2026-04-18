! eq_graphics_stubs.f90
!
! Phase L-4: minimal no-op stand-ins for the GSAF / grafix entry points
! that eq's SRCS_CORE references at run-time even though libeqapi.so
! excludes all real graphics output.
!
! Background: libgsp / libg3d (the real GSAF implementations) are
! distributed as non-PIC static archives and cannot be linked into a
! PIC shared object. libeqapi.so therefore provides these symbols as
! no-ops so that dlopen() succeeds and any code path that happens to
! reach a plotting hook returns silently. None of them are exercised
! by eq_init -> eq_run -> eq_get_state -> eq_finalize on the happy
! path, so the no-op behaviour is safe. If a future caller needs real
! plots the right answer is to add a libeqgrf_pic.a (see design doc
! Section A.4) rather than to extend these stubs.
!
! GUCLIP is the one exception: it is called from equread / eqfile to
! cast REAL(8) -> REAL(4) for time-series storage, so we implement the
! actual cast, matching tr_graphics_stubs.f90.
!
! grd2d / grd1d are libgrf module procedures rather than plain GSAF
! symbols; they are satisfied at link time by libgrf_pic.a and do NOT
! need a stub here.

REAL FUNCTION GUCLIP(X)
  IMPLICIT NONE
  DOUBLE PRECISION, INTENT(IN) :: X
  GUCLIP = REAL(X)
END FUNCTION GUCLIP

SUBROUTINE PAGES
  IMPLICIT NONE
END SUBROUTINE PAGES

SUBROUTINE PAGEE
  IMPLICIT NONE
END SUBROUTINE PAGEE

SUBROUTINE GUDATE(KK)
  IMPLICIT NONE
  CHARACTER(LEN=*), INTENT(OUT) :: KK
  KK = ' '
END SUBROUTINE GUDATE

SUBROUTINE GUTIME(KK)
  IMPLICIT NONE
  CHARACTER(LEN=*), INTENT(OUT) :: KK
  KK = ' '
END SUBROUTINE GUTIME

SUBROUTINE GUFLSH
  IMPLICIT NONE
END SUBROUTINE GUFLSH
