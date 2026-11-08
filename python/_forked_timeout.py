"""Make pytest-timeout fail the hung test under pytest-forked (#247).

pytest-forked runs each test in a forked child (``forked_run_report`` ->
``runner.runtestprotocol`` in the child) and forwards the child's reports.
pytest-timeout arms its timer in a ``pytest_runtest_protocol`` hookwrapper,
which executes in the **parent** around that fork-and-wait. With
``--timeout-method=signal`` the ``SIGALRM`` therefore fires in the parent
while it sits in ``waitpid``: ``Failed: Timeout`` is raised inside the
protocol hook, pytest reports ``INTERNALERROR`` and stops the session, the
hung child keeps running, and no test is marked failed. (``thread`` is no
better: the parent's watchdog calls ``os._exit`` on the parent.)

This plugin moves the timer into the child:

* ``pytest_timeout_set_timer`` / ``pytest_timeout_cancel_timer`` are
  ``firstresult`` hooks; a ``tryfirst`` implementation that returns ``True``
  for a forked item **in the parent process** stops pytest-timeout's own
  implementation, so the parent never arms anything.
* The settings pytest-timeout resolved for the item (marker over ini /
  command line) arrive as the ``settings`` argument of that parent-side
  call; they are stored on the item, which the forked child inherits.
* In the child, a timer is armed at the start of ``pytest_runtest_setup`` and
  cancelled at the end of ``pytest_runtest_teardown`` (both run in the child
  via ``runtestprotocol``; both wrappers are ``tryfirst`` = outermost, so
  other plugins' setup / teardown wrappers are inside the budget), so setup,
  call and teardown are covered by one budget of ``timeout`` seconds, as
  they are without ``--forked``. The child side goes through pytest-timeout's
  own ``pytest_timeout_set_timer``, so ``--timeout-method`` keeps its
  meaning; the expiry raises ``Failed: Timeout`` inside the child (signal)
  or ends the child with ``os._exit`` (thread), and either way pytest-forked
  reports it as that test's failure / crash and the session continues.

Items that are not forked are left to pytest-timeout unchanged.
``timeout_func_only`` is honoured: pytest-timeout then never calls
``set_timer`` at protocol level, nothing is stored, and its own
``pytest_runtest_call`` wrapper arms in the child. With pytest-timeout not
loaded (``-p no:timeout``, or autoload disabled without ``-p pytest_timeout``)
the two timeout hooks are ``optionalhook`` and the plugin is inert.
"""
from __future__ import annotations

import os

import pytest

_PARENT_PID: int | None = None
_SETTINGS_ATTR = "_forked_timeout_settings"
_ARMED_ATTR = "_forked_timeout_armed"


def _is_forked(item) -> bool:
    try:
        if item.config.getoption("forked"):
            return True
    except (ValueError, AttributeError):
        return False
    return item.get_closest_marker("forked") is not None


def _in_parent() -> bool:
    return _PARENT_PID is not None and os.getpid() == _PARENT_PID


def pytest_configure(config):
    global _PARENT_PID
    _PARENT_PID = os.getpid()


# ---- parent: never arm for a forked item ---------------------------------
# Implementations of hooks that pytest-timeout declares (pytest_addhooks);
# optionalhook so this module and the conftest load when that plugin is not
# registered (-p no:timeout, autoload disabled without -p pytest_timeout).

@pytest.hookimpl(tryfirst=True, optionalhook=True)
def pytest_timeout_set_timer(item, settings):
    if _in_parent() and _is_forked(item):
        # Keep what pytest-timeout resolved (marker / ini / CLI) for the
        # child, then stop the parent-side arming (firstresult hook).
        setattr(item, _SETTINGS_ATTR, settings)
        return True
    return None


@pytest.hookimpl(tryfirst=True, optionalhook=True)
def pytest_timeout_cancel_timer(item):
    if _in_parent() and _is_forked(item):
        return True
    return None


# ---- child: one budget across setup + call + teardown --------------------

@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_setup(item):
    if not _in_parent() and _is_forked(item):
        settings = getattr(item, _SETTINGS_ATTR, None)
        if settings is not None:
            item.ihook.pytest_timeout_set_timer(item=item, settings=settings)
            setattr(item, _ARMED_ATTR, True)
    yield


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_teardown(item, nextitem):
    # tryfirst = outermost wrapper: the cancel below runs after every other
    # teardown wrapper has finished, so those are inside the budget too.
    yield
    if getattr(item, _ARMED_ATTR, False):
        item.ihook.pytest_timeout_cancel_timer(item=item)
        setattr(item, _ARMED_ATTR, False)
