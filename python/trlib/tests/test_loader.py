"""Unit tests for :mod:`trlib.loader`.

Pure parsing / application tests — libtrapi.so is not needed because
we use a :class:`_FakeTrlib` double to record calls.
"""
from __future__ import annotations

import io
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
PYTHON_ROOT = HERE.parents[2]
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from trlib import loader  # noqa: E402


class _FakeTrlib:
    """Record set_param / set_param_str calls for assertion.

    The loader shouldn't care that this isn't a real :class:`Trlib`; it
    only touches ``set_param`` / ``set_param_str`` / ``get_state``.
    """

    def __init__(self):
        self.scalar_calls = []
        self.string_calls = []
        self.closed = False

    def set_param(self, name, value):
        self.scalar_calls.append((name, value))

    def set_param_str(self, name, value):
        self.string_calls.append((name, value))

    def get_state(self):
        # Minimal stand-in so run_plots can iterate; the real plot call
        # path is exercised in tests/test_plot.py.
        raise NotImplementedError


_SAMPLE_TOML = textwrap.dedent("""
    [module]
    name = "tr"
    ntmax = 42

    [scalars]
    RR = 3.0
    NSMAX = 4

    [arrays]
    PN = [0.7, 0.315, 0.315, 0.035]
    PA = { 2 = 1.0 }

    [strings]
    KNAMEQ = "eqdata.ITER"

    [[plots]]
    variable = "RNT"
    output = "file"
    format = "png"
    path = "./plots/rnt.png"

    [[plots]]
    variable = "AJ"
    output = "return"
""").strip()


class TestLoadConfig(unittest.TestCase):

    def test_parse_inline_string(self):
        cfg = loader.load_config(_SAMPLE_TOML)
        self.assertEqual(cfg["module"]["name"], "tr")
        # ntmax alias propagates into NTMAX scalar.
        self.assertEqual(cfg["scalars"]["NTMAX"], 42)
        self.assertEqual(cfg["scalars"]["RR"], 3.0)
        self.assertEqual(cfg["arrays"]["PN"][0], 0.7)
        self.assertEqual(cfg["strings"]["KNAMEQ"], "eqdata.ITER")
        self.assertEqual(len(cfg["plots"]), 2)
        self.assertEqual(cfg["plots"][0]["variable"], "RNT")

    def test_parse_bytes_stream(self):
        buf = io.BytesIO(_SAMPLE_TOML.encode("utf-8"))
        cfg = loader.load_config(buf)
        self.assertEqual(cfg["module"]["name"], "tr")

    def test_parse_file_path(self):
        with tempfile.NamedTemporaryFile(
            "w", suffix=".toml", delete=False, encoding="utf-8"
        ) as fh:
            fh.write(_SAMPLE_TOML)
            tmp = Path(fh.name)
        try:
            cfg = loader.load_config(tmp)
            self.assertEqual(cfg["scalars"]["RR"], 3.0)
        finally:
            tmp.unlink()

    def test_ntmax_alias_does_not_overwrite_explicit_ntmax(self):
        raw = textwrap.dedent("""
            [module]
            ntmax = 10

            [scalars]
            NTMAX = 99
        """).strip()
        cfg = loader.load_config(raw)
        self.assertEqual(cfg["scalars"]["NTMAX"], 99)

    def test_missing_sections_default_empty(self):
        cfg = loader.load_config("[module]\nname='tr'\n")
        self.assertEqual(cfg["scalars"], {})
        self.assertEqual(cfg["arrays"], {})
        self.assertEqual(cfg["strings"], {})
        self.assertEqual(cfg["plots"], [])

    def test_singular_plot_section(self):
        raw = textwrap.dedent("""
            [plot]
            variable = "RT"
            output = "return"
        """).strip()
        cfg = loader.load_config(raw)
        self.assertEqual(len(cfg["plots"]), 1)
        self.assertEqual(cfg["plots"][0]["variable"], "RT")


class TestApplyConfig(unittest.TestCase):

    def test_apply_scalars_arrays_strings(self):
        cfg = loader.load_config(_SAMPLE_TOML)
        fake = _FakeTrlib()
        loader.apply_config(fake, cfg)

        # Strings applied first.
        self.assertEqual(fake.string_calls, [("KNAMEQ", "eqdata.ITER")])

        # Scalars expanded.
        scalar_names = [n for n, _ in fake.scalar_calls]
        self.assertIn("RR", scalar_names)
        self.assertIn("NSMAX", scalar_names)
        self.assertIn("NTMAX", scalar_names)

        # Array with 1-origin index.
        self.assertIn(("PN[1]", 0.7), fake.scalar_calls)
        self.assertIn(("PN[4]", 0.035), fake.scalar_calls)
        # Sparse dict form: only PA[2] set.
        pa_keys = [n for n, _ in fake.scalar_calls if n.startswith("PA[")]
        self.assertEqual(pa_keys, ["PA[2]"])

    def test_apply_rejects_unsupported_array_shape(self):
        cfg = {
            "strings": {},
            "scalars": {},
            "arrays": {"PN": "not a list"},
            "plots": [],
        }
        fake = _FakeTrlib()
        with self.assertRaises(ValueError):
            loader.apply_config(fake, cfg)


class TestSampleTomlFiles(unittest.TestCase):
    """Make sure the shipped samples parse and include plot specs."""

    SAMPLES = PYTHON_ROOT / "trlib" / "samples"

    def test_iter01_parses(self):
        cfg = loader.load_config(self.SAMPLES / "iter01.toml")
        self.assertEqual(cfg["module"]["name"], "tr")
        self.assertEqual(cfg["scalars"]["NSMAX"], 4)
        self.assertEqual(len(cfg["arrays"]["PN"]), 4)
        self.assertTrue(any(p.get("variable") == "RNT" for p in cfg["plots"]))

    def test_tst2_parses(self):
        cfg = loader.load_config(self.SAMPLES / "tst2.toml")
        self.assertEqual(cfg["module"]["name"], "tr")
        self.assertEqual(cfg["scalars"]["NSMAX"], 2)
        # Sparse dict form preserved.
        self.assertEqual(cfg["arrays"]["PA"], {"2": 1.0})
        self.assertTrue(cfg["plots"])


if __name__ == "__main__":
    unittest.main()
