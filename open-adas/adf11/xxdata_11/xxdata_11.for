C STUB xxdata_11 - local build workaround for missing vendor sources.
C Not committed. Actual subroutine signature taken from open-adas upstream docs.
      SUBROUTINE XXDATA_11( IUNIT , ICLASS ,
     &                      ISDIMD, IDDIMD , ITDIMD ,
     &                      NDPTNL, NDPTN  , NDPTNC , NDCNCT ,
     &                      IZ0   , IS1MIN , IS1MAX ,
     &                      NPTNL , NPTN   , NPTNC  ,
     &                      IPTNLA, IPTNA  , IPTNCA ,
     &                      NCNCT , ICNCTV ,
     &                      IBLMX , ISMAX  , DNR_ELE, DNR_AMS,
     &                      ISPPR , ISPBR  , ISSTGR ,
     &                      IDMAX , ITMAX  ,
     &                      DDENS , DTEV   , DRCOF  ,
     &                      LRES  , LSTAN  , LPTN )
      INTEGER IUNIT, ICLASS, ISDIMD, IDDIMD, ITDIMD
      INTEGER NDPTNL, NDPTN, NDPTNC, NDCNCT
      INTEGER IZ0, IS1MIN, IS1MAX
      INTEGER NPTNL, NPTN(NDPTNL), NPTNC(NDPTNL, NDPTN)
      INTEGER IPTNLA(NDPTNL), IPTNA(NDPTNL, NDPTN)
      INTEGER IPTNCA(NDPTNL, NDPTN, NDPTNC)
      INTEGER NCNCT, ICNCTV(NDCNCT)
      INTEGER IBLMX, ISMAX, IDMAX, ITMAX
      INTEGER ISPPR(ISDIMD), ISPBR(ISDIMD), ISSTGR(ISDIMD)
      DOUBLE PRECISION DNR_AMS
      DOUBLE PRECISION DDENS(IDDIMD), DTEV(ITDIMD)
      DOUBLE PRECISION DRCOF(ISDIMD, ITDIMD, IDDIMD)
      LOGICAL LRES, LSTAN, LPTN
      CHARACTER*12 DNR_ELE
      WRITE(*,*) 'XX XXDATA_11 stub called - ADAS data not available'
      STOP 'XXDATA_11 stub'
      END
