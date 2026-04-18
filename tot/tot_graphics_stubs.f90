! tot_graphics_stubs.f90
!
! Phase L-4: minimal no-op stand-ins for the GSAF / grafix entry points
! that tot's SRCS_CORE references at run-time even though libtotapi.so
! excludes all real graphics output.
!
! Background: libgsp / libg3d (the real GSAF implementations) are
! distributed as non-PIC static archives and cannot be linked into a
! PIC shared object. libtotapi.so therefore provides these symbols as
! no-ops so that dlopen() succeeds and any code path that happens to
! reach a plotting hook returns silently.
!
! Mirrors eq_graphics_stubs.f90 / tr_graphics_stubs.f90. Each of the
! per-module .so's libtotapi.so links also ships its own copy of these
! stubs; ld silently picks the first definition seen, so tot's stub
! file is here mainly to keep totregress / any direct caller from
! pulling the real GSAF symbols when libtotapi.so is loaded standalone
! via dlopen for testing.
!
! GUCLIP is the one exception: it is called from many regression / file
! paths to cast REAL(8) -> REAL(4) for time-series storage, so we
! implement the actual cast, matching tr_graphics_stubs.f90.

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
