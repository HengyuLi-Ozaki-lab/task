!     ***********************************************************
!
!       Phase 3 split of trrslt.f90 --- printed / text output
!
!       Contains:
!         TRPRNT        (print global quantities)
!         tr_setup_kv   (label tables KVT / KVRT)
!
!     ***********************************************************

MODULE trrslt_print
  USE trrslt_files, ONLY: TRMXMN, TRDATA
  IMPLICIT NONE
  PUBLIC

CONTAINS

!     ***********************************************************

!           PRINT GLOBAL QUANTITIES

!     ***********************************************************

      SUBROUTINE TRPRNT(KID)

      USE TRCOMM, ONLY: rkind, &
           NRMAX, NTMAX, NGT, NGR, NSMAX, NSM, NFM, &
           BB, DT, GTCPU1, T, &
           ANC, ANFE, ANFAV, ANSAV, &
           AJ, AJBST, AJNBT, AJOHT, AJRFT, AJT, AJTTOR, ALI, &
           BETA0, BETAA, BETAN, BETAP0, BETAPA, &
           PN, PNB, PNBT, PNF, PNFT, POH, POHT, POUT, &
           PIN, PIE, PIET, PINT, &
           PCX, PCXT, PEX, PFCLT, PFIN, PFINT, &
           PBCLT, PBIN, PBINT, &
           PRBT, PRCT, PRFT, PRL, PRLT, PRSUMT, &
           PLT, PLHNPR, PLHTOT, PICTOT, &
           Q0, QF, QP, RQ1, &
           RIPS, RIPE, &
           S, SIE, SIET, SINT, SLT, SNB, SNBT, SNF, SNFT, SOUT, &
           TAUE1, TAUE2, TAUE89, TAUE98, TF0, TFAV, TS0, TSAV, &
           VLOOP, VSEC, &
           WBULKT, WFT, WPDOT, WPT, WST, WTAILT, &
           ZEFF, ZEFF0, KFNLOG
      USE trparm
      IMPLICIT NONE
      CHARACTER(LEN=1),INTENT(IN):: KID
      INTEGER:: I, IERR, IST, NDD, NDM, NDY, NTH1, NTM1, NTS1
      REAL   :: GTCPU2
      CHARACTER(LEN=3) :: K1, K2, K3, K4, K5, K6
      CHARACTER(LEN=40):: KCOM


      IF(KID.EQ.'N') THEN
         CALL tr_nlin(-29,IST,IERR)
      ELSEIF(KID.EQ.'1') THEN
         WRITE(6,601) T,WPT,WBULKT,WTAILT,WPDOT,TAUE1,TAUE2,TAUE89,TAUE98, &
     &                QF,BETAP0,BETAPA,BETA0,BETAA,Q0,RQ1,ZEFF0,BETAN
  601    FORMAT(' ','# TIME : ',F7.3,' SEC'/ &
     &          ' ',3X,'WPT   =',1PD10.3,'  WBULKT=',1PD10.3, &
     &               '  WTAILT=',1PD10.3,'  WPDOT =',1PD10.3/ &
     &          ' ',3X,'TAUE1 =',1PD10.3,'  TAUE2 =',1PD10.3, &
     &               '  TAUE89=',1PD10.3,'  TAUE98=',1PD10.3/ &
     &          ' ',3X,'QF    =',1PD10.3/ &
     &          ' ',3X,'BETAP0=',1PD10.3,'  BETAPA=',1PD10.3, &
     &               '  BETA0 =',1PD10.3,'  BETAA =',1PD10.3/ &
     &          ' ',3X,'Q0    =',1PD10.3,'  RQ1   =',1PD10.3, &
     &               '  ZEFF0 =',1PD10.3,'  BETAN =',1PD10.3)

         WRITE(6,602) WST(1),TS0(1),TSAV(1),ANSAV(1), &
     &                WST(2),TS0(2),TSAV(2),ANSAV(2), &
     &                WST(3),TS0(3),TSAV(3),ANSAV(3), &
     &                WST(4),TS0(4),TSAV(4),ANSAV(4), &
     &                WFT(1),TF0(1),TFAV(1),ANFAV(1), &
     &                WFT(2),TF0(2),TFAV(2),ANFAV(2)
  602    FORMAT(' ',3X,'WE    =',1PD10.3,'  TE0   =',1PD10.3, &
     &               '  TEAVE =',1PD10.3,'  NEAVE =',1PD10.3/ &
     &          ' ',3X,'WD    =',1PD10.3,'  TD0   =',1PD10.3, &
     &               '  TDAVE =',1PD10.3,'  NDAVE =',1PD10.3/ &
     &          ' ',3X,'WT    =',1PD10.3,'  TT0   =',1PD10.3, &
     &               '  TTAVE =',1PD10.3,'  NTAVE =',1PD10.3/ &
     &          ' ',3X,'WA    =',1PD10.3,'  TA0   =',1PD10.3, &
     &               '  TAAVE =',1PD10.3,'  NAAVE =',1PD10.3/ &
     &          ' ',3X,'WB    =',1PD10.3,'  TB0   =',1PD10.3, &
     &               '  TBAVE =',1PD10.3,'  NBAVE =',1PD10.3/ &
     &          ' ',3X,'WF    =',1PD10.3,'  TF0   =',1PD10.3, &
     &               '  TFAVE =',1PD10.3,'  NFAVE =',1PD10.3)

         WRITE(6,603) AJT,VLOOP,ALI,VSEC, &
     &                AJOHT,AJNBT,AJRFT,AJBST
  603    FORMAT(' ',3X,'AJT   =',1PD10.3,'  VLOOP =',1PD10.3, &
     &               '  ALI   =',1PD10.3,'  VSEC  =',1PD10.3/ &
     &          ' ',3X,'AJOHT =',1PD10.3,'  AJNBT =',1PD10.3, &
     &               '  AJRFT =',1PD10.3,'  AJBST =',1PD10.3)

