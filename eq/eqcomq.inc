!   eqcomq (shim): transitional bundle header.
!   Kept for backwards-compatibility of cross-module
!   INCLUDE '../eq/eqcomq.inc' sites (wmf/wmfn/wmx/fp/eq).
!   New code should USE eqcom0_mod/eqcom1_mod/eqcom3_mod directly.
!   Phase F-5 will remove this shim along with eqcom{0..5}.inc.
      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom3_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
