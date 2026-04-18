!   eqcomc (shim): transitional bundle header.
!   Kept for backwards-compatibility of INCLUDE '../eq/eqcomc.inc'.
!   Original composition: eqcom0 + eqcom1 + eqcom2.
!   New code should USE eqcom0_mod/eqcom1_mod/eqcom2_mod directly.
!   Phase F-5 will remove this shim.
      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom2_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
