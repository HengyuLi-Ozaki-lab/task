###### $Id$ ###
include ../make.header
include ../mtxp/make.mtxp

#LIB_MTX=$(LIB_MTX_BND)
#LIBX_MTX=$(LIBX_MTX_BND)
#LIB_MTX=$(LIB_MTX_PCG)
#LIBX_MTX=$(LIBX_MTX_PCG)
#LIB_MTX=$(LIB_MTX_MUMPS)
#LIBX_MTX=$(LIBX_MTX_MUMPS)
#LIB_MTX=$(LIBXMTX_KSP)
#LIBX_MTX=$(LIBX_MTX_KSP)

FFLAGS=$(OFLAGS)
#FFLAGS=$(DFLAGS)

.SUFFIXES:
.SUFFIXES: .f .f90 .mod .o .a

.f.o :
	$(FCFIXED) $(FFLAGS) -c $< -o $@ $(MODDIR) $(MODINCLUDE)
.f90.o :
	$(FCFREE) $(FFLAGS) -cpp $(EXTRA_DEFS) -c $< -o $@ $(MODDIR) $(MODINCLUDE)

MODINCLUDE= -I$(MOD) -I../open-adas/adf11/adf11-lib/$(MOD) \
            -I../adpost/$(MOD) -I../eq/$(MOD) -I../pl/$(MOD) \
            -I../dp/$(MOD) -I../wrx/$(MOD) -I../wmx/$(MOD) \
            -I../fp/$(MOD) -I../ob/$(MOD) \
            -I../tr/$(MOD) -I../ti/$(MOD) \
            -I../mtxp/$(MOD) -I../lib/$(MOD) \
            -I../../bpsd/$(MOD) 

EQLIBS= ../pl/noequlib.o ../eq/libeq.a

# Source layout (logical groups; SRCS still single list for now):
#   SRCS_CORE  : files needed by both `tot` binary and future libtotapi.so
#                (regression dump goes here so library users can also dump).
#   SRCS_MENU  : interactive dispatcher only used by `tot` binary.
#   SRCS_API   : added in L-2 (tot_state.f90, tot_api.f90). Orchestrator
#                stubs. NOT part of $(SRCS); compiled only via the
#                independent `tot_api_check` target so the default
#                `tot` binary has no hard build dependency on any
#                per-module L-2 (tr_state, ti_state, ...).
SRCS_CORE = totregress.f90
SRCS_MENU = totmenu.f90
SRCS_API  = tot_state.f90 tot_api.f90
SRCS      = $(SRCS_CORE) $(SRCS_MENU)

OBJS     = $(SRCS:.f90=.o)
OBJ_API  = $(SRCS_API:.f90=.o)

LIBS = ../lib/libmds.a ../lib/libgrf.a ../lib/libtask.a ../../bpsd/libbpsd.a \
       ../adpost/lib-adpost.a ../open-adas/adf11/adf11-lib/lib-adf11.a \
       ../pl/libpl.a \
       $(EQLIBS) \
       ../tr/libtr2.a ../dp/libdp.a ../wrx/libwr.a ../wmx/libwm.a \
       ../fp/libfp.a ../ob/libob.a ../ti/libti.a


all : libs tot

../open-adas/adf11/adf11-lib/lib-adf11.a:
	(cd ../open-adas/adf11/adf11-lib; make lib-adf11.a)
../adpost/lib-adpost.a:
	(cd ../adpost; make lib-adpost.a)
../lib/libtask.a:
	(cd ../lib; make libtask.a)
../lib/libgrf.a:
	(cd ../lib; make libgrf.a)
../lib/libmds.a:
	(cd ../lib; make libmds.a)
$(LIB_MTX):
	(cd ../mtxp; make)
../../bpsd/libbpsd.a:
	(cd ../../bpsd; make libbpsd.a)
../pl/libpl.a:
	(cd ../pl; make libpl.a)
../pl/noeqlib.o:
	(cd ../pl; make noeqlib.o)
../pl/noequlib.o:
	(cd ../pl; make noequlib.o)
../eq/libeq.a:
	(cd ../eq; make libeq.a)
../tr/libtr2.a:
	(cd ../tr; make libtr2.a)
../dp/libdp.a:
	(cd ../dp; make libdp.a)
../wrx/libwr.a:
	(cd ../wrx; make libwr.a)
../wmx/libwm.a:
	(cd ../wmx; make libwm.a)
../fp/libfp.a:
	(cd ../fp; make libfp.a)
../fp/libob.a:
	(cd ../ob; make libob.a)
../ti/libti.a:
	(cd ../ti; make libti.a)

