# Pitfalls and anti-patterns

Distilled from the six modules library-ized in 2026-04-17/18. When you
hit one of these, read this file before debugging from scratch.

## Build / linker

### bpsd PIC archive missing
**Symptom:** `lib<module>api.so` fails to link with undefined references
to `bpsd_*`.
**Cause:** bpsd's vendored Makefile only builds the static `libbpsd.a`
(non-PIC). The `.so` link needs `libbpsd_pic.a`.
**Fix:** Add an in-tree `libbpsd_pic.a` target to `bpsd/Makefile`:

```make
PIC_OBJS = $(SRCS:%.f90=obj/pic/%.o)
obj/pic/%.o: %.f90
	$(FC) $(FFLAGS) -fPIC -Jmod_pic -c $< -o $@
libbpsd_pic.a: $(PIC_OBJS) | obj/pic mod_pic
	$(AR) rcs $@ $^
```

DO NOT install PIC artefacts to the standard `obj/` tree — that breaks
the non-PIC `<module>` binary build.

### --start-group / --end-group required
**Symptom:** Cross-archive symbols unresolved at link time.
**Cause:** TASK's PIC archives have cyclic dependencies
(`libpl_pic.a` ↔ `libeq_pic.a`).
**Fix:** Wrap the archives in `-Wl,--start-group ... -Wl,--end-group`
so the linker re-scans.

### Residual graphics symbols
**Symptom:** Link succeeds with warnings about undefined
`gsline_`, `viewgtlist_`, etc. Or `dlopen()` fails at runtime with
`undefined symbol`.
**Cause:** Even after L-1 splits SRCS_GRAPHICS out, some `.o` files in
SRCS_CORE reference graphics symbols from unreachable code paths
(e.g., a `?` menu branch in `<module>fout.f90`).
**Fix:** Two layers:
1. Link with `-Wl,--unresolved-symbols=ignore-in-shared-libs` so the
   `.so` is produced.
2. Python wrapper opens with `RTLD_LAZY` (mode=1) so symbols are
   resolved at first use, not at dlopen. Since the C ABI never calls
   the unreachable paths, lazy binding is safe.

### libgrf::grd1d cannot be link-time stubbed (wrx-specific)
**Symptom:** wrx's `wrcalpwr.f90` calls `libgrf::grd1d` which is a
**module procedure**, not a plain symbol. Linker stubs do not work.
**Fix:** Don't try to stub. Gate `wrx.run()` behind an env var
(`WRX_RUN_OK=1`) and document the limitation. wrx's other entry
points (init, set_param, get_state, finalize) work normally.

## C ABI

### Name collision with legacy SUBROUTINE
**Symptom:** `<module>_api.f90` won't compile — symbol `<module>_init`
already defined in `<module>init.f`.
**Fix:** USE-rename + `BIND(C, NAME=...)`:

```fortran
USE <module>init, ONLY: <module>init_fortran => <module>_init
FUNCTION <module>_api_init() RESULT(ierr) BIND(C, NAME="<module>_init")
   CALL <module>init_fortran      ! invoke the legacy SUBROUTINE
END FUNCTION
```

The Fortran-side function is named `<module>_api_init` (no collision);
the C-side public symbol is `<module>_init` (per spec).

### Fortran/C array memory layout
**Symptom:** Python wrapper returns garbage for profile arrays.
**Cause:** C declares `RN[NRMAX][NSMAX]` row-major; Fortran column-major
matching declaration is `RN(NSMAX, NRMAX)`. If you instead declare
`RN(NRMAX, NSMAX)` in Fortran, the bytes are transposed.
**Fix:** Always declare Fortran with **species index first**:
`RN(NSMAX, NRMAX)`. Then `state.RN[i][j]` in Python (row-major)
matches `RN(j+1, i+1)` in Fortran (column-major, 1-origin).

### Fixed-size struct vs runtime dims
The C struct uses `<MOD>_MAX_*` compile-time maxima. At runtime,
only the `[0..nrmax-1]` slice carries valid data; the rest is padding.
The Python `state.to_dict()` should slice to `state.nrmax × state.nsmax`
before returning.

## Parameter registry

### Bare-name array writes silently corrupt state
**Symptom:** `set_param("PA", 1.0)` returns OK but the array is
unchanged or `PA(0)` is written (out-of-bounds).
**Cause:** `parse_array_subscript("PA", base, idx)` left `idx`
uninitialized or zero.
**Fix:** Initialize `idx = -1` as a sentinel. Every array CASE branch
checks `IF (idx < 1 .OR. idx > SIZE(arr)) THEN; ierr = 1; ELSE; ...`.

