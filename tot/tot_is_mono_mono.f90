! tot_is_mono_mono.f90 — MONO build variant.
!
! Linked into libtotapi_mono.so (instead of tot_is_mono.f90 which
! returns 0).
!
! Standalone (NOT inside any MODULE) so the per-target swap is
! Makefile-controlled and does NOT force a recompile of tot_api.o.
!
! See L-7b-ii Phase 2b spec §3 + tot_api.h `tot_is_mono` documentation.

FUNCTION tot_api_is_mono() RESULT(is_mono) BIND(C, NAME="tot_is_mono")
  USE, INTRINSIC :: ISO_C_BINDING, ONLY: C_INT
  IMPLICIT NONE
  INTEGER(C_INT) :: is_mono
  is_mono = 1
END FUNCTION tot_api_is_mono
