! libnf.f90

MODULE libnf_local
  USE bpsd_kinds
  INTEGER:: id_nf_local
  REAL(rkind):: temperature_local
END MODULE libnf_local

MODULE libnf
  USE bpsd_kinds
  USE bpsd_constants

  ! model_pnf=0:     no fusion reaction

  ! model_pnf=1,2:   DT -> He4, n
  !                       D bulk, T bulk
  ! model_pnf=3,4:   DT -> He4, n
  !                       D beam: D bulk, T bulk
  ! model_pnf=5,6:   DT -> He4, n
  !                       T beam: D bulk, T bulk
  ! model_pnf=7,8:   DT -> He4, n
  !                       D beam , T beam: D bulk, T bulk

  ! model_pnf=11,12: DT,DD: -> T n (He3 -> He4, p -> He4/2)
  !                       D bulk, T bulk
  ! model_pnf=13,14: DT,DD: -> T n (He3 -> He4, p -> He4/2)
  !                       D beam: D bulk, T bulk
  ! model_pnf=15,16: DT,DD: -> T n (He3 -> He4, p -> He4/2)
  !                       T beam: D bulk, T bulk
  ! model_pnf=17,18: DT,DD: -> T n (He3 -> He4, p -> He4/2)
  !                       D beam, T beam: D bulk, T bulk

  ! model_pnf=2X :   DT,DD: D T He4 + He3 H
  ! model_pnf=3X3:   DT,DD,DHe3,TT,He3T: D T He + He3 H

  
  ! Fusion reaction id
  
  INTEGER,PARAMETER,PUBLIC:: id_nf_DD1=1  ! D + D -> T + p
  INTEGER,PARAMETER,PUBLIC:: id_nf_DD2=2  ! D + D -> He3 + n
  INTEGER,PARAMETER,PUBLIC:: id_nf_DT =3  ! D + T -> He4 + n
  INTEGER,PARAMETER,PUBLIC:: id_nf_DHe3=4 ! D + He3 -> He4 + p
  INTEGER,PARAMETER,PUBLIC:: id_nf_TT =5  ! T + T -> He4 + 2n
  INTEGER,PARAMETER,PUBLIC:: id_nf_THe3=6 ! T + He3 ->
                                          !    He4 + p + n; He4 + D; He5 + p

  ! Duane coef (NEL Formulary 2019)

  REAL(rkind),DIMENSION(5,6):: &
       Duane=reshape((/46.097D0, 372.D0, 4.36D-4,  1.220D0, 0.D0, &
                       47.88D0,  482.D0, 3.08D-4,  1.177D0, 0.D0, &
                       45.95D0,  5.02D4, 1.368D-2, 1.076D0, 409.D0, &
                       89.27D0,  2.59D4, 3.98D-3,  1.297D0, 647.D0, &
                       38.39D0,  448.D0, 1.02D-3,  2.09D0,  0.D0, &
                       123.1D0, 1.125D4, 0.D0,     0.D0,    0.D0/), &
                       (/5,6/))

  ! temperature range for reaction rate sigmav
    
  REAL(rkind),DIMENSION(10):: &
       tempa=(/ 1.D0, 2.D0, 5.D0, 10.D0, 20.D0, &
       50.D0, 100.D0, 200.D0, 500.D0, 1000.D0 /)
  
  ! reaction rate sigmav for DD
  REAL(rkind),DIMENSION(10):: &
       svnf_dd=(/ 1.5D-21, 5.4D-21, 1.8D-19, 1.2D-18, 5.2D-18, &
                  2.1D-17, 4.5D-17, 8.8D-17, 1.8D-16, 2.2D-16 /)
  ! reaction rate sigmav for DT
  REAL(rkind),DIMENSION(10):: &
       svnf_dt=(/ 5.5D-21, 2.6D-19, 1.3D-17, 1.1D-16, 4.2D-16, &
                  8.7D-16, 8.5D-16, 6.3D-16, 3.7D-16, 2.7D-16 /)
  ! reaction rate sigmav for DHe3
  REAL(rkind),DIMENSION(10):: &
       svnf_dhe3=(/ 1.0D-26, 1.4D-23, 6.7D-21, 2.3D-19, 3.8D-18, &
                    5.4D-17, 1.6D-16, 2.4D-16, 2.3D-16, 1.8D-16 /)
  ! reaction rate sigmav for TT
  REAL(rkind),DIMENSION(10):: &
       svnf_tt=(/ 3.3D-22, 7.1D-21, 1.4D-19, 7.2D-19, 2.5D-18, &
                  8.7D-18, 1.9D-17, 4.2D-17, 8.4D-17, 8.0D-17 /)
  ! reaction rate sigmav for THe3
  REAL(rkind),DIMENSION(10):: &
       svnf_the3=(/ 1.0D-28, 1.0D-25, 2.1D-22, 1.2D-20, 2.6D-19, &
                    5.3D-18, 2.7D-17, 9.2D-17, 2.9D-16, 5.2D-16 /)

  ! Mass of incident particle

  REAL(rkind),DIMENSION(6):: am_nf
  
  REAL(rkind),DIMENSION(4,10):: &
       usvnf_dd,usvnf_dt,usvnf_dhe3,usvnf_tt,usvnf_the3
  REAL(rkind),DIMENSION(10):: &
       dsvnf,tempa_log

  ! *** library subroutines ***

  PUBLIC sigma_nf          ! sigma_nf(id_nf,energy)
  PUBLIC set_usigmav_nf    ! set_usigmav_nf
  PUBLIC sigmav_nf         ! sigmav_nf(id_nf,temperature)

