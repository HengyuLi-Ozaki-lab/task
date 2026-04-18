"""Smoke tests for ``python -m trlib``.

The full library run is gated on libtrapi.so being present; the
``--dry-run`` and ``--help`` paths are always exercised.
"""
from __future__ import annotations

import io
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve()
PYTHON_ROOT = HERE.parents[2]
REPO = HERE.parents[3]
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from trlib import __main__ as trlib_main  # noqa: E402

DEFAULT_SO = REPO / "tr" / "libtrapi.so"
SAMPLE_ITER01 = PYTHON_ROOT / "trlib" / "samples" / "iter01.toml"
SAMPLE_TST2 = PYTHON_ROOT / "trlib" / "samples" / "tst2.toml"


class TestMainCli(unittest.TestCase):

    def test_help_exits_zero(self):
        # argparse exits with SystemExit(0) on --help.
        buf = io.StringIO()
        with self.assertRaises(SystemExit) as cm, redirect_stdout(buf):
            trlib_main.main(["--help"])
        self.assertEqual(cm.exception.code, 0)
        out = buf.getvalue()
        self.assertIn("python -m trlib", out)
        self.assertIn("--dry-run", out)

    def test_missing_config_returns_2(self):
        buf = io.StringIO()
        with redirect_stderr(buf):
            rc = trlib_main.main(["/no/such/path.toml"])
        self.assertEqual(rc, 2)
        self.assertIn("config not found", buf.getvalue())

    def test_dry_run_iter01_returns_0(self):
        out = io.StringIO()
        with redirect_stdout(out):
            rc = trlib_main.main([str(SAMPLE_ITER01), "--dry-run"])
        self.assertEqual(rc, 0)
        text = out.getvalue()
        self.assertIn("module: tr", text)
        self.assertIn("NTMAX", text)
        self.assertIn("--dry-run", text)

    def test_dry_run_tst2_returns_0(self):
        out = io.StringIO()
        with redirect_stdout(out):
            rc = trlib_main.main([str(SAMPLE_TST2), "--dry-run"])
        self.assertEqual(rc, 0)

    def test_ntmax_override_visible_in_summary(self):
        out = io.StringIO()
        with redirect_stdout(out):
            rc = trlib_main.main(
                [str(SAMPLE_TST2), "--dry-run", "--ntmax", "7"]
            )
        self.assertEqual(rc, 0)
        self.assertIn("NTMAX:  7", out.getvalue())

    def test_no_plots_zeroes_plot_count(self):
        out = io.StringIO()
        with redirect_stdout(out):
            rc = trlib_main.main(
                [str(SAMPLE_ITER01), "--dry-run", "--no-plots"]
            )
        self.assertEqual(rc, 0)
        self.assertIn("plots:   0", out.getvalue())

    def test_malformed_config_returns_2(self):
        import tempfile
        with tempfile.NamedTemporaryFile(
            "w", suffix=".toml", delete=False, encoding="utf-8"
        ) as fh:
            fh.write("this is = not [valid] = toml\n")
            tmp = Path(fh.name)
        try:
            buf = io.StringIO()
            with redirect_stderr(buf):
                rc = trlib_main.main([str(tmp)])
            self.assertEqual(rc, 2)
            self.assertIn("failed to parse", buf.getvalue())
        finally:
            tmp.unlink()


@unittest.skipUnless(
    DEFAULT_SO.exists(),
    f"libtrapi.so not built at {DEFAULT_SO}; run `make -C tr libtrapi.so`",
)
class TestMainLibrary(unittest.TestCase):

    def test_iter01_full_run_returns_0(self):
        # Disable plots so the test doesn't depend on filesystem write
        # permissions to ./plots/. The library path itself is the value
        # we want to exercise here.
        rc = trlib_main.main(
            [str(SAMPLE_ITER01), "--no-plots", "--ntmax", "0"]
        )
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