libs:
	(cd ../../bpsd; make libbpsd.a)
	(cd ../lib; make libtask.a)
	(cd ../lib; make libgrf.a)
	(cd ../lib; make libmds.a)
	(cd ../mtxp; make)
	(cd ../adpost; make lib-adpost.a)
	(cd ../open-adas/adf11/adf11-lib; make lib-adf11.a)
	(cd ../pl; make libpl.a)
	(cd ../pl; make noeqlib.o)
	(cd ../pl; make noequlib.o)
	(cd ../eq; make libeq.a)
	(cd ../tr; make libtr2.a)
	(cd ../dp; make libdp.a)
	(cd ../wrx; make libwr.a)
	(cd ../wmx; make libwm.a)
	(cd ../ob; make libob.a)
	(cd ../fp; make libfp.a)
	(cd ../ti; make libti.a)
	make totmenu.o
	make totregress.o

tot : $(LIB_MTX) $(LIBS) totmenu.o totregress.o totmain.o
	$(FLINKER) totmenu.o totregress.o totmain.o -o $@ $(FFLAGS) $(LIBS) $(FLIBS) $(LIBX_MTX)

# ---------------------------------------------------------------------
# Phase L-2: orchestrator C ABI check (independent of default `tot`)
#
# `make tot_api_check` builds the new API objects (tot_state.o,
# tot_api.o) AND a small C smoke test against tot_api.h. This is a
# header / link sanity check only -- the API objects are NOT linked
# into the `tot` binary and the `tot` binary remains byte-for-byte
# identical with or without this target being invoked.
#
# Importantly, SRCS_API is deliberately kept OUT of the default `tot`
# target so this Makefile does not hard-depend on any per-module L-2
# being present (tr/tr_state.f90, ti/ti_state.f90, ...). The L-2 stubs
# are self-contained; real per-module fan-out (and the corresponding
# USE lines) arrives in L-3+.
#
# The smoke driver expects every entry point to return
# TOT_ERR_NOT_IMPL (=4) at L-2.
#
# CC defaults to gcc; override on the command line if necessary
# (e.g. `make tot_api_check CC=clang`).
# ---------------------------------------------------------------------
CC ?= gcc
CFLAGS_API ?= -Wall -Wextra -O2

TOT_API_SMOKE_DIR=tests/c_abi
TOT_API_SMOKE_C=$(TOT_API_SMOKE_DIR)/test_smoke.c
TOT_API_SMOKE_O=$(TOT_API_SMOKE_DIR)/test_smoke.o
TOT_API_SMOKE_BIN=$(TOT_API_SMOKE_DIR)/test_smoke

# Step 1: header-only C compile (matches the documented user-level check
#         `gcc -Wall -Wextra -c -o test_smoke.o test_smoke.c`).
$(TOT_API_SMOKE_O): $(TOT_API_SMOKE_C) tot_api.h
	$(CC) $(CFLAGS_API) -I. -c -o $(TOT_API_SMOKE_O) $(TOT_API_SMOKE_C)

# Step 2: link the C smoke against the API objects only. This proves
# the BIND(C) names emitted by tot_api.f90 (tot_init, tot_run,
# tot_set_param, tot_get_state, tot_finalize) match the prototypes in
# tot_api.h. We use gfortran as the driver so the libgfortran runtime
# is pulled in automatically; no other tot/ libraries are required at
# L-2 because the stubs do not USE any per-module API.
$(TOT_API_SMOKE_BIN): $(TOT_API_SMOKE_O) $(OBJ_API)
	$(FLINKER) -o $(TOT_API_SMOKE_BIN) $(TOT_API_SMOKE_O) $(OBJ_API)

.PHONY: tot_api_check
tot_api_check: $(OBJ_API) $(TOT_API_SMOKE_BIN)
	@echo "Phase L-2 tot_api_check: running smoke ..."
	@$(TOT_API_SMOKE_BIN)
	@echo "Phase L-2 tot_api_check OK:"
	@echo "  - Fortran API objects compiled: $(OBJ_API)"
	@echo "  - C smoke object compiled    : $(TOT_API_SMOKE_O)"
	@echo "  - C smoke linked + executed  : $(TOT_API_SMOKE_BIN)"

clean:
	-rm -f core a.out *.o *.mod ./*~ *.a $(MOD)/*.mod
	-rm -f $(TOT_API_SMOKE_O) $(TOT_API_SMOKE_BIN)

veryclean: clean
	-rm -f tot

totmain.o: totmain.f90 totregress.o
totmenu.o: totmenu.f90
totregress.o: totregress.f90

# Phase L-2 C ABI sources (independent of any *COMM at this stage).
tot_state.o : tot_state.f90
tot_api.o   : tot_api.f90 tot_state.f90 tot_state.o

