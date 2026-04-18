### Makefile for Phase 2 submodule unit tests
###
### Builds test_trcomm_submodules by linking against the same
### libraries that tr2 uses.  The test driver is a standalone
### Fortran program that calls allocate_trcomm_<name> /
### deallocate_trcomm_<name> directly on each submodule.
###
### Run from this directory:
###     make            # build
###     ./test_trcomm_submodules   # run tests; STOP 0 = pass

include ../../../make.header
include ../../../mtxp/make.mtxp

FFLAGS = $(OFLAGS)

TR_DIR = ../..
MOD_DIR = $(TR_DIR)/$(MOD)
MTXP_DIR = $(TR_DIR)/../mtxp

# make.mtxp defines LIBX_MTX with paths relative to tr/ ("../mtxp/...");
# rewrite for our nested location (tr/tests/submodule_unit/).
LIBX_MTX_LOCAL = $(MTXP_DIR)/libmtxnompi.o $(MTXP_DIR)/libmtxbnd.o

MODINCLUDE = -I$(MOD_DIR) -I$(TR_DIR)/../pl/$(MOD) \
             -I$(TR_DIR)/../eq/$(MOD) -I$(TR_DIR)/../lib/$(MOD) \
             -I$(MTXP_DIR)/$(MOD) -I$(TR_DIR)/../../bpsd/$(MOD)

LIBS = $(TR_DIR)/libtr2.a \
       $(TR_DIR)/../eq/libeq.a $(TR_DIR)/../pl/libpl.a \
       $(TR_DIR)/../lib/libmds.a $(TR_DIR)/../lib/libtask.a \
       $(TR_DIR)/../lib/libgrf.a $(TR_DIR)/../../bpsd/libbpsd.a

all: test_trcomm_submodules

test_trcomm_submodules.o: test_trcomm_submodules.f90
	$(FCFREE) $(FFLAGS) -c test_trcomm_submodules.f90 -o test_trcomm_submodules.o $(MODINCLUDE)

test_trcomm_submodules: test_trcomm_submodules.o $(LIBS)
	$(FLINKER) test_trcomm_submodules.o $(LIBS) -o test_trcomm_submodules \
	    $(FFLAGS) $(FLIBS) $(LIBX_MTX_LOCAL)

run: test_trcomm_submodules
	./test_trcomm_submodules

clean:
	-rm -f *.o *.mod test_trcomm_submodules

.PHONY: all run clean
