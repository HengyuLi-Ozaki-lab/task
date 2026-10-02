#!/usr/bin/env bash
# Install this repository's tracked git hooks (.githooks/) for this clone and
# every worktree of it: once per clone, and again after .githooks/ changes.
#
#   scripts/install-hooks.sh           copy .githooks/* to <git dir>/tracked-hooks
#                                      and point core.hooksPath there
#   scripts/install-hooks.sh --check   exit 0 when what is installed is this
#                                      worktree's .githooks/, 1 when it is not
#
# The hooks are copied, not linked: core.hooksPath is one absolute folder under
# the shared git directory, so the gate also runs in a worktree whose branch has
# no .githooks/ (a topic branch from upstream develop) and never depends on
# another worktree staying where it is. The installed folder is this script's:
# whatever .githooks/ does not have is removed from it.
#
# It installs the .githooks/ of the worktree it runs in, for all of them: run it
# from the checkout whose hooks you want (normally the newest kyoshimi-develop).
# core.hooksPath REPLACES the folder .git/hooks (and any earlier or global
# core.hooksPath): the script lists the other active hooks that stop running.
set -euo pipefail
die() { echo "install-hooks: $*" >&2; exit 1; }

top="$(git rev-parse --show-toplevel)"
src="$top/.githooks"
[ -x "$src/pre-push" ] || die "$src/pre-push is missing or not executable (run this on kyoshimi-develop or a branch from it)"
common="$(cd "$(git rev-parse --git-common-dir)" && pwd -P)"
dest="$common/tracked-hooks"

if [ "${1:-}" = "--check" ]; then
    [ "$(git config --get core.hooksPath || true)" = "$dest" ] || die "core.hooksPath is not $dest: run scripts/install-hooks.sh"
    for hook in "$src"/*; do
        cmp -s "$hook" "$dest/$(basename "$hook")" || die "$(basename "$hook") is not the installed one: run scripts/install-hooks.sh"
        [ -x "$dest/$(basename "$hook")" ] || die "$(basename "$hook") is installed but not executable (git skips it): run scripts/install-hooks.sh"
    done
    for hook in "$dest"/*; do
        [ -e "$hook" ] || continue
        [ -e "$src/$(basename "$hook")" ] || die "$(basename "$hook") is installed but not in .githooks/: run scripts/install-hooks.sh"
    done
    echo "install-hooks: $dest is this worktree's .githooks/"
    exit 0
fi
[ $# -eq 0 ] || die "usage: $0 [--check]"

[ ! -L "$dest" ] || die "$dest is a symlink: refusing to copy into, or clean up, what it points to"
mkdir -p "$dest"
for hook in "$src"/*; do
    name="$(basename "$hook")"
    cp "$hook" "$dest/$name.new"
    chmod +x "$dest/$name.new"
    mv -f "$dest/$name.new" "$dest/$name"
done
for hook in "$dest"/*; do
    [ -e "$hook" ] || continue
    [ -e "$src/$(basename "$hook")" ] && continue
    echo "install-hooks: removed $hook (not in .githooks/)" >&2
    rm -f "$hook"
done
previous="$(git config --path --get core.hooksPath || true)"      # ~ expanded
git config core.hooksPath "$dest"
[ "$(git config --get core.hooksPath)" = "$dest" ] || die "core.hooksPath did not stick"
echo "core.hooksPath = $dest (pre-push: a review marker for every pushed ref tip)"
# What the new core.hooksPath stops: hooks of the folder it replaces, which git no longer reads.
replaced="${previous:-$common/hooks}"
case "$replaced" in /*) ;; *) replaced="$top/$replaced" ;; esac    # git reads a relative path from the worktree top
if [ "$replaced" != "$dest" ] && [ -d "$replaced" ]; then
    for hook in "$replaced"/*; do
        [ -f "$hook" ] && [ -x "$hook" ] || continue
        case "$(basename "$hook")" in          # only the names git runs
            applypatch-msg|pre-applypatch|post-applypatch|pre-commit|pre-merge-commit|prepare-commit-msg|commit-msg|\
            post-commit|pre-rebase|post-checkout|post-merge|pre-push|pre-receive|update|proc-receive|post-receive|\
            post-update|reference-transaction|push-to-checkout|pre-auto-gc|post-rewrite|sendemail-validate|\
            fsmonitor-watchman|p4-changelist|p4-prepare-changelist|p4-post-changelist|p4-pre-submit|post-index-change) ;;
            *) continue ;;
        esac
        [ -e "$src/$(basename "$hook")" ] && continue          # replaced by the tracked one
        echo "install-hooks: $hook no longer runs here (core.hooksPath replaces $replaced); copy it into .githooks/ to keep it" >&2
    done
fi
[ -z "$previous" ] || [ "$replaced" = "$dest" ] || echo "install-hooks: core.hooksPath was $replaced; it is now $dest" >&2
