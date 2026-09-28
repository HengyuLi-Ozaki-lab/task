"""Regression tests for ``QQPS``, the q profile on the psi-surface grid.

``EqState.qqps`` (length ``NPSMAX``, sampled on ``PSIPS``) is set in one
of two ways:

* A g-eqdsk load (``MODELG=5`` or ``25``, ``EQDSKR`` in eq/eq-eqdsk.f90)
  reads it from the file's q column. ``EQCALQ`` runs after that read
  and must leave the column alone: a file whose q is 7.0 everywhere, or
  negative, comes back unchanged.
* Nothing else reads or computes it: ``EQRTSK`` (``MODELG=3``) loads a
  binary format that does not store ``QQPS``, and ``EQCALC`` never set
  it, so the C-API getter (eq/eq_api_common.f) used to return the
  zero-initialised COMMON value. ``EQCALQ`` (eq/eqcalq.f90) now
  resamples the per-NR q profile (``profile[].QPS`` on ``PSIP``, spline
  ``UQPS``) onto ``PSIPS``. A ``PSIPS`` point outside the ``PSIP``
  range is clamped to the nearest end rather than written as 0.0.

The g-eqdsk files are written into ``tmp_path`` from the committed
``eqdata.ITER01`` fixture, so no large fixture is committed.
"""
from __future__ import annotations

import bisect
import contextlib
import math
import os
import sys
import unittest
from pathlib import Path

import pytest

HERE = Path(__file__).resolve()
PYTHON_ROOT = HERE.parents[2]  # .../python
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from eqlib import Eq  # noqa: E402
from eqlib import _ffi  # noqa: E402

# The same resolution Eq() uses: EQLIB_PATH, then eq/ and lib/, with the
# platform's file name (libeqapi.dll on Windows).
LIB_PATH = _ffi._default_lib_path()
LIB_MISSING = (
    f"{LIB_PATH.name} not found at {LIB_PATH}; run `make -C eq libeqapi.so`"
)
FIXTURES_DIR = HERE.parent / "fixtures"
FIXTURE_EQDATA = FIXTURES_DIR / "eqdata.ITER01"
FIXTURE_MISSING = f"fixture {FIXTURE_EQDATA} missing"

requires_lib = pytest.mark.skipif(not LIB_PATH.exists(), reason=LIB_MISSING)
requires_fixture = pytest.mark.skipif(
    not FIXTURE_EQDATA.exists(), reason=FIXTURE_MISSING
)


@contextlib.contextmanager
def _pushd(target: Path):
    """Run the body with ``cwd`` switched to ``target``.

    The loaders open ``KNAMEQ`` relative to the current working
    directory (``OPEN(21, FILE=KNAMEQ, ...)``), and ``KNAMEQ`` holds at
    most 80 characters, so files are opened by a relative name from
    inside their directory.
    """
    prev = Path.cwd()
    os.chdir(target)
    try:
        yield target
    finally:
        os.chdir(prev)


def _load_iter01(eq: Eq):
    """EQRTSK (``MODELG=3``) load of the committed ITER01 fixture."""
    with _pushd(FIXTURES_DIR):
        eq.set_param("MODELG", 3)
        eq.set_param_str("KNAMEQ", FIXTURE_EQDATA.name)
        eq.run(mode=1)
    return eq.get_state()


