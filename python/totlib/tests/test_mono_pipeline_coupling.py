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


def _default_per_module_so_present() -> bool:
    """Return True iff every per-module .so the negative test
    actually loads via the resolution chain exists at its default
    repo path. eqlib/trlib/totlib wrappers each look in
    <repo>/<mod>/lib<mod>api.so (priority 2 in PR-A's spec §D-5),
    so we check those directly. Per Codex 2026-05-26 spec round-3
    review, TOTLIB_PATH is NOT included here: eqlib and trlib do
    not honor it (they use EQLIB_PATH / TRLIB_PATH respectively),
    so gating on it would either over-skip (false-negative on
    TOTLIB_PATH-only setups) or under-cover (false-positive when
    eq/tr .so are missing).
    """
    return all(
        (REPO / mod / f"lib{name}.so").exists()
        for mod, name in (
            ("eq", "eqapi"),
            ("tr", "trapi"),
            ("tot", "totapi"),
        )
    )


@unittest.skipUnless(
    _default_per_module_so_present() and _EQDATA_FIXTURE.exists(),
    "per-module .so (eq/libeqapi.so, tr/libtrapi.so, "
    "tot/libtotapi.so) and/or eqdata-HT6M fixture missing; "
    "build via setup.sh or `make -C <mod> lib<mod>api.so`",
)
class TestEqToTrRuleDormantOnDefault(unittest.TestCase):
    """Layer-D negative path: rule must NOT fire on the default
    per-module image even though _MONO_ONLY_RULES is now populated.

    Pinned per Codex 2026-05-26 design review MED-6: if a future
    refactor of _detect_mono() or _build_active_rules() silently
    activates the overlay on non-mono, this test catches it.
    """

    def test_eq_to_tr_rule_dormant_on_default(self):
        import _runtime_mode
        from totlib import TotPipeline

        # Unset MONO_LIB_PATH so the wrappers route to per-module
        # .so files via their priority-1 env vars (EQLIB_PATH /
        # TRLIB_PATH / TOTLIB_PATH) or priority-2 repo defaults.
        # _detect_mono() reads tot_is_mono() from the totlib
        # wrapper's loaded image, which is the default
        # libtotapi.so, returning 0 — so the overlay stays inactive.
        # Defensive: also pop the per-module env vars (Codex 2026-05-26
        # cumulative review LOW-1). EQLIB_PATH / TRLIB_PATH would route
        # eqlib / trlib away from the repo-default per-module .so files
        # we just asserted exist, defeating the test's intent.
        original_mono = os.environ.pop("MONO_LIB_PATH", None)
        original_eqlib = os.environ.pop("EQLIB_PATH", None)
        original_trlib = os.environ.pop("TRLIB_PATH", None)
        _runtime_mode.mono_lib_path.cache_clear()

        result = None
        try:
            with tempfile.TemporaryDirectory(prefix="prb_neg_") as td:
                shutil.copy2(_EQDATA_FIXTURE, Path(td) / "eqdata-HT6M")
                prev = os.getcwd()
                os.chdir(td)
                try:
                    with TotPipeline() as p:
                        p.set_param("eq:MODELG", 3.0)
                        p.set_param("eq:KNAMEQ", "eqdata-HT6M")
                        # IMPORTANT: this is expected to SUCCEED.
                        # On default per-module .so, eq's BPSD push
                        # lands in libeqapi's private storage; tr
                        # reads from libtrapi's private storage. The
                        # rule MUST stay dormant or the pipeline
                        # would fail for the wrong reason (the
                        # verify would return False).
                        result = p.run_pipeline([
                            ("eq", {"mode": 1}),
                            ("tr", {"ntmax": 1}),
                        ])
                finally:
                    os.chdir(prev)
        finally:
            if original_mono is not None:
                os.environ["MONO_LIB_PATH"] = original_mono
            if original_eqlib is not None:
                os.environ["EQLIB_PATH"] = original_eqlib
            if original_trlib is not None:
                os.environ["TRLIB_PATH"] = original_trlib
            _runtime_mode.mono_lib_path.cache_clear()

        self.assertIsNotNone(result, "run_pipeline returned None")
        tr_step = result.last("tr")
        self.assertNotIn(
            "eq -> tr BPSD broker round-trip",
            " ".join(tr_step.coupling_applied),
            f"rule should NOT fire on default per-module image; "
            f"coupling_applied={tr_step.coupling_applied}",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
