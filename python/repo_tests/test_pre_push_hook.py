"""The tracked pre-push hook (.githooks/pre-push) and scripts/install-hooks.sh.

Everything runs in throwaway repositories under tmp_path, with a bare
repository on disk as the remote: no network, and neither this checkout's
git configuration nor the user's is read or written.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
HOOK = REPO / ".githooks" / "pre-push"
INSTALL = REPO / "scripts" / "install-hooks.sh"
ZERO = "0" * 40
ELSEWHERE = "/somewhere/remote.git"
PRODUCT_URLS = ["https://github.com/HengyuLi-Ozaki-lab/task.git", "https://github.com/HengyuLi-Ozaki-lab/task",
                "git@github.com:HengyuLi-Ozaki-lab/task.git", "ssh://git@github.com/hengyuli-ozaki-lab/TASK/",
                "https://github.com/HengyuLi-Ozaki-lab/task.git/", "git://github.com/HengyuLi-Ozaki-lab/task.git",
                "https://someone@github.com/HengyuLi-Ozaki-lab/task.git",
                "ssh://git@github.com:22/HengyuLi-Ozaki-lab/task.git",
                "ssh://git@ssh.github.com:443/HengyuLi-Ozaki-lab/task.git",
                "git@github.com:/HengyuLi-Ozaki-lab/task.git", "github.com:HengyuLi-Ozaki-lab/task.git",
                "https://www.github.com/HengyuLi-Ozaki-lab/task.git", "git+ssh://git@github.com/HengyuLi-Ozaki-lab/task.git",
                "ssh+git://git@github.com/HengyuLi-Ozaki-lab/task.git", "https://github.com/HengyuLi-Ozaki-lab//task",
                "https://github.com//HengyuLi-Ozaki-lab/task.git", "git@www.github.com:HengyuLi-Ozaki-lab/task.git"]
OTHER_URLS = ["https://github.com/HengyuLi-Ozaki-lab/task-merge.git", "https://github.com/k-yoshimi/task.git",
              "https://github.com/HengyuLi-Ozaki-lab/task-web-client.git", ELSEWHERE,
              "https://notgithub.com/HengyuLi-Ozaki-lab/task.git",
              "https://github.com.example.invalid/HengyuLi-Ozaki-lab/task.git",
              "https://github.com/another-org/HengyuLi-Ozaki-lab/task.git",
              "git@github.com:HengyuLi-Ozaki-lab/tasks.git",
              "file://github.com/HengyuLi-Ozaki-lab/task.git", "github.com/HengyuLi-Ozaki-lab/task",
              "/srv/github.com/HengyuLi-Ozaki-lab/task.git",
              "git@github.com:22/HengyuLi-Ozaki-lab/task.git",          # scp syntax has no port: 22/... is the path
              "https://www.github.com.example.invalid/HengyuLi-Ozaki-lab/task.git", "https://wwwgithub.com/HengyuLi-Ozaki-lab/task.git",
              "https://www.notgithub.com/HengyuLi-Ozaki-lab/task.git", "https://x.www.github.com/HengyuLi-Ozaki-lab/task.git",
              "https://example.invalid/www.github.com/HengyuLi-Ozaki-lab/task.git",
              "https://github.com/another-org//HengyuLi-Ozaki-lab/task.git", "git+ssh://git@notgithub.com/HengyuLi-Ozaki-lab/task.git"]

pytestmark = pytest.mark.skipif(
    sys.platform == "win32" or shutil.which("git") is None or shutil.which("bash") is None,
    reason="needs git and a POSIX shell")


def _env(tmp_path: Path, **extra: str) -> dict:
    env = {k: v for k, v in os.environ.items()
           if not k.startswith("GIT_") and k not in ("SKIP_PREPUSH_REVIEW", "SKIP_PREPUSH_REVIEW_REASON")}
    env.update(HOME=str(tmp_path), GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1",
               GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.invalid",
               GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.invalid")
    env.update(extra)
    return env


def _git(cwd: Path, env: dict, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, env=env, check=check,
                          capture_output=True, text=True, timeout=60)


@pytest.fixture
def clone(tmp_path):
    """A clone with one commit on `topic`, the tracked hook and installer in
    its tree, and a bare repository as the remote `origin`."""
    env = _env(tmp_path)
    remote = tmp_path / "remote.git"
    _git(tmp_path, env, "init", "-q", "--bare", str(remote))
    work = tmp_path / "work"
    _git(tmp_path, env, "init", "-q", str(work))
    _git(work, env, "symbolic-ref", "HEAD", "refs/heads/topic")          # `git init -b` needs git 2.28
    (work / ".githooks").mkdir()
    (work / "scripts").mkdir()
    shutil.copy2(HOOK, work / ".githooks" / "pre-push")
    shutil.copy2(INSTALL, work / "scripts" / "install-hooks.sh")
    _git(work, env, "add", "-A")
    _git(work, env, "commit", "-q", "-m", "hooks")
    _git(work, env, "remote", "add", "origin", str(remote))
    return work, env


def _hook(work: Path, env: dict, stdin: str, url: str = ELSEWHERE) -> subprocess.CompletedProcess:
    return subprocess.run([str(work / ".githooks" / "pre-push"), "origin", url], cwd=work, env=env,
                          input=stdin, capture_output=True, text=True, timeout=60)


def _head(work: Path, env: dict) -> str:
    return _git(work, env, "rev-parse", "HEAD").stdout.strip()


def _marker(work: Path, env: dict, sha: str) -> Path:
    common = _git(work, env, "rev-parse", "--git-common-dir").stdout.strip()
    return (work / common).resolve() / f"REVIEW_OK_{sha}"


def _commit(work: Path, env: dict, name: str) -> str:
    (work / name).write_text("x\n")
    _git(work, env, "add", name)
    _git(work, env, "commit", "-q", "-m", name)
    return _head(work, env)


def test_a_push_is_refused_until_its_tip_has_a_marker_and_the_refusal_names_it(clone):
    work, env = clone
    sha = _head(work, env)
    line = f"refs/heads/topic {sha} refs/heads/topic {ZERO}\n"
    proc = _hook(work, env, line)
    assert proc.returncode == 1
    assert f"REVIEW_OK_{sha}" in proc.stderr and "REFUSED" in proc.stderr
    assert f'touch "{_marker(work, env, sha)}"' in proc.stderr          # quoted: a path with a space still pastes
    _marker(work, env, sha).touch()
    assert _hook(work, env, line).returncode == 0


def test_the_marker_is_for_the_ref_pushed_not_for_head(clone):
    work, env = clone
    pushed = _head(work, env)
    _marker(work, env, _commit(work, env, "later.txt")).touch()     # HEAD is reviewed, the pushed tip is not
    proc = _hook(work, env, f"refs/heads/old {pushed} refs/heads/old {ZERO}\n")
    assert proc.returncode == 1 and f"REVIEW_OK_{pushed}" in proc.stderr


def test_every_pushed_ref_needs_the_marker_of_its_own_tip(clone):
    work, env = clone
    first = _head(work, env)
    second = _commit(work, env, "b.txt")
    _marker(work, env, first).touch()
    proc = _hook(work, env, f"refs/heads/a {first} refs/heads/a {ZERO}\nrefs/heads/b {second} refs/heads/b {ZERO}\n")
    assert proc.returncode == 1 and f"REVIEW_OK_{second}" in proc.stderr
    assert f"REVIEW_OK_{first}" not in proc.stderr


@pytest.mark.parametrize("unreviewed_at", [0, 1, 2])
def test_the_unreviewed_ref_is_refused_wherever_it_stands_in_the_push(clone, unreviewed_at):
    """A hook that looked at only the first, or only the last, pushed ref would pass this."""
    work, env = clone
    tips = [_head(work, env), _commit(work, env, "b.txt"), _commit(work, env, "c.txt")]
    for i, tip in enumerate(tips):
        if i != unreviewed_at:
            _marker(work, env, tip).touch()
    stdin = "".join(f"refs/heads/r{i} {tip} refs/heads/r{i} {ZERO}\n" for i, tip in enumerate(tips))
    proc = _hook(work, env, stdin)
    assert proc.returncode == 1 and f"REVIEW_OK_{tips[unreviewed_at]}" in proc.stderr
    assert sum(f"REVIEW_OK_{tip}" in proc.stderr for tip in tips) == 1       # and only that one is named


def test_an_annotated_tag_is_gated_by_the_marker_of_the_commit_it_points_to(clone):
    """A tag of a reviewed commit adds no code; the marker is the commit's, whatever object the ref names."""
    work, env = clone
    commit = _head(work, env)
    _git(work, env, "tag", "-a", "-m", "v1", "v1")
    tag_object = _git(work, env, "rev-parse", "v1").stdout.strip()
    assert tag_object != commit
    line = f"refs/tags/v1 {tag_object} refs/tags/v1 {ZERO}\n"
    refused = _hook(work, env, line)
    assert refused.returncode == 1 and f"REVIEW_OK_{commit}" in refused.stderr
    _marker(work, env, commit).touch()
    assert _hook(work, env, line).returncode == 0


