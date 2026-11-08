"""Make ``unittest.TestCase.subTest`` failures fail the test under ``--forked``.

Why this exists (#241)
----------------------
``pytest-forked`` runs each test in a forked child and sends back only the
reports returned by ``runtestprotocol``.  unittest ``subTest`` outcomes are
reported separately, through ``pytest_runtest_logreport`` called *directly*
inside the child (pytest >= 9 does this in core; on older pytest the
``pytest-subtests`` plugin does), so those reports never reach the parent, and
the enclosing test -- whose own outcome is "passed" because ``subTest``
swallowed the assertion -- is all the parent sees.  Net effect:
``pytest --forked`` reports a test whose every assertion sits inside
``subTest`` as passed, no matter what.  Reproduced with pytest 9.1.1 /
pytest-forked 1.7.5, with and without pytest-subtests installed.

What it does
------------
``install()`` patches ``unittest.TestCase`` (and ``IsolatedAsyncioTestCase``,
which overrides the second method):

* ``subTest`` becomes a context manager that records each failing or skipped
  sub-case on the test instance (every sub-case still runs; a failure does
  not abort the loop; nested blocks merge their parameters, outer first).
* ``_callTestMethod`` (the hook ``TestCase.run`` uses to call the test body)
  raises, after the body returns, one ``AssertionError`` listing every failed
  sub-case (parameters + traceback), or ``unittest.SkipTest`` when every
  *leaf* sub-case (a block with no nested block inside it) was skipped and
  none failed.

Because that exception is raised *inside* unittest's own test-part executor
it is handled exactly like an assertion written directly in the test body:
pytest sees an ordinary failure (also in the forked child), ``xfail`` marks
and ``@unittest.expectedFailure`` keep their meaning, and ``--forked`` needs
no special support.  Raising from a pytest hook instead would not work:
unittest routes body-level ``skipTest()`` / ``fail()`` through pytest's result
protocol and pytest's unittest plugin replaces whatever the hook raised with
that outcome, erasing the sub-case failures.

If the test body itself raises after a sub-case failed, the two are combined
into one failure (the body exception is kept as the chained cause, the
sub-case failures are listed in the message) so nothing is hidden -- in
particular a ``skipTest()`` or ``pytest.skip()`` after a failed sub-case is a
failure, not a skip.  Other ``BaseException`` (pytest's ``Failed`` outcome,
``KeyboardInterrupt``, pytest-timeout's signal method) propagates unchanged
and the recorded sub-case failures are dropped with it; ``pytest.exit`` (which
subclasses ``Exception``) is re-raised from the sub-case context manager, not
recorded.

Known differences from stock unittest (none exercised in this repository):
``pytest.fail()`` / ``pytest.skip()`` inside a sub-case abort the loop instead
of being recorded as a sub-case outcome; a partially skipped test (some
sub-cases skipped, others passed) is reported as passed, with no per-sub-case
skip report; unittest's failure-vs-error distinction collapses into one
``AssertionError``.  Outside a patched ``_callTestMethod`` -- ``setUp`` /
``tearDown`` / cleanups, ``TestCase.debug()`` on Python < 3.10, or a
``TestCase`` subclass that overrides ``_callTestMethod`` itself -- ``subTest``
falls back to the stock implementation, i.e. the pre-#241 behaviour (reported
by pytest when not forked, lost under ``--forked``).

``python/conftest.py`` installs the override for the whole suite.  The
self-tests in ``python/tests/test_strict_subtest.py`` load it with
``-p _strict_subtest`` in a subprocess so the behaviour is verified
independently of conftest discovery.  Works with or without ``--forked`` and
with or without pytest-subtests.
"""
from __future__ import annotations

import contextlib
import traceback
import unittest

from _pytest.outcomes import Exit as _PytestExit
from _pytest.outcomes import Skipped as _PytestSkipped

_ATTR = "_strict_subtest_state"
_ARMED = "_strict_subtest_armed"
_MSG_UNSET = object()
_ORIGINAL_SUBTEST = unittest.TestCase.subTest
# ``_callTestMethod`` exists since Python 3.8; ``TestCase.run()`` calls it
# inside ``testPartExecutor``. ``IsolatedAsyncioTestCase`` overrides it, so it
# is patched separately. Other subclasses that override it are not covered
# (none in this repository).
_PATCHED_CLASSES = (unittest.TestCase, unittest.IsolatedAsyncioTestCase)
_ORIGINALS = {cls: cls.__dict__["_callTestMethod"] for cls in _PATCHED_CLASSES}


def _state(testcase) -> dict:
    return testcase.__dict__.setdefault(
        _ATTR, {"stack": [], "leaves": 0, "failures": [], "skips": []}
    )


