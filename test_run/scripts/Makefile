### Standalone build for the gen-dummy-adf11 generator program.
###
### This Makefile is intentionally tiny and only knows how to build the
### one generator. Everything else (lib-adf11.a, libtask.a, ...) is
### delegated to the upstream Makefiles via `make -C`.
###
### Invocations:
###   make                   # build gen-dummy-adf11 (binary stays here)
###   make gen-fixture       # build + run the generator, writing the
###                          # ADF11-bin.data file to ../fixtures/
###   make clean             # remove gen-dummy-adf11 + its .o
###
### The generator uses the canonical `SAVE_ADF11_bin` routine in
### lib-adf11.f90 so any future binary-layout change in lib-adf11 is
### automatically reflected in the generated fixture.
###

TASK_ROOT      := $(abspath $(CURDIR)/../..)
ADF11_DIR      := $(TASK_ROOT)/open-adas/adf11/adf11-lib
LIB_DIR        := $(TASK_ROOT)/lib
MTXP_DIR       := $(TASK_ROOT)/mtxp
BPSD_DIR       := $(TASK_ROOT)/../bpsd

include $(TASK_ROOT)/make.header
include $(MTXP_DIR)/make.mtxp

# make.mtxp uses '../mtxp/libmtxnompi.o' style paths (it expects the
# including Makefile to live one level above mtxp/). Override with
# absolute paths so this Makefile, which lives two levels deeper, links
# correctly.
LIBMTXMPI      = $(MTXP_DIR)/libmtxnompi.o
LIB_MTX_BND    = $(LIBMTXMPI) $(MTXP_DIR)/libmtxbnd.o
LIBX_MTX_BND   = $(LIB_MTX_BND)
LIB_MTX        = $(LIB_MTX_BND)
LIBX_MTX       = $(LIBX_MTX_BND)

FFLAGS         = $(OFLAGS)

MODINCLUDE     = -I$(ADF11_DIR)/$(MOD) -I$(LIB_DIR)/$(MOD) \
                 -I$(MTXP_DIR)/$(MOD) -I$(BPSD_DIR)/$(MOD)

# Same library chain as conv-adf11 in adf11-lib/Makefile (which links
# lib-adf11.a, libmtxp, libtask, libgrf, libbpsd plus the BND mtx
# backend). gen-dummy-adf11 only calls SAVE_ADF11_bin + SPL2D, so the
# heavier dependencies (libgrf, libmtxp BND backend) are pulled in only
# to satisfy module/use-statement transitive dependencies in lib-adf11.
#
# Note: $(LIBX_MTX) (libmtxnompi.o + libmtxbnd.o) is appended at link
# time via the recipe -- do NOT include it in $(LIBS) too or ld will
# complain about multiple definitions.
LIBS           = $(ADF11_DIR)/lib-adf11.a \
                 $(LIB_DIR)/libtask.a \
                 $(LIB_DIR)/libgrf.a \
                 $(BPSD_DIR)/libbpsd.a

GEN_BIN        = gen-dummy-adf11
GEN_SRC        = gen-dummy-adf11.f90
GEN_OBJ        = gen-dummy-adf11.o

FIXTURE_DIR    = $(CURDIR)/../fixtures
FIXTURE_FILE   = $(FIXTURE_DIR)/ADF11-bin.data

.PHONY: all gen-fixture clean upstream-libs

all: $(GEN_BIN)

# Build upstream archives on demand so a fresh checkout works.
upstream-libs:
	$(MAKE) -C $(BPSD_DIR) libbpsd.a
	$(MAKE) -C $(LIB_DIR) libtask.a libgrf.a
	$(MAKE) -C $(MTXP_DIR)
	$(MAKE) -C $(ADF11_DIR) lib-adf11.a

$(GEN_OBJ): $(GEN_SRC) upstream-libs
	$(FCFREE) $(FFLAGS) -c $< -o $@ $(MODINCLUDE)

$(GEN_BIN): $(GEN_OBJ)
	$(FLINKER) $(GEN_OBJ) $(LIBS) -o $@ $(FFLAGS) $(FLIBS) $(LIBX_MTX)

# Run the generator and place the result in test_run/fixtures/. The
# generator writes ADF11-bin.data to its current working directory, so
# we cd into FIXTURE_DIR before invoking it.
gen-fixture: $(GEN_BIN)
	@mkdir -p $(FIXTURE_DIR)
	@cp $(GEN_BIN) $(FIXTURE_DIR)/.gen-dummy-adf11.tmp
	cd $(FIXTURE_DIR) && ./.gen-dummy-adf11.tmp
	@rm -f $(FIXTURE_DIR)/.gen-dummy-adf11.tmp
	@echo "Fixture written: $(FIXTURE_FILE)"
	@ls -l $(FIXTURE_FILE)

clean:
	-rm -f $(GEN_BIN) $(GEN_OBJ)