!         WRITE(16,603) AJTTOR,VLOOP,ALI,VSEC, &
!     &                AJT,AJOHT,AJNBT,AJBST
!  603    FORMAT(' ',3X,'AJTTOR=',1PD10.3,'  VLOOP =',1PD10.3, &
!     &               '  ALI   =',1PD10.3,'  VSEC  =',1PD10.3/ &
!     &          ' ',3X,'AJT   =',1PD10.3,'  AJOHT =',1PD10.3, &
!     &               '  AJNBT =',1PD10.3,'  AJBST =',1PD10.3)

         WRITE(6,604) PINT,POHT,PNBT,PNFT, &
     &                PRFT(1),PRFT(2),PRFT(3),PRFT(4), &
     &                PBINT,PFINT,AJ(1)*1.D-6, &
     &                PBCLT(1),PBCLT(2),PBCLT(3),PBCLT(4), &
     &                PFCLT(1),PFCLT(2),PFCLT(3),PFCLT(4), &
     &                POUT,PRSUMT,PCXT,PIET, &
     &                PLT(1),PLT(2),PLT(3),PLT(4), &
                      PRBT,PRCT,PRLT
  604    FORMAT(' ',3X,'PINT  =',1PD10.3,'  POHT  =',1PD10.3, &
     &               '  PNBT  =',1PD10.3,'  PNFTE =',1PD10.3/ &
     &          ' ',3X,'PRFTE =',1PD10.3,'  PRFTD =',1PD10.3, &
     &               '  PRFTT =',1PD10.3,'  PRFTA =',1PD10.3/ &
     &          ' ',3X,'PBIN  =',1PD10.3,'  PFIN  =',1PD10.3, &
     &               '  AJ0   =',1PD10.3/ &
     &          ' ',3X,'PBCLE =',1PD10.3,'  PBCLD =',1PD10.3, &
     &               '  PBCLT =',1PD10.3,'  PBCLA =',1PD10.3/ &
     &          ' ',3X,'PFCLE =',1PD10.3,'  PFCLD =',1PD10.3, &
     &               '  PFCLT =',1PD10.3,'  PFCLA =',1PD10.3/ &
     &          ' ',3X,'POUT  =',1PD10.3,'  PRSUMT=',1PD10.3, &
     &               '  PCXT  =',1PD10.3,'  PIETE =',1PD10.3/ &
     &          ' ',3X,'PLTE  =',1PD10.3,'  PLTD  =',1PD10.3, &
     &               '  PLTTE =',1PD10.3,'  PLTA  =',1PD10.3/ &
     &          ' ',3X,'PRBT  =',1PD10.3,'  PRCT  =',1PD10.3, &
     &               '  PRLT  =',1PD10.3)

         WRITE(6,605) SINT,SIET,SNBT,SNFT, &
     &                SOUT,ZEFF(1),ANC(1),ANFE(1), &
     &                SLT(1),SLT(2),SLT(3),SLT(4)
  605    FORMAT(' ',3X,'SINT  =',1PD10.3,'  SIET  =',1PD10.3, &
     &               '  SNBT  =',1PD10.3,'  SNFT  =',1PD10.3/ &
     &          ' ',3X,'SOUT  =',1PD10.3,'  ZEFF0 =',1PD10.3, &
     &               '  ANC0  =',1PD10.3,'  ANFE0 =',1PD10.3/ &
     &          ' ',3X,'SLTET =',1PD10.3,'  SLTD  =',1PD10.3, &
     &               '  SLTTT =',1PD10.3,'  SLTA  =',1PD10.3)
      ENDIF

      IF(KID.EQ.'2') THEN
         WRITE(6,611) Q0,(QP(I),I=1,NRMAX)
  611    FORMAT(' ','* Q PROFILE *'/ &
     &         (' ',5F7.3,2X,5F7.3))
      ENDIF

      IF(KID.EQ.'3') THEN
         CALL GUTIME(GTCPU2)
         WRITE(6,621) GTCPU2-GTCPU1
  621    FORMAT(' ','# CPU TIME = ',F8.3,' S')
         RETURN
      ENDIF

      IF(KID.EQ.'4') THEN
         WRITE(6,631)
  631    FORMAT(' ','#',12X,'FIRST',7X,'MAX',9X,'MIN',9X,'LAST')
         CALL TRMXMN( 1,'  NE0  ')