def _natural_cubic_spline(xs, ys):
    """Return the natural cubic spline through ``(xs, ys)`` as a function.

    ``SPL1D(..., ID=0)`` (lib/libspl1d.f90) builds the same interpolant
    (zero second derivative at both ends) by solving for the first
    derivatives; this solves for the second derivatives instead, so it
    is an independent construction.
    """
    n = len(xs)
    h = [xs[i + 1] - xs[i] for i in range(n - 1)]
    # Tridiagonal system for the second derivatives; rows 0 and n-1
    # pin them to 0.
    sub, diag, sup, rhs = [0.0] * n, [1.0] * n, [0.0] * n, [0.0] * n
    for i in range(1, n - 1):
        sub[i] = h[i - 1]
        diag[i] = 2.0 * (h[i - 1] + h[i])
        sup[i] = h[i]
        rhs[i] = 6.0 * ((ys[i + 1] - ys[i]) / h[i] - (ys[i] - ys[i - 1]) / h[i - 1])
    for i in range(1, n):
        w = sub[i] / diag[i - 1]
        diag[i] -= w * sup[i - 1]
        rhs[i] -= w * rhs[i - 1]
    m = [0.0] * n
    m[-1] = rhs[-1] / diag[-1]
    for i in range(n - 2, -1, -1):
        m[i] = (rhs[i] - sup[i] * m[i + 1]) / diag[i]

    def spline(x):
        k = min(max(bisect.bisect_right(xs, x) - 1, 0), n - 2)
        a, b, hk = xs[k + 1] - x, x - xs[k], h[k]
        return ((m[k] * a ** 3 + m[k + 1] * b ** 3) / (6.0 * hk)
                + (ys[k] / hk - m[k] * hk / 6.0) * a
                + (ys[k + 1] / hk - m[k + 1] * hk / 6.0) * b)

    return spline


