# `totlib` API リファレンス

本ページは `python/totlib/` のドキュメンテーション文字列 (docstring)
から `sphinx.ext.autodoc` で自動抽出したものです.

## `Tot`

`libtotapi.so` への in-process ハンドル.

```{eval-rst}
.. autoclass:: totlib.Tot
   :members:
   :special-members: __enter__, __exit__
   :show-inheritance:
```

## `TotState`

`tot_get_state` の返り値.

```{eval-rst}
.. autoclass:: totlib.TotState
   :members:
   :show-inheritance:
```

## 例外階層

```{eval-rst}
.. autoexception:: totlib.errors.TotlibError
   :members:
.. autoexception:: totlib.errors.TotlibInitError
.. autoexception:: totlib.errors.TotlibInvalidParamError
.. autoexception:: totlib.errors.TotlibNotInitializedError
.. autoexception:: totlib.errors.TotlibCalculationFailedError
.. autoexception:: totlib.errors.TotlibNotImplementedError
```
