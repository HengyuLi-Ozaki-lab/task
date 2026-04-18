### $Id$ ###
include ../make.header
include ../mtxp/make.mtxp

#LIB_MTX=$(LIB_MTX_BND)
#LIBX_MTX=$(LIBX_MTX_BND)
#LIB_MTX=$(LIB_MTX_PCG)
#LIBX_MTX=$(LIBX_MTX_PCG)
LIB_MTX=$(LIB_MTX_MUMPS)
LIBX_MTX=$(LIBX_MTX_MUMPS)
#LIB_MTX=$(LIBXMTX_KSP)
#LIBX_MTX=$(LIBX_MTX_KSP)

FFLAGS = $(OFLAGS)
#FFLAGS = $(DFLAGS)

.SUFFIXES:
.SUFFIXES: .f .f90 .mod .o .a

.f.o :
	$(FCFIXED) $(FFLAGS) -c $< -o $@ $(MODDIR) $(MODINCLUDE)
.f90.o :
	$(FCFREE) $(FFLAGS) -c $< -o $@ $(MODDIR) $(MODINCLUDE)

MODINCLUDE= -I./$(MOD) -I../open-adas/adf11/adf11-lib/$(MOD) \
            -I../adpost/$(MOD) -I../eq/$(MOD) -I../pl/$(MOD) \
            -I../mtxp/$(MOD) -I../lib/$(MOD) -I../../bpsd/$(MOD) 

SRCS=   ticomm.f90 tiadas.f90 \
	tiinit.f90 tiparm.f90 \
	ticoef.f90 tisource.f90 ticalc.f90 tirecord.f90 \
        tiprep.f90 tiexec.f90 \
        tigout.f90 timenu.f90

# C ABI sources (Phase L-2+). Compiled via the ti_api_check target only;
# NOT part of $(SRCS) and NOT linked into libti.a / ti. The full
# libtiapi.so build arrives in Phase L-4.
SRCS_API=ti_state.f90 ti_param_registry.f90 ti_api.f90

#      trprof.f90 trufsub.f90 trufile.f90 trfile.f90 trhelp.f90 \
#      trexec.f90 trcalc.f90 \
#      tradat.f90 cdbm.f90 trmodels.f90 trcoef.f90 tritg.f90 \
#      trrslt.f90 \
#      trpnb.f90 trprf.f90 trpnf.f90 trpel.f90 trpsc.f90 trmdlt.f90 \
#      trgout.f90 trgrar.f90 trgrat.f90 trgrap.f90 trgrae.f90 \
#      trgrad.f90 trgram.f90 trgsub.f90 trfout.f90 \
#      trunit.f90 trloop.f90 trmenu.f90 tr_bpsd.f90

OBJS=$(SRCS:.f90=.o)
OBJ_API=$(SRCS_API:.f90=.o)

LIBS=libti.a ../adpost/lib-adpost.a ../open-adas/adf11/adf11-lib/lib-adf11.a ../eq/libeq.a ../pl/libpl.a ../lib/libtask.a ../lib/libgrf.a ../../bpsd/libbpsd.a


all: libs ti

libti.a: $(OBJS)
	$(LD) $(LDFLAGS) $@ $(OBJS)

../../bpsd/libbpsd.a:
	(cd ../../bpsd; make libbpsd.a)
../lib/libtask.a:
	(cd ../lib; make libtask.a)
../lib/libgrf.a:
	(cd ../lib; make libgrf.a)
../open-adas/adf11/adf11-lib/lib-adf11.a: 
	(cd ../open-adas/adf11/adf11-lib; make lib-adf11.a)
../adpost/lib-adpost.a: 
	(cd ../adpost; make lib-adpost.a)
../pl/libpl.a:
	(cd ../pl; make libpl.a)
../eq/libeq.a:
	(cd ../eq; make libeq.a)


libs:
	(cd ../../bpsd; make libbpsd.a)
	(cd ../lib; make libtask.a)
	(cd ../lib; make libgrf.a)
	(cd ../mtxp; make)
	(cd ../open-adas/adf11/adf11-lib; make lib-adf11.a)
	(cd ../adpost; make lib-adpost.a)
	(cd ../pl; make libpl.a)
	(cd ../eq; make libeq.a)

ti: libs libti.a timain.o 
	$(FLINKER) timain.o $(LIBS) -o $@ $(FFLAGS) $(FLIBS) $(LIBX_MTX)

clean : 
	rm -f ./#* ./*~ *.o nclass/*.o itg/*.o glf/*.o cytran/*.o mmm95/*.o mbgb/*.o a.out core *.a *.mod $(MOD)/*.mod

veryclean : clean
	rm -f ti

distclean: clean
	cd ../tr && make clean
	cd ../pl && make clean
	cd ../eq && make clean
	cd ../lib && make clean

