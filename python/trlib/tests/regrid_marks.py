"""Skip marks for the tests of a grid change inside one process (one place)."""
import os

import pytest

# A TR NRMAX change between preparations of one process is refused by tr_run (mesh_violation, tr/tr_api.f90).
TR_MESH_GUARD = pytest.mark.skip(
    reason="one TR mesh per process (61ff3cdf) until the pinned bpsd has k-yoshimi/bpsd#7; "
           "the commit that lifts the guard enables this test")

# An EQ-grid change with TR's NRMAX unchanged passes the guard but needs bpsd's spline resize.
NEEDS_BPSD_FIX = pytest.mark.skipif(
    os.environ.get("TRLIB_BPSD_REGRID_FIX") != "1",
    reason="needs bpsd with k-yoshimi/bpsd#7 (spline resized after a regrid); "
           "set TRLIB_BPSD_REGRID_FIX=1 with such a bpsd")

# An eq: set after a preparation of the process is refused (eq_name_refused, tr/tr_api.f90), whatever the bpsd.
EQ_MESH_GUARD = pytest.mark.skip(
    reason="eq: names are refused after the process's first preparation (the guard of 61ff3cdf's kind, "
           "tr/tr_api.f90 eq_name_refused) until the pinned bpsd has k-yoshimi/bpsd#7; "
           "the commit that lifts both guards enables this test")
