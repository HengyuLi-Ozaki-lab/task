"""Suite-wide pytest configuration for python/.

Installs the strict ``unittest.subTest`` override from ``_strict_subtest`` so
that a failing ``subTest`` block fails its test under ``pytest --forked`` too
(issue #241 -- pytest-forked drops the per-sub-case reports that pytest's
unittest support emits inside the forked child, so CI reported such tests as
passed), and ``_forked_timeout`` so that a hung test under ``--forked`` is
reported as that test's failure instead of aborting the whole session with
INTERNALERROR (issue #247 -- pytest-timeout armed its timer in the parent).

Discovery: pytest loads this file for any argument under ``python/`` when run
from the repository root (``pytest python/`` as well as a bare
``pytest python/totlib/tests/test_mono_routing.py``); ``pytest.ini`` at the
repository root keeps that true when pytest is started from a subdirectory.
"""
import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import _forked_timeout  # noqa: E402
import _strict_subtest  # noqa: E402


# Re-export the plugins' hooks so pluggy picks them up from this conftest.
def pytest_configure(config):
    _strict_subtest.pytest_configure(config)
    _forked_timeout.pytest_configure(config)


pytest_unconfigure = _strict_subtest.pytest_unconfigure
pytest_runtest_setup = _forked_timeout.pytest_runtest_setup
pytest_runtest_teardown = _forked_timeout.pytest_runtest_teardown
pytest_timeout_set_timer = _forked_timeout.pytest_timeout_set_timer      # optionalhook
pytest_timeout_cancel_timer = _forked_timeout.pytest_timeout_cancel_timer  # optionalhook