!         CALL TRMXMN( 2,'  ND0  ')
!         CALL TRMXMN( 3,'  NT0  ')
!         CALL TRMXMN( 4,'  NA0  ')
         CALL TRMXMN( 5,'  NEAV ')
!         CALL TRMXMN( 6,'  NDAV ')
!         CALL TRMXMN( 7,'  NTAV ')
!         CALL TRMXMN( 8,'  NAAV ')
         CALL TRMXMN( 9,'  TE0  ')
         CALL TRMXMN(10,'  TD0  ')
         CALL TRMXMN(11,'  TT0  ')
!         CALL TRMXMN(12,'  TA0  ')
         CALL TRMXMN(13,'  TEAV ')
         CALL TRMXMN(14,'  TDAV ')
!         CALL TRMXMN(15,'  TTAV ')
!         CALL TRMXMN(16,'  TAAV ')
!         CALL TRMXMN(17,'  WE   ')
!         CALL TRMXMN(18,'  WD   ')
!         CALL TRMXMN(19,'  WT   ')
!         CALL TRMXMN(20,'  WA   ')

!         CALL TRMXMN(21,'  NB0  ')
!         CALL TRMXMN(22,'  NF0  ')
!         CALL TRMXMN(23,'  NBAV ')
!         CALL TRMXMN(24,'  NFAV ')
!         CALL TRMXMN(25,'  TB0  ')
!         CALL TRMXMN(26,'  TF0  ')
!         CALL TRMXMN(27,'  TBAV ')
!         CALL TRMXMN(28,'  TFAV ')
         CALL TRMXMN(29,'  WB   ')
         CALL TRMXMN(30,'  WF   ')
         CALL TRMXMN(31,' WBULK ')
