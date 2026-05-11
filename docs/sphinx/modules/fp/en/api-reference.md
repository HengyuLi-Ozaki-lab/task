# `fplib` API Reference

This page is auto-generated from the docstrings in `python/fplib/` via
`sphinx.ext.autodoc`.

## `Fplib`

In-process handle to `libfpapi.so`.

```{eval-rst}
.. autoclass:: fplib.Fplib
   :members:
   :special-members: __enter__, __exit__
   :show-inheritance:
```

## `FpState`

Return value of `fp_get_state`.

```{eval-rst}
.. autoclass:: fplib.FpState
   :members:
   :show-inheritance:
```

## Exception hierarchy

```{eval-rst}
.. autoexception:: fplib.errors.FplibError
   :members:
.. autoexception:: fplib.errors.FplibInitError
.. autoexception:: fplib.errors.FplibInvalidParamError
.. autoexception:: fplib.errors.FplibNotInitError
.. autoexception:: fplib.errors.FplibCalcFailedError
.. autoexception:: fplib.errors.FplibNotImplementedError
```