def _write_geqdsk(path: Path, st, psirz, q_of_s, axis_psi_scale: float = 1.0):
    """Write the ITER01 equilibrium ``st`` as a g-eqdsk text file.

    Laid out as ``EQDSKR`` (eq/eq-eqdsk.f90) reads it. psi is TASK's
    (boundary at 0) divided by 2*pi, which ``EQDSKR`` undoes, so PSIRZ
    round-trips. ``axis_psi_scale`` scales only the axis psi
    (``simag``), which sets the file's PSIPS grid (0 .. -2*pi*simag).
    The boundary is ITER01's analytic shape. The q column is
    ``q_of_s(s)`` at ``nw`` uniform ``s`` in [0, 1]; returns it as the
    reader will see it (after the ``%16.9E`` round trip).
    """
    import numpy as np

    from eqlib.tests.fixtures.eq_iter01_params import SCALARS as shape

    two_pi = 2.0 * math.pi
    rg, zg = np.array(st.rg), np.array(st.zg)
    nw, nh = len(rg), len(zg)
    sc = st.scalars
    simag = sc["psi0"] * axis_psi_scale / two_pi
    # 1-D profiles on the reader's grid: nw points uniform in psi.
    x = np.linspace(0.0, st.psips[-1], nw)
    fpol = np.interp(x, st.psips, st.ttps) / two_pi  # F = R * B_phi
    pres = np.interp(x, st.psips, st.ppps)
    dpsi = (x[1] - x[0]) / two_pi
    ffprim = fpol * np.gradient(fpol, dpsi)
    pprime = np.gradient(pres, dpsi)
    q = [float("%16.9E" % q_of_s(s)) for s in np.linspace(0.0, 1.0, nw)]
    th = np.linspace(0.0, two_pi, 65)
    rbdy = shape["RR"] + shape["RA"] * np.cos(th + shape["RDLT"] * np.sin(th))
    zbdy = shape["RKAP"] * shape["RA"] * np.sin(th)
    lim = [rg[1], zg[1], rg[-2], zg[1], rg[-2], zg[-2], rg[1], zg[-2], rg[1], zg[1]]
    rcentr = shape["RR"]

    def block(values):
        values = list(values)
        return "".join(
            "".join("%16.9E" % v for v in values[i:i + 5]) + "\n"
            for i in range(0, len(values), 5)
        )

    path.write_text(
        "%-48s%4d%4d%4d\n" % ("TASK ITER01 test", 0, nw, nh)
        + block([rg[-1] - rg[0], zg[-1] - zg[0], rcentr, rg[0], 0.5 * (zg[0] + zg[-1])])
        + block([sc["raxis"], sc["zaxis"], simag, 0.0, fpol[-1] / rcentr])
        + block([sc["ripx"] * 1e6, simag, 0.0, sc["raxis"], 0.0])
        + block([sc["zaxis"], 0.0, 0.0, 0.0, 0.0])
        + block(fpol) + block(pres) + block(ffprim) + block(pprime)
        + block((np.asarray(psirz) / two_pi).T.reshape(-1))  # R fastest
        + block(q)
        + "%5d%5d\n" % (len(rbdy), len(lim) // 2)
        + block(np.column_stack([rbdy, zbdy]).reshape(-1))
        + block(lim)
    )
    return q


@unittest.skipUnless(LIB_PATH.exists(), LIB_MISSING)
@unittest.skipUnless(FIXTURE_EQDATA.exists(), FIXTURE_MISSING)
class TestQqpsAfterEqrtskLoad(unittest.TestCase):
    """QQPS after a MODELG=3 (EQRTSK) load: the all-zeros regression."""

    # QQPS[0] / QQPS[-1] against the QAXIS / QSURF scalars. EQCALQ
    # evaluates those from the same UQPS spline, at PSIP = 0 and at the
    # PSIP of rho = 1, so this checks alignment, not the q values. The
    # axis end matches exactly (PSIPS[0] = PSIP[0] = 0); the LCFS end
    # is off by the gap between the file's PSIPS[-1] and EQAXIS's PSIPA
    # (4.7e-5 out of 103 for ITER01, so 4e-6 in q).
    ENDPOINT_TOL = 1e-4
    # QQPS against an independently built spline: the same interpolant,
    # so only rounding separates them.
    SPLINE_REL_TOL = 1e-10

    def _load_iter01(self):
        with Eq() as eq:
            return _load_iter01(eq)

    def test_qqps_not_all_zero(self):
        st = self._load_iter01()
        nps = st.npsmax
        self.assertGreater(nps, 0, "NPSMAX should be > 0 after EQRTSK load")
        qqps = list(st.qqps)[:nps]
        self.assertFalse(
            all(q == 0.0 for q in qqps),
            f"QQPS is all zeros (npsmax={nps}) after an EQRTSK load: "
            "EQCALQ did not resample the per-NR q profile onto PSIPS. "
            "See eq/eqcalq.f90::EQCALQ.",
        )

    def test_qqps_endpoints_match_scalars(self):
        st = self._load_iter01()
        nps = st.npsmax
        qqps = list(st.qqps)[:nps]
        qaxis = st.scalars["qaxis"]
        qsurf = st.scalars["qsurf"]
        self.assertAlmostEqual(
            qqps[0], qaxis, delta=self.ENDPOINT_TOL,
            msg=f"QQPS[0]={qqps[0]} != QAXIS={qaxis} (tol {self.ENDPOINT_TOL})",
        )
        self.assertAlmostEqual(
            qqps[-1], qsurf, delta=self.ENDPOINT_TOL,
            msg=f"QQPS[-1]={qqps[-1]} != QSURF={qsurf} (tol {self.ENDPOINT_TOL})",
        )

    def test_qqps_interior_matches_independent_spline(self):
        st = self._load_iter01()
        psip = [row["PSIP"] for row in st.profile]
        q_at = _natural_cubic_spline(psip, [row["QPS"] for row in st.profile])
        self.assertGreater(st.npsmax, 2)
        for i in range(1, st.npsmax - 1):
            psi = st.psips[i]
            self.assertTrue(
                psip[0] < psi < psip[-1],
                f"PSIPS[{i}]={psi} outside PSIP [{psip[0]}, {psip[-1]}]",
            )
            expected = q_at(psi)
            self.assertAlmostEqual(
                st.qqps[i], expected, delta=self.SPLINE_REL_TOL * abs(expected),
                msg=(
                    f"QQPS[{i}]={st.qqps[i]} at PSIPS={psi} != {expected}, "
                    "the natural spline of profile (PSIP, QPS)"
                ),
            )

    def test_qqps_monotone_for_iter_baseline(self):
        st = self._load_iter01()
        nps = st.npsmax
        qqps = list(st.qqps)[:nps]
        for i in range(1, nps):
            self.assertGreaterEqual(
                qqps[i], qqps[i - 1],
                msg=(
                    f"QQPS not monotone at i={i}: "
                    f"{qqps[i - 1]} -> {qqps[i]}"
                ),
            )


@pytest.mark.parametrize(
    "q_of_s",
    [lambda s: 7.0, lambda s: -(1.0 + 2.5 * s * s)],
    ids=["q_constant_7", "q_negative"],
)
@requires_lib
@requires_fixture
def test_geqdsk_q_column_survives_the_load(tmp_path, q_of_s):
    """A MODELG=5 (g-eqdsk) load returns the file's q column unchanged.

    EQ_READ calls EQCALQ right after EQDSKR reads the column, and
    eq_load calls it again. TASK's own q for this equilibrium runs from
    0.58 to 3.33, so a column that differs from it (constant 7.0, or
    negative as in the opposite sign convention) shows whether either
    call overwrote the file's values.
    """
    pytest.importorskip("numpy")
    with Eq() as eq:
        st = _load_iter01(eq)
        psirz = eq.get_psi_rz()
        with _pushd(tmp_path):
            expected = _write_geqdsk(tmp_path / "g_iter01", st, psirz, q_of_s)
            eq.set_param("MODELG", 5)
            eq.set_param_str("KNAMEQ", "g_iter01")
            eq.run(mode=1)
        st5 = eq.get_state()
    assert st5.npsmax == len(expected)
    # The load recomputed q, and TASK's q differs from the column.
    assert 0.0 < st5.scalars["qaxis"] < st5.scalars["qsurf"]
    assert abs(st5.scalars["qsurf"] - expected[-1]) > 1.0
    assert st5.qqps == pytest.approx(expected, rel=1e-12, abs=0.0)


@requires_lib
@requires_fixture
def test_psips_point_beyond_psip_range_is_clamped(tmp_path):
    """A PSIPS point outside the PSIP range gets q at the end, not 0.0.

    A g-eqdsk whose axis psi is 0.1% deeper than the axis EQAXIS finds
    has a PSIPS grid that ends 0.1% beyond PSIPA. Saved and reloaded as
    MODELG=3 (EQRTSK does not re-derive PSIPS), with NSUMAX=0 so PSIP
    ends at the LCFS and NRMAX=1000 so the overshoot exceeds half an
    average PSIP cell, the last PSIPS point is one SPL1DF reports as out
    of range (IERR=2). EQCALQ used to store 0.0 there while the run
    reported success.
    """
    pytest.importorskip("numpy")
    with Eq() as eq:
        st = _load_iter01(eq)
        psirz = eq.get_psi_rz()
        with _pushd(tmp_path):
            # The q column does not matter: EQSAVE does not store QQPS.
            _write_geqdsk(tmp_path / "g_offset", st, psirz, lambda s: 7.0,
                          axis_psi_scale=1.001)
            eq.set_param("MODELG", 5)
            eq.set_param_str("KNAMEQ", "g_offset")
            eq.run(mode=1)
            eq.save("saved.eqdata")
            eq.set_param("MODELG", 3)
            eq.set_param_str("KNAMEQ", "saved.eqdata")
            eq.set_param("NSUMAX", 0)
            eq.set_param("NRMAX", 1000)
            eq.run(mode=1)
        st3 = eq.get_state()
    psip = [row["PSIP"] for row in st3.profile]
    assert (st3.nrmax, st3.nsumax) == (1000, 0)
    half_cell = 0.5 * (psip[-1] - psip[0]) / (st3.nrmax - 1)
    assert st3.psips[-1] - psip[-1] > half_cell
    zeros = [i for i, q in enumerate(st3.qqps) if q == 0.0]
    assert not zeros, f"QQPS is 0.0 at PSIPS indices {zeros}"
    # Clamped to the last flux surface (the LCFS, as NSUMAX=0): q there.
    assert st3.qqps[-1] == pytest.approx(st3.profile[-1]["QPS"], rel=1e-12)


if __name__ == "__main__":
    unittest.main()
