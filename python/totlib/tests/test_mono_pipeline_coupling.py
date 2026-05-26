"""Layer-D — TotPipeline rule firing on the mono image.

Phase 2c PR-B (#208). Drives eq -> tr through
TotPipeline.run_pipeline on the mono image and asserts the
("eq","tr") verify rule fires (mono) / stays dormant (default).

Process isolation: pytest.mark.forked module-level. The mono .so
carries module-level state across calls; without forking,
tot/eq/tr init state from a prior test could leak into this
test's pipeline.

Spec: docs/superpowers/specs/2026-05-26-l7b-ii-phase-2c-prb-rule-activation-design.md
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import pytest

pytestmark = [pytest.mark.forked]

HERE = Path(__file__).resolve()
REPO = HERE.parents[3]
PYTHON_ROOT = REPO / "python"
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

_EQDATA_FIXTURE = (
    REPO / "python" / "totlib" / "tests" / "fixtures" / "eqdata-HT6M"
)


def _mono_path() -> str:
    p = os.environ.get("MONO_LIB_PATH", "")
    return p if p and os.path.exists(p) else ""


@unittest.skipUnless(
    _mono_path() and _EQDATA_FIXTURE.exists(),
    "MONO_LIB_PATH and/or eqdata-HT6M fixture missing; "
    "build with `make -C tot libtotapi_mono.so` and ensure PR #199 "
    "fixture is in place",
)
class TestEqToTrPipelineCoupling(unittest.TestCase):
    """Layer-D happy path: pipeline runs eq -> tr on mono, the
    ("eq","tr") verify rule fires, broker round-trip succeeds.
    """

    def test_eq_to_tr_bpsd_pipeline_succeeds_on_mono(self):
        import _runtime_mode
        from totlib import TotPipeline

        _runtime_mode.mono_lib_path.cache_clear()
        result = None
        with tempfile.TemporaryDirectory(prefix="prb_") as td:
            shutil.copy2(_EQDATA_FIXTURE, Path(td) / "eqdata-HT6M")
            prev = os.getcwd()
            os.chdir(td)
            try:
                with TotPipeline() as p:
                    p.set_param("eq:MODELG", 3.0)
                    p.set_param("eq:KNAMEQ", "eqdata-HT6M")
                    result = p.run_pipeline([
                        ("eq", {"mode": 1}),
                        ("tr", {"ntmax": 1}),
                    ])
            finally:
                os.chdir(prev)

        # Assertions OUTSIDE the `with TotPipeline()` block (Codex
        # 2026-05-26 LOW-5: a __exit__ failure should not be able
        # to mask the assertion).
        self.assertIsNotNone(result, "run_pipeline returned None")
        tr_step = result.last("tr")
        self.assertIn(
            "eq -> tr BPSD broker round-trip",
            " ".join(tr_step.coupling_applied),
            f"verify rule did not fire; coupling_applied="
            f"{tr_step.coupling_applied}",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
