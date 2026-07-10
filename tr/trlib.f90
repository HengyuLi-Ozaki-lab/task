! trlib.f90 --- shared scalar helper functions for the TR transport module.
!
! COULOG (Coulomb logarithm) and HY (fast-ion slowing-down integral) used to
! be bare external functions in trcalc.f90 and trpnb.f90.  They are collected
! here as module procedures so that every consumer binds a single definition
! (P1 Task 3, mirroring bpsi's trx/trlib.f90 layout).
!
! The bodies are moved verbatim: no numerical change.

MODULE trlib

  IMPLICIT NONE
  PRIVATE
  PUBLIC :: COULOG, HY

CONTAINS

!     ***********************************************************

!           COULOMB LOGARITHM

!     ***********************************************************

      FUNCTION COULOG(NS1,NS2,ANEL,TL)

!     ANEL : electron density [10^20 /m^3]
!     TL   : electron or ion temperature [keV]
!            in case of ion-ion collision, TL becomes ion temp.

      USE TRCOMM,ONLY: rkind
      IMPLICIT NONE
      INTEGER:: NS1,NS2
      REAL(rkind)   :: ANEL,TL,COULOG

      IF(NS1.EQ.1.AND.NS2.EQ.1) THEN
         COULOG=14.9D0-0.5D0*LOG(ANEL)+LOG(TL)
      ELSE
         IF(NS1.EQ.1.OR.NS2.EQ.1) THEN
            COULOG=15.2D0-0.5D0*LOG(ANEL)+LOG(TL)
         ELSE
            COULOG=17.3D0-0.5D0*LOG(ANEL)+1.5D0*LOG(TL)
         ENDIF
      ENDIF

      RETURN
      END FUNCTION COULOG

!     ***********************************************************

!           FAST ION SLOWING-DOWN INTEGRAL

!     ***********************************************************

      FUNCTION HY(V)

      USE TRCOMM, ONLY : PI,rkind
      IMPLICIT NONE
      REAL(rkind), INTENT(IN) :: V
      REAL(rkind) :: HY

      HY = 2.D0*(LOG((V**3+1.D0)/(V+1.D0)**3)/6.D0 &
     &      +(ATAN((2.D0*V-1.D0)/SQRT(3.D0))+PI/6.D0)/SQRT(3.D0))/V**2
      RETURN
      END FUNCTION HY

END MODULE trlib
