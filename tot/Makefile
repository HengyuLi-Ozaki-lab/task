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
# Phase L-3: tot_param_registry.f90 is a pure dispatcher that USEs the
# six per-module registries (eq, tr, fp, ti, wrx) and MUST sit between
# tot_state.f90 and tot_api.f90 in dependency order (tot_api USEs
# tot_param_registry).
SRCS_API  = tot_state.f90 tot_param_registry.f90 tot_api.f90
SRCS      = $(SRCS_CORE) $(SRCS_MENU)

OBJS     = $(SRCS:.f90=.o)
OBJ_API  = $(SRCS_API:.f90=.o)

# Phase L-3: per-module param_registry .o files (NOT in the static
# libs, because every per-module Makefile keeps SRCS_API out of its
# libX.a). The tot_api_check link needs them explicitly.
#
# Paths follow each module's OBJDIR convention:
#   tr  : ./obj (OBJDIR)
#   fp  : ./obj (OBJDIR)
#   ti  : flat  (no OBJDIR)
#   wrx : ./obj (OBJDIR) -- tot links wrx/libwr.a, so we route wr:/wrx:
#                           to wrx_param_registry (see tot_param_registry.f90)
#   eq  : flat
TOT_L3_DEPS_OBJ = \
    ../tr/obj/tr_param_registry.o \
    ../fp/obj/fp_param_registry.o \
    ../ti/ti_param_registry.o \
    ../wrx/obj/wrx_param_registry.o \
    ../eq/eq_param_registry.o

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
# Phase L-3: orchestrator C ABI check (independent of default `tot`)
#
# `make tot_api_check` builds the API objects (tot_state.o,
# tot_param_registry.o, tot_api.o) plus two C drivers linked against
# tot_api.h:
#
#   test_smoke  : init/run/get_state/finalize stubs + dispatcher error
#                 paths (no-prefix, bad-prefix reject -> INVALID)
#   test_param  : namespaced success paths + per-module error paths
#                 (tr:RR, fp:NRMAX, ti:DT, wrx:RF, wr: alias)
#
# The API objects are NOT linked into the `tot` binary; the default
# `tot` target therefore stays byte-for-byte identical with or without
# this target being invoked. SRCS_API is kept out of $(SRCS) for the
# same reason.
#
# tot_param_registry USEs five per-module registries (tr, fp, ti, wrx,
# eq). Those modules keep their SRCS_API objects out of libX.a, so we
# must link each *_param_registry.o explicitly via TOT_L3_DEPS_OBJ;
# the supporting libs (libtr2.a, libeq.a, libfp.a, libti.a,
# wrx/libwr.a, ...) are pulled in after to resolve the indirect
# TRCOMM / PLCOMM / ... symbols those registries touch.
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

TOT_API_PARAM_C=$(TOT_API_SMOKE_DIR)/test_param.c
TOT_API_PARAM_O=$(TOT_API_SMOKE_DIR)/test_param.o
TOT_API_PARAM_BIN=$(TOT_API_SMOKE_DIR)/test_param

# Libraries the per-module registries transitively depend on. Matches
# the $(LIBS) set used by the `tot` binary link so that references to
# TRCOMM / PLCOMM / EQCOMM / ... from each *_param_registry.o resolve.
TOT_L3_DEPS_LIB = $(LIBS)

# Step 1: header-only C compile (matches the documented user-level check
#         `gcc -Wall -Wextra -c -o test_smoke.o test_smoke.c`).
$(TOT_API_SMOKE_O): $(TOT_API_SMOKE_C) tot_api.h
	$(CC) $(CFLAGS_API) -I. -c -o $(TOT_API_SMOKE_O) $(TOT_API_SMOKE_C)
$(TOT_API_PARAM_O): $(TOT_API_PARAM_C) tot_api.h
	$(CC) $(CFLAGS_API) -I. -c -o $(TOT_API_PARAM_O) $(TOT_API_PARAM_C)

