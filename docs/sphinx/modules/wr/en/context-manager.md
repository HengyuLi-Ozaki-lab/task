# The `with` Context Manager

`Wrlib` shares the same context-manager design as `tr` / `eq`. This page
focuses on `wr`-specific aspects. For the general meaning of the `with`
statement and its pitfalls, see the corresponding page in the `tr`
module (`docs/sphinx/modules/tr/en/context-manager.md`).

## Minimal usage

```python
from wrlib import Wrlib

with Wrlib() as wr:
    wr.set_params(RR=3.0, BB=3.0)
    wr.set_param("RF", 170e9)
    wr.run(nray_request=1)
    state = wr.get_state()
# ← wr_finalize runs the moment the block exits
```

## `wr`-specific notes

### Ray-buffer size

`wr` allocates a ray-trajectory buffer of size `NRAYMAX × NSTPMAX`. With
large `NSTPMAX` (e.g. 10000 steps × 100 rays) the memory cost is no
longer negligible. Use `with` to make sure `finalize` runs and frees the
buffer.

### Relationship between `wr` and `wrx`

`wr` (geometric optics ray tracing) and `wrx` (beam tracing) share much
of their source code, but they are **separate C ABIs / separate `.so`s**.
Both can be loaded in the same process, but each is its own `Wrlib` /
`Wrxlib` instance.

### Static-state handling

The `wr` Fortran side shares `pl_*` with the other modules, just like
they all do. Constructing `Wrlib()` also runs `pl_init`, so do not start
`tr_mcp` and `wr_mcp` in the same process simultaneously.

## Behaviour on exceptions

If an exception is raised inside the `with` block, `__exit__` still
calls `wr_finalize`, so:

- ray buffers are freed
- `pl_*` state is reset
- the next `Wrlib()` session is unaffected

## Without `with` (not recommended)

```python
wr = Wrlib()                          # wr_init runs here
try:
    wr.set_params(RR=3.0)
    wr.run(nray_request=1)
    state = wr.get_state()
finally:
    wr.close()
```
