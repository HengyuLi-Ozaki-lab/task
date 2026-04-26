#!/usr/bin/env bash
# setup.sh — one-shot bootstrap: clone external deps, provision configs,
# and build all libXapi.so shared libraries needed for the Python wrappers.
#
# Mirrors the steps in .github/workflows/python-tests.yml so a fresh
# checkout of `task` becomes runnable with a single command:
#
#     scripts/setup.sh
#
# After this completes:
#   - ../bpsd       (sibling clone of k-yoshimi/bpsd@develop)
#   - mtxp/make.mtxp     (from make.mtxp.nompi)
#   - make.header        (gfortran, no graphics, no MPI)
#   - tr/libtrapi.so, eq/libeqapi.so, ti/libtiapi.so, fp/libfpapi.so,
#     wr/libwrapi.so, wrx/libwrxapi.so, tot/libtotapi.so
#
# Idempotent: re-running on an already-set-up tree skips finished steps.
# Override defaults with environment variables:
#
#   BPSD_REPO    URL to clone bpsd from
#                (default: https://github.com/k-yoshimi/bpsd)
#   BPSD_BRANCH  branch to check out (default: develop)
#   BPSD_DIR     where to clone (default: $REPO_ROOT/../bpsd)
#   SKIP_BUILD   set to 1 to clone + provision configs only
#                (skip the Fortran build chain)
#
# Platform notes:
#   - Linux + gfortran (Ubuntu, RHEL, etc.): works out of the box.
#     This is what CI uses (.github/workflows/python-tests.yml).
#   - macOS + Homebrew gfortran: the per-module Makefile link lines
#     pass GNU-ld-only flags (`-Wl,-soname,...`, `-Wl,--start-group`)
#     that Apple's `ld` rejects, so the per-module .so step fails.
#     Workarounds: build inside Docker (`ubuntu:24.04` is what CI uses),
#     or patch each module Makefile with a Darwin guard. The PIC support
#     libraries (libbpsd.a, lib*_pic.a, libpl_pic.a, libeq_pic.a) build
#     fine on macOS — only the final lib*api.so step is affected.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BPSD_REPO="${BPSD_REPO:-https://github.com/k-yoshimi/bpsd}"
BPSD_BRANCH="${BPSD_BRANCH:-develop}"
BPSD_DIR="${BPSD_DIR:-$REPO_ROOT/../bpsd}"

# ── 1. Clone BPSD (sibling of task/) ───────────────────────────────────
if [ ! -d "$BPSD_DIR" ]; then
    echo "=== cloning $BPSD_REPO ($BPSD_BRANCH) → $BPSD_DIR ==="
    git clone --branch "$BPSD_BRANCH" "$BPSD_REPO" "$BPSD_DIR"
else
    echo "=== bpsd already at $BPSD_DIR (skipping clone) ==="
fi

# ── 2. Apply bpsd patches (idempotent via apply-bpsd-patches.sh) ──────
# The CI workflow patches upstream ats-fukuyama/bpsd. The k-yoshimi
# fork's develop branch may already have these merged, in which case
# the script reports "already-applied" and exits cleanly.
#
# apply-bpsd-patches.sh also rebuilds every libXapi.so. On a fresh
# checkout the .so build step necessarily fails (lib*_pic.a etc. are
# not built yet), so we only run the patch portion here and grep the
# log for genuine patch-step failures. Any "ERROR: <patch> failed
# --check" line means git apply rejected the patch in both directions
# (neither apply nor reverse-apply works) and we abort hard.
echo "=== applying bpsd patches (idempotent) ==="
patch_log="/tmp/setup-bpsd-patches.log"
BPSD_DIR="$BPSD_DIR" "$REPO_ROOT/scripts/apply-bpsd-patches.sh" \
    > "$patch_log" 2>&1 || true
if grep -qE "ERROR: .* failed --check" "$patch_log"; then
    echo "ERROR: bpsd patch application failed:" >&2
    cat "$patch_log" >&2
    exit 1
fi
echo "(patch log: $patch_log)"

# ── 3. Provision mtxp/make.mtxp from nompi template ───────────────────
if [ ! -f "$REPO_ROOT/mtxp/make.mtxp" ]; then
    echo "=== provisioning mtxp/make.mtxp from make.mtxp.nompi ==="
    cp "$REPO_ROOT/mtxp/make.mtxp.nompi" "$REPO_ROOT/mtxp/make.mtxp"
else
    echo "=== mtxp/make.mtxp already exists (skipping) ==="
fi