def test_a_tag_that_is_not_on_a_commit_is_gated_by_its_own_object_quietly(clone):
    work, env = clone
    _git(work, env, "tag", "-a", "-m", "tree", "tree-tag", "HEAD^{tree}")
    tag_object = _git(work, env, "rev-parse", "tree-tag").stdout.strip()
    refused = _hook(work, env, f"refs/tags/tree-tag {tag_object} refs/tags/tree-tag {ZERO}\n")
    assert refused.returncode == 1 and f"REVIEW_OK_{tag_object}" in refused.stderr
    assert "expected commit type" not in refused.stderr and "error:" not in refused.stderr


def test_a_deletion_and_an_empty_push_need_no_marker(clone):
    work, env = clone
    assert _hook(work, env, f"(delete) {ZERO} refs/heads/gone {_head(work, env)}\n").returncode == 0
    assert _hook(work, env, "").returncode == 0


SPACED_SOURCES = ["HEAD@{0 0 0}", "HEAD@{0 minutes ago}"]       # git writes the local ref as typed, spaces included


def _real_push(work: Path, env: dict, source: str, remote_ref: str, **extra: str) -> subprocess.CompletedProcess:
    """git push of `<source>:<remote_ref>` to the bare repository `origin`, the tracked hook in force."""
    _git(work, env, "config", "core.hooksPath", str(work / ".githooks"))
    return subprocess.run(["git", "push", "origin", f"{source}:{remote_ref}"], cwd=work, env={**env, **extra},
                          capture_output=True, text=True, timeout=60)


