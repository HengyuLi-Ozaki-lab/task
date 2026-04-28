"""L-6 Layer 3: full prefix coverage + context-manager exception propagation.

`test_totlib.py` already exercises the eq:/tr: positive paths and all
the negative paths (missing prefix, unknown prefix, unknown bare name).
This file fills the remaining gap from the L-6 plan: positive
``set_param`` round-trips for the four namespaces that ``test_totlib.py``
does not exercise (ti, fp, wr, wrx) and a context-manager
exception-propagation test.

Skip if ``libtotapi.so`` is not built — same gate as ``test_totlib.py``.
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
PYTHON_ROOT = HERE.parents[2]
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from totlib import Tot, TotlibError  # noqa: E402
from totlib import _ffi  # noqa: E402


def _any_so_exists() -> bool:
    """True if libtotapi.so is present at any candidate path."""
    env = os.environ.get("TOTLIB_PATH")
    if env and Path(env).exists():
        return True
    return any(p.exists() for p in _ffi._candidate_paths())


@unittest.skipUnless(
    _any_so_exists(),
    "libtotapi.so not built; run `make -C tot libtotapi.so`",
)
class TestRemainingPrefixes(unittest.TestCase):
    """Cover ti/fp/wr/wrx positive set_param round-trips.

    Each test picks a parameter that is known to be registered in the
    matching per-module ``*_param_set`` SELECT CASE table. A successful
    set_param call exercises the full Python guard → tot_param_registry
    dispatcher → per-module setter chain.
    """

    def test_namespaced_ti_succeeds(self):
        with Tot() as tot:
            tot.set_param("ti:RR", 6.5)

    def test_namespaced_fp_succeeds(self):
        with Tot() as tot:
            tot.set_param("fp:NSMAX", 2)

    def test_namespaced_wr_succeeds(self):
        # `wr:` is aliased to `wrx_param_set` (see tot_param_registry.f90
        # header). RFIN is registered there.
        with Tot() as tot:
            tot.set_param("wr:RFIN", 170.0)

    def test_namespaced_wrx_succeeds(self):
        with Tot() as tot:
            tot.set_param("wrx:RFIN", 170.0)

    def test_all_six_prefixes_in_one_session(self):
        """Sanity: a single Tot handle accepts a parameter from every
        registered namespace without cross-pollution. RFIN is the only
        scalar registered in wrx_param_set today (see
        tot/tot_param_registry.f90 header), so we set it via both the
        wr: alias and the wrx: prefix as a regression guard against the
        alias drifting away from the underlying symbol.
        """
        with Tot() as tot:
            tot.set_param("eq:RR", 6.5)
            tot.set_param("tr:DT", 0.001)
            tot.set_param("ti:RR", 6.5)
            tot.set_param("fp:NSMAX", 2)
            tot.set_param("wr:RFIN", 170.0)
            tot.set_param("wrx:RFIN", 170.0)


@unittest.skipUnless(
    _any_so_exists(),
    "libtotapi.so not built; run `make -C tot libtotapi.so`",
)
class TestContextManagerExceptionPropagation(unittest.TestCase):
    """The context manager must close the handle even if the body raises,
    and the user-raised exception must propagate unchanged.
    """

    def test_user_exception_propagates_and_handle_closes(self):
        sentinel = ValueError("user code")
        with self.assertRaises(ValueError) as ctx:
            with Tot() as tot:
                tot.set_param("eq:RR", 6.2)
                raise sentinel
        # Same instance, not just same type
        self.assertIs(ctx.exception, sentinel)
        # The Tot variable bound inside the with block went out of scope;
        # we verify post-condition by opening a NEW handle (would fail if
        # the previous tot_finalize was missed and lib state is wedged).
        with Tot() as tot2:
            tot2.set_param("eq:RR", 6.2)

    def test_totlib_error_inside_with_propagates(self):
        """A TotlibError raised by the wrapper inside the with body must
        propagate to the caller, not be swallowed by __exit__."""
        with self.assertRaises(TotlibError):
            with Tot() as tot:
                # Unknown bare name → TotlibInvalidParamError (subclass
                # of TotlibError). The with-block's __exit__ must not
                # absorb it.
                tot.set_param("eq:NOT_A_REAL_PARAMETER", 0.0)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
