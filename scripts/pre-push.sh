#!/usr/bin/env bash
# Pre-push guard: refuses to push unless the current HEAD SHA has a
# REVIEW_OK_<sha> marker under the shared git dir. See CLAUDE.md
# §Pre-push gate.
#
# Marker + override log are stored under `git rev-parse --git-common-dir`
# so both the main checkout and any linked worktrees see the same set:
# a worktree's `.git` is a *file* (pointing to
# <main>/.git/worktrees/<name>/), so a literal `.git/` relative path
# would not resolve. `--git-common-dir` returns the shared `<main>/.git`
# regardless, keeping markers keyed on content (SHA), not workspace.
#
# To install for your clone:
#   ln -sf ../../scripts/pre-push.sh .git/hooks/pre-push
#   chmod +x scripts/pre-push.sh
# The hook is inherited by linked worktrees automatically.
#
# Override escape hatch (use sparingly, e.g. for documentation-only
# pushes that have been reviewed elsewhere): prefix with
#   SKIP_PREPUSH_REVIEW=1 git push ...
# The override logs a one-line reason to REVIEW_OVERRIDES.log (under
# the shared git dir) for later audit.

set -eu

# Resolve to an absolute path: `git rev-parse --git-common-dir` returns
# the literal ".git" when run with CWD = main worktree root, which makes
# the error message below ("touch $marker") non-copy-pasteable from any
# other shell CWD. The cd + pwd round-trip normalises both relative
# (main) and absolute (linked worktree) cases.
git_common_dir=$(cd "$(git rev-parse --git-common-dir)" && pwd)

if [ "${SKIP_PREPUSH_REVIEW:-0}" = "1" ]; then
    printf "%s  SHA=%s  reason=%s\n" \
        "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        "$(git rev-parse HEAD)" \
        "${SKIP_PREPUSH_REVIEW_REASON:-unspecified}" \
        >> "$git_common_dir/REVIEW_OVERRIDES.log"
    echo "pre-push: SKIP_PREPUSH_REVIEW=1 set — skipping review gate (logged)" >&2
    exit 0
fi

sha=$(git rev-parse HEAD)
marker="$git_common_dir/REVIEW_OK_${sha}"

if [ ! -f "$marker" ]; then
    cat >&2 <<EOF
============================================================
pre-push: REFUSED — no review marker for HEAD ${sha:0:12}

Per CLAUDE.md §Pre-push gate, you must:
  1. Run local pytest with CI-equivalent flags
  2. Launch feature-dev:code-reviewer on the diff
  3. Address HIGH / MED findings
  4. touch $marker

Escape hatch (rare):
  SKIP_PREPUSH_REVIEW=1 SKIP_PREPUSH_REVIEW_REASON='...' git push ...
============================================================
EOF
    exit 1
fi

echo "pre-push: review marker present — OK"
exit 0
