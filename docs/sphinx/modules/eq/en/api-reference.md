# `eqlib` API Reference

This page is auto-generated from the docstrings in `python/eqlib/`
via `sphinx.ext.autodoc`. The source docstrings are the canonical
reference — everything below is a reflection of them.

## `Eq`

In-process handle to `libeqapi.so`. One live instance per process
(the singleton boundary is enforced via `EqlibError`). Note that
`eq.run()` takes a `mode` argument, not a time-step count.

```{eval-rst}
.. autoclass:: eqlib.Eq
   :members:
   :special-members: __enter__, __exit__
   :show-inheritance:
```

## `EqState`

Return type of `eq_get_state`. A Python dataclass mirroring the
`eq_state_t` C structure. Field descriptions come from the
`Attributes:` block of the class docstring (rendered inline via
`napoleon_use_ivar`).

```{eval-rst}
.. autoclass:: eqlib.EqState
   :members:
   :show-inheritance:
```

## `EqDiagEntryPy` / `EqDiagCode`

Diagnostic entries returned by `Eq.validate()` (PR #164 / #165).

```{eval-rst}
.. autoclass:: eqlib.EqDiagEntryPy
   :members:
   :show-inheritance:

.. autoclass:: eqlib.EqDiagCode
   :members:
   :undoc-members:
   :show-inheritance:
```

## Exception hierarchy

```{eval-rst}
.. autoexception:: eqlib.errors.EqlibError
   :members:
.. autoexception:: eqlib.errors.EqlibInitError
.. autoexception:: eqlib.errors.EqlibInvalidParamError
.. autoexception:: eqlib.errors.EqlibNotInitializedError
.. autoexception:: eqlib.errors.EqlibCalculationFailedError
.. autoexception:: eqlib.errors.EqlibNotImplementedError

.. autofunction:: eqlib.errors.raise_for_rc
.. autofunction:: eqlib.errors.raise_for_ierr
```

### Legacy camelCase aliases

For backwards compatibility with caller code written against an early
API draft, `python/eqlib/errors.py` also re-exports the exception
classes under `EqLib*` (capital L-ib) names:

- `EqLibError` ≡ `EqlibError`
- `EqLibInvalidParam` ≡ `EqlibInvalidParamError`
- `EqLibNotInitialized` ≡ `EqlibNotInitializedError`
- `EqLibCalculationFailed` ≡ `EqlibCalculationFailedError`
- `EqLibNotImplemented` ≡ `EqlibNotImplementedError`

New code should use the canonical `Eqlib*` names. The aliases remain
as module attributes but are not separately documented.