!         CALL TRMXMN(32,' WTAIL ')
         CALL TRMXMN(33,'  WP   ')

!         CALL TRMXMN(34,'  IP   ')
         CALL TRMXMN(35,'  IOH  ')
         CALL TRMXMN(36,'  INB  ')
!         CALL TRMXMN(37,'  IRF  ')
         CALL TRMXMN(38,'  IBS  ')

!         CALL TRMXMN(39,'  PIN  ')
         CALL TRMXMN(40,'  POH  ')
         CALL TRMXMN(41,'  PNB  ')
!         CALL TRMXMN(42,'  PRFE ')
!         CALL TRMXMN(43,'  PRFD ')
!         CALL TRMXMN(44,'  PRFT ')
!         CALL TRMXMN(45,'  PRFA ')
         CALL TRMXMN(46,'  PNF  ')
!         CALL TRMXMN(47,'  PBINT')
!         CALL TRMXMN(48,'  PBCLE')
!         CALL TRMXMN(49,'  PBCLD')
!         CALL TRMXMN(50,'  PBCLT')
!         CALL TRMXMN(51,'  PBCLA')
!         CALL TRMXMN(52,'  PFINT')
!         CALL TRMXMN(53,'  PFCLE')
!         CALL TRMXMN(54,'  PFCLD')
!         CALL TRMXMN(55,'  PFCLT')
!         CALL TRMXMN(56,'  PFCLA')
!         CALL TRMXMN(57,'  POUT ')
         CALL TRMXMN(58,'  PCX  ')
         CALL TRMXMN(59,'  PIE  ')
         CALL TRMXMN(60,'  PRL  ')
         CALL TRMXMN(61,'  PLE  ')
         CALL TRMXMN(62,'  PLD  ')
         CALL TRMXMN(63,'  PLT  ')
         CALL TRMXMN(64,'  PLA  ')

!         CALL TRMXMN(65,'  SIN  ')
!         CALL TRMXMN(66,'  SIE  ')
!         CALL TRMXMN(67,'  SNB  ')
!         CALL TRMXMN(68,'  SNF  ')
!         CALL TRMXMN(69,'  SOUT ')
!         CALL TRMXMN(70,'  SLE  ')
!         CALL TRMXMN(71,'  SLD  ')
!         CALL TRMXMN(72,'  SLT  ')
!         CALL TRMXMN(73,'  SLA  ')

         CALL TRMXMN(74,' VLOOP ')
         CALL TRMXMN(75,'  LI   ')
!         CALL TRMXMN(76,'  RQ1  ')
!         CALL TRMXMN(77,'   Q0  ')
!         CALL TRMXMN(78,' WPDOT ')
!         CALL TRMXMN(79,' TAUE1 ')
!         CALL TRMXMN(80,' TAUE2 ')
!         CALL TRMXMN(81,' TAUE89')
!         CALL TRMXMN(82,' BETAP0')
         CALL TRMXMN(83,' BETAPA')
!         CALL TRMXMN(84,' BETA0 ')
!         CALL TRMXMN(85,' BETAA ')
!         CALL TRMXMN(86,' ZEFF0 ')
         CALL TRMXMN(87,'   QF  ')
