# The product line — rules for AI sessions and their humans

This repository is `HengyuLi-Ozaki-lab/task`, a public fork of `k-yoshimi/task` ("upstream", itself a fork of
`ats-fukuyama/task`). Its branch **`kyoshimi-develop` is the product line**: the TASK library that TASK Web
Client (task-web) builds, tests and ships; task-web's `deps.lock` only ever names a commit on it.
`CLAUDE.md` is the engineering discipline shared with upstream (the pre-push gate, the test rules). This file
is what is specific to the product line. `docs/product-line/upstream-status.md` says which of its commits
are upstream, proposed, or product-only. `origin/develop` and `origin/master` of this fork are stale mirrors:
the reference is `upstream/develop`.

## Remotes

In a fresh clone `origin` = `https://github.com/HengyuLi-Ozaki-lab/task.git` (this fork) and you add `upstream` =
`https://github.com/k-yoshimi/task.git` (working branch `develop`; contributions go there as pull requests). Other
checkouts may name their remotes differently: the commands below say `origin` for the fork and `upstream` for
`k-yoshimi/task`, and the pre-push hook goes by the push URL, not by the remote's name.
`gh` in a clone of a fork targets the parent: name the repository in every `gh pr` command
(`-R HengyuLi-Ozaki-lab/task --base kyoshimi-develop` for a product pull request).

## Every change: a topic branch and two pull requests

1. `git fetch origin && git fetch upstream`, then branch `<type>/<topic>` (`fix`, `feat`, `docs`, `chore`, `ci`)
   from the newest commit both lines hold, which is the upstream commit the last sync merged (or a later one that
   upstream took from us):
   `git switch -c fix/<topic> "$(git merge-base origin/kyoshimi-develop upstream/develop)"`.
   Right after a sync that is `upstream/develop`. A newer upstream commit as the base would carry unsynced
   upstream work into the product line inside your pull request.
2. Pull request 1, into the product line, usable at once:
   `gh pr create -R HengyuLi-Ozaki-lab/task --base kyoshimi-develop --head <branch>`.
3. Pull request 2, the contribution, from the same branch:
   `gh pr create -R k-yoshimi/task --base develop --head HengyuLi-Ozaki-lab:<branch>`. The author opens it, or
   gives the go-ahead. The product never waits for upstream.
4. A change that needs commits upstream does not have yet starts from `origin/kyoshimi-develop`, and its pull
   request 1 carries the label `product-only` (once, if the fork lacks it: `gh label create product-only -R
   HengyuLi-Ozaki-lab/task`). Add it to `docs/product-line/upstream-status.md`; its pull request 2 follows when
   what it depends on is upstream.

`kyoshimi-develop` takes **merge commits only** (`gh pr merge --merge`): both pull requests then hold the same
commits, and the next sync merges them without a conflict. GitHub enforces this, the pull request and the CI
checks for everyone, the author included (the ruleset recorded in `.github/rulesets/kyoshimi-develop.json`;
nobody bypasses it, and `CLAUDE.md` forbids `--admin`). Never force-push a branch with an open pull request,
never delete or move a tag. The author reviews and merges; a second ruleset asking an approving review
(`kyoshimi-develop-review.json`) is not in force while AI sessions share the author's account. The live ruleset has
id 24351353; the author applies a changed record with
`gh api -X PUT repos/HengyuLi-Ozaki-lab/task/rulesets/24351353 --input .github/rulesets/kyoshimi-develop.json`.

## Checks

- **CI** (`.github/workflows/python-tests.yml`, on pull requests into `kyoshimi-develop` and pushes to it):
  `pytest (Python 3.11)`, `pytest (Python 3.13)` (each builds the seven `lib*api.so` on Linux and runs
  `pytest python/ --forked --timeout=120 --timeout-method=signal`), `mono build (Linux libtotapi_mono.so)` and
  `build modules not covered by pytest`. All four are required. The workflows keep upstream's floating action
  tags (`actions/checkout@v4`, `actions/setup-python@v5`): pinning them here would conflict on every sync. A
  change of the workflow's job names changes `.github/rulesets/kyoshimi-develop.json` in the same pull request
  (`python/repo_tests/test_rulesets.py` fails otherwise), and the author updates the live ruleset before merging it.
