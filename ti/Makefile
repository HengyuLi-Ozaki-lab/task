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

# Core sources: included in both `ti` binary and (later) libtiapi.so.
# Graphics and menu are split out so libtiapi.so can be built without them.
SRCS_CORE=   ticomm.f90 tiadas.f90 \
	tiinit.f90 tiparm.f90 \
	ticoef.f90 tisource.f90 ticalc.f90 tirecord.f90 \
        tiprep.f90 tiregress.f90 tiexec.f90

SRCS_GRAPHICS= tigout.f90

SRCS_MENU=     timenu.f90

# C ABI sources (Phase L-2+). Compiled via the ti_api_check target only;
# NOT part of $(SRCS) and NOT linked into libti.a / ti. The full
# libtiapi.so build arrives in Phase L-4.
SRCS_API=ti_state.f90 ti_param_registry.f90 ti_api.f90

SRCS=$(SRCS_CORE) $(SRCS_GRAPHICS) $(SRCS_MENU)

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

.PHONY: srcs-core-list srcs-graphics-list srcs-menu-list

srcs-core-list:
	@echo $(SRCS_CORE)

srcs-graphics-list:
	@echo $(SRCS_GRAPHICS)

srcs-menu-list:
	@echo $(SRCS_MENU)

# ---------------------------------------------------------------------
# Phase L-2 / L-3: C ABI check
#
# `make ti_api_check` builds the new API objects (ti_state.o,
# ti_param_registry.o, ti_api.o) and three small C drivers linked
# against ti_api.h:
#
#   test_smoke  : 4 entry points return TI_OK           (sanity)
#   test_param  : ti_set_param + ti_get_state dispatch  (L-3)
#   test_run    : ti_run advances T by N*DT             (L-3)
#
# The API objects are NOT linked into libti.a / ti and the ti binary
# remains byte-for-byte identical with or without this target being
# invoked. L-3 drivers depend on libti.a (for TICOMM, ti_exec, ti_prep,
# ...) so we link it in after the API objects. The full libtiapi.so
# build arrives in Phase L-4.
#
# CC defaults to gcc; override on the command line if necessary
# (e.g. `make ti_api_check CC=clang`).
# ---------------------------------------------------------------------
CC ?= gcc
CFLAGS_API ?= -Wall -Wextra -O2

TI_API_SMOKE_DIR=tests/c_abi
TI_API_SMOKE_C=$(TI_API_SMOKE_DIR)/test_smoke.c
TI_API_SMOKE_O=$(TI_API_SMOKE_DIR)/test_smoke.o
TI_API_SMOKE_BIN=$(TI_API_SMOKE_DIR)/test_smoke

TI_API_PARAM_C=$(TI_API_SMOKE_DIR)/test_param.c
TI_API_PARAM_O=$(TI_API_SMOKE_DIR)/test_param.o
TI_API_PARAM_BIN=$(TI_API_SMOKE_DIR)/test_param

TI_API_RUN_C=$(TI_API_SMOKE_DIR)/test_run.c
TI_API_RUN_O=$(TI_API_SMOKE_DIR)/test_run.o
TI_API_RUN_BIN=$(TI_API_SMOKE_DIR)/test_run

# At L-3 the API drivers pull in TICOMM, ti_exec, ti_prep, ... so we
# need the full ti + eq + pl + bpsd + mtx link just like ti.
TI_API_DEPS=$(LIBS) $(LIBX_MTX)

# Step 1: header-only C compile (matches the documented user-level check
#         `gcc -Wall -Wextra -c -o test_smoke.o test_smoke.c`).
$(TI_API_SMOKE_O): $(TI_API_SMOKE_C) ti_api.h
	$(CC) $(CFLAGS_API) -I. -c -o $(TI_API_SMOKE_O) $(TI_API_SMOKE_C)
