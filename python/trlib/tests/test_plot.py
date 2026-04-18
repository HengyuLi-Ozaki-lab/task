"""Unit tests for :mod:`trlib.plot`.

Skipped entirely if matplotlib is not installed. The non-matplotlib
bits (``plot_available``, ``VARIABLE_INFO`` structure) are re-checked
in :mod:`tests.test_loader` so the TOML parser's reliance on the
metadata is always exercised.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
PYTHON_ROOT = HERE.parents[2]  # .../python
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))


try:
    import matplotlib  # noqa: F401
    HAS_MPL = True
except ImportError:  # pragma: no cover - CI-only
    HAS_MPL = False


@unittest.skipUnless(HAS_MPL, "matplotlib not installed")
class TestPlotModule(unittest.TestCase):

    def setUp(self):
        # Force a non-interactive backend so the test never tries to
        # open a window.
        import matplotlib
        matplotlib.use("Agg", force=True)

        from trlib import plot as plot_mod
        from trlib.state import TrState
        self.plot_mod = plot_mod
        self.TrState = TrState

    def _fake_state(self, nr=4, ns=2):
        """Build a small :class:`TrState` without touching libtrapi.so."""
        scalars = {
            "T": 0.0, "WPT": 1.0, "AJT": 2.0, "Q0": 0.9,
            "BETA0": 0.01, "BETAP0": 0.02, "BETAA": 0.03, "BETAN": 0.04,
            "TAUE1": 0.5, "TAUE2": 0.6, "ZEFF0": 1.0, "ALI": 0.7, "RQ1": 1.1,
        }
        rn = [[0.5 + 0.1 * i + 0.01 * j for j in range(ns)] for i in range(nr)]
        rt = [[1.0 - 0.1 * i + 0.01 * j for j in range(ns)] for i in range(nr)]
        aj = [0.2 * i for i in range(nr)]
        qp = [1.0 + 0.1 * i for i in range(nr)]
        return self.TrState(
            nt=0, nrmax=nr, nsmax=ns, scalars=scalars,
            RN=rn, RT=rt, AJ=aj, QP=qp,
        )

    # --- metadata tests ----------------------------------------------
    def test_plot_available_sorted(self):
        names = self.plot_mod.plot_available()
        self.assertEqual(names, sorted(names))
        # Must include the core profile variables called out in the spec.
        for key in ("RN", "RT", "AJ", "QP", "RNT", "RWT"):
            self.assertIn(key, names)

    def test_variable_info_structure(self):
        for name, info in self.plot_mod.VARIABLE_INFO.items():
            self.assertIn("label", info, f"{name} missing 'label'")
            self.assertIn("kind", info, f"{name} missing 'kind'")
            self.assertIn("dim", info, f"{name} missing 'dim'")
            self.assertIn(info["kind"], ("profile_1d", "profile_2d", "scalar"))
            self.assertIn(info["dim"], (0, 1, 2))

    def test_plot_unknown_variable_raises(self):
        with self.assertRaises(KeyError):
            self.plot_mod.plot("NOT_A_REAL_VAR", state=self._fake_state())

    def test_plot_invalid_output_raises(self):
        with self.assertRaises(ValueError):
            self.plot_mod.plot(
                "AJ", state=self._fake_state(), output="bogus",
            )

    def test_plot_requires_state_or_figure(self):
        with self.assertRaises(ValueError):
            self.plot_mod.plot("AJ")

    # --- rendering tests ---------------------------------------------
    def test_plot_return_mode_returns_figure(self):
        fig = self.plot_mod.plot(
            "AJ", state=self._fake_state(), output="return",
        )
        from matplotlib.figure import Figure
        self.assertIsInstance(fig, Figure)

    def test_plot_file_mode_writes_png(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "aj.png"
            out = self.plot_mod.plot(
                "AJ", state=self._fake_state(),
                output="file", format="png", path=str(target),
            )
            self.assertEqual(Path(out), target)
            self.assertTrue(target.exists())
            self.assertGreater(target.stat().st_size, 0)

    def test_plot_profile_2d_species_stacked(self):
        # RN is 2D (nrmax x nsmax). Make sure we don't blow up.
        fig = self.plot_mod.plot(
            "RN", state=self._fake_state(nr=5, ns=3), output="return",
        )
        from matplotlib.figure import Figure
        self.assertIsInstance(fig, Figure)

    def test_plot_alias_rnt_to_rn(self):
        # RNT is an alias of RN. Both paths should succeed without the
        # alias leaking into the figure title.
        fig = self.plot_mod.plot(
            "RNT", state=self._fake_state(), output="return",
        )
        from matplotlib.figure import Figure
        self.assertIsInstance(fig, Figure)

    def test_plot_scalar_draws_bar(self):
        # Scalars can't be 1D-plotted from a snapshot; the module falls
        # back to a single-bar chart so the caller still gets a figure.
        fig = self.plot_mod.plot(
            "WPT", state=self._fake_state(), output="return",
        )
        from matplotlib.figure import Figure
        self.assertIsInstance(fig, Figure)

    def test_plot_file_creates_parent_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "nested" / "out" / "rn.png"
            out = self.plot_mod.plot(
                "RN", state=self._fake_state(),
                output="file", format="png", path=str(target),
            )
            self.assertTrue(Path(out).exists())


if __name__ == "__main__":
    unittest.main()
