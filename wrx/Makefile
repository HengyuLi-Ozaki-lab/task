### Makefile for wr

include ../make.header
include ../mtxp/make.mtxp

#LIB_MTX=$(LIB_MTX_NOMPI)
#LIBX_MTX=$(LIBX_MTX_NOMPI)
#LIB_MTX=$(LIB_MTX_PCG)
#LIBX_MTX=$(LIBX_MTX_PCG)
#LIB_MTX=$(LIB_MTX_MUMPS)
#LIBX_MTX=$(LIBX_MTX_MUMPS)
#LIB_MTX=$(LIBXMTX_KSP)
#LIBX_MTX=$(LIBX_MTX_KSP)

FFLAGS=$(OFLAGS)
#FFLAGS=$(DFLAGS)

OBJDIR   = ./obj

#.SUFFIXES:
#.SUFFIXES: .f90 .mod .o .a

#.f.o :
#	$(FCFIXED) $(FFLAGS) -c $< -o $@ $(MODDIR) $(MODINCLUDE)
#.f90.o :
#	$(FCFREE) $(FFLAGS) -c $< -o $@ $(MODDIR) $(MODINCLUDE)

${OBJDIR}/%.o:%.f90
	$(FCFREE) $(FFLAGS) -c $< -o $@ $(MODDIR) $(MODINCLUDE)

${OBJDIR}/%.o:%.f
	$(FCFIXED) $(FFLAGS) -c $< -o $@ $(MODDIR) $(MODINCLUDE)

MODINCLUDE= -I./$(MOD) -I../pl/$(MOD) -I../dp/$(MOD) -I../eq/$(MOD) \
            -I../lib/$(MOD) -I../mtxp/$(MOD) -I../../bpsd/$(MOD)

SRCS_CORE = wrcomm.f90 wrinit.f90 wrparm.f90 wrprep.f90 wrview.f90 \
            wrsub.f90 \
            wrsetup.f90 wrcalpwr.f90 wrfdrv.f90 wroxb.f90 \
            wrexecr.f90 wrexecb.f90 \
            wrexec.f90 \
            wrfile.f90 \
            wrxregress.f90

SRCS_GRAPHICS = wrgout.f90

SRCS_MENU = wrmenu.f90

# C ABI sources (Phase L-2+). Compiled via the wrx_api_check target only;
# NOT part of $(SRCS) and NOT linked into libwr.a / the wrx binary.
# The full libwrxapi.so build arrives in Phase L-4.
SRCS_API = wrx_state.f90 wrx_api.f90

SRCS = $(SRCS_CORE) $(SRCS_GRAPHICS) $(SRCS_MENU)

OBJS = $(addprefix $(OBJDIR)/, $(SRCS:.f90=.o))
OBJ_API = $(addprefix $(OBJDIR)/, $(SRCS_API:.f90=.o))

LIBS = libwr.a  ../dp/libdp.a ../eq/libeq.a ../pl/libpl.a \
       ../lib/libtask.a ../lib/libgrf.a ../../bpsd/libbpsd.a

LIBSPLOT = ../lib/libtask.a ../lib/libgrf.a ../../bpsd/libbpsd.a

all : libs wr

../../bpsd/libbpsd.a:
	(cd ../../bpsd; make libbpsd.a)
../lib/libtask.a:
	(cd ../lib; make libtask.a)
../lib/libgrf.a:
	(cd ../lib; make libgrf.a)
../pl/libpl.a:
	(cd ../pl; make libpl.a)
../eq/libeq.a:
	(cd ../eq; make libeq.a)
../dp/libdp.a:
	(cd ../dp; make libdp.a)

libwr.a: $(OBJS)
	$(LD) $(LDFLAGS) $@ $(OBJS)

libs:
	(cd ../../bpsd; make libbpsd.a)
	(cd ../lib; make libtask.a)
	(cd ../lib; make libgrf.a)
	(cd ../mtxp; make)
	(cd ../pl; make libpl.a)
	(cd ../eq; make libeq.a)
	(cd ../dp; make libdp.a)

wr : $(LIB_MTX) $(LIBS) $(OBJDIR)/wrmain.o
	$(FLINKER) $(OBJDIR)/wrmain.o $(LIBS) -o $@ $(FFLAGS) $(FLIBS) $(LIBX_MTX)

wrplot : $(LIBS) $(OBJDIR)/wrplot.o
	$(FLINKER) $(OBJDIR)/wrplot.o $(LIBSPLOT) -o $@ $(FFLAGS) $(FLIBS)

# ---------------------------------------------------------------------
# Phase L-2: C ABI check
#
# `make wrx_api_check` builds the new API objects (wrx_state.o,
# wrx_api.o) AND a small C smoke test against wrx_api.h.  This is a
# header / link sanity check only -- the API objects are NOT linked
# into libwr.a and the wrx binary remains byte-for-byte identical with
# or without this target being invoked.  The smoke driver expects every
# entry point to return WRX_ERR_NOT_IMPL (=4) at L-2.
#
# CC defaults to gcc; override on the command line if necessary
# (e.g. `make wrx_api_check CC=clang`).
# ---------------------------------------------------------------------
CC ?= gcc
CFLAGS_API ?= -Wall -Wextra -O2

WRX_API_SMOKE_DIR = tests/c_abi
WRX_API_SMOKE_C   = $(WRX_API_SMOKE_DIR)/test_smoke.c
WRX_API_SMOKE_O   = $(WRX_API_SMOKE_DIR)/test_smoke.o
WRX_API_SMOKE_BIN = $(WRX_API_SMOKE_DIR)/test_smoke

