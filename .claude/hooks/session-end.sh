#!/usr/bin/env bash
# session-end.sh — captures git state at session end into memory dir
# so that the next session's `/start` can resume cold.
#
# Wired via .claude/settings.local.json hooks.SessionEnd.
#
# Failure modes: this script MUST NOT block the session from ending.
# Final `exit 0` is forced; intermediate failures degrade gracefully.

set -u

TASK_REPO="/Users/k-yoshimi/Dropbox/cursor/task"
MEMORY_DIR="$HOME/.claude/projects/-Users-k-yoshimi-Dropbox-cursor-task/memory"
OUT="$MEMORY_DIR/_last_session_end.md"

# Only act when this hook fires inside the TASK repo *or any of its
# linked worktrees*. Use `git rev-parse --git-common-dir` because it
# resolves to the shared `<main>/.git` no matter which worktree you
# invoke from — a plain `case` on CWD silently misses worktrees that
# live outside the repo's tree (e.g., `~/.config/superpowers/worktrees/`).
#
# Claude Code passes hook context (session id, transcript path, etc.)
# as JSON on stdin. We intentionally do NOT read it: a blocking read on
# a buffered pipe could hang the script (and thus the session shutdown)
# if Claude Code holds the write end open. The hook captures all
# needed state from git/PWD without needing stdin.
project_dir="${CLAUDE_PROJECT_DIR:-$PWD}"
gcd=$(cd "$project_dir" 2>/dev/null \
      && cd "$(git rev-parse --git-common-dir 2>/dev/null)" 2>/dev/null \
      && pwd -P 2>/dev/null) || gcd=""
if [ "$gcd" != "$TASK_REPO/.git" ]; then
  exit 0
fi

mkdir -p "$MEMORY_DIR" 2>/dev/null || exit 0

cd "$TASK_REPO" 2>/dev/null || exit 0

# Atomic write: render into a tmp sibling, then `mv -f`. Prevents
# torn-frontmatter races when two Claude Code sessions happen to end
# at the same instant (the loser's mv overwrites the winner's intact
# file, which is fine — both contain a valid snapshot).
#
# Trap is installed BEFORE mktemp so a SIGTERM in the narrow window
# between file creation and the trap cannot leak a `.XXXXXX` sibling.
tmp=""
trap 'rm -f "${tmp:-}"' EXIT
tmp=$(mktemp "${OUT}.XXXXXX" 2>/dev/null) || exit 0

# Compose the snapshot into $tmp. `mv` is gated on the block's exit
# status, so a mid-write failure (disk full, signal) leaves the
# previous `_last_session_end.md` untouched rather than publishing a
# truncated snapshot.
if {
  echo "---"
  echo "name: last-session-end"
  echo "description: Auto-written by SessionEnd hook — git/branch/worktree snapshot at the moment the previous session ended. Consumed by /start."
  echo "metadata:"
  echo "  type: project"
  echo "---"
  echo
  echo "# Last Session End — $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo
  echo "**Repo:** \`$TASK_REPO\`"
  echo
  echo "**Branch:** $(git branch --show-current 2>/dev/null || echo '(detached)')"
  echo
  echo "**HEAD:**"
  echo
  echo '```'
  git log --oneline -1 2>/dev/null || echo "(git log failed)"
  echo '```'
  echo
  echo "## Last 5 commits on current branch"
  echo
  echo '```'
  git log --oneline -5 2>/dev/null || echo "(git log failed)"
  echo '```'
  echo
  echo "## Working tree (git status -s, max 25 lines)"
  echo
  echo '```'
  git status -s 2>/dev/null | head -25 || echo "(git status failed)"
  echo '```'
  echo
  echo "## Local branches (most recent activity)"
  echo
  echo '```'
  git for-each-ref --sort=-committerdate --count=10 \
    --format='%(refname:short)  %(objectname:short)  %(committerdate:short)  %(subject)' \
    refs/heads/ 2>/dev/null || echo "(git for-each-ref failed)"
  echo '```'
  echo
  echo "## Worktrees"
  echo
  echo '```'
  git worktree list 2>/dev/null || echo "(git worktree list failed)"
  echo '```'
  echo
  echo "## Origin sync state"
  echo
  echo '```'
  git status -sb 2>/dev/null | head -1 || echo "(git status -sb failed)"
  echo '```'
} > "$tmp" 2>/dev/null; then
  mv -f "$tmp" "$OUT" 2>/dev/null && trap - EXIT
fi

exit 0
