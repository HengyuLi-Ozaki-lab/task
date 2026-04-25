# The `with` Context Manager

`Wrxlib` follows the same context-manager design as `tr`, `eq`, and `wr`.
This page focuses on the aspects specific to `wrx`. For a general
explanation of `with` semantics and pitfalls, see also the context-manager
page of the `tr` module
(`docs/sphinx/modules/tr/en/context-manager.md`).

## Minimal usage

```python
from wrxlib import Wrxlib

with Wrxlib() as wrx:
    wrx.set_params(RR=3.0, BB=3.0, NSMAX=1)
    wrx.set_param("NRAYMAX", 1)
    wrx.set_param("RFIN[1]", 170e9)
    wrx.set_param("RPIN[1]", 3.5)
    wrx.run(nray_request=1)
    state = wrx.get_state()
# ← wrx_finalize fires the moment we leave the block
```

## wrx-specific notes

### Memory used by beam curvature/width data

Because `wrx` tracks a beam shape (curvature tensor + wave-packet expansion
coefficients) for every ray, **memory consumption per ray is larger than
in `wr`**.

```
wr:  ray state ≈ 20 double per step
wrx: ray state ≈ 40–50 double per step  (curvature + width info included)
```

For large `NRAYMAX × NSTPMAX`, this can reach hundreds of MB. Memory is
not released until the `with` block exits.

### Using `wr` and `wrx` in the same process

`wr` (libwrapi.so) and `wrx` (libwrxapi.so) are **separate `.so` files**,
so loading both into the same process is fine. They both share the
`pl_*` state, however, so **they cannot be in the `init` state at the
same time**. Use them sequentially:

```python
with Wrlib() as wr:
    wr.set_param("RF", 170e9)
    wr.run(nray_request=1)

# after wr_finalize
with Wrxlib() as wrx:
    wrx.set_param("RFIN[1]", 170e9)
    wrx.run(nray_request=1)
```

### Argument name of `run`

In the Python API you write `run(nray_request=N)`, but inside the C ABI
this is treated as `nstpmax_arg` (the maximum-step-count override) in
some cases. If the behaviour differs from `wr`, consult the `wrxlib`
docstrings ({doc}`api-reference`).

## Behaviour on exceptions

Even if an exception is raised inside the `with` block, `__exit__` calls
`wrx_finalize` so that:

- Ray-trajectory buffers and beam-shape data are released
- The `pl_*` state is reset
- The next session is unaffected

## Without `with` (not recommended)

```python
wrx = Wrxlib()
try:
    wrx.set_params(RR=3.0, NSMAX=1)
    wrx.run(nray_request=1)
    state = wrx.get_state()
finally:
    wrx.close()
```
