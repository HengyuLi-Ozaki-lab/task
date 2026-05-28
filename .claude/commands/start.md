---
description: Resume work from the previous session — reads the latest session handoff memo + SessionEnd hook snapshot, briefs the user, and offers a next-step menu.
---

You are resuming a session. Pick up where the previous session left off.

## Your job

1. **Locate the project + user memory dir — derive everything from
   the current checkout, do not hardcode paths.**

   - `PROJECT_ROOT=$(git rev-parse --show-toplevel)` — the repo root.
     If git fails (e.g., invoked outside a checkout), tell the user
     and stop.
   - The user-level memory dir is keyed by the project root with `/`
     replaced by `-`:
       `MEM_DIR=$HOME/.claude/projects/${PROJECT_ROOT//\//-}/memory`
   - If `$MEM_DIR` does not exist, this is a first-ever session on
     this machine — skip to step 6 ("fresh-clone fallback").

2. **Find the latest session handoff memo.**
   - Read `$MEM_DIR/MEMORY.md`.
   - Pick the entry with the most recent date in
     `session_handoff_YYYY-MM-DD*.md` form (including `*_v2.md`,
     `*_v3.md`, etc).
   - Read that handoff file fully.
   - If no `session_handoff_*` entry exists in MEMORY.md, skip to
     step 6 ("fresh-clone fallback").

3. **Read the SessionEnd hook snapshot** (if it exists):
   - `$MEM_DIR/_last_session_end.md`
   - Auto-written by the project's SessionEnd hook; contains git
     state at the moment the previous session ended.
   - If absent or older than the handoff, treat as missing — the
     handoff is the source of truth.

4. **Capture current repo state** by running these in parallel
   (use `git -C "$PROJECT_ROOT" ...`):
   - `git log --oneline -5`
   - `git status -s | head -15`
   - `git branch -vv | head -10`
   - `git worktree list`

5. **Verify the handoff's "next-up" item is still actionable.**
   If the handoff names a specific issue (e.g., "#215"), run
   `gh issue view <N> --json state,title` to confirm it's still
   open. If closed externally, surface the closure and re-pick from
   the open-issues table in the handoff.

6. **Brief the user in ≤8 lines:**
   - 1 line: what last session shipped (PR # + one-line title from
     the handoff's "What landed" section)
   - 1 line: current branch / HEAD / dirty-file count
   - 1 line: any divergence between handoff snapshot and current
     state (new commits, branch changes, etc.)
   - 3-5 lines: condensed numbered menu of "Next session entry
     point" items from the handoff

   **Fresh-clone fallback (no handoff yet):** brief with branch +
   HEAD + recent commit subjects only, then ask what the user wants
   to work on. Do not invent a menu.

7. **Offer the numbered menu via AskUserQuestion** with 2-4
   options derived from the handoff's "Next session entry point" +
   "Open issues at session end" sections. The explicit
   next-deliverable is option 1 (Recommended).

8. **Wait for the user's choice.** Do NOT start work, do NOT invoke
   `superpowers:brainstorming` / `superpowers:subagent-driven-development`
   / any implementation skill until the user confirms direction in
   reply to your menu.

## Constraints

- Respect CLAUDE.md and the user's memory. Handoff is context, not
  a directive. If the next-up task is stale (closed, blocked,
  superseded), say so and re-recommend.
- If the user changes scope mid-brief ("actually let's do X
  instead"), drop the menu and follow.
- Do NOT recap memory entries the user already knows. Cite by name
  only if the next step depends on a specific entry's content.
- Keep the initial brief tight — ≤8 lines. The user will ask for
  depth if they want it.