def _remote_branches(work: Path, env: dict) -> str:
    return _git(work, env, "--git-dir", str(work.parent / "remote.git"), "branch", "--list").stdout.strip()


@pytest.mark.parametrize("source", SPACED_SOURCES)
def test_a_source_refspec_with_spaces_does_not_get_past_the_marker_rule(clone, source):
    work, env = clone
    sha = _head(work, env)
    direct = _hook(work, env, f"{source} {sha} refs/heads/x {ZERO}\n")           # the stdin git writes
    assert direct.returncode == 1 and f"REVIEW_OK_{sha}" in direct.stderr
    refused = _real_push(work, env, source, "refs/heads/x")                      # and a real push
    assert refused.returncode != 0 and f"REVIEW_OK_{sha}" in refused.stderr and _remote_branches(work, env) == ""
    _marker(work, env, sha).touch()
    assert _real_push(work, env, source, "refs/heads/x").returncode == 0 and "x" in _remote_branches(work, env)


@pytest.mark.parametrize("source", SPACED_SOURCES)
def test_a_source_refspec_with_spaces_does_not_get_past_the_fork_rule(clone, tmp_path, source):
    """No real push can name the fork here (no network), so a real push to a local bare repository records the
    exact stdin git writes for that refspec, and the hook is run on it with the fork's URL."""
    work, env = clone
    sha = _head(work, env)
    _marker(work, env, sha).touch()
    recorder = tmp_path / "recorder"
    recorder.mkdir()
    (recorder / "pre-push").write_text(f"#!/bin/sh\ncat > '{tmp_path / 'stdin.txt'}'\n")
    (recorder / "pre-push").chmod(0o755)
    _git(work, env, "config", "core.hooksPath", str(recorder))
    pushed = subprocess.run(["git", "push", "origin", f"{source}:refs/heads/kyoshimi-develop"], cwd=work, env=env,
                            capture_output=True, text=True, timeout=60)
    assert pushed.returncode == 0, pushed.stderr
    stdin = (tmp_path / "stdin.txt").read_text()
    assert stdin.startswith(f"{source} {sha} refs/heads/kyoshimi-develop ")
    for url in PRODUCT_URLS[:2]:
        for extra in ({}, {"SKIP_PREPUSH_REVIEW": "1"}):
            for line in (stdin, f"{source} {sha} refs/heads/kyoshimi-develop {ZERO}\n"):
                proc = _hook(work, {**env, **extra}, line, url)
                assert proc.returncode == 1 and "only through pull requests" in proc.stderr, (url, extra, line)


