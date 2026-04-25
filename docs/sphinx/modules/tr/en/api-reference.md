# `trlib` API Reference

This page is auto-extracted from the docstrings in `python/trlib/`
via `sphinx.ext.autodoc`. The source-code docstrings are the primary
reference, and changes there are reflected here.

## `Trlib`

In-process handle to `libtrapi.so`. One instance per process
(the singleton boundary is enforced via `TrlibStateError`).

```{eval-rst}
.. autoclass:: trlib.Trlib
   :members:
   :special-members: __enter__, __exit__
   :show-inheritance:
```

## `TrState`

Return type of `tr_get_state`. A Python dataclass corresponding to
the `tr_state_t` C struct. Field descriptions come from the
`Attributes:` block of the docstring, expanded inline by
`napoleon_use_ivar`.

```{eval-rst}
.. autoclass:: trlib.TrState
   :members:
   :show-inheritance:
```

## `TrDiagEntryPy` / `TrDiagCode`

Diagnostic entries returned by `Trlib.validate()` (PR #172).

```{eval-rst}
.. autoclass:: trlib.TrDiagEntryPy
   :members:
   :show-inheritance:

.. autoclass:: trlib.TrDiagCode
   :members:
   :undoc-members:
   :show-inheritance:
```

## Exception hierarchy

```{eval-rst}
.. autoexception:: trlib.errors.TrlibError
   :members:
.. autoexception:: trlib.errors.TrlibInitError
.. autoexception:: trlib.errors.TrlibParamError
.. autoexception:: trlib.errors.TrlibStateError
.. autoexception:: trlib.errors.TrlibRunError
.. autoexception:: trlib.errors.TrlibNotImplementedError

.. autofunction:: trlib.errors.raise_for_ierr
```
