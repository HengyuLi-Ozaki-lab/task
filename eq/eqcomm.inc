C     eqcomm (shim): transitional bundle header.
C     Kept for backwards-compatibility of INCLUDE '../eq/eqcomm.inc'.
C     Original composition: eqcom0 + eqcom1.
C     New code should USE eqcom0_mod/eqcom1_mod directly.
C     Phase F-5 will remove this shim.
      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
