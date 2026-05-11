# The `with` Context Manager

`Trlib` is designed as a **context manager**, and the recommended use
is in combination with the `with` statement. This page explains why
`with` is needed, what happens internally, and the common mistakes —
in that order.

## Why `with` is needed

The `tr` library carries a **large global state** (the `TRCOMM` module
variables) on the Fortran side. There is a singleton constraint of
one instance per process (see Q4 of {doc}`faq`), and the dynamic
arrays allocated by `tr_init` must be released by `tr_finalize`.
Forgetting to release them causes:

- a memory leak (large arrays remain allocated),
- the next `Trlib()` call to be rejected with `TrlibStateError`,
- the inability to re-simulate within the same process.

The `with` statement is a Python language-level guarantee that **the
cleanup at the end of the block always runs**, so `tr_finalize` is
called even when an exception is raised.

```{admonition} Python's `with` statement (note)
:class: note

This is the same mechanism as `with open(...) as f:` for files. It is
the idiomatic pattern for resources (files, locks, database connections,
shared libraries, ...) where you want to "always do something on entry
and exit".
```

## Minimal usage

```python
from trlib import Trlib

with Trlib() as tr:
    tr.set_params(RR=3.0, BB=3.0)
    tr.run(ntmax=10)
    state = tr.get_state()
# ← tr_finalize runs the moment we leave the block
```

The instant we exit the `with` block, `Trlib.close()` (which calls
`tr_finalize` internally) runs.

## What happens internally

`Trlib`'s implementation is roughly as follows
(`python/trlib/trlib.py`):

```python
class Trlib:
    def __init__(self, *, lib_path=None):
        # load the library and call tr_init
        self._lib = _ffi.load_library(lib_path)
        ierr = self._lib.tr_init()
        raise_for_ierr("tr_init", ierr)
        self._closed = False

    def __enter__(self) -> "Trlib":
        return self                        # the object bound by `with X() as tr:`

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()                       # called whether or not an exception occurred

    def close(self) -> None:
        """Finalise the library. Idempotent."""
        if self._closed:
            return                         # double close is harmless
        ierr = self._lib.tr_finalize()
        self._closed = True
        raise_for_ierr("tr_finalize", ierr)

    def __del__(self) -> None:
        try:
            self.close()                   # GC-time fallback
        except Exception:
            pass                           # destructors must never raise
```

Key points:

- **`__init__` calls `tr_init`**. The library is already initialised
  the moment `Trlib()` returns. `__enter__` itself does nothing.
- **`__exit__` does not suppress exception propagation**. After
  `close()` runs, the original exception continues to propagate
  (`__exit__` does not return `True`).
- **`close()` is idempotent**. It is safe whether called by `with`,
  by explicit `tr.close()`, or by `__del__` (GC).
- **The destructor is a fallback**. If a reference is dropped without
  using `with`, `__del__` will try to `close()`, but the timing of GC
  is not guaranteed — **do not rely on it**.

## Without `with` (not recommended)

The explicit equivalent of `with` is:

```python
tr = Trlib()                          # tr_init runs here
try:
    tr.set_params(RR=3.0)
    tr.run(ntmax=10)
    state = tr.get_state()
finally:
    tr.close()                        # always runs, even on exception
```

Writing `try/finally` every time is tedious and easy to forget.
**Use `with` unless there is a specific reason not to.**

## What if an exception is raised?

Even if an exception is raised inside the `with` block, `__exit__`
(= `close()`) **always** runs.

```python
with Trlib() as tr:
    tr.set_params(RR=3.0, BB=3.0)
    tr.run(ntmax=10)
    raise RuntimeError("intentional error")  # ←
    state = tr.get_state()                   # not executed
# ← tr_finalize has already run before reaching this line
# the RuntimeError propagates out as-is
```

So neither memory leaks nor a stuck singleton can occur even on the
exception path.

```{admonition} What if `tr_finalize` itself fails?
:class: warning

When `__exit__` calls `close()` and `tr_finalize` returns a non-zero
ierr, `raise_for_ierr` raises `TrlibError`. In that case:

- If an exception was already in flight inside the `with` block, the
  original exception is preserved on `__context__` and the new
  `TrlibError` propagates (Python exception chaining).
- If no exception was in flight, `TrlibError` simply propagates.

In practice `tr_finalize` rarely fails, but it should be debuggable
through log collection.
```

## Common mistakes

### Mistake 1: trying to create a second instance in the same process

```python
with Trlib() as tr1:
    ...
with Trlib() as tr2:    # OK: tr1 has already been finalised
    ...

# ↓ NG
with Trlib() as tr1:
    with Trlib() as tr2:   # TrlibStateError (singleton violation)
        ...
```

After `tr_finalize` completes, the next `Trlib()` is fine. Two at the
same time is not allowed (see Q4 of {doc}`faq`).

### Mistake 2: trying to call `get_state` again outside the `with` block

```python
with Trlib() as tr:
    state = tr.get_state()
print(state.scalars["T"])    # OK: state is a pure Python object

# ↓ NG
with Trlib() as tr:
    pass
state = tr.get_state()       # TrlibStateError: tr is already closed
```

Once you leave the `with` block, the `tr` handle is closed. **Get the
result inside the block** and use it outside. `TrState` is a
`dataclass`, so you can reference it freely outside the block.

### Mistake 3: holding the block open for a long time

```python
with Trlib() as tr:
    tr.run(ntmax=100000)       # tens of minutes
    do_something_else()         # the memory allocated by Trlib stays put
```

Once the simulation finishes, leaving the `with` block before any
follow-up work avoids waste. Snapshotting just the result is enough:

```python
with Trlib() as tr:
    tr.run(ntmax=100000)
    state = tr.get_state()
# ← finalize here. From now on only state is used
do_something_else_with(state)
```

## Equivalents in other languages

The `with` statement corresponds to the following patterns in other
languages. Readers coming from C/C++ or Go may find these more
intuitive.

| Language | Pattern | Mapping |
|---|---|---|
| C++ | RAII (release in destructor) | behaves like a stack-local `Trlib()` instance |
| Java | try-with-resources | equivalent to `try (Trlib tr = new Trlib())` |
| Go  | `defer tr.Close()` | matches the exit of the `with` block |
| Rust | `Drop` trait | auto-drop at scope exit |

## Summary

- Always wrap `Trlib` in a `with` block.
- `__enter__` does nothing (just returns); initialisation finished in
  `__init__`.
- `__exit__` calls `close()` regardless of whether an exception was
  raised, firing `tr_finalize`.
- `close()` is idempotent. Calling it twice is safe.
- Pull the result (`TrState`) out inside the `with` block and use it
  outside.
