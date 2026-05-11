# `fplib` API リファレンス

本ページは `python/fplib/` のドキュメンテーション文字列 (docstring)
から `sphinx.ext.autodoc` で自動抽出したものです.

## `Fplib`

`libfpapi.so` への in-process ハンドル.

```{eval-rst}
.. autoclass:: fplib.Fplib
   :members:
   :special-members: __enter__, __exit__
   :show-inheritance:
```

## `FpState`

`fp_get_state` の返り値.

```{eval-rst}
.. autoclass:: fplib.FpState
   :members:
   :show-inheritance:
```

## 例外階層

```{eval-rst}
.. autoexception:: fplib.errors.FplibError
   :members:
.. autoexception:: fplib.errors.FplibInitError
.. autoexception:: fplib.errors.FplibInvalidParamError
.. autoexception:: fplib.errors.FplibNotInitError
.. autoexception:: fplib.errors.FplibCalcFailedError
.. autoexception:: fplib.errors.FplibNotImplementedError
```