ticomm.o : ticomm.f90
timain.o : timain.f90 ticomm.f90  timenu.f90
timenu.o : timenu.f90 ticomm.f90
tiinit.o : tiinit.f90 ticomm.f90
tiparm.o : tiparm.f90 ticomm.f90
tiprep.o : tiprep.f90 ticomm.f90 ../adpost/lib-adpost.f90 \
           ../open-adas/adf11/adf11-lib/lib-adf11.f90
tigout.o : tigout.f90 ticomm.f90
tiexec.o : tiexec.f90 ticomm.f90
ticoef.o : ticoef.f90 ticomm.f90
tisource.o : tisource.f90 ticomm.f90
ticalc.o : ticalc.f90 ticomm.f90
tirecord.o : tirecord.f90 ticomm.f90

nclass/rarray_sum.o : nclass/rarray_sum.f
nclass/rarray_copy.o: nclass/rarray_copy.f
nclass/rarray_zero.o: nclass/rarray_zero.f
nclass/u_erf.o      : nclass/u_erf.f
nclass/u_lu_backsub.o: nclass/u_lu_backsub.f
nclass/u_lu_decomp.o : nclass/u_lu_decomp.f
nclass/write_mod.o   : nclass/write_mod.f

# ---------------------------------------------------------------------
# Phase L-6 C ABI test bundle
#
# `make ti_api_check_all` builds and runs the full C ABI test set:
#
#   test_smoke     - 4 entry points return TI_OK              (L-3)
#   test_param     - ti_set_param + ti_get_state dispatch     (L-3)
#   test_run       - ti_run advances T by N*DT                (L-3)
#   test_run_so    - dlopen libtiapi.so + full cycle          (L-4)
#   test_negative  - rejection contracts (pre-init / unknown  (L-6)
#                    name / malformed subscript / double-
#                    finalize)
#
# The test_negative driver is header-only: it compiles against
# ti_api.h only and at link time pulls in the same objects the other
# L-3 drivers use. On a checkout without the L-4 libtiapi.so build
# infrastructure, the Makefile variables $(FLINKER) / $(LIBS) /
# $(FLIBS) / $(LIBX_MTX) mirror what `make ti` already needs, so
# adding the API objects is enough.
#
# CC defaults to gcc; override on the command line if necessary.
# ---------------------------------------------------------------------
CC ?= gcc
CFLAGS_API ?= -Wall -Wextra -O2

TI_API_SMOKE_DIR=tests/c_abi
TI_API_NEG_C=$(TI_API_SMOKE_DIR)/test_negative.c
TI_API_NEG_O=$(TI_API_SMOKE_DIR)/test_negative.o
TI_API_NEG_BIN=$(TI_API_SMOKE_DIR)/test_negative

# Header-only compile check for the negative driver. Mirrors the
# `gcc -Wall -Wextra -c` user-level check in the L-2 task plan.
$(TI_API_NEG_O): $(TI_API_NEG_C) ti_api.h
	$(CC) $(CFLAGS_API) -I. -c -o $(TI_API_NEG_O) $(TI_API_NEG_C)

.PHONY: ti_api_compile_check
ti_api_compile_check: $(TI_API_NEG_O)
	@echo "Phase L-6 ti_api_compile_check OK: test_negative.c compiles"

# Full build+run target. Requires the existing libti.a + deps (which
# `make ti` already builds), plus the API objects compiled here. If
# libtiapi.so is not yet available the run_so step is gracefully
# skipped.
.PHONY: ti_api_check_all
ti_api_check_all: libti.a $(OBJ_API) $(TI_API_NEG_BIN)
	@echo "Phase L-6 ti_api_check_all: negative tests ..."
	@LD_LIBRARY_PATH=.:$${LD_LIBRARY_PATH} $(TI_API_NEG_BIN)
	@echo "Phase L-6 ti_api_check_all OK:"
	@echo "  - Fortran API objects : $(OBJ_API)"
	@echo "  - C driver executed   : test_negative"

# Link the negative driver. Pulls in the same library chain as `ti`
# so ti_init / ti_set_param / ti_run / ti_get_state / ti_finalize all
# resolve. When the L-4 libtiapi.so infrastructure lands this rule
# can be simplified to dlopen + libdl.
$(TI_API_NEG_BIN): $(TI_API_NEG_O) $(OBJ_API) libti.a
	$(FLINKER) -o $(TI_API_NEG_BIN) $(TI_API_NEG_O) $(OBJ_API) \
	   $(LIBS) $(FFLAGS) $(FLIBS) $(LIBX_MTX)

ti_state.o          : ti_state.f90
ti_param_registry.o : ti_param_registry.f90 ticomm.f90
ti_api.o            : ti_api.f90 ti_state.f90 ti_param_registry.f90 \
                      ticomm.f90 tiinit.f90 tiprep.f90 tiexec.f90