!         CALL TRMXMN(88,'   IP  ')
         CALL TRMXMN(89,'  PEX  ')
      ENDIF

      IF(KID.EQ.'5') THEN
         WRITE(6,641)NGR,NGT,DT,NTMAX
  641    FORMAT(' ','# PARAMETER INFORMATION',/ &
     &          ' ','  NGR   =',I3,'    NGT   =',I3,/ &
     &          ' ','  DT    =',1F5.3,'  NTMAX =',I3)
      ENDIF

      IF(KID.EQ.'6') THEN
         WRITE(6,651)T,TAUE1,TAUE2,TAUE89,PINT
 651     FORMAT(' ','# TIME : ',F7.3,' SEC'/ &
     &          ' ',3X,'TAUE1 =',1PD10.3,'  TAUE2 =',1PD10.3, &
     &               '  TAUE89=',1PD10.3,'  PINT  =',1PD10.3)
      ENDIF

      IF(KID.EQ.'7'.OR.KID.EQ.'8') THEN
         WRITE(6,671) T,WPT,TAUE1,TAUE2,TAUE89,BETAN,BETAPA,BETA0,BETAA
  671    FORMAT(' ','# TIME : ',F7.3,' SEC'/ &
     &          ' ',3X,'WPT   =',1PD10.3,'  TAUE1 =',1PD10.3, &
     &               '  TAUE2 =',1PD10.3,'  TAUE89=',1PD10.3/ &
     &          ' ',3X,'BETAN =',1PD10.3,'  BETAPA=',1PD10.3, &
     &               '  BETA0 =',1PD10.3,'  BETAA =',1PD10.3)

         WRITE(6,672) WST(1),TS0(1),TSAV(1),ANSAV(1), &
     &                WST(2),TS0(2),TSAV(2),ANSAV(2)
  672    FORMAT(' ',3X,'WE    =',1PD10.3,'  TE0   =',1PD10.3, &
     &               '  TEAVE =',1PD10.3,'  NEAVE =',1PD10.3/ &
     &          ' ',3X,'WD    =',1PD10.3,'  TD0   =',1PD10.3, &
     &               '  TDAVE =',1PD10.3,'  NDAVE =',1PD10.3)

         WRITE(6,673) AJTTOR,VLOOP,ALI,Q0,AJOHT,AJNBT,AJRFT,AJBST
  673    FORMAT(' ',3X,'AJTTOR=',1PD10.3,'  VLOOP =',1PD10.3, &
     &               '  ALI   =',1PD10.3,'  Q0    =',1PD10.3/ &
     &          ' ',3X,'AJOHT =',1PD10.3,'  AJNBT =',1PD10.3, &
     &               '  AJRFT =',1PD10.3,'  AJBST =',1PD10.3)

         WRITE(6,674) PINT,POHT,PNBT, &
     &                PRFT(1)+PRFT(2)+PRFT(3)+PRFT(4),POUT,PRLT,PCXT,PIET
  674    FORMAT(' ',3X,'PINT  =',1PD10.3,'  POHT  =',1PD10.3, &
     &               '  PNBT  =',1PD10.3,'  PRFT  =',1PD10.3/ &
     &          ' ',3X,'POUT  =',1PD10.3,'  PRLT  =',1PD10.3, &
     &               '  PCXT  =',1PD10.3,'  PIETE =',1PD10.3)

      IF(KID.EQ.'8') THEN
 1600    WRITE(6,*) '## INPUT COMMENT FOR trn.data (A40)'
         READ(5,'(A40)',END=9000,ERR=1600) KCOM

