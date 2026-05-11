# `totlib` API Reference

This page is auto-extracted from the docstrings in `python/totlib/` via
`sphinx.ext.autodoc`.

## `Tot`

In-process handle to `libtotapi.so`.

```{eval-rst}
.. autoclass:: totlib.Tot
   :members:
   :special-members: __enter__, __exit__
   :show-inheritance:
```

## `TotState`

Return value of `tot_get_state`.

```{eval-rst}
.. autoclass:: totlib.TotState
   :members:
   :show-inheritance:
```

## Exception hierarchy

```{eval-rst}
.. autoexception:: totlib.errors.TotlibError
   :members:
.. autoexception:: totlib.errors.TotlibInitError
.. autoexception:: totlib.errors.TotlibInvalidParamError
.. autoexception:: totlib.errors.TotlibNotInitializedError
.. autoexception:: totlib.errors.TotlibCalculationFailedError
.. autoexception:: totlib.errors.TotlibNotImplementedError
```
