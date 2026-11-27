"""The CI workflows' package installer (``.github/scripts/apt-install.sh``).

The script runs against stand-ins for ``dpkg-query``, ``sudo``, ``apt-get``
and ``sleep`` placed first on ``PATH``: no package is installed, no network is
used and nothing waits. The stand-ins append each call to a log, which is what
the checks read.
"""
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / ".github" / "scripts" / "apt-install.sh"

pytestmark = pytest.mark.skipif(sys.platform == "win32" or shutil.which("bash") is None,
                                reason="needs bash")

# STATUS_<pkg> is what dpkg would report: "ii " for an installed package,
# "rc " for one removed with its configuration kept, "un " for one dpkg knows
# but has not installed; unset means unknown to dpkg. FAIL_UPDATES /
# FAIL_INSTALLS: how many of the first calls fail (a real `apt-get update`
# exits 0 on a failed index and the install fails instead: FAIL_INSTALLS).
STUBS = {
    "dpkg-query": r"""
echo "dpkg-query $*" >> "$LOG"
if [ "$1" = "-W" ] && [ "${2#-f=}" != "$2" ]; then
  var="STATUS_${3//-/_}"
  if [ -z "${!var+x}" ]; then
    echo "dpkg-query: no packages found matching $3" >&2
    exit 1
  fi
  printf '%s' "${!var}"
  exit 0
fi
shift
for p in "$@"; do printf '%s\t1.0\n' "$p"; done
""",
    "sudo": r"""
echo "sudo $*" >> "$LOG"
exec "$@"
""",
    "apt-get": r"""
echo "apt-get $*" >> "$LOG"
count_file="$STATE/$1.count"
n=$(( $(cat "$count_file" 2>/dev/null || echo 0) + 1 ))
echo "$n" > "$count_file"
case "$1" in
  update)  [ "$n" -gt "${FAIL_UPDATES:-0}" ] || exit 100 ;;
  install) [ "$n" -gt "${FAIL_INSTALLS:-0}" ] || { echo "E: Unable to fetch some archives" >&2; exit 100; } ;;
esac
""",
    "sleep": r"""
echo "sleep $*" >> "$LOG"
""",
}


def run(tmp_path, *packages, **env):
    bindir = tmp_path / "bin"
    state = tmp_path / "state"
    if not bindir.exists():
        bindir.mkdir()
        state.mkdir()
        for name, body in STUBS.items():
            stub = bindir / name
            stub.write_text("#!/usr/bin/env bash\n" + body)
            stub.chmod(0o755)
    log = tmp_path / "log"
    full_env = {k: v for k, v in os.environ.items()
                if not k.startswith(("STATUS_", "FAIL_", "APT_INSTALL_")) and k != "SECONDS"}
    full_env.update(PATH=f"{bindir}{os.pathsep}{os.environ['PATH']}", LOG=str(log), STATE=str(state))
    full_env.update(env)
    result = subprocess.run(["bash", str(SCRIPT), *packages], env=full_env,
                            capture_output=True, text=True, timeout=60)
    calls = log.read_text().splitlines() if log.exists() else []
    return result, calls


def apt_calls(calls):
    return [c for c in calls if c.startswith("apt-get ")]


def test_nothing_is_installed_when_the_image_has_every_package(tmp_path):
    result, calls = run(tmp_path, "gfortran", "gcc", "make", STATUS_gfortran="ii ", STATUS_gcc="ii ", STATUS_make="ii ")
    assert result.returncode == 0, result.stderr
    assert apt_calls(calls) == []
    assert not any(c.startswith(("sudo ", "sleep ")) for c in calls)
    assert "nothing to install" in result.stdout
    assert "gfortran\t1.0" in result.stdout      # the versions are printed


def test_only_the_missing_packages_are_installed(tmp_path):
    result, calls = run(tmp_path, "gfortran", "gcc", "make", "valgrind",
                        STATUS_gfortran="ii ", STATUS_gcc="ii ", STATUS_make="ii ")
    assert result.returncode == 0, result.stderr
    assert apt_calls(calls) == ["apt-get update", "apt-get install -y --no-install-recommends valgrind"]
    assert "sudo apt-get update" in calls
    assert not any(c.startswith("sleep ") for c in calls)


