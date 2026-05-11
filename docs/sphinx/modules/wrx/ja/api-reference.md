# `wrxlib` API リファレンス

本ページは `python/wrxlib/` のドキュメンテーション文字列 (docstring)
から `sphinx.ext.autodoc` で自動抽出したものです.

## `Wrxlib`

`libwrxapi.so` への in-process ハンドル.

```{eval-rst}
.. autoclass:: wrxlib.Wrxlib
   :members:
   :special-members: __enter__, __exit__
   :show-inheritance:
```

## `WrxState`

`wrx_get_state` の返り値.

```{eval-rst}
.. autoclass:: wrxlib.WrxState
   :members:
   :show-inheritance:
```

## 例外階層

```{eval-rst}
.. autoexception:: wrxlib.errors.WrxlibError
   :members:
.. autoexception:: wrxlib.errors.WrxlibInitError
.. autoexception:: wrxlib.errors.WrxlibParamError
.. autoexception:: wrxlib.errors.WrxlibStateError
.. autoexception:: wrxlib.errors.WrxlibRunError
.. autoexception:: wrxlib.errors.WrxlibNotImplementedError
```
