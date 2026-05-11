# `wrlib` API リファレンス

本ページは `python/wrlib/` のドキュメンテーション文字列 (docstring)
から `sphinx.ext.autodoc` で自動抽出したものです.

## `Wrlib`

`libwrapi.so` への in-process ハンドル.

```{eval-rst}
.. autoclass:: wrlib.Wrlib
   :members:
   :special-members: __enter__, __exit__
   :show-inheritance:
```

## `WrState`

`wr_get_state` の返り値.

```{eval-rst}
.. autoclass:: wrlib.WrState
   :members:
   :show-inheritance:
```

## 例外階層

```{eval-rst}
.. autoexception:: wrlib.errors.WrlibError
   :members:
.. autoexception:: wrlib.errors.WrlibInitError
.. autoexception:: wrlib.errors.WrlibParamError
.. autoexception:: wrlib.errors.WrlibStateError
.. autoexception:: wrlib.errors.WrlibRunError
.. autoexception:: wrlib.errors.WrlibNotImplementedError
```