@pytest.mark.parametrize("status", ["rc ", "un "])
def test_a_package_dpkg_knows_but_has_not_installed_is_installed(tmp_path, status):
    result, calls = run(tmp_path, "gcc", "jq", STATUS_gcc="ii ", STATUS_jq=status)
    assert result.returncode == 0, result.stderr
    assert apt_calls(calls)[-1] == "apt-get install -y --no-install-recommends jq"


def test_a_failed_install_is_tried_again_after_30_and_60_seconds(tmp_path):
    result, calls = run(tmp_path, "valgrind", FAIL_INSTALLS="2")
    assert result.returncode == 0, result.stderr
    install = "apt-get install -y --no-install-recommends valgrind"
    assert apt_calls(calls) == ["apt-get update", install] * 3
    assert [c for c in calls if c.startswith("sleep ")] == ["sleep 30", "sleep 60"]
    assert result.stdout.count("::warning::") == 2


def test_a_failed_update_is_tried_again_before_any_install(tmp_path):
    result, calls = run(tmp_path, "valgrind", FAIL_UPDATES="1")
    assert result.returncode == 0, result.stderr
    install = "apt-get install -y --no-install-recommends valgrind"
    assert apt_calls(calls) == ["apt-get update", "apt-get update", install]
    assert [c for c in calls if c.startswith("sleep ")] == ["sleep 30"]


def test_the_step_fails_after_three_failed_attempts(tmp_path):
    result, calls = run(tmp_path, "valgrind", FAIL_INSTALLS="99")
    assert result.returncode == 1
    assert len([c for c in apt_calls(calls) if c.startswith("apt-get install")]) == 3
    assert [c for c in calls if c.startswith("sleep ")] == ["sleep 30", "sleep 60"]
    assert "::error::apt-install: valgrind not installed; attempt 3, the last, failed" in result.stdout


# bash takes SECONDS, the time the script has run, from the environment
# (init_seconds_var in bash's variables.c, 3.2 and 5.2 alike): SECONDS=181
# is a script whose first attempt failed after 181 s. The stand-in sleep does
# not advance it; the real clock can, by the time the script checks: the 215
# case holds for any later reading, the 181 case for one up to 29 s later.
@pytest.mark.parametrize("elapsed, attempts, sleeps", [("215", 1, []), ("181", 2, ["sleep 30"])])
def test_no_attempt_starts_after_240_seconds(tmp_path, elapsed, attempts, sleeps):
    result, calls = run(tmp_path, "valgrind", FAIL_INSTALLS="99", SECONDS=elapsed)
    assert result.returncode == 1
    assert len([c for c in apt_calls(calls) if c.startswith("apt-get install")]) == attempts
    assert [c for c in calls if c.startswith("sleep ")] == sleeps
    # SECONDS may have ticked on by the time of the message: not its value.
    assert re.search(rf"attempt {attempts} failed at \d+ s, and no attempt starts after 240 s", result.stdout)


def test_the_budget_is_apt_install_budget(tmp_path):
    result, calls = run(tmp_path, "valgrind", FAIL_INSTALLS="99", APT_INSTALL_BUDGET="0")
    assert result.returncode == 1
    assert len([c for c in apt_calls(calls) if c.startswith("apt-get install")]) == 1
    assert "no attempt starts after 0 s" in result.stdout


@pytest.mark.parametrize("budget", ["240s", ""])
def test_a_budget_that_is_not_a_number_is_refused(tmp_path, budget):
    result, calls = run(tmp_path, "valgrind", APT_INSTALL_BUDGET=budget)
    assert result.returncode == 2
    assert "APT_INSTALL_BUDGET must be a number of seconds" in result.stderr
    assert calls == []


def test_no_package_is_a_usage_error(tmp_path):
    result, calls = run(tmp_path)
    assert result.returncode == 2
    assert "usage:" in result.stderr
    assert calls == []