!         OPEN(16,POSITION='APPEND',FILE=KFNLOG)
!         OPEN(16,ACCESS='APPEND',FILE=KFNLOG)
         OPEN(16,ACCESS='SEQUENTIAL',FILE=KFNLOG)

         CALL GUDATE(NDY,NDM,NDD,NTH1,NTM1,NTS1)
         WRITE(K1,'(I3)') 100+NDY
         WRITE(K2,'(I3)') 100+NDM
         WRITE(K3,'(I3)') 100+NDD
         WRITE(K4,'(I3)') 100+NTH1
         WRITE(K5,'(I3)') 100+NTM1
         WRITE(K6,'(I3)') 100+NTS1
         WRITE(16,1670) K1(2:3),K2(2:3),K3(2:3),K4(2:3),K5(2:3),K6(2:3), &
     &                  KCOM, &
     &                  RIPS,RIPE,PN(1),PN(2),BB,PICTOT,PLHTOT,PLHNPR
 1670    FORMAT(' '/ &
     &          ' ','## DATE : ', &
     &              A2,'-',A2,'-',A2,'  ',A2,':',A2,':',A2,' : ',A40/ &
     &          ' ',3X,'RIPS  =',1PD10.3,'  RIPE  =',1PD10.3, &
     &               '  PNE   =',1PD10.3,'  PNI   =',1PD10.3/ &
     &          ' ',3X,'BB    =',1PD10.3,'  PICTOT=',1PD10.3, &
     &               '  PLHTOT=',1PD10.3,'  PLHNPR=',1PD10.3)
         WRITE(16,1671) T, &
     &                WPT,TAUE1,TAUE2,TAUE89, &
     &                BETAN,BETAPA,BETA0,BETAA
 1671    FORMAT(' ','# TIME : ',F7.3,' SEC'/ &
     &          ' ',3X,'WPT   =',1PD10.3,'  TAUE  =',1PD10.3, &
     &               '  TAUED =',1PD10.3,'  TAUE89=',1PD10.3/ &
     &          ' ',3X,'BETAN =',1PD10.3,'  BETAPA=',1PD10.3, &
     &               '  BETA0 =',1PD10.3,'  BETAA =',1PD10.3)

         WRITE(16,1672) WST(1),TS0(1),TSAV(1),ANSAV(1), &
     &                WST(2),TS0(2),TSAV(2),ANSAV(2)
 1672    FORMAT(' ',3X,'WE    =',1PD10.3,'  TE0   =',1PD10.3, &
     &               '  TEAVE =',1PD10.3,'  NEAVE =',1PD10.3/ &
     &          ' ',3X,'WD    =',1PD10.3,'  TD0   =',1PD10.3, &
     &               '  TDAVE =',1PD10.3,'  NDAVE =',1PD10.3)

         WRITE(16,1673) AJTTOR,VLOOP,ALI,Q0, &
     &                AJOHT,AJNBT,AJRFT,AJBST
 1673    FORMAT(' ',3X,'AJTTOR=',1PD10.3,'  VLOOP =',1PD10.3, &
     &               '  ALI   =',1PD10.3,'  Q0    =',1PD10.3/ &
     &          ' ',3X,'AJOHT =',1PD10.3,'  AJNBT =',1PD10.3, &
     &               '  AJRFT =',1PD10.3,'  AJBST =',1PD10.3)

         WRITE(16,1674) PINT,POHT,PNBT, &
     &                PRFT(1)+PRFT(2)+PRFT(3)+PRFT(4), &
     &                POUT,PRLT,PCXT,PIET
 1674    FORMAT(' ',3X,'PINT  =',1PD10.3,'  POHT  =',1PD10.3, &
     &               '  PNBT  =',1PD10.3,'  PRFT  =',1PD10.3/ &
     &          ' ',3X,'POUT  =',1PD10.3,'  PRLT  =',1PD10.3, &
     &               '  PCXT  =',1PD10.3,'  PIETE =',1PD10.3)
         CLOSE(16)
      ENDIF
      ENDIF

      IF(KID.EQ.'9') THEN
         CALL TRDATA
      ENDIF

 9000 RETURN
      END SUBROUTINE TRPRNT

