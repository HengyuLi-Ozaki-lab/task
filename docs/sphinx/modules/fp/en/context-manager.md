# The `with` Context Manager

`Fplib` follows the same context-manager design as `tr` / `eq` / `ti`.
This page focuses on `fp`-specific aspects. For the general meaning of
the `with` statement and its pitfalls, see the `tr` context-manager
page (`docs/sphinx/modules/tr/en/context-manager.md`).

## Minimal usage

```python
from fplib import Fplib

with Fplib() as fp:
    fp.set_params(RR=3.0, BB=3.0, NSMAX=1)
    fp.set_param("NPMAX", 50)
    fp.set_param("NTHMAX", 25)
    fp.run(ntmax=5)
    state = fp.get_state()
# ← fp_finalize fires the moment we leave the block
```

## fp-specific notes

### Releasing large arrays

`fp` allocates a 5D grid (`NRMAX × NPMAX × NTHMAX × NSAMAX`). For
example, `NRMAX=50, NPMAX=100, NTHMAX=50, NSAMAX=2` gives roughly
500 000 grid points; with the distribution-function floats and the
related auxiliary arrays this comes to **several hundred MB**.

If you leave the `with` block without running `fp_finalize`, that
memory stays committed for the rest of the process. Using `with` is
especially important for large grids.

### Sharing `pl_*` state

`fp` shares the `pl_*` module state with `tr` / `ti`. Loading both
`fp_mcp` and `tr_mcp` in the same process causes a collision — start
them in separate processes.

### Iterative-solver reproducibility

`fp.run()` runs an inner iteration (up to `LMAXFP` times). Calling
`run` repeatedly reuses the previous step's internal state as the
initial guess, so **a single `run(ntmax=10)` and ten `run(ntmax=1)`
calls can give slightly different results** (the iteration histories
differ). For strict reproducibility, prefer a single `run(ntmax=N)`.

## Without `with` (not recommended)

```python
fp = Fplib()                         # fp_init runs here
try:
    fp.set_params(RR=3.0, NSMAX=1)
    fp.run(ntmax=10)
    state = fp.get_state()
finally:
    fp.close()                       # always runs, even on exceptions
```
