"""Self-tests for the forked-timeout plugin (#247).

Each case runs a child pytest with plugin autoload disabled and the plugins
loaded explicitly, so the behaviour is verified independently of conftest
discovery. The session must survive the hang and report it against the
hung test; the tests before and after it must still run.
"""
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

PYTHON_DIR = pathlib.Path(__file__).resolve().parents[1]

_HANG_IN_CALL = '''
import time
def test_before():
    assert True
def test_hang():
    time.sleep(8)
def test_after():
    assert True
'''

# Same shape with a short hang: the orphaned child of the no-plugin case
# holds the pipe until its sleep ends, so keep that one brief.
_SHORT_HANG_IN_CALL = _HANG_IN_CALL.replace("time.sleep(8)", "time.sleep(4)")

_HANG_IN_SETUP = '''
import time, unittest
class T(unittest.TestCase):
    def setUp(self):
        time.sleep(8)
    def test_never_reached(self):
        assert True
def test_after():
    assert True
'''

_HANG_IN_FIXTURE = '''
import time, pytest
@pytest.fixture
def slow():
    time.sleep(8)
    yield
def test_uses_slow(slow):
    assert True
def test_after():
    assert True
'''

_HANG_IN_TEARDOWN = '''
import time, pytest
@pytest.fixture
def slow_exit():
    yield
    time.sleep(8)
def test_uses_slow_exit(slow_exit):
    assert True
def test_after():
    assert True
'''

_MARKER_OVERRIDE = '''
import time, pytest
@pytest.mark.timeout(1)
def test_short_budget():
    time.sleep(8)
def test_after():
    assert True
'''

_FAST = '''
import time
def test_quick():
    time.sleep(0.2)
'''

# A conftest whose teardown hookwrapper hangs after yield: the child timer
# must still be armed around it (our teardown wrapper is outermost).
_HANGING_TEARDOWN_WRAPPER_CONFTEST = '''
import time, pytest
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_teardown(item, nextitem):
    yield
    if item.name == "test_slow_plugin_teardown":
        time.sleep(8)
'''
_WITH_PLUGIN_TEARDOWN = '''
def test_slow_plugin_teardown():
    assert True
def test_after():
    assert True
'''


def _run_child(source, *extra, forked=True, plugin=True, timeout_plugin=True,
               conftest=None):
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = pathlib.Path(tmpdir) / "test_case.py"
        test_file.write_text(source)
        if conftest is not None:
            (pathlib.Path(tmpdir) / "conftest.py").write_text(conftest)
        env = dict(os.environ)
        parts = [str(PYTHON_DIR)] + [p for p in env.get("PYTHONPATH", "").split(os.pathsep) if p]
        env["PYTHONPATH"] = os.pathsep.join(parts)
        env.pop("PYTEST_ADDOPTS", None)
        env.pop("PYTEST_PLUGINS", None)
        env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
        cmd = [sys.executable, "-m", "pytest", "-p", "no:cacheprovider",
               "-q", "-s", str(test_file), *extra]
        if timeout_plugin:
            cmd += ["-p", "pytest_timeout"]
        if plugin:
            cmd += ["-p", "_forked_timeout"]
        if forked:
            cmd += ["-p", "pytest_forked", "--forked"]
        return subprocess.run(
            cmd, cwd=tmpdir, env=env, capture_output=True, text=True, timeout=60,
        )


_SIGNAL = ("--timeout=2", "--timeout-method=signal")
_THREAD = ("--timeout=2", "--timeout-method=thread")


class TestInstalledInThisSession(unittest.TestCase):
    def test_plugin_is_loaded(self):
        import _forked_timeout
        self.assertIsNotNone(
            _forked_timeout._PARENT_PID,
            "python/conftest.py did not configure the forked-timeout plugin (#247)",
        )