$(TI_API_PARAM_O): $(TI_API_PARAM_C) ti_api.h
	$(CC) $(CFLAGS_API) -I. -c -o $(TI_API_PARAM_O) $(TI_API_PARAM_C)
$(TI_API_RUN_O):   $(TI_API_RUN_C)   ti_api.h
	$(CC) $(CFLAGS_API) -I. -c -o $(TI_API_RUN_O)   $(TI_API_RUN_C)

# Step 2: link against API objects + ti/eq/pl/bpsd/mtx. gfortran drives
# the link so libgfortran is pulled in automatically.
$(TI_API_SMOKE_BIN): $(TI_API_SMOKE_O) $(OBJ_API) libti.a
	$(FLINKER) -o $(TI_API_SMOKE_BIN) $(TI_API_SMOKE_O) $(OBJ_API) \
	   $(TI_API_DEPS) $(FFLAGS) $(FLIBS)
$(TI_API_PARAM_BIN): $(TI_API_PARAM_O) $(OBJ_API) libti.a
	$(FLINKER) -o $(TI_API_PARAM_BIN) $(TI_API_PARAM_O) $(OBJ_API) \
	   $(TI_API_DEPS) $(FFLAGS) $(FLIBS)
$(TI_API_RUN_BIN):   $(TI_API_RUN_O)   $(OBJ_API) libti.a
	$(FLINKER) -o $(TI_API_RUN_BIN)   $(TI_API_RUN_O)   $(OBJ_API) \
	   $(TI_API_DEPS) $(FFLAGS) $(FLIBS)

.PHONY: ti_api_check
ti_api_check: $(OBJ_API) $(TI_API_SMOKE_BIN) $(TI_API_PARAM_BIN) $(TI_API_RUN_BIN)
	@echo "Phase L-3 ti_api_check: running smoke / param / run ..."
	@$(TI_API_SMOKE_BIN)
	@$(TI_API_PARAM_BIN)
	@$(TI_API_RUN_BIN)
	@echo "Phase L-3 ti_api_check OK:"
	@echo "  - Fortran API objects : $(OBJ_API)"
	@echo "  - C drivers executed  : test_smoke, test_param, test_run"

clean :
	rm -f ./#* ./*~ *.o nclass/*.o itg/*.o glf/*.o cytran/*.o mmm95/*.o mbgb/*.o a.out core *.a *.mod $(MOD)/*.mod
	rm -f $(TI_API_SMOKE_O) $(TI_API_SMOKE_BIN)
	rm -f $(TI_API_PARAM_O) $(TI_API_PARAM_BIN)
	rm -f $(TI_API_RUN_O)   $(TI_API_RUN_BIN)

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
tiregress.o : tiregress.f90 ticomm.f90
tiexec.o : tiexec.f90 ticomm.f90 tiregress.f90
ticoef.o : ticoef.f90 ticomm.f90
tisource.o : tisource.f90 ticomm.f90
ticalc.o : ticalc.f90 ticomm.f90
tirecord.o : tirecord.f90 ticomm.f90

# Phase L-2 / L-3 C ABI sources. ti_state is independent of TICOMM;
# ti_param_registry and ti_api pull in TICOMM plus ti_prep / ti_exec.
ti_state.o : ti_state.f90
ti_param_registry.o : ti_param_registry.f90 ticomm.f90 ticomm.o
ti_api.o   : ti_api.f90 ti_state.f90 ti_state.o ti_param_registry.o \
             ticomm.o tiinit.o tiprep.o tiexec.o

nclass/rarray_sum.o : nclass/rarray_sum.f
nclass/rarray_copy.o: nclass/rarray_copy.f
nclass/rarray_zero.o: nclass/rarray_zero.f
nclass/u_erf.o      : nclass/u_erf.f
nclass/u_lu_backsub.o: nclass/u_lu_backsub.f
nclass/u_lu_decomp.o : nclass/u_lu_decomp.f
nclass/write_mod.o   : nclass/write_mod.f