CONTAINS
  
  ! --- cross section of nuclear fusion reaction ---
  ! ---     in barn (10^{-28}m^{-2})
  ! ---     as a function of energy in keV

  FUNCTION sigma_nf(id_nf,energy)

    IMPLICIT NONE
    INTEGER,INTENT(IN):: id_nf
    REAL(rkind),INTENT(IN):: energy
    REAL(rkind):: sigma_nf
    
    IF(id_nf.LT.1.OR.id_nf.GT.6) THEN
       WRITE(6,'(A,I4)') &
            'XX sigma_nf: input error: undefined id_nf: ',id_nf
       STOP
    ENDIF
    
    IF(energy.LE.0.D0) THEN
       WRITE(6,*) 'XX sigma_duane: input error: non-positive energy: ',energy
       STOP
    ENDIF
    
    sigma_nf=(Duane(5,id_nf) &
         +Duane(2,id_nf) &
         /((Duane(4,id_nf)-Duane(3,id_nf)*energy)**2+1.D0)) &
         /(energy*(EXP(Duane(1,id_nf)/SQRT(energy))-1.D0))
    RETURN
  END FUNCTION sigma_nf
  
  ! --- set spline coefficients for reaction rate sigmav

  SUBROUTINE set_usigmav_nf
    USE libspl1d
    IMPLICIT NONE
    REAL(rkind),DIMENSION(10):: dsvnf
    INTEGER:: id_nf,ntemp,ierr

    am_nf(id_nf_dd1 )=AMD
    am_nf(id_nf_dd2 )=AMD
    am_nf(id_nf_dt  )=AMD
    am_nf(id_nf_dhe3)=AMD
    am_nf(id_nf_tt  )=AMT
    am_nf(id_nf_the3)=AMT
    
    DO ntemp=1,10
       tempa_log(ntemp)=LOG10(tempa(ntemp))
    END DO
    
    DO id_nf=1,6
       SELECT CASE(id_nf)
       CASE(id_nf_dd1,id_nf_dd2)
          CALL SPL1D(tempa_log,svnf_dd,  dsvnf,usvnf_dd,  10,0,ierr)
       CASE(id_nf_dt)
          CALL SPL1D(tempa_log,svnf_dt,  dsvnf,usvnf_dt,  10,0,ierr)
       CASE(id_nf_dhe3)
          CALL SPL1D(tempa_log,svnf_dhe3,dsvnf,usvnf_dhe3,10,0,ierr)
       CASE(id_nf_tt)
          CALL SPL1D(tempa_log,svnf_tt,  dsvnf,usvnf_tt,  10,0,ierr)
       CASE(id_nf_the3)
          CALL SPL1D(tempa_log,svnf_the3,dsvnf,usvnf_the3,10,0,ierr)
       END SELECT
       IF(ierr.NE.0) THEN
          WRITE(6,'(A,I4)') 'XX SPL1D error in set_usvnf: id_nf=',id_nf
          STOP
       END IF
    END DO
    RETURN
  END SUBROUTINE set_usigmav_nf

  ! --- reaction rate of nuclear fusion: sigmav  ---
  ! ---     as a function of temperature in keV

  FUNCTION sigmav_nf(id_nf,temperature)

    USE libspl1d
    IMPLICIT NONE
    INTEGER,INTENT(IN):: id_nf
    REAL(rkind),INTENT(IN):: temperature
    REAL(rkind):: sigmav_nf,temperature_log
    INTEGER:: ierr
    
    IF(id_nf.LT.1.OR.id_nf.GT.6) THEN
       WRITE(6,'(A,I4)') 'XX sigmav_nf: input error: undefined id_nf: ',id_nf
       STOP
    END IF

    IF(temperature.LT.1.D0) THEN
       sigmav_nf=0.D0
       RETURN
    END IF

    IF(temperature.GT.1000.D0) THEN
       WRITE(6,'(A,ES12.4)') &
            'XX sigmav_nf: input error: Too high temperature: temperature=', &
            temperature
       STOP
    END IF

    temperature_log=LOG10(temperature)
    SELECT CASE(id_nf)
    CASE(id_nf_dd1,id_nf_dd2)
       CALL SPL1DF(temperature_log,sigmav_nf,tempa_log,usvnf_dd,10,ierr)
    CASE(id_nf_dt)
       CALL SPL1DF(temperature_log,sigmav_nf,tempa_log,usvnf_dt,10,ierr)
    CASE(id_nf_dhe3)
       CALL SPL1DF(temperature_log,sigmav_nf,tempa_log,usvnf_dhe3,10,ierr)
    CASE(id_nf_tt)
       CALL SPL1DF(temperature_log,sigmav_nf,tempa_log,usvnf_tt,10,ierr)
    CASE(id_nf_the3)
       CALL SPL1DF(temperature_log,sigmav_nf,tempa_log,usvnf_the3,10,ierr)
    END SELECT
    IF(ierr.NE.0) THEN
       WRITE(6,'(A,I4)')     'XX SPL1DF error in sigmav_nf: id_nf=',id_nf
       WRITE(6,'(A,ES12.4)') '       temperature=',temperature
       STOP
    END IF
  END FUNCTION sigmav_nf

  ! --- sigmav_nf by integeral over energy ---
  !         <sigmav>=\int_0^\infty 4\pi v^2 dv sigma v f(v)
  !                  f(v)=(m/2\pi T)^{3/2} exp(-mv^2/2T)   normalized to 1
  !                  E=mv^2/2
  !                  v=SQRT{2E/m}
  !                  dv=(1/2) SQRT{2/mE} dE
  !                  4\pi v^2 dv=4\pi (2E/m) (1/2) SQRT{2/mE} dE
  !                             =4\pi SQRT{E^2/m^2 2/mE} dE
  !                             =4\pi SQRT{2E/m^3} dE
  !                  f(E)=(m/2\pi T)^{3/2} exp(-E/T)
  !                <f(E)>=\int_0^\infty 4\pi v^2 dv f(v) 
  !                      =\int_0^\infty 4\pi SQRT{2E/m^3} dE
  !                               (m/2\pi T)^{3/2} exp(-E/T)
  !                      =\int_0^\infty SQRT{16 \pi^2 2E/m^3 m^3/8 \pi^3 T^3}
  !                               dE exp(-E/T)
  !                      =\int_0^\infty SQRT{4E/\pi T} exp(-E/T) dE/T
  !                      =\int_0^\infty SQRT{4X/\pi} exp(-X) dX
  !                      = (2/SQRT{\pi}) \int_0^\infty SQRT{X} exp(-X) dX
  !                      = 1
  !          <sigmav>=\int_0^\infty 4\pi SQRT{2E/m^3} dE sigma SQRT{2E/m} f(E)
  !                  =\int_0^\infty 4\pi 2E/m^2 dE sigma
  !                                   (m/2\pi T)^{3/2} exp(-E/T)
  !                  =\int_0^\infty SQRT{8 E^2/m\pi T} sigma exp(-E/T) dE/T
  !                  =\int_0^\infty SQRT{8T/m\pi} (E/T) sigma exp(-E/T) dE/T
  !                  =\int_0^\infty SQRT{8T/m\pi} X sigma exp(-X) dX

  ! --- sigmav for energy --- X=energy/temperature

  FUNCTION sigmav_nf_local(X)
    USE libnf_local
    IMPLICIT NONE
    REAL(rkind),INTENT(IN):: X
    REAL(rkind):: sigmav_nf_local
    REAL(rkind):: energy,velocity

    energy=temperature_local*X
    velocity=SQRT(2.D0*energy/am_nf(id_nf_local))
    sigmav_nf_local=sigma_nf(id_nf_local,energy)*velocity
    RETURN
  END FUNCTION sigmav_nf_local


  FUNCTION sigmav_nf_int(id_nf,temperature)

    USE libnf_local
    USE libde
    IMPLICIT NONE
    INTEGER,INTENT(IN):: id_nf
    REAL(rkind),INTENT(IN):: temperature
    REAL(rkind):: sigmav_nf_int
    REAL(rkind):: error_int,H0,EPS
    INTEGER:: ILST

    IF(id_nf.LT.1.OR.id_nf.GT.6) THEN
       WRITE(6,'(A,I4)') 'XX sigmav_nf: input error: undefined id_nf: ',id_nf
       STOP
    END IF

    IF(temperature.LT.1.D0) THEN
       sigmav_nf_int=0.D0
       RETURN
    END IF

    IF(temperature.GT.1000.D0) THEN
       WRITE(6,'(A,ES12.4)') &
            'XX sigmav_nf: input error: Too high temperature: temperature=', &
            temperature
       STOP
    END IF

    id_nf_local=id_nf
    temperature_local=temperature

    H0=1.D-4
    EPS=1.D-6
    
    CALL DEHIFE(sigmav_nf_int,error_int,H0,eps,ilst,sigmav_nf_local, &
         'sigmav_nf_int')

    RETURN
  END FUNCTION sigmav_nf_int
  
END MODULE libnf
      
