# `equ` — 自由境界平衡

```{admonition} この章で学ぶこと
:class: tip

TASK/EQU (安積による**自由境界** MHD 平衡コード) を Python (`equlib`)・C
(`equ/equ_api.h`)・MCP クライアント (`equ_mcp`) から実行し, 平衡を状態・ψ(R, Z)・
G-EQDSK ファイルとして得る方法.
```

## `equ` がすること

EQU はコイルのあるトカマクの自由境界平衡を解く. プラズマ境界は, コイル電流 (固定,
またはマーカー点への当てはめ) と圧力・電流分布から決まる. 入力は `&EQU` ネームリストと
コイルファイルで, 対話型プログラム `equ` として動く. ライブラリは同じコードを実行する.

- **`run(mode=1)`** — プログラムの `R` コマンド: セットアップ解, 模擬 TR インタフェースの
  分布の bpsd 経由の受け渡し, FCT 解. その G-EQDSK は例題でプログラムのもの (`R` の後 `E`)
  と 1e-10 で一致する.
- **`run(mode=0)`** — `R` の最初の段階 (`equ_prof`) だけ.

```{note}
`equ` は `eq` とは別のコードである. `eq` (TASK/EQ) は固定境界の平衡を解くかファイルから
読み込む. `equ` はコイルから境界を求める. `equ` の G-EQDSK は `eq` (`MODELG=5`) で読めるが,
EQU は圧力を MPa で書く ([状態](state.md) を参照).
```

```{toctree}
:maxdepth: 1

quickstart
parameters
state
mcp
```

設計と決定事項: `docs/superpowers/specs/2026-11-22-equ-library-design.md`,
構成: `docs/equ-library/architecture.md`.