def _label(stack) -> str:
    msg = None
    params: dict = {}
    for m, p, _ in stack:
        if m is not _MSG_UNSET:
            msg = m
        params.update(p)
    body = ", ".join(f"{k}={v!r}" for k, v in params.items()) or "<no params>"
    return f"[{msg}] {body}" if msg is not None else body


def _summary(kind: str, entries) -> str:
    n = len(entries)
    return (
        f"{n} subTest sub-case{'s' if n != 1 else ''} {kind} "
        f"(strict subTest, python/_strict_subtest.py, #241):\n\n"
        + "\n".join(entries)
    )


@contextlib.contextmanager
def strict_subtest(self, msg=_MSG_UNSET, **params):
    """Replacement for ``unittest.TestCase.subTest`` (see module doc)."""
    __tracebackhide__ = True
    if not self.__dict__.get(_ARMED):
        # Not inside a patched _callTestMethod (setUp/tearDown/cleanups,
        # debug(), a subclass overriding _callTestMethod): nobody would
        # finalize what we record, so keep stock unittest behaviour.
        kwargs = {} if msg is _MSG_UNSET else {"msg": msg}
        with _ORIGINAL_SUBTEST(self, **kwargs, **params):
            yield
        return
    state = _state(self)
    frame = [msg, params, False]  # msg, params, had_child
    if state["stack"]:
        state["stack"][-1][2] = True
    state["stack"].append(frame)
    label = _label(state["stack"])
    try:
        yield
    except unittest.SkipTest as exc:
        # unittest skips just this sub-case and carries on; so do we. A block
        # that skips itself counts as a sub-case outcome even if it had
        # nested blocks, so it is counted in "leaves" unconditionally.
        state["skips"].append(f"subTest({label}) skipped: {exc}")
        state["leaves"] += 1
    except _PytestExit:
        raise
    except Exception:
        state["failures"].append(
            f"subTest({label}) failed:\n" + "".join(traceback.format_exc())
        )
        if not frame[2]:
            state["leaves"] += 1
    else:
        # Only leaf blocks count towards "every sub-case was skipped"; a
        # block that merely contained nested blocks is not a sub-case.
        if not frame[2]:
            state["leaves"] += 1
    finally:
        state["stack"].pop()


def _finalize(self, exc):
    """Called by the ``_callTestMethod`` wrappers once the body has finished.

    Raises the aggregate outcome, or returns normally when the body's own
    exception ``exc`` should pass through untouched (the caller re-raises
    it with a bare ``raise`` so its traceback is unchanged).
    """
    __tracebackhide__ = True
    state = self.__dict__.pop(_ATTR, None)
    if exc is not None:
        if state and state["failures"] and (
            (isinstance(exc, Exception) and not isinstance(exc, _PytestExit))
            or isinstance(exc, _PytestSkipped)  # pytest.skip() must not hide failures
        ):
            # The body exception stays visible as the chained cause.
            raise AssertionError(
                f"test body raised {type(exc).__name__}: {exc}\n"
                f"-- after sub-case failures (see the chained exception above "
                f"for the body traceback):\n\n{_summary('failed', state['failures'])}"
            ) from exc
        return
    if state:
        if state["failures"]:
            raise AssertionError(_summary("failed", state["failures"]))
        if state["skips"] and len(state["skips"]) == state["leaves"]:
            raise unittest.SkipTest(_summary("skipped (all of them)", state["skips"]))


def _make_call_test_method(original):
    def strict_call_test_method(self, method):
        __tracebackhide__ = True
        self.__dict__[_ARMED] = True
        try:
            original(self, method)
        except BaseException as exc:
            self.__dict__.pop(_ARMED, None)
            _finalize(self, exc)  # raises the combined failure, or returns
            raise
        else:
            self.__dict__.pop(_ARMED, None)
            _finalize(self, None)

    return strict_call_test_method


_WRAPPERS = {cls: _make_call_test_method(orig) for cls, orig in _ORIGINALS.items()}


def install() -> None:
    """Patch ``unittest.TestCase`` / ``IsolatedAsyncioTestCase`` (idempotent)."""
    unittest.TestCase.subTest = strict_subtest
    for cls, wrapper in _WRAPPERS.items():
        cls._callTestMethod = wrapper


def uninstall() -> None:
    unittest.TestCase.subTest = _ORIGINAL_SUBTEST
    for cls, original in _ORIGINALS.items():
        cls._callTestMethod = original


def is_installed() -> bool:
    return unittest.TestCase.subTest is strict_subtest and all(
        cls.__dict__.get("_callTestMethod") is wrapper
        for cls, wrapper in _WRAPPERS.items()
    )


def pytest_configure(config):
    install()


def pytest_unconfigure(config):
    uninstall()
