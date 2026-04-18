!     ***********************************************************

!           CALCULATE TRANSPORT COEFFICIENTS
!
!     ***********************************************************

      SUBROUTINE TRCOEF

      USE trcoef_turbulence, ONLY: TRCFDW
      USE trcoef_neoclassical, ONLY: TRCFNC
      USE trcoef_resistivity,  ONLY: TRCFET
      USE trcoef_adhoc,        ONLY: TRCFAD
      IMPLICIT NONE

      CALL TRCFDW
      CALL TRCFNC
      CALL TRCFET
      CALL TRCFAD

      RETURN
      END SUBROUTINE TRCOEF

      FUNCTION TRCOFS(S,ALPHA,RKCV)

      USE TRCOMM,ONLY: rkind
      IMPLICIT NONE
      REAL(rkind):: S, ALPHA, RKCV, TRCOFS
      REAL(rkind):: FS1,FS2, SA

      IF(ALPHA.GE.0.D0) THEN
         SA=S-ALPHA
         IF(SA.GE.0.D0) THEN
            FS1=(1.D0+9.0D0*SQRT(2.D0)*SA**2.5D0) &
                 & /(SQRT(2.D0)*(1.D0-2.D0*SA+3.D0*SA*SA+2.0D0*SA*SA*SA))
         ELSE
            FS1=1.D0/SQRT(2.D0*(1.D0-2.D0*SA)*(1.D0-2.D0*SA+3.D0*SA*SA))
         ENDIF
         IF(RKCV.GT.0.D0) THEN
            FS2=SQRT(RKCV)**3/(S*S)
         ELSE
            FS2=0.D0
         ENDIF
      ELSE
         SA=ALPHA-S
         IF(SA.GE.0.D0) THEN
            FS1=(1.D0+9.0D0*SQRT(2.D0)*SA**2.5D0) &
                 & /(SQRT(2.D0)*(1.D0-2.D0*SA+3.D0*SA*SA+2.0D0*SA*SA*SA))
         ELSE
            FS1=1.D0/SQRT(2.D0*(1.D0-2.D0*SA)*(1.D0-2.D0*SA+3.D0*SA*SA))
         ENDIF
         IF(RKCV.LT.0.D0) THEN
            FS2=SQRT(-RKCV)**3/(S*S)
         ELSE
            FS2=0.D0
         ENDIF
      ENDIF
      TRCOFS=MAX(FS1,FS2)
      RETURN
      END FUNCTION TRCOFS

      FUNCTION TRCOFSX(S,ALPHA,RKCV,EPSA)

      USE TRCOMM,ONLY: rkind
      IMPLICIT NONE
      REAL(rkind):: S, ALPHA, RKCV, EPSA, TRCOFSX
      REAL(rkind):: FS1, FS2, SA

      IF(ALPHA.GE.0.D0) THEN
!        SA=S-ALPHA
!        SA=S-(1.D0-(2.D0*ALPHA)/(1+3.D0*(ALPHA)**2))*ALPHA
         SA=S-(1.D0-(2.D0*ALPHA)/(1+6.D0*ALPHA))*ALPHA
         IF(SA.GE.0.D0) THEN
           FS1=((1.D0+RKCV)**2.5D0)*(1.D0+9.0D0*SQRT(2.D0)*SA**2.5D0) &
     &         /(SQRT(2.D0)*(1.D0-2.D0*SA+3.D0*SA*SA*(1.D0+RKCV) &
     &                       +2.0D0*SA*SA*SA*(1.D0+RKCV)**2.5D0))
         ELSE
            FS1=((1.D0+RKCV)**2.5D0)/SQRT(2.D0*(1.D0-2.D0*SA) &
     &          *(1.D0-2.D0*SA+3.D0*SA*SA*(1.D0+RKCV)))
         ENDIF
         IF(RKCV.GT.0.D0) THEN
            FS2=SQRT(RKCV/EPSA)**3/(S*S)
         ELSE
            FS2=0.D0
         ENDIF
      ELSE
