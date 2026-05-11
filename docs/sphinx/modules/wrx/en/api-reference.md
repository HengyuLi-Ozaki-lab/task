# `wrxlib` API Reference

This page is auto-generated from the docstrings in `python/wrxlib/`
using `sphinx.ext.autodoc`.

## `Wrxlib`

In-process handle to `libwrxapi.so`.

```{eval-rst}
.. autoclass:: wrxlib.Wrxlib
   :members:
   :special-members: __enter__, __exit__
   :show-inheritance:
```

## `WrxState`

Return value of `wrx_get_state`.

```{eval-rst}
.. autoclass:: wrxlib.WrxState
   :members:
   :show-inheritance:
```

## Exception hierarchy

```{eval-rst}
.. autoexception:: wrxlib.errors.WrxlibError
   :members:
.. autoexception:: wrxlib.errors.WrxlibInitError
.. autoexception:: wrxlib.errors.WrxlibParamError
.. autoexception:: wrxlib.errors.WrxlibStateError
.. autoexception:: wrxlib.errors.WrxlibRunError
.. autoexception:: wrxlib.errors.WrxlibNotImplementedError
```
