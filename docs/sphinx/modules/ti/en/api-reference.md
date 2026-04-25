# `tilib` API Reference

This page is auto-generated from the docstrings in `python/tilib/` via
`sphinx.ext.autodoc`. The source docstrings are the canonical
reference; everything below is extracted from them.

## `Tilib`

In-process handle to `libtiapi.so`. One live instance per process
(the singleton boundary is enforced via `TilibStateError`).

```{eval-rst}
.. autoclass:: tilib.Tilib
   :members:
   :special-members: __enter__, __exit__
   :show-inheritance:
```

## `TiState`

Return type of `ti_get_state`. A Python dataclass mirroring the
`ti_state_t` C struct.

```{eval-rst}
.. autoclass:: tilib.TiState
   :members:
   :show-inheritance:
```

## Exception hierarchy

```{eval-rst}
.. autoexception:: tilib.errors.TilibError
   :members:
.. autoexception:: tilib.errors.TilibInitError
.. autoexception:: tilib.errors.TilibParamError
.. autoexception:: tilib.errors.TilibStateError
.. autoexception:: tilib.errors.TilibRunError
.. autoexception:: tilib.errors.TilibNotImplementedError

.. autofunction:: tilib.errors.raise_for_ierr
```