!        SA=ALPHA-S
!        SA=(1.D0-(2.D0*ALPHA)/(1+3.D0*(ALPHA)**2))*ALPHA-S
         SA=(1.D0-(2.D0*ALPHA)/(1.D0+6.D0*ALPHA))*ALPHA-S
         IF(SA.GE.0.D0) THEN
            FS1=((1.D0+RKCV)**2.5D0)*(1.D0+9.0D0*SQRT(2.D0)*SA**2.5D0) &
     &         /(SQRT(2.D0)*(1.D0-2.D0*SA+3.D0*SA*SA*(1.D0+RKCV) &
     &                       +2.0D0*SA*SA*SA*(1.D0+RKCV)**2.5D0))
         ELSE
            FS1=((1.D0+RKCV)**2.5D0) &
            & /SQRT(2.D0*(1.D0-2.D0*SA)*(1.D0-2.D0*SA+3.D0*SA*SA*(1.D0+RKCV)))
         ENDIF
         IF(RKCV.LT.0.D0) THEN
            FS2=SQRT(-RKCV/EPSA)**3/(S*S)
         ELSE
            FS2=0.D0
         ENDIF
      ENDIF
      TRCOFSX=MAX(FS1,FS2)
      RETURN
      END FUNCTION TRCOFSX

      FUNCTION TRCOFSS(S,ALPHA)

      USE TRCOMM,ONLY: rkind
      IMPLICIT NONE
      REAL(rkind):: S,ALPHA,TRCOFSS
      REAL(rkind):: SA,FS1

      SA=S-ALPHA
      FS1=2.D0*SA**2/(1.D0+(2.D0/9.D0)*SQRT(ABS(SA))**5)
      TRCOFSS=FS1
      RETURN
      END FUNCTION TRCOFSS

      FUNCTION TRCOFT(S,ALPHA,RKCV,EPSA)

      USE TRCOMM,ONLY: rkind
      IMPLICIT NONE
      REAL(rkind):: S,ALPHA,RKCV,EPSA,TRCOFT
      REAL(rkind):: FS1,FS2, SA

      IF(ALPHA.GE.0.D0) THEN
         SA=S-ALPHA
         IF(SA.GE.0.D0) THEN
            FS1=(1.D0+9.0D0*SQRT(2.D0)*SA**2.5D0) &
                 & /(SQRT(2.D0)*(1.D0-2.D0*SA+3.D0*SA*SA+2.0D0*SA*SA*SA))
         ELSE
            FS1=1.D0/SQRT(2.D0*(1.D0-2.D0*SA)*(1.D0-2.D0*SA+3.D0*SA*SA))
         ENDIF
         IF(RKCV.GT.0.D0) THEN
            FS2=SQRT(RKCV/EPSA)**3/(S*S)
         ELSE
            FS2=0.D0
         ENDIF
      ELSE
         SA=ALPHA-S
         IF(SA.GE.0.D0) THEN
            FS1=(1.D0+9.0D0*SQRT(2.D0)*SA**2.5D0) &
                 & /(SQRT(2.D0)*(1.D0-2.D0*SA+3.D0*SA*SA+2.0D0*SA*SA*SA))
         ELSE
            FS1=1.D0/SQRT(2.D0*(1.D0-2.D0*SA)*(1.D0-2.D0*SA+3.D0*SA*SA))
         ENDIF
         IF(RKCV.LT.0.D0) THEN
            FS2=SQRT(-RKCV/EPSA)**3/(S*S)
         ELSE
            FS2=0.D0
         ENDIF
      ENDIF
      TRCOFT=MAX(FS1,FS2)
      RETURN
      END FUNCTION TRCOFT

      FUNCTION RLAMBDA(X)

      USE TRCOMM,ONLY: rkind
      IMPLICIT NONE
      REAL(rkind):: X,RLAMBDA
      REAL(rkind):: AX, Y
      REAL(rkind),SAVE:: P1=1.0D0, P2=3.5156229D0, P3=3.0899424D0, &
           &         P4=1.2067492D0, P5=0.2659732D0, P6=0.360768D-1, &
           &         P7=0.45813D-2
      REAL(rkind),SAVE:: Q1=0.39894228D0,  Q2=0.1328592D-1, Q3=0.225319D-2, &
           &         Q4=-0.157565D-2, Q5=0.916281D-2, Q6=-0.2057706D-1, &
           &         Q7=0.2635537D-1, Q8=-0.1647633D-1,Q9=0.392377D-2


      AX=ABS(X)
      IF (AX.LT.3.75D0) THEN
        Y=(X/3.75D0)**2
        RLAMBDA=(P1+Y*(P2+Y*(P3+Y*(P4+Y*(P5+Y*(P6+Y*P7)))))) *EXP(-AX)
      ELSE
        Y=3.75D0/AX
        RLAMBDA=(1.D0/SQRT(AX))*(Q1+Y*(Q2+Y*(Q3+Y*(Q4+Y*(Q5 &
        &                          +Y*(Q6+Y*(Q7+Y*(Q8+Y*Q9))))))))
      ENDIF
      RETURN
      END FUNCTION RLAMBDA

!     *** for Mixed Bohm/gyro-Bohm model ***

      FUNCTION FBHM(WEXB,AGITG,S)

      USE TRCOMM,ONLY: rkind
      IMPLICIT NONE
      REAL(rkind):: AGITG,S, WEXB,FBHM

      FBHM=1.D0/(1.D0+EXP(20.D0*(0.05D0+WEXB/AGITG-S)))

      RETURN
      END FUNCTION FBHM

!     *** ExB shearing effect for CDBM model ***

      FUNCTION FEXB(X,S,ALPHA)

      USE TRCOMM,ONLY: rkind
      IMPLICIT NONE
      REAL(rkind):: A, ALPHA, ALPHAL, BETA, GAMMA, S, X,FEXB

      IF(ABS(ALPHA).LT.1.D-3) THEN
         ALPHAL=1.D-3
      ELSE
         ALPHAL=ABS(ALPHA)
      ENDIF
      BETA=0.5D0*ALPHAL**(-0.602D0)*(13.018D0-22.28915D0*S+17.018D0*S**2) &
           & /(1.D0-0.277584D0*S+1.42913D0*S**2)

      A=-10.D0/3.D0*ALPHA+16.D0/3.D0
      IF(S.LT.0.D0) THEN
         GAMMA = 1.D0/(1.1D0*SQRT(1.D0-S-2.D0*S**2-3.D0*S**3))+0.75D0
      ELSE
         GAMMA = (1.D0-0.5D0*S)/(1.1D0-2.D0*S+A*S**2+4.D0*S**3)+0.75D0
      ENDIF
      FEXB=EXP(-BETA*X**GAMMA)

      RETURN
      END FUNCTION FEXB
