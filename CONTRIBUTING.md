# Contributing to the product line (`kyoshimi-develop`)

The rules are in `AGENTS.md` (branches, the two pull requests, checks, the upstream sync) and `CLAUDE.md`
(tests, and the pre-push gate for AI sessions). In short:

## Set up

```bash
git clone https://github.com/HengyuLi-Ozaki-lab/task.git task && cd task   # keep the name `task`: bpsd's Makefile reads ../task/make.header
git remote add upstream https://github.com/k-yoshimi/task.git && git fetch upstream
git switch kyoshimi-develop
scripts/setup.sh              # Linux: bpsd beside the checkout, make.header, every lib*api.so
scripts/install-hooks.sh      # AI sessions: the pre-push gate (sets core.hooksPath: see AGENTS.md)
```

On macOS, or to build exactly what TASK Web Client ships (-O0 with runtime checks, bpsd at its lock), use
task-web's `scripts/build_fortran.sh <this checkout> <the bpsd beside it>`.

## A change

1. A topic branch from `git merge-base origin/kyoshimi-develop upstream/develop` (`AGENTS.md` says when to start
   from `origin/kyoshimi-develop` instead).
2. Tests, with the libraries built: `PYTHONPATH=python:python/mcp-servers python -m pytest python/ --forked
   --timeout=120 --timeout-method=signal` (`pip install pytest pytest-forked pytest-timeout pytest-mock
   pytest-subtests numpy 'mcp>=0.9,<2'`, in an environment of your own).
3. A pull request into `kyoshimi-develop` of this repository (`gh pr create -R HengyuLi-Ozaki-lab/task --base
   kyoshimi-develop`). The same branch also goes to `k-yoshimi/task` `develop` as a pull request, but the author opens
   that one or gives the go-ahead (`AGENTS.md`): do not open it yourself without that go-ahead. A branch that carries
   product-only commits waits until what it depends on is upstream.
4. The four CI checks green; the author reviews it and merges, with a merge commit (GitHub accepts nothing else).
5. TASK Web Client picks the change up with a pull request of its own (`scripts/deps.py bump kyoshimi <sha>`).
