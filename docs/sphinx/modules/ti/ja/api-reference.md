# `tilib` API リファレンス

本ページは `python/tilib/` のドキュメンテーション文字列 (docstring)
から `sphinx.ext.autodoc` で自動抽出したものです. ソースコードの
docstring が一次情報で, ここに反映されます.

## `Tilib`

`libtiapi.so` への in-process ハンドル. 1 プロセス 1 インスタンス
(シングルトン境界は `TilibStateError` で強制).

```{eval-rst}
.. autoclass:: tilib.Tilib
   :members:
   :special-members: __enter__, __exit__
   :show-inheritance:
```

## `TiState`

`ti_get_state` の返り値. `ti_state_t` C 構造体と対応する Python dataclass.

```{eval-rst}
.. autoclass:: tilib.TiState
   :members:
   :show-inheritance:
```

## 例外階層

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