class TestSubprocess(unittest.TestCase):
    def _assert_hang_attributed(self, res, nodeid: str):
        # A hang in the call phase is always a failure of that test.
        last = res.stdout.strip().splitlines()[-1] if res.stdout.strip() else ""
        self.assertNotIn("INTERNALERROR", res.stdout + res.stderr, res.stdout + res.stderr)
        self.assertNotEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn(nodeid, res.stdout, res.stdout)
        self.assertIn("1 failed, 2 passed", last, res.stdout)

    def test_without_plugin_the_session_aborts(self):
        # The hazard itself (#247): documents what this plugin prevents.
        res = _run_child(_SHORT_HANG_IN_CALL, *_SIGNAL, plugin=False)
        self.assertIn("INTERNALERROR", res.stdout + res.stderr)
        self.assertNotIn("test_after", res.stdout)

    def test_conftest_path_as_in_ci(self):
        # The production path: no -p, plugin autoload on, the hang file
        # placed under python/tests/ so python/conftest.py is discovered.
        here = pathlib.Path(__file__).resolve().parent
        with tempfile.TemporaryDirectory(dir=here, prefix="_tmp247_") as tmpdir:
            test_file = pathlib.Path(tmpdir) / "test_case.py"
            test_file.write_text(_HANG_IN_CALL)
            env = dict(os.environ)
            env.pop("PYTEST_ADDOPTS", None)
            env.pop("PYTEST_DISABLE_PLUGIN_AUTOLOAD", None)
            res = subprocess.run(
                [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "-q",
                 str(test_file), "--forked", *_SIGNAL],
                cwd=PYTHON_DIR.parent, env=env, capture_output=True, text=True, timeout=60,
            )
        self._assert_hang_attributed(res, "test_hang")
        self.assertIn("Timeout", res.stdout)

    def test_hang_in_call_fails_that_test_signal(self):
        res = _run_child(_HANG_IN_CALL, *_SIGNAL)
        self._assert_hang_attributed(res, "test_hang")
        self.assertIn("Timeout", res.stdout)

    def test_hang_in_call_fails_that_test_thread(self):
        res = _run_child(_HANG_IN_CALL, *_THREAD)
        self._assert_hang_attributed(res, "test_hang")

    def test_hang_in_unittest_setup_is_attributed(self):
        res = _run_child(_HANG_IN_SETUP, *_SIGNAL)
        self.assertNotIn("INTERNALERROR", res.stdout + res.stderr)
        self.assertIn("test_never_reached", res.stdout)
        last = res.stdout.strip().splitlines()[-1]
        # unittest's setUp runs inside the call phase: a failure
        self.assertIn("1 failed, 1 passed", last, last)

    def test_hang_in_fixture_setup_is_attributed(self):
        res = _run_child(_HANG_IN_FIXTURE, *_SIGNAL)
        self.assertNotIn("INTERNALERROR", res.stdout + res.stderr)
        self.assertIn("test_uses_slow", res.stdout)
        last = res.stdout.strip().splitlines()[-1]
        # a fixture setup hang is an error of that test
        self.assertIn("1 passed, 1 error", last, last)

    def test_hang_in_fixture_teardown_is_attributed(self):
        res = _run_child(_HANG_IN_TEARDOWN, *_SIGNAL)
        self.assertNotIn("INTERNALERROR", res.stdout + res.stderr)
        self.assertIn("test_uses_slow_exit", res.stdout)
        last = res.stdout.strip().splitlines()[-1]
        # the test itself passed; its teardown is reported as an error
        self.assertIn("2 passed, 1 error", last, last)

    def test_timeout_marker_is_honoured_in_the_child(self):
        res = _run_child(_MARKER_OVERRIDE, "--timeout=30", "--timeout-method=signal")
        self.assertNotIn("INTERNALERROR", res.stdout + res.stderr)
        self.assertIn("test_short_budget", res.stdout)
        last = res.stdout.strip().splitlines()[-1]
        self.assertIn("1 failed", last, last)
        self.assertIn("1 passed", last, last)

    def test_hang_in_another_teardown_wrapper_is_inside_the_budget(self):
        res = _run_child(_WITH_PLUGIN_TEARDOWN, *_SIGNAL,
                         conftest=_HANGING_TEARDOWN_WRAPPER_CONFTEST)
        self.assertNotIn("INTERNALERROR", res.stdout + res.stderr)
        self.assertIn("test_slow_plugin_teardown", res.stdout)
        last = res.stdout.strip().splitlines()[-1]
        self.assertIn("2 passed, 1 error", last, last)

    def test_loads_without_the_timeout_plugin(self):
        # pytest-timeout installed but not loaded: the two timeout hooks are
        # optionalhook, so the plugin registers and is inert.
        res = _run_child(_FAST, timeout_plugin=False)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertNotIn("PluginValidationError", res.stdout + res.stderr)
        self.assertIn("1 passed", res.stdout)

    def test_fast_test_passes_and_timer_is_cancelled(self):
        res = _run_child(_FAST, *_SIGNAL)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("1 passed", res.stdout)

    def test_func_only_is_left_to_pytest_timeout(self):
        res = _run_child(_HANG_IN_CALL, *_SIGNAL, "-o", "timeout_func_only=true")
        self._assert_hang_attributed(res, "test_hang")

    def test_not_forked_is_unchanged(self):
        res = _run_child(_HANG_IN_CALL, *_SIGNAL, forked=False)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("1 failed, 2 passed", res.stdout)
        self.assertIn("Timeout", res.stdout)


if __name__ == "__main__":
    unittest.main()