# Step 2: link each C driver against the API objects + per-module
# param_registry .o + backing libs. gfortran drives the link so the
# libgfortran runtime is pulled in automatically.
$(TOT_API_SMOKE_BIN): $(TOT_API_SMOKE_O) $(OBJ_API) $(TOT_L3_DEPS_OBJ) $(TOT_L3_DEPS_LIB)
	$(FLINKER) -o $(TOT_API_SMOKE_BIN) $(TOT_API_SMOKE_O) $(OBJ_API) \
	    $(TOT_L3_DEPS_OBJ) $(TOT_L3_DEPS_LIB) $(FFLAGS) $(FLIBS) $(LIBX_MTX)
$(TOT_API_PARAM_BIN): $(TOT_API_PARAM_O) $(OBJ_API) $(TOT_L3_DEPS_OBJ) $(TOT_L3_DEPS_LIB)
	$(FLINKER) -o $(TOT_API_PARAM_BIN) $(TOT_API_PARAM_O) $(OBJ_API) \
	    $(TOT_L3_DEPS_OBJ) $(TOT_L3_DEPS_LIB) $(FFLAGS) $(FLIBS) $(LIBX_MTX)

# Each per-module registry .o is built by the owning module's Makefile
# (part of its SRCS_API target). Delegate so that `make tot_api_check`
# from a clean tree is self-bootstrapping.
../tr/obj/tr_param_registry.o:
	(cd ../tr; make obj/tr_param_registry.o)
../fp/obj/fp_param_registry.o:
	(cd ../fp; make obj/fp_param_registry.o)
../ti/ti_param_registry.o:
	(cd ../ti; make ti_param_registry.o)
../wrx/obj/wrx_param_registry.o:
	(cd ../wrx; make obj/wrx_param_registry.o)
../eq/eq_param_registry.o:
	(cd ../eq; make eq_param_registry.o)

.PHONY: tot_api_check tot_api_compile_check
# A cheaper target that only proves the Fortran side compiles (no
# link of the C drivers). Useful during local iteration.
tot_api_compile_check: $(OBJ_API)
	@echo "Phase L-3 tot_api_compile_check: Fortran API objects built"
	@echo "  $(OBJ_API)"

tot_api_check: $(OBJ_API) $(TOT_API_SMOKE_BIN) $(TOT_API_PARAM_BIN)
	@echo "Phase L-3 tot_api_check: running smoke / param ..."
	@$(TOT_API_SMOKE_BIN)
	@$(TOT_API_PARAM_BIN)
	@echo "Phase L-3 tot_api_check OK:"
	@echo "  - Fortran API objects       : $(OBJ_API)"
	@echo "  - C drivers executed        : test_smoke, test_param"

clean:
	-rm -f core a.out *.o *.mod ./*~ *.a $(MOD)/*.mod
	-rm -f $(TOT_API_SMOKE_O) $(TOT_API_SMOKE_BIN)
	-rm -f $(TOT_API_PARAM_O) $(TOT_API_PARAM_BIN)

veryclean: clean
	-rm -f tot

totmain.o: totmain.f90 totregress.o
totmenu.o: totmenu.f90
totregress.o: totregress.f90

# Phase L-2 C ABI sources (independent of any *COMM at this stage).
tot_state.o : tot_state.f90
# Phase L-3: tot_param_registry USEs tr_param_registry, fp_param_registry,
# ti_param_registry, wrx_param_registry, eq_param_registry. Those .mod
# files are produced under ../tr/mod, ../fp/mod, ../ti/mod, ../wrx/mod
# and ../eq/mod respectively (all already on MODINCLUDE). We therefore
# depend on the owning module's libX.a so the .mod files are present
# before this source is compiled.
tot_param_registry.o : tot_param_registry.f90 \
                       ../tr/libtr2.a ../fp/libfp.a ../ti/libti.a \
                       ../wrx/libwr.a ../eq/libeq.a
tot_api.o   : tot_api.f90 tot_state.f90 tot_state.o tot_param_registry.o

