# The `with` Context Manager

`Tilib` follows the same context-manager design as `tr` / `eq`. This
page focuses on `ti`-specific aspects only. For the general meaning of
`with` and the common gotchas, see the corresponding `tr` page
(`docs/sphinx/modules/tr/en/context-manager.md`).

## Minimal usage

```python
from tilib import Tilib

with Tilib() as ti:
    ti.set_params(RR=3.0, BB=3.0, NSMAX=2)
    ti.run(ntmax=10)
    state = ti.get_state()
# ← ti_finalize runs the moment we leave the block
```

## `ti`-specific notes

### State of auxiliary-physics modules

`ti` internally references the state of other modules (`tr`, `eq`,
`bpsd`, …). As a result, constructing `Tilib()` also runs **`pl_init`
and `eq_init` behind the scenes**.

- Creating `Tilib()` and `Trlib()` **simultaneously in the same
  process will conflict** (both grab the same global `pl_*` state).
- If you experimented with `Trlib()` and then want to create
  `Tilib()`, leave the `Trlib()` block first (so that `tr_finalize`
  runs) and only then create `Tilib()`.

### Iteration solver state

`ti.run()` drives an inner iteration solver (up to `MAXLOOP`
iterations). If iteration does not converge, the resulting state is
**undefined** (implementation-dependent). It will be cleared properly
when `with` exits and `ti_finalize` runs, so it does not affect the
next `Tilib()` session.

## Without `with` (not recommended)

```python
ti = Tilib()                          # ti_init runs here
try:
    ti.set_params(RR=3.0, NSMAX=2)
    ti.run(ntmax=10)
    state = ti.get_state()
finally:
    ti.close()                        # always runs, even on exception
```

Writing `try/finally` every time is tedious — **use `with` unless you
have a specific reason not to**.

## Behaviour on exceptions

Even when an exception is raised inside the `with` block, `__exit__`
(i.e. `close()`) still runs and `ti_finalize` is invoked. As a result:

- The intermediate state of the iteration solver does not leak into
  the next session
- The shared `pl_*` state is reset cleanly
- Allocated arrays are freed