# Step 1: header-only C compile (matches the documented user-level check
#         `gcc -Wall -Wextra -c -o test_smoke.o test_smoke.c`).
$(WRX_API_SMOKE_O): $(WRX_API_SMOKE_C) wrx_api.h
	$(CC) $(CFLAGS_API) -I. -c -o $(WRX_API_SMOKE_O) $(WRX_API_SMOKE_C)

# Step 2: link the C smoke against the API objects only. This proves
# the BIND(C) names emitted by wrx_api.f90 (wrx_init, wrx_run,
# wrx_set_param, wrx_get_state, wrx_finalize) match the prototypes in
# wrx_api.h. We use gfortran as the driver so the libgfortran runtime
# is pulled in automatically; no other wrx/ libraries are required at
# L-2.
$(WRX_API_SMOKE_BIN): $(WRX_API_SMOKE_O) $(OBJ_API)
	$(FLINKER) -o $(WRX_API_SMOKE_BIN) $(WRX_API_SMOKE_O) $(OBJ_API)

.PHONY: wrx_api_check
wrx_api_check: $(OBJ_API) $(WRX_API_SMOKE_BIN)
	@echo "Phase L-2 wrx_api_check: running smoke ..."
	@$(WRX_API_SMOKE_BIN)
	@echo "Phase L-2 wrx_api_check OK:"
	@echo "  - Fortran API objects compiled: $(OBJ_API)"
	@echo "  - C smoke object compiled    : $(WRX_API_SMOKE_O)"
	@echo "  - C smoke linked + executed  : $(WRX_API_SMOKE_BIN)"

clean:
	-rm -f core a.out *.o *.a ./*~
	-rm -f ./mod/*.mod
	-rm -f ./obj/*.o
	-rm -rf ./*.dSYM
	-rm -f $(WRX_API_SMOKE_O) $(WRX_API_SMOKE_BIN)

veryclean: clean
	-rm -f wr

WRCOMM=wrcomm.f90 ../dp/dpcomm.f90 ../pl/plcomm.f90
$(OBJDIR)/wrcomm.o: $(WRCOMM)
$(OBJDIR)/wrmain.o: wrmain.f90 $(WRCOMM) ../pl/plinit.f90 ../pl/plparm.f90 \
../dp/dpinit.f90 ../dp/dpparm.f90 wrinit.f90 wrparm.f90 wrmenu.f90
$(OBJDIR)/wrmenu.o: wrmenu.f90 $(WRCOMM) ../pl/plparm.f90 ../dp/dpparm.f90 \
../dp/dproot.f90 ../dp/dpcont.f90 wrparm.f90 wrview.f90 wrprep.f90 \
wrsetup.f90 wrexec.f90 wrgout.f90 wrfile.f90 
$(OBJDIR)/wrinit.o: wrinit.f90 $(WRCOMM)
$(OBJDIR)/wrparm.o: wrparm.f90 $(WRCOMM) ../dp/dpparm.f90
$(OBJDIR)/wrview.o: wrview.f90 $(WRCOMM)
$(OBJDIR)/wrprep.o: wrprep.f90 $(WRCOMM) ../dp/dpparm.f90 ../eq/equnit.f
$(OBJDIR)/wrsetup.o: wrsetup.f90 $(WRCOMM)
$(OBJDIR)/wrcalpwr.o: wrcalpwr.f90 $(WRCOMM) ../pl/plprof.f90 \
../pl/plprof.f90 
$(OBJDIR)/wrfdrv.o: wrfdrv.f90 $(WRCOMM) wrsub.f90
$(OBJDIR)/wroxb.o: wroxb.f90 $(WRCOMM) ../pl/plprof.f90 \
wrfdrv.f90 wrsub.f90 ../dp/dpdisp.f90

$(OBJDIR)/wrexecr.o: wrexecr.f90 $(WRCOMM) ../pl/plprof.f90 \
wrsub.f90 wrcalpwr.f90 wrfdrv.f90 wroxb.f90 
$(OBJDIR)/wrexecb.o: wrexecb.f90 $(WRCOMM) ../pl/plprof.f90 \
wrsub.f90
$(OBJDIR)/wrexec.o: wrexec.f90 $(WRCOMM) wrexecr.f90 wrexecb.f90

$(OBJDIR)/wrsetup.o: wrsetup.f90 $(WRCOMM)
$(OBJDIR)/wrsub.o: wrsub.f90 $(WRCOMM)  ../pl/plprof.f90 \
../pl/plprofw.f90 ../dp/dpdisp.f90 ../dp/dppola.f90 ../dp/dpdisp.f90
$(OBJDIR)/wrgout.o: wrgout.f90 $(WRCOMM) ../pl/plprof.f90 ../pl/plgout.f90 \
wrsub.f90 
$(OBJDIR)/wrfile.o: wrfile.f90 $(WRCOMM) wrcalpwr.f90
$(OBJDIR)/wrxregress.o: wrxregress.f90 $(WRCOMM)
$(OBJDIR)/wrmenu.o: wrxregress.f90

# Phase L-2 C ABI sources (independent of WRCOMM at this stage).
$(OBJDIR)/wrx_state.o: wrx_state.f90
$(OBJDIR)/wrx_api.o:   wrx_api.f90 wrx_state.f90 $(OBJDIR)/wrx_state.o