- **The pre-push gate** (`CLAUDE.md`) applies to every push **by an AI session**: local pytest with the CI
  flags, a code review, a Codex review, then the marker of every pushed ref tip. `scripts/install-hooks.sh`
  installs the hook, once per clone and again when `.githooks/` changes; it sets `core.hooksPath`, which replaces
  the folder `.git/hooks`, and says which other active hook there stops running. A lab member's own change is gated
  by the author's review of its pull request and by CI; they need not install the hook.
- The 1e-10 equivalence tests run on Linux only (`docs/baseline-policy.md`): a local run on macOS skips them,
  and **a skip is not a verification**. Before a merge, confirm from the CI run's log that they ran: the pytest
  progress lines of the seven modules (`python/eqlib/tests/test_equivalence.py ..` and so on) show passes, and
  no `SKIPPED … test_equivalence` line and no "Equivalence tests are Linux-canonical" skip reason appears in
  the short summary. The `equivalence-actuals-*` artifact is no substitute: it holds a metrics folder only for
  the `tot` and `wrx` cases (the only tests that write one), so a folder missing for `eq`, `tr`, `fp`, `ti` or
  `wr` says nothing. A baseline changes only through `regen-baselines.yml`, with the author's approval. That
  workflow is `workflow_dispatch`-only and GitHub dispatches such a workflow only from the default branch, so on
  this fork it can run only once `.github/` is on the default branch (the optional switch of the default branch to
  `kyoshimi-develop`); until then the route that worked is described in the workflow's own header (a scratch branch
  with a temporary `push:` trigger).

## The upstream sync (at the start of each task-web minor cycle)

1. The freeze: while a sync pull request is open, nothing else is opened against or merged into
   `kyoshimi-develop`, and nobody bumps task-web's `deps.lock`. It starts when the coordinator announces it and
   ends when the sync merges.
2. `git switch -c sync/upstream-YYYYMMDD origin/kyoshimi-develop && git merge --no-ff upstream/develop`.
   **A merge, never a rebase**: task-web's lock points at published commits. Where upstream took a patch of
   ours, take upstream's version; elsewhere keep both intents; never drop an upstream change silently.
3. The gate reviews a **change packet**, not upstream's commits again: the areas changed; whether anything
   under `eq/ tr/ fp/ pl/ lib/ mtxp/ dp/ ob/` or `python/mcp-servers/` changes (then those diffs, line by
   line); the hand resolutions (`git show --remerge-diff <merge>`); the files both sides changed since the
   merge-base (bash or zsh: `MB=$(git merge-base <merge>^1 <merge>^2)`, then
   `comm -12 <(git diff --name-only $MB <merge>^1 | sort) <(git diff --name-only $MB <merge>^2 | sort)`);
   every commit after the merge; whether task-web's installers (they copy `python/eqlib`, `trlib`, `fplib`,
   three MCP servers and the top-level modules those import) now need something else; the test results. The
   pull request states what was not reviewed line by line.
4. The trial bump in task-web (its `CONTRIBUTING.md`, "The TASK library") shows the wiki and test impact
   before the merge. Label the pull request `sync`; the author merges it with a merge commit.

## The cross-repository order

1. The pull request into `kyoshimi-develop` merges.
2. One task-web pull request runs `scripts/deps.py bump kyoshimi <sha>` (a commit on `kyoshimi-develop`) and
   uses the change. Only one such pull request is open at a time.
3. The spec and the plan of a feature live in task-web; its CHANGELOG lists the library change under "TASK
   library". mdx and the installers move only with a task-web release.
