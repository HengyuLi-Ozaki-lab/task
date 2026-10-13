"""Self-tests for the strict subTest override (#241).

Two layers:

* ``TestInstalledInThisSession`` guards conftest discovery: if a future layout
  change stops ``python/conftest.py`` from loading, this fails.
* ``TestSubprocess`` runs a child pytest with plugin autoload disabled and the
  plugin loaded explicitly (``-p _strict_subtest``), so the behaviour is
  verified independently of conftest discovery and of whatever other plugins
  happen to be installed.  Cases that matter for CI run under ``--forked``.
"""
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

PYTHON_DIR = pathlib.Path(__file__).resolve().parents[1]

_FAILING = '''
import unittest
class T(unittest.TestCase):
    def test_all_in_subtests(self):
        for n in (1, 2, 3):
            with self.subTest(n=n):
                self.assertEqual(n, 2)
'''

_SKIP_ONE = '''
import unittest
class T(unittest.TestCase):
    def test_skip_inside_subtest(self):
        seen = []
        for n in (1, 2, 3):
            with self.subTest(n=n):
                seen.append(n)
                if n == 2:
                    self.skipTest("skip this sub-case only")
        self.assertEqual(seen, [1, 2, 3])
'''

_SKIP_ALL = '''
import unittest
class T(unittest.TestCase):
    def test_all_skipped(self):
        for n in (1, 2):
            with self.subTest(n=n):
                self.skipTest("fixture missing")
'''

_SKIP_AFTER_FAILURE = '''
import unittest
class T(unittest.TestCase):
    def test_skip_after_failed_subcase(self):
        with self.subTest(n=1):
            self.assertEqual(1, 2)
        self.skipTest("late skip must not hide the failure")
'''

_LATER_EXCEPTION = '''
import unittest
class T(unittest.TestCase):
    def test_later_error(self):
        with self.subTest(n=1):
            self.assertEqual(1, 2)
        raise RuntimeError("later error wins")
'''

_TIMEOUT_AFTER_FAILURE = '''
import time, unittest
class T(unittest.TestCase):
    def test_hang_after_failure(self):
        with self.subTest(n=1):
            self.assertEqual(1, 2)
        time.sleep(30)
'''

_PYTEST_EXIT = '''
import unittest, pytest
class T(unittest.TestCase):
    def test_exit(self):
        with self.subTest(n=1):
            pytest.exit("stop now")
        print("SHOULD-NOT-RUN")
'''

_EXIT_AFTER_FAILURE = '''
import unittest, pytest
class T(unittest.TestCase):
    def test_exit_after_failure(self):
        with self.subTest(n=1):
            self.assertEqual(1, 2)
        with self.subTest(n=2):
            pytest.exit("stop now")
    def test_second(self):
        print("SHOULD-NOT-RUN")
'''

_NESTED_ALL_SKIPPED = '''
import unittest
class T(unittest.TestCase):
    def test_nested_all_skipped(self):
        for outer in (1, 2):
            with self.subTest(outer=outer):
                with self.subTest(inner=0):
                    self.skipTest("no fixture")
'''

_ASYNC = '''
import unittest
class T(unittest.IsolatedAsyncioTestCase):
    async def test_async_subtests(self):
        for n in (1, 2):
            with self.subTest(n=n):
                self.assertEqual(n, 1)
'''

_PYTEST_SKIP_AFTER_FAILURE = '''
import unittest, pytest
class T(unittest.TestCase):
    def test_pytest_skip_after_failed_subcase(self):
        with self.subTest(n=1):
            self.assertEqual(1, 2)
        pytest.skip("late pytest.skip must not hide the failure")
'''

_TEARDOWN_SUBTEST = '''
import unittest
class T(unittest.TestCase):
    def tearDown(self):
        with self.subTest(phase="teardown"):
            self.assertTrue(False)
    def test_body_ok(self):
        pass
'''

_NESTED = '''
import unittest
class T(unittest.TestCase):
    def test_nested(self):
        with self.subTest("outer msg", outer=1):
            with self.subTest(inner=2):
                self.assertTrue(False)
'''

_EXPECTED_FAILURE = '''
import unittest
class T(unittest.TestCase):
    @unittest.expectedFailure
    def test_expected(self):
        with self.subTest(n=1):
            self.assertTrue(False)
'''

# The shape of trlib test_NSMAX_in_range (#189): pytest xfail mark on a
# unittest test whose only assertions sit inside subTest.
_XFAIL_MARK = '''
import unittest, pytest
class T(unittest.TestCase):
    @pytest.mark.xfail(strict=False, reason="known")
    def test_xfail_marked(self):
        for n in (1, 2):
            with self.subTest(n=n):
                self.assertEqual(n, 1)
'''


def _run_child(source, *extra, forked=True):
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = pathlib.Path(tmpdir) / "test_case.py"
        test_file.write_text(source)
        env = dict(os.environ)
        parts = [str(PYTHON_DIR)] + [p for p in env.get("PYTHONPATH", "").split(os.pathsep) if p]
        env["PYTHONPATH"] = os.pathsep.join(parts)
        env.pop("PYTEST_ADDOPTS", None)
        env.pop("PYTEST_PLUGINS", None)
        env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
        cmd = [
            sys.executable, "-m", "pytest",
            "-p", "_strict_subtest", "-p", "no:cacheprovider",
            "-q", "-s", str(test_file), *extra,
        ]
        if forked:
            cmd += ["-p", "pytest_forked", "--forked"]
        return subprocess.run(
            cmd, cwd=tmpdir, env=env, capture_output=True, text=True, timeout=120,
        )