def test_a_stdin_line_the_hook_cannot_read_is_refused_not_skipped(clone):
    work, env = clone
    sha = _head(work, env)
    _marker(work, env, sha).touch()
    for line in ("refs/heads/a", f"refs/heads/a {sha}", f"refs/heads/a {sha} refs/heads/a",
                 f"refs/heads/a nothex refs/heads/a {ZERO}", f"refs/heads/a {sha[:39]} refs/heads/a {ZERO}",
                 f"refs/heads/a {sha} refs/heads/a {ZERO[:39]}", f"refs/heads/a {sha.upper()} refs/heads/a {ZERO}",
                 f"{sha} refs/heads/a {ZERO}"):
        for extra in ({}, {"SKIP_PREPUSH_REVIEW": "1"}):
            proc = _hook(work, {**env, **extra}, line + "\n")
            assert proc.returncode == 1 and "cannot read" in proc.stderr, (line, extra)


def test_a_blank_line_is_refused_not_skipped_and_empty_input_is_not_a_line(clone):
    work, env = clone
    sha = _head(work, env)
    _marker(work, env, sha).touch()
    good = f"refs/heads/a {sha} refs/heads/a {ZERO}\n"
    assert _hook(work, env, good).returncode == 0
    for stdin in ("\n", good + "\n", "\n" + good, good + "\n" + good, "   \n"):
        proc = _hook(work, env, stdin)
        assert proc.returncode == 1 and "cannot read" in proc.stderr, stdin
    assert _hook(work, env, "").returncode == 0


def test_a_last_line_without_a_newline_is_still_read(clone):
    work, env = clone
    sha = _head(work, env)
    refused = _hook(work, env, f"refs/heads/a {sha} refs/heads/a {ZERO}")           # git always ends the line; do not rely on it
    assert refused.returncode == 1 and f"REVIEW_OK_{sha}" in refused.stderr


def test_sha256_object_names_are_read_too(clone):
    work, env = clone
    sha, zero = "a" * 64, "0" * 64
    refused = _hook(work, env, f"refs/heads/a {sha} refs/heads/a {zero}\n")
    assert refused.returncode == 1 and f"REVIEW_OK_{sha}" in refused.stderr
    _marker(work, env, sha).touch()
    assert _hook(work, env, f"refs/heads/a {sha} refs/heads/a {zero}\n").returncode == 0
    assert _hook(work, env, f"(delete) {zero} refs/heads/gone {sha}\n").returncode == 0


@pytest.mark.parametrize("url", PRODUCT_URLS)
@pytest.mark.parametrize("local_ref", ["refs/heads/kyoshimi-develop", "refs/heads/topic", "HEAD"])
def test_a_push_to_the_product_line_is_refused_even_with_a_marker(clone, url, local_ref):
    work, env = clone
    sha = _head(work, env)
    _marker(work, env, sha).touch()
    proc = _hook(work, {**env, "SKIP_PREPUSH_REVIEW": "1"},
                 f"{local_ref} {sha} refs/heads/kyoshimi-develop {ZERO}\n", url)
    assert proc.returncode == 1 and "only through pull requests" in proc.stderr
    assert "gh pr create -R HengyuLi-Ozaki-lab/task --base kyoshimi-develop" in proc.stderr


@pytest.mark.parametrize("url", PRODUCT_URLS)
def test_other_branches_of_the_product_repository_only_need_their_marker(clone, url):
    work, env = clone
    sha = _head(work, env)
    line = f"refs/heads/topic {sha} refs/heads/topic {ZERO}\n"
    assert _hook(work, env, line, url).returncode == 1
    _marker(work, env, sha).touch()
    assert _hook(work, env, line, url).returncode == 0


@pytest.mark.parametrize("url", OTHER_URLS)
def test_a_branch_named_kyoshimi_develop_on_another_remote_is_an_ordinary_push(clone, url):
    """The research repository has other remotes with a kyoshimi-develop
    (the merge sandbox): the product rule is about one repository."""
    work, env = clone
    sha = _head(work, env)
    line = f"refs/heads/kyoshimi-develop {sha} refs/heads/kyoshimi-develop {ZERO}\n"
    refused = _hook(work, env, line, url)
    assert refused.returncode == 1 and "no review marker" in refused.stderr
    assert "only through pull requests" not in refused.stderr
    _marker(work, env, sha).touch()
    assert _hook(work, env, line, url).returncode == 0


