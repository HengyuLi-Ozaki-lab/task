"""Regression test: ``QQPS`` must be populated by EQRTSK (MODELG=3) loads.

Bug history
-----------
Before this fix, ``EqState.qqps`` (the q profile on the psi-surface grid,
length ``NPSMAX``) was returned as all zeros after an EQRTSK binary load
(MODELG=3 / ``equnit::eq_load``):

* ``EQRTSK`` (eq/eqfile.f90) reads ``PSIPS`` / ``PPPS`` / ``TTPS`` /
  ``TEPS`` / ``OMPS`` from the binary file but **skips** ``QQPS`` -- the
  format does not store it.
* ``eqcalq`` later computes ``QPS`` on the per-NR flux-surface grid
  (which the C ABI exposes as ``profile[].QPS``) but does not project
  it onto the ``PSIPS`` grid where ``QQPS`` lives.
* The C-API getter (eq_api_common.f:186) faithfully copies the
  zero-initialised COMMON slot, leaving the Python ``EqState.qqps``
  field misleadingly silent.

The fix in ``EQRTSK`` interpolates ``QPS(NRMAX)`` onto ``PSIPS(NPSMAX)``
via the existing ``UQPS`` spline table populated by ``eqcalq``, so the
docstring claim ("q profile (psi-surface)") matches reality.

This test runs against the committed ``eqdata.ITER01`` fixture and
asserts:

1. ``QQPS`` is not all zeros (the original bug),
2. its endpoints match the ``QAXIS`` / ``QSURF`` scalars to a tight
   tolerance (consistency with the per-NR profile computed by
   eqcalq), and
3. it is monotone non-decreasing across the plasma (true for the
   ITER baseline; would need relaxing if a non-monotone-q fixture
   is ever added).
"""
from __future__ import annotations

import contextlib
import os
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
PYTHON_ROOT = HERE.parents[2]  # .../python
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from eqlib import Eq  # noqa: E402
from eqlib import _ffi  # noqa: E402

REPO = HERE.parents[3]
DEFAULT_SO = REPO / "eq" / "libeqapi.so"
FIXTURES_DIR = HERE.parent / "fixtures"
FIXTURE_EQDATA = FIXTURES_DIR / "eqdata.ITER01"


def _resolved_so() -> Path:
    env = os.environ.get("EQLIB_PATH")
    if env:
        return Path(env)
    return DEFAULT_SO


@contextlib.contextmanager
def _pushd(target: Path):
    """Run the body with ``cwd`` switched to ``target``.

    EQRTSK opens ``KNAMEQ`` relative to the current working directory
    (eq/eqfile.f90 ``OPEN(21, FILE=KNAMEQ, ...)``), so the test must
    chdir into the directory holding ``eqdata.ITER01``.
    """
    prev = Path.cwd()
    os.chdir(target)
    try:
        yield target
    finally:
        os.chdir(prev)


@unittest.skipUnless(
    _resolved_so().exists(),
    f"libeqapi.so not built at {_resolved_so()}; "
    "run `make -C eq libeqapi.so`",
)
@unittest.skipUnless(
    FIXTURE_EQDATA.exists(),
    f"fixture {FIXTURE_EQDATA} missing",
)
class TestQqpsPopulatedByEqrtsk(unittest.TestCase):
    """Regression coverage for the QQPS-all-zeros bug under MODELG=3."""

    # Endpoint match of QQPS[0] / QQPS[-1] against the QAXIS / QSURF
    # scalars. The axis end (PSIPS[0] = 0) lands exactly on the first
    # PSIP knot so machine precision is achievable; the LCFS end
    # (PSIPS[-1] = PSIPA) lands on the LCFS PSIP knot but the UQPS
    # spline has a small smoothness defect there because the per-NR
    # mesh continues into a vacuum extension (NR > LCFS index) with a
    # different physics regime. 1e-4 absolute (~3e-5 relative for ITER
    # q ~ 3.3) is well below any physically meaningful precision.
    ENDPOINT_TOL = 1e-4

    def _load_iter01(self):
        with _pushd(FIXTURES_DIR):
            with Eq() as eq:
                eq.set_param("MODELG", 3)
                eq.set_param_str("KNAMEQ", "eqdata.ITER01")
                eq.run(mode=1)
                return eq.get_state()

    def test_qqps_not_all_zero(self):
        st = self._load_iter01()
        nps = st.npsmax
        self.assertGreater(nps, 0, "NPSMAX should be > 0 after EQRTSK load")
        qqps = list(st.qqps)[:nps]
        self.assertFalse(
            all(q == 0.0 for q in qqps),
            f"QQPS is all zeros (npsmax={nps}); EQRTSK did not populate "
            "the psi-surface q profile. See eqfile.f90::EQRTSK.",
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


if __name__ == "__main__":
    unittest.main()