!   *** setup variable name strings ***

      SUBROUTINE tr_setup_kv

      USE TRCOMM, ONLY: KVT, KVRT
      IMPLICIT NONE

      KVT( 1) = 'ANS0(1)   '
      KVT( 2) = 'ANS0(2)   '
      KVT( 3) = 'ANS0(3)   '
      KVT( 4) = 'ANS0(4)   '
      KVT( 5) = 'ANSAV(1)  '
      KVT( 6) = 'ANSAV(2)  '
      KVT( 7) = 'ANSAV(3)  '
      KVT( 8) = 'ANSAV(4)  '

      KVT( 9) = 'TS0(1)    '
      KVT(10) = 'TS0(2)    '
      KVT(11) = 'TS0(3)    '
      KVT(12) = 'TS0(4)    '
      KVT(13) = 'TSAV(1)   '
      KVT(14) = 'TSAV(2)   '
      KVT(15) = 'TSAV(3)   '
      KVT(16) = 'TSAV(4)   '

      KVT(17) = 'WST(1)    '
      KVT(18) = 'WST(2)    '
      KVT(19) = 'WST(3)    '
      KVT(20) = 'WST(4)    '

      KVT(21) = 'ANF0(1)   '
      KVT(22) = 'ANF0(2)   '
      KVT(23) = 'ANFAV(1)  '
      KVT(24) = 'ANFAV(2)  '
      KVT(25) = 'TF0(1)    '
      KVT(26) = 'TF0(2)    '
      KVT(27) = 'TFAV(1)   '
      KVT(28) = 'TFAV(2)   '

      KVT(29) = 'WFT(1)    '
      KVT(30) = 'WFT(2)    '
      KVT(31) = 'WBULKT    '
      KVT(32) = 'WTAILT    '
      KVT(33) = 'WPT       '

      KVT(34) = 'AJT       '
      KVT(35) = 'AJOHT     '
      KVT(36) = 'AJNBT     '
      KVT(37) = 'AJRFT     '
      KVT(38) = 'AJBST     '

      KVT(39) = 'PINT      '
      KVT(40) = 'POHT      '
      KVT(41) = 'PNBT      '
      KVT(42) = 'PRFT(1)   '
      KVT(43) = 'PRFT(2)   '
      KVT(44) = 'PRFT(3)   '
      KVT(45) = 'PRFT(4)   '
      KVT(46) = 'PNFT      '

      KVT(47) = 'PBINT     '
      KVT(48) = 'PBCLT(1)  '
      KVT(49) = 'PBCLT(2)  '
      KVT(50) = 'PBCLT(3)  '
      KVT(51) = 'PBCLT(4)  '
      KVT(52) = 'PFINT     '
      KVT(53) = 'PFCLT(1)  '
      KVT(54) = 'PFCLT(2)  '
      KVT(55) = 'PFCLT(3)  '
      KVT(56) = 'PFCLT(4)  '

      KVT(57) = 'POUT      '
      KVT(58) = 'PCXT      '
      KVT(59) = 'PIET      '
      KVT(60) = 'PRSUMT    '
      KVT(61) = 'PLT(1)    '
      KVT(62) = 'PLT(2)    '
      KVT(63) = 'PLT(3)    '
      KVT(64) = 'PLT(4)    '

      KVT(65) = 'SINT      '
      KVT(66) = 'SIET      '
      KVT(67) = 'SNBT      '
      KVT(68) = 'SNFT      '
      KVT(69) = 'SOUT      '
      KVT(70) = 'SLT(1)    '
      KVT(71) = 'SLT(2)    '
      KVT(72) = 'SLT(3)    '
      KVT(73) = 'SLT(4)    '

      KVT(74) = 'VLOOP     '
      KVT(75) = 'ALI       '
      KVT(76) = 'RQ1       '
      KVT(77) = 'Q0        '

      KVT(78) = 'WPDOT     '
      KVT(79) = 'TAUE1     '
      KVT(80) = 'TAUE2     '
      KVT(81) = 'TAUE89    '

      KVT(82) = 'BETAP0    '
      KVT(83) = 'BETAPA    '
      KVT(84) = 'BETA0     '
      KVT(85) = 'BETAA     '

      KVT(86) = 'ZEFF0     '
      KVT(87) = 'QF        '
      KVT(88) = 'RIP       '
!
      KVT(89) = 'PEXT(1)   '
      KVT(90) = 'PEXT(2)   '
      KVT(91) = 'PRFVT(1,1)' ! ECH  to electron
      KVT(92) = 'PRFVT(2,1)' ! ECH  to ions
      KVT(93) = 'PRFVT(1,2)' ! LH   to electron
      KVT(94) = 'PRFVT(2,2)' ! LH   to ions
      KVT(95) = 'PRFVT(1,3)' ! ICRH to electron
      KVT(96) = 'PRFVT(2,3)' ! ICRH to ions

      KVT(97) = 'RR        '
      KVT(98) = 'RA        '
      KVT(99) = 'BB        '
      KVT(100)= 'RKAP      '
      KVT(101)= 'AJTTOR    '

      KVT(102)= 'TAUE98    '
      KVT(103)= 'H98Y2     '
      KVT(104)= 'ANLAV(1)  '
      KVT(105)= 'ANLAV(2)  '
      KVT(106)= 'ANLAV(3)  '
      KVT(107)= 'ANLAV(4)  '

      KVT(108)= 'PRBT      '
      KVT(109)= 'PRCT      '
      KVT(110)= 'PRLT      '

