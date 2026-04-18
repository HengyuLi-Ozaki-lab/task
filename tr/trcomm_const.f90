MODULE trcomm_const
!     ****** CONSTANTS, based on CODATA 2006 ******
! TRCNS
!        PI    : Pi
!        AEE   : Elementaty charge
!        AME   : Electron mass
!        AMM   : Proton mass
!        VC    : Speed of light in vacuum
!        RMU0  : Permeability of free space
!        EPS0  : Permittivity of free space
!        RKEV  : Factor ([keV] -> [J])
  USE bpsd_kinds, ONLY: rkind
  IMPLICIT NONE
  PUBLIC

  REAL(rkind), PARAMETER :: PI   = 3.14159265358979323846D0
  REAL(rkind), PARAMETER :: AEE  = 1.602176487D-19
  REAL(rkind), PARAMETER :: AME  = 9.10938215D-31
  REAL(rkind), PARAMETER :: AMM  = 1.672621637D-27
  REAL(rkind), PARAMETER :: VC   = 2.99792458D8
  REAL(rkind), PARAMETER :: RMU0 = 4.D0*PI*1.D-7
  REAL(rkind), PARAMETER :: EPS0 = 1.D0/(VC*VC*RMU0)
  REAL(rkind), PARAMETER :: RKEV = AEE*1.D3

  INTEGER, PARAMETER :: NPSCM = 10 ! Maximum number of particle source

! TRADD parameter (logically constant)
  REAL(rkind), PARAMETER :: VOID = 0.D0

END MODULE trcomm_const