def test_the_review_override_is_logged_with_the_pushed_tip_and_the_reason(clone):
    work, env = clone
    sha = _head(work, env)
    proc = _hook(work, {**env, "SKIP_PREPUSH_REVIEW": "1", "SKIP_PREPUSH_REVIEW_REASON": "docs only"},
                 f"refs/heads/topic {sha} refs/heads/topic {ZERO}\n")
    assert proc.returncode == 0
    log = (_marker(work, env, sha).parent / "REVIEW_OVERRIDES.log").read_text()
    assert f"SHA={sha}" in log and "reason=docs only" in log


def test_install_hooks_makes_git_refuse_in_a_worktree_whose_branch_has_no_githooks(clone, tmp_path):
    """The reason the hooks are copied: a topic branch from upstream develop
    has no .githooks/, and the gate must still run there."""
    work, env = clone
    proc = subprocess.run(["bash", "scripts/install-hooks.sh"], cwd=work, env=env,
                          capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, proc.stderr
    common = _marker(work, env, "x").parent
    assert _git(work, env, "config", "--get", "core.hooksPath").stdout.strip() == str(common / "tracked-hooks")
    assert os.access(common / "tracked-hooks" / "pre-push", os.X_OK)

    _git(work, env, "checkout", "-q", "--orphan", "upstream-like")
    _git(work, env, "rm", "-rq", "--cached", ".")
    (work / "f.txt").write_text("no hooks on this branch\n")
    _git(work, env, "add", "f.txt")
    _git(work, env, "commit", "-q", "-m", "a branch without .githooks")
    _git(work, env, "checkout", "-q", "-f", "topic")
    other = tmp_path / "other-worktree"
    _git(work, env, "worktree", "add", "-q", str(other), "upstream-like")
    assert not (other / ".githooks").exists()

    refused = _git(other, env, "push", "origin", "upstream-like", check=False)
    assert refused.returncode != 0 and "no review marker" in refused.stderr
    _marker(other, env, _head(other, env)).touch()
    assert _git(other, env, "push", "origin", "upstream-like", check=False).returncode == 0
    # A branch that is not checked out needs the marker of ITS tip, from any worktree.
    topic = _git(other, env, "push", "origin", "topic", check=False)
    assert topic.returncode != 0 and _git(work, env, "rev-parse", "topic").stdout.strip()[:12] in topic.stderr


def test_install_hooks_check_says_when_the_installed_hook_is_not_the_tracked_one(clone):
    work, env = clone
    run = lambda *a: subprocess.run(["bash", "scripts/install-hooks.sh", *a], cwd=work, env=env,
                                    capture_output=True, text=True, timeout=60)
    assert run("--check").returncode == 1                    # nothing installed yet
    assert run().returncode == 0
    assert run("--check").returncode == 0
    with open(work / ".githooks" / "pre-push", "a") as fh:
        fh.write("# a newer hook\n")
    stale = run("--check")
    assert stale.returncode == 1 and "run scripts/install-hooks.sh" in stale.stderr
    assert run().returncode == 0 and run("--check").returncode == 0


def test_install_hooks_check_and_reinstall_deal_with_a_hook_the_tracked_folder_no_longer_has(clone):
    work, env = clone
    run = lambda *a: subprocess.run(["bash", "scripts/install-hooks.sh", *a], cwd=work, env=env,
                                    capture_output=True, text=True, timeout=60)
    assert run().returncode == 0
    installed = Path(_git(work, env, "config", "--get", "core.hooksPath").stdout.strip())
    (installed / "pre-commit").write_text("#!/bin/sh\nexit 1\n")        # a hook that .githooks/ no longer has
    stale = run("--check")
    assert stale.returncode == 1 and "pre-commit" in stale.stderr and "run scripts/install-hooks.sh" in stale.stderr
    assert run().returncode == 0 and not (installed / "pre-commit").exists()
    assert run("--check").returncode == 0


def _active_hook(folder: Path, name: str) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_text("#!/bin/sh\nexit 0\n")
    (folder / name).chmod(0o755)


def _install(work: Path, env: dict) -> subprocess.CompletedProcess:
    proc = subprocess.run(["bash", "scripts/install-hooks.sh"], cwd=work, env=env, capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, proc.stderr
    return proc


def test_install_hooks_check_says_when_the_installed_hook_is_not_executable(clone):
    """git silently skips a hook that is not executable: --check must not call that current."""
    work, env = clone
    run = lambda *a: subprocess.run(["bash", "scripts/install-hooks.sh", *a], cwd=work, env=env,
                                    capture_output=True, text=True, timeout=60)
    assert run().returncode == 0
    installed = Path(_git(work, env, "config", "--get", "core.hooksPath").stdout.strip()) / "pre-push"
    installed.chmod(0o644)
    broken = run("--check")
    assert broken.returncode == 1 and "not executable" in broken.stderr and "run scripts/install-hooks.sh" in broken.stderr
    assert run().returncode == 0 and os.access(installed, os.X_OK) and run("--check").returncode == 0


def test_install_hooks_never_cleans_up_through_a_symlinked_folder(clone, tmp_path):
    work, env = clone
    elsewhere = tmp_path / "somebody-elses-hooks"
    elsewhere.mkdir()
    (elsewhere / "precious").write_text("keep\n")
    (work / ".git" / "tracked-hooks").symlink_to(elsewhere)
    proc = subprocess.run(["bash", "scripts/install-hooks.sh"], cwd=work, env=env, capture_output=True, text=True, timeout=60)
    assert proc.returncode == 1 and "symlink" in proc.stderr
    assert (elsewhere / "precious").read_text() == "keep\n" and not (elsewhere / "pre-push").exists()


def test_install_hooks_says_which_hooks_of_git_hooks_stop_running(clone):
    """core.hooksPath replaces the folder .git/hooks: say which active hooks that stops."""
    work, env = clone
    for name in ("pre-commit", "pre-rebase.sample", "pre-push"):    # a sample is inert; pre-push is replaced
        _active_hook(work / ".git" / "hooks", name)
    proc = _install(work, env)
    assert "pre-commit" in proc.stderr and "no longer runs" in proc.stderr
    assert "pre-rebase" not in proc.stderr and "pre-push" not in proc.stderr and "was " not in proc.stderr


def test_install_hooks_reports_only_files_git_would_have_run(clone):
    work, env = clone
    for name in ("README.md", "helper.sh", "pre-commit"):
        _active_hook(work / ".git" / "hooks", name)
    proc = _install(work, env)
    assert "pre-commit" in proc.stderr and "README" not in proc.stderr and "helper" not in proc.stderr


@pytest.mark.parametrize("form", ["absolute", "relative to the worktree", "tilde"])
def test_install_hooks_says_when_it_replaces_an_earlier_core_hooks_path(clone, tmp_path, form):
    work, env = clone
    earlier = work / "earlier-hooks"
    _active_hook(earlier, "commit-msg")
    _active_hook(work / ".git" / "hooks", "pre-commit")             # not running before, so not reported
    written = {"absolute": str(earlier), "relative to the worktree": "earlier-hooks", "tilde": "~/work/earlier-hooks"}[form]
    _git(work, env, "config", "core.hooksPath", written)
    (work / "scripts" / "sub").mkdir()
    proc = subprocess.run(["bash", str(work / "scripts" / "install-hooks.sh")], cwd=work / "scripts" / "sub", env=env,
                          capture_output=True, text=True, timeout=60)           # from a subdirectory
    assert proc.returncode == 0, proc.stderr
    assert "commit-msg" in proc.stderr and f"core.hooksPath was {earlier}" in proc.stderr
    assert "pre-commit" not in proc.stderr
    assert "was " not in _install(work, env).stderr                  # only the first install replaced anything


def test_install_hooks_says_when_it_removes_a_hook_the_tracked_folder_no_longer_has(clone):
    work, env = clone
    _install(work, env)
    installed = Path(_git(work, env, "config", "--get", "core.hooksPath").stdout.strip())
    _active_hook(installed, "post-merge")
    proc = _install(work, env)
    assert "removed" in proc.stderr and "post-merge" in proc.stderr and not (installed / "post-merge").exists()


def test_the_hook_and_the_installer_are_committed_executable():
    for path in (HOOK, INSTALL):
        assert os.access(path, os.X_OK), path
        assert b"\r\n" not in path.read_bytes(), path
