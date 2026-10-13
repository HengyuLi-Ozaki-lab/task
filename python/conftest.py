"""Suite-wide pytest configuration for python/.

Installs the strict ``unittest.subTest`` override from ``_strict_subtest`` so
that a failing ``subTest`` block fails its test under ``pytest --forked`` too
(issue #241 -- pytest-forked drops the per-sub-case reports that pytest's
unittest support emits inside the forked child, so CI reported such tests as
passed).

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

import _strict_subtest  # noqa: E402

# Re-export the plugin's hooks so pluggy picks them up from this conftest.
pytest_configure = _strict_subtest.pytest_configure
pytest_unconfigure = _strict_subtest.pytest_unconfigure