class TestInstalledInThisSession(unittest.TestCase):
    def test_override_is_active(self):
        import _strict_subtest
        self.assertTrue(
            _strict_subtest.is_installed(),
            "python/conftest.py did not install the strict subTest override; "
            "check pytest.ini / conftest discovery (#241)",
        )


class TestSubprocess(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import pytest_forked  # noqa: F401
        except ImportError:  # pragma: no cover - CI always installs it
            raise unittest.SkipTest("pytest-forked not installed")

    def test_failing_subtest_fails_under_forked(self):
        res = _run_child(_FAILING)
        self.assertNotEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("1 failed", res.stdout)
        # Every failing sub-case is listed, not just the first.
        self.assertIn("subTest(n=1) failed", res.stdout)
        self.assertIn("subTest(n=3) failed", res.stdout)
        self.assertNotIn("subTest(n=2) failed", res.stdout)

    def test_skiptest_inside_one_subtest_continues(self):
        res = _run_child(_SKIP_ONE)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("1 passed", res.stdout)

    def test_all_subtests_skipped_reports_skipped(self):
        res = _run_child(_SKIP_ALL, "-rs")
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("1 skipped", res.stdout)
        self.assertIn("fixture missing", res.stdout)

    def test_skip_after_failed_subcase_is_a_failure(self):
        res = _run_child(_SKIP_AFTER_FAILURE)
        self.assertNotEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("1 failed", res.stdout)
        self.assertNotIn("skipped", res.stdout.splitlines()[-1])
        self.assertIn("subTest(n=1) failed", res.stdout)
        self.assertIn("late skip must not hide the failure", res.stdout)

    def test_pytest_skip_after_failed_subcase_is_a_failure(self):
        res = _run_child(_PYTEST_SKIP_AFTER_FAILURE)
        self.assertNotEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("1 failed", res.stdout)
        self.assertNotIn("skipped", res.stdout.splitlines()[-1])
        self.assertIn("subTest(n=1) failed", res.stdout)

    def test_teardown_subtest_falls_back_to_stock_reporting(self):
        # Outside the test body the stock subTest is used; pytest (not
        # forked) reports its failure as before.
        res = _run_child(_TEARDOWN_SUBTEST, forked=False)
        self.assertNotEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("failed", res.stdout.splitlines()[-1])

    def test_later_exception_keeps_both(self):
        res = _run_child(_LATER_EXCEPTION)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("1 failed", res.stdout)
        self.assertIn("RuntimeError: later error wins", res.stdout)
        self.assertIn("subTest(n=1) failed", res.stdout)

    def test_signal_timeout_propagates_after_subtest_failure(self):
        res = _run_child(
            _TIMEOUT_AFTER_FAILURE, "-p", "pytest_timeout",
            "--timeout=2", "--timeout-method=signal", forked=False,
        )
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("1 failed", res.stdout)
        self.assertIn("Timeout", res.stdout)

    def test_signal_timeout_propagates_after_subtest_failure_forked(self):
        # Under --forked the timer has to be armed in the child
        # (_forked_timeout, #247); with it the hung test is reported as a
        # failure (the Timeout wins over the recorded subTest failure, as
        # in the non-forked case above) instead of an INTERNALERROR.
        res = _run_child(
            _TIMEOUT_AFTER_FAILURE, "-p", "pytest_timeout", "-p", "_forked_timeout",
            "--timeout=2", "--timeout-method=signal",
        )
        self.assertNotIn("INTERNALERROR", res.stdout + res.stderr)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("1 failed", res.stdout)
        self.assertIn("Timeout", res.stdout)

    def test_pytest_exit_inside_subtest_propagates(self):
        res = _run_child(_PYTEST_EXIT, forked=False)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("stop now", res.stdout + res.stderr)
        self.assertNotIn("SHOULD-NOT-RUN", res.stdout)

    def test_pytest_exit_after_failed_subcase_still_exits(self):
        res = _run_child(_EXIT_AFTER_FAILURE, forked=False)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("stop now", res.stdout + res.stderr)
        self.assertNotIn("SHOULD-NOT-RUN", res.stdout)

    def test_nested_all_leaves_skipped_reports_skipped(self):
        res = _run_child(_NESTED_ALL_SKIPPED, "-rs")
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("1 skipped", res.stdout)

    def test_async_testcase_subtest_failure_fails(self):
        res = _run_child(_ASYNC)
        self.assertNotEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("1 failed", res.stdout)
        self.assertIn("subTest(n=2) failed", res.stdout)

    def test_nested_subtests_merge_parameters(self):
        res = _run_child(_NESTED)
        self.assertIn("1 failed", res.stdout)
        self.assertIn("subTest([outer msg] outer=1, inner=2) failed", res.stdout)

    def test_expected_failure_still_xfails(self):
        res = _run_child(_EXPECTED_FAILURE)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("1 xfailed", res.stdout)

    def test_pytest_xfail_mark_reports_xfailed_not_xpassed(self):
        res = _run_child(_XFAIL_MARK)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("1 xfailed", res.stdout)
        self.assertNotIn("xpassed", res.stdout)