# ── 4. Provision make.header (gfortran, no graphics, no MPI) ──────────
if [ ! -f "$REPO_ROOT/make.header" ]; then
    echo "=== provisioning make.header (gfortran, no graphics, no MPI) ==="
    cat > "$REPO_ROOT/make.header" <<'HEADER_EOF'
### setup.sh-generated make.header (gfortran, no graphics, no MPI)
LAPACK = nolapack.f
LIBLA =
MODLA95 =
MDSPLUS = nomdsplus.f
MDSLIB =
MF77 = mpif77
MF90 = mpif90
MF95 = mpif90
MFC  = $(MF90)

## gfortran (64-bit), no graphics linkage (libXapi.so path)
GFLIBS=
OFLAGS = -g -O3 -m64 -std=legacy
DFLAGS = -g -m64 -fbounds-check -ffpe-trap=invalid,zero,overflow -fbacktrace -fcheck=all -std=legacy
FCFIXED = gfortran -ffixed-form
FCFREE = gfortran -ffree-form
MOD = mod
MODDIR = -Jmod
LD=ld
LDFLAGS=-r -o
FPP=
HEADER_EOF
else
    echo "=== make.header already exists (skipping) ==="
fi

# ── Optional: stop here if SKIP_BUILD=1 ──────────────────────────────
if [ "${SKIP_BUILD:-0}" = "1" ]; then
    echo "=== SKIP_BUILD=1: configs provisioned, build skipped ==="
    exit 0
fi

# ── 5. Build PIC support libraries ────────────────────────────────────
# Order matters; mirrors .github/workflows/python-tests.yml.
echo "=== building bpsd ==="
make -C "$BPSD_DIR" libbpsd.a

echo "=== building lib (PIC archives) ==="
make -C "$REPO_ROOT/lib" libtask_pic.a libgrf_pic.a libmds_pic.a

echo "=== building mtxp (PIC) ==="
make -C "$REPO_ROOT/mtxp" libmtxnompi_pic.o libmtxbnd_pic.o

echo "=== building tr/bpsd_pic (canonical builder for bpsd PIC objs) ==="
make -C "$REPO_ROOT/tr" bpsd_pic

echo "=== building pl libpl_noeq_pic ==="
make -C "$REPO_ROOT/pl" libpl_noeq_pic

echo "=== building eq libeq_pic.a ==="
make -C "$REPO_ROOT/eq" libeq_pic.a

echo "=== building pl libpl_pic.a (after eq) ==="
make -C "$REPO_ROOT/pl" libpl_pic.a

if [ -d "$REPO_ROOT/dp" ]; then
    echo "=== building dp libdp_pic.a ==="
    make -C "$REPO_ROOT/dp" libdp_pic.a
fi

if [ -d "$REPO_ROOT/ob" ]; then
    echo "=== building ob libob_pic.a ==="
    make -C "$REPO_ROOT/ob" libob_pic.a
fi

if [ -d "$REPO_ROOT/open-adas/adf11/adf11-lib" ]; then
    echo "=== building open-adas adf11_pic ==="
    make -C "$REPO_ROOT/open-adas/adf11/adf11-lib" lib-adf11_pic.a
fi

if [ -d "$REPO_ROOT/adpost" ]; then
    echo "=== building adpost lib-adpost_pic.a ==="
    make -C "$REPO_ROOT/adpost" lib-adpost_pic.a
fi

# ── 6. Build per-module .so files ─────────────────────────────────────
# IMPORTANT: tot must come last; it links against the others' .so.
echo "=== building libXapi.so for each module ==="
for mod in tr fp ti wr wrx eq tot; do
    if [ ! -d "$REPO_ROOT/$mod" ]; then
        echo "  (skipping $mod: directory not present)"
        continue
    fi
    echo "::: $mod / lib${mod}api.so"
    if [ "$mod" != "tot" ]; then
        make -C "$REPO_ROOT/$mod" bpsd_pic
    fi
    make -C "$REPO_ROOT/$mod" "lib${mod}api.so"
done

# ── Done ──────────────────────────────────────────────────────────────
echo ""
echo "=== setup complete ==="
for mod in tr eq ti fp wr wrx tot; do
    so="$REPO_ROOT/$mod/lib${mod}api.so"
    if [ -f "$so" ]; then
        echo "  ✓ $so ($(du -h "$so" | cut -f1))"
    fi
done
echo ""
echo "Next:"
echo "  export PYTHONPATH=$REPO_ROOT/python:\$PYTHONPATH"
echo "  python3 -c 'from trlib import Trlib; print(Trlib)'"
