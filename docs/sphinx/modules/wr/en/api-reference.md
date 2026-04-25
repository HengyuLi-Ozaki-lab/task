# `wrlib` API Reference

This page is generated from the docstrings in `python/wrlib/` via
`sphinx.ext.autodoc`.

## `Wrlib`

In-process handle to `libwrapi.so`.

```{eval-rst}
.. autoclass:: wrlib.Wrlib
   :members:
   :special-members: __enter__, __exit__
   :show-inheritance:
```

## `WrState`

The return value of `wr_get_state`.

```{eval-rst}
.. autoclass:: wrlib.WrState
   :members:
   :show-inheritance:
```

## Exception hierarchy

```{eval-rst}
.. autoexception:: wrlib.errors.WrlibError
   :members:
.. autoexception:: wrlib.errors.WrlibInitError
.. autoexception:: wrlib.errors.WrlibParamError
.. autoexception:: wrlib.errors.WrlibStateError
.. autoexception:: wrlib.errors.WrlibRunError
.. autoexception:: wrlib.errors.WrlibNotImplementedError
```