This was caught by Bugbot on `eq` PR #78 — see commit `966cda23`
("fix(eq-registry): reject bare PSIB (0-origin array), default idx=-1").

### Strings vs numerics
String parameters (e.g. `KNAMEQ`) cannot go through `set_param(name, double)`.
**Fix:** Add a separate entry point `<module>_set_param_str(name, str)`.
Python wrapper has both `set_param(name, value)` and
`set_param_str(name, value)`; MCP server's `set_params` dispatches by
type.

## Python wrapper

### Repository root off-by-one
**Symptom:** `_ffi.py` reports `lib<module>api.so not found`.
**Cause:** `Path(__file__).resolve().parents[1]` instead of `parents[2]`.
**Fix:** From `python/<module>lib/_ffi.py`, the repo root is two
parents up, not one (`parents[2]`).

### numpy hard dependency
**Symptom:** Wrapper import fails on bare Python install.
**Fix:** Wrap numpy import in try/except, set `HAS_NUMPY` flag, degrade
to plain Python lists. Tests skip numpy-specific assertions if
`not HAS_NUMPY`.

### Forgot to attach set_param_str to old .so
**Symptom:** Wrapper import fails on .so built before L-3 wired
`set_param_str`.
**Fix:** In `_apply_prototypes`, wrap `lib.<module>_set_param_str`
attribute access in `try/except AttributeError: pass`. Wrapper raises
on first call instead.

## Tests

### Fixture order matters
**Symptom:** Layer 1 equivalence test fails by exactly the difference
between two PA values.
**Cause:** Set `PA[1]` before `NSMAX` — the registry checked the index
against the old (smaller) `SIZE(PA)`.
**Fix:** Always set `NSMAX` first in fixture `PARAMS` dict, then array
elements. Use an `OrderedDict` if dict ordering is suspect.

### NaN in sweep results
**Symptom:** `test_sweep` flakes occasionally with `assert isfinite()`.
**Cause:** Some parameter combos drive the kernel into a degenerate
regime (e.g., RR=0).
**Fix:** Add a `SKIP_COMBOS` set to the sweep test for known-bad
combos. The sweep is for NaN/Inf detection in *good* combos, not
robustness against absurd inputs.

## Process / git

### Sandbox bash denial mid-task
**Symptom:** Agent reports "Permission to use Bash has been denied"
after running successfully for several turns.
**Cause:** Some sandbox profiles revoke Bash on long-running agents.
**Fix:** Plan to write all files via the file-edit tools first
(Write/Edit), then ask the parent agent or user to do the git
operations. Use `isolation: "worktree"` in the agent spawn so file
edits land in an isolated checkout.

### Cache stale "CONFLICTING" PRs
**Symptom:** GitHub shows `CONFLICTING` even after `git fetch` /
`git rebase origin/develop` shows no conflicts.
**Cause:** GitHub's mergeability cache lags ~5 minutes behind.
**Fix:** Either wait, or recover by:
1. Create a fresh branch off `origin/develop`.
2. `git checkout <pr-branch> -- <changed-files>` to copy diffs.
3. Push the new branch and open a new PR.
4. Close the old PR with a comment linking the new one.

### Don't bypass Bugbot
**Symptom:** Tempting to `gh pr merge --admin` because Bugbot is slow.
**Don't:** Bugbot has caught real issues in this codebase (the bare-name
sentinel was found by Bugbot). Always wait for `Cursor Bugbot` check
`COMPLETED` before merging.

After pushing a fix, post `@cursor review` (NOT `@cursorbot review`) to
retrigger the bot.

### Conflict in shared config files
**Symptom:** `Makefile` or `test_definitions.conf` conflicts between
two parallel module branches.
**Fix:** Merge BOTH sections side-by-side. The library-ization PRs
intentionally namespace by module prefix (`trlib_`, `tilib_`,
`fplib_`, ...) so all entries can coexist.

## Documentation

### README.md emojis
**Symptom:** PR review asks to remove emojis.
**Fix:** TASK docs are emoji-free. Keep Japanese (です・ます調) prose,
use `**bold**` for emphasis, ASCII-art for diagrams.

### Architecture diagram > 80 columns
**Symptom:** ASCII diagram wraps in PR review pane.
**Fix:** Keep diagram lines ≤ 80 columns. Split wide boxes vertically.

### Examples need --dry-run
**Symptom:** Docs CI fails because `quickstart.py` requires the `.so`
which isn't built in the docs-only job.
**Fix:** Examples must early-exit on `--dry-run`:

```python
if "--dry-run" in sys.argv:
    print("dry-run OK")
    sys.exit(0)
```
