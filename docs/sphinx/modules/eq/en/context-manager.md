# The `with` Context Manager

The `Eq` class is designed as a context manager and is intended to be
used with the `with` statement. The mechanism is identical to `tr`'s,
so the `tr` version of this page (`docs/sphinx/modules/tr/en/context-manager.md`)
is also a useful reference.

## Why `with` is necessary

The Fortran side of `eq` carries **global module state** such as the
EQCOMM blocks, with a singleton constraint of one instance per process.
`eq_init` allocates dynamic arrays and `eq_finalize` releases them, and
the two must be paired.

The `with` statement is a Python-level guarantee that **the cleanup
runs at block exit**. This ensures that `eq_finalize` is called even
when an exception is raised.

## Minimal usage

```python
from eqlib import Eq

with Eq() as eq:
    eq.set_param("RR", 6.5)
    eq.set_param("BB", 5.3)
    eq.set_param("RIP", 1.5)
    eq.run()
    state = eq.get_state()
# ← eq_finalize runs the moment we leave the block
```

## What happens internally

The `Eq` implementation looks roughly like this:

```python
class Eq:
    def __init__(self, *, lib_path=None):
        self._lib = _ffi.load_library(lib_path)
        ierr = self._lib.eq_init()
        raise_for_ierr("eq_init", ierr)
        self._closed = False

    def __enter__(self) -> "Eq":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        """Finalise the library. Idempotent."""
        if self._closed:
            return
        ierr = self._lib.eq_finalize()
        self._closed = True
        raise_for_ierr("eq_finalize", ierr)
```

Key points:

- `__init__` calls `eq_init`. The library is initialised the moment
  `Eq()` is created.
- `__exit__` does not suppress exception propagation; it calls
  `close()` and then lets the original exception fly out.
- `close()` is idempotent — double calls are safe.

## Without `with` (not recommended)

```python
eq = Eq()                         # eq_init here
try:
    eq.set_param("RR", 6.5)
    eq.run()
    state = eq.get_state()
finally:
    eq.close()                    # always runs, even on exception
```

Writing `try/finally` every time is tedious, so **use `with` unless you
have a special reason not to**.

## What happens on an exception

Even if an exception is raised inside the `with` block, `__exit__`
(and therefore `close()`) **always** runs. This prevents memory leaks
and stale-state issues.

## Common mistakes

### Trying to grab `state` outside `with`

```python
with Eq() as eq:
    state = eq.get_state()
print(state.scalars["raxis"])    # OK: state is a pure-Python object

# ↓ NG
with Eq() as eq:
    pass
state = eq.get_state()           # EqlibError: eq is already closed
```

The `eq` handle is closed once the block exits. If you need the
result, **fetch it inside the block** and use it outside.

### Trying to create a second instance in the same process

```python
# ↓ NG (singleton violation)
with Eq() as eq1:
    with Eq() as eq2:    # EqlibError
        ...
```

Sequential creation is fine:

```python
with Eq() as eq1:
    ...
with Eq() as eq2:        # OK: eq1 is already finalised
    ...
```