!     *** FOR 3D ***

      KVRT( 1) = 'RT(1)     '
      KVRT( 2) = 'RT(2)     '
      KVRT( 3) = 'RT(3)     '
      KVRT( 4) = 'RT(4)     '

      KVRT( 5) = 'RN(1)     '
      KVRT( 6) = 'RN(2)     '
      KVRT( 7) = 'RN(3)     '
      KVRT( 8) = 'RN(4)     '

      KVRT( 9) = 'AJ        '
      KVRT(10) = 'AJOH      '
      KVRT(11) = 'AJNB      '
      KVRT(12) = 'AJRF      '
      KVRT(13) = 'AJBS      '

      KVRT(14) = 'PTOT      '
      KVRT(15) = 'POH       '
      KVRT(16) = 'PNB       '
      KVRT(17) = 'PNF       '
      KVRT(18) = 'PRF(1)    '
      KVRT(19) = 'PRF(2)    '
      KVRT(20) = 'PRF(3)    '
      KVRT(21) = 'PRF(4)    '
      KVRT(22) = 'PRL       '
      KVRT(23) = 'PCX       '
      KVRT(24) = 'PIE       '
      KVRT(25) = 'PEX(1)    '
      KVRT(26) = 'PEX(2)    '
      KVRT(27) = 'QP        '
      KVRT(28) = 'EZOH      '
      KVRT(29) = 'BETA      '
      KVRT(30) = 'BETAP     '
      KVRT(31) = 'EZOH*2PIRR'
      KVRT(32) = 'ETA       '
      KVRT(33) = 'ZEFF      '
      KVRT(34) = 'AK(1)     '
      KVRT(35) = 'AK(2)     '

      KVRT(36) = 'PRFV(1,1) '
      KVRT(37) = 'PRFV(1,2) '
      KVRT(38) = 'PRFV(1,3) '
      KVRT(39) = 'PRFV(2,1) '
      KVRT(40) = 'PRFV(2,2) '
      KVRT(41) = 'PRFV(2,3) '

      KVRT(42) = 'AJRFV(1)  '
      KVRT(43) = 'AJRFV(2)  '
      KVRT(44) = 'AJRFV(3)  '

      KVRT(45) = 'RW(1+2)   '
      KVRT(46) = 'ANC+ANFE  '
      KVRT(47) = 'BP        '
      KVRT(48) = 'RPSI      '

      KVRT(49) = 'RMJRHO    '
      KVRT(50) = 'RMNRHO    '
      KVRT(51) = 'F0D       '
      KVRT(52) = 'RKPRHO    '
      KVRT(53) = 'DELTAR    '
      KVRT(54) = 'AR1RHO    '
      KVRT(55) = 'AR2RHO    '
      KVRT(56) = 'AKDW(1)   '
      KVRT(57) = 'AKDW(2)   '
      KVRT(58) = 'RN*RT(1)  '
      KVRT(59) = 'RN*RT(2)  '

      KVRT(60) = 'VTOR      '
      KVRT(61) = 'VPOL      '

      KVRT(62) = 'S-ALPHA   '
      KVRT(63) = 'ER        '
      KVRT(64) = 'S         '
      KVRT(65) = 'ALPHA     '
      KVRT(66) = 'TRCOFS    '
      KVRT(67) = '2PI/QP    '

      RETURN
    END SUBROUTINE tr_setup_kv

END MODULE trrslt_print
