# コンテキストマネージャ `with` の解説

`Fplib` は `tr` / `eq` / `ti` と同じコンテキストマネージャ設計です. ここでは
fp 固有の側面に絞って解説します. 一般的な `with` 文の意味と落とし穴は
`tr` 側のコンテキストマネージャページ
(`docs/sphinx/modules/tr/ja/context-manager.md`) も参照してください.

## 最短の使い方

```python
from fplib import Fplib

with Fplib() as fp:
    fp.set_params(RR=3.0, BB=3.0, NSMAX=1)
    fp.set_param("NPMAX", 50)
    fp.set_param("NTHMAX", 25)
    fp.run(ntmax=5)
    state = fp.get_state()
# ← ブロックを抜けた瞬間に fp_finalize が走る
```

## fp 固有の注意点

### 大規模配列の解放

`fp` は 5D グリッド (`NRMAX × NPMAX × NTHMAX × NSAMAX`) を確保します.
たとえば `NRMAX=50, NPMAX=100, NTHMAX=50, NSAMAX=2` だと 50 万点に
分布関数の浮動小数 + 関連配列で **数百 MB** のメモリ確保になります.

`with` ブロックを抜けて `fp_finalize` が走らないと, このメモリが解放
されないままプロセスが進みます. 大規模グリッドでは `with` の使用が
特に重要です.

### `pl_*` 状態との共有

`fp` は `pl_*` モジュール状態を `tr` / `ti` と共有します. 同一プロセスで
`fp_mcp` と `tr_mcp` を両方ロードすると衝突します — 別プロセスで
立ち上げてください.

### 反復ソルバの再現性

`fp` の `run()` は内部反復 (`LMAXFP` 回まで) を回します. `run` を複数回
連続で呼ぶと, 内部の前回ステップ状態を初期値として再利用するため,
**`fp` 1 回の `run(ntmax=10)` と 10 回の `run(ntmax=1)` は微妙に異なる
場合があります** (反復履歴が違うため). 確実に再現したい場合は
1 回の `run(ntmax=N)` を推奨.

## `with` を使わない場合 (非推奨)

```python
fp = Fplib()                         # ここで fp_init
try:
    fp.set_params(RR=3.0, NSMAX=1)
    fp.run(ntmax=10)
    state = fp.get_state()
finally:
    fp.close()                       # 例外発生時も必ず実行
```
