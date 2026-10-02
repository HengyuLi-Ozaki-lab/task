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
# another worktree staying where it is.
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
    done
    echo "install-hooks: $dest is this worktree's .githooks/"
    exit 0
fi
[ $# -eq 0 ] || die "usage: $0 [--check]"

mkdir -p "$dest"
for hook in "$src"/*; do
    name="$(basename "$hook")"
    cp "$hook" "$dest/$name.new"
    chmod +x "$dest/$name.new"
    mv -f "$dest/$name.new" "$dest/$name"
done
git config core.hooksPath "$dest"
[ "$(git config --get core.hooksPath)" = "$dest" ] || die "core.hooksPath did not stick"
echo "core.hooksPath = $dest (pre-push: a review marker for every pushed ref tip)"
