---
name: sphinx-module-manual
description: Use this skill when expanding, restructuring, or creating a TASK module manual under docs/sphinx/modules/<mod>/{en,ja}/. Apply this pattern for new modules (ti / fp / wr / wrx / tot when filling placeholders) and for cross-language synchronization. Establishes the page split, naming conventions, content templates, and required cross-references the project has standardized on (as of 2026-04-25, after tr/ja and eq/ja were converted to this layout).
---

# Sphinx module manual — standard layout

## When to apply

- Expanding a placeholder module (`ti`, `fp`, `wr`, `wrx`, `tot`) into a full chapter
- Synchronising the English version of a module from a completed Japanese version (or vice versa)
- Adding a new module to TASK that needs library documentation
- Refactoring a single-page `index.md` that has grown long enough to warrant splitting

The reference implementations are:
- `docs/sphinx/modules/tr/ja/` — first module written in this layout
- `docs/sphinx/modules/eq/ja/` — second, validates the pattern

## Hybrid Sphinx infrastructure (already set up)

```
docs/sphinx/
├── conf_common.py            shared config (extensions, theme, mathjax, css)
├── _shared_static/
│   └── toc_h2_only.css       hides H3+ from furo right sidebar
├── portal/{en,ja}/           landing page with sphinx-design cards
├── modules/<mod>/{en,ja}/    per-module independent Sphinx project
└── shared/notebooks/         executable .ipynb (symlinked into modules)
```

Key `conf_common.py` settings (do NOT change without strong reason):
- `html_theme = "furo"` — left sidebar = page nav, right sidebar = on-this-page
- `myst_enable_extensions = [..., "dollarmath", "amsmath"]` — `$...$` and `$$...$$` work
- `html_css_files = ["toc_h2_only.css"]` — right sidebar shows H2 only
- `toc_object_entries = False` — autodoc symbols don't pollute TOC

The Makefile has per-module targets: `make tr-ja`, `make eq-en`, etc. Build order: portal → modules (intersphinx dependency).

## Page split — use these filenames

A complete module has these pages (some may be omitted if not relevant):

```
modules/<mod>/<lang>/
├── index.md                   landing page (overview + 4-group toctree)
├── build.md                   ライブラリビルド・nm 確認・PYTHONPATH
├── hello-world.md             5–8 行の最短例 + 行ごと解説 + 期待出力
├── parameters.md              全パラメータの完全リファレンス + 必須セクション
├── parameter-setting.md       4 通りの指定方法 (scalar/array/string/validate)
├── state.md                   全出力フィールドの解説
├── context-manager.md         with 文の意味と落とし穴
├── faq.md                     つまずきどころ Q&A
├── quickstart.md              notebook へのリンク (myst-nb)
├── api-reference.md           autodoc (eval-rst)
├── design.md                  Fortran 設計の具体的解説
├── mcp.md                     <mod>_mcp サーバの使い方
├── testing.md                 4 層テストの具体的解説
├── appendix-sensitivity.md    入力 ↔ 出力の対応 (代数 + 物理スケーリング)
├── appendix-<switch>.md       重要 switch (例: MDLKAI) の全値解説
└── <mod>-quickstart.ipynb     symlink → ../../../shared/notebooks/
```

## Title naming convention (CRITICAL — keep consistent across modules)

| ファイル | H1 タイトル |
|---|---|
| `parameters.md` | `# サポートされている入力パラメータ` |
| `parameter-setting.md` | `# 入力パラメータの指定方法` |
| `state.md` | `# 出力されるパラメータ・物理量 (\`<MOD>State\`)` |
| `context-manager.md` | `# コンテキストマネージャ \`with\` の解説` |
| `faq.md` | `# FAQ — \`<mod>\` 固有` または `# FAQ / つまずきどころ` |
| `design.md` | `# Fortran 設計` |
| `mcp.md` | `# MCP サーバ (\`<mod>_mcp\`)` |
| `testing.md` | `# テスト` |
| `appendix-sensitivity.md` | `# 付録: 入力パラメータと出力の対応` |

「入力／出力」の対比を一貫させること。「サポートされているパラメータ」(無印) は使わない。

## index.md structure

```markdown
# `<mod>` — <module display name>

```{admonition} この章で学ぶこと
:class: tip

<1-2 paragraph elevator pitch — what this module does and what's covered>
```

## 概要 — `<mod>` は何をする

<3-5 paragraphs on physics + outputs + key concepts>

## 使い方ガイド

```{toctree}
:maxdepth: 1

build
hello-world
parameters
parameter-setting
state
context-manager
faq
```

## リファレンス

```{toctree}
:maxdepth: 1

quickstart
api-reference
```

## 内部情報

```{toctree}
:maxdepth: 1

design
mcp
testing
```

## 付録

```{toctree}
:maxdepth: 1

appendix-sensitivity
<other-appendix-files>
```

## 読みすすめ方

初めて触る場合は次の順序がおすすめです:

1. {doc}`build`
2. {doc}`hello-world`
3. {doc}`parameters`
4. {doc}`parameter-setting`
5. {doc}`state`
6. {doc}`context-manager`
7. {doc}`quickstart`

困ったときは {doc}`faq` を. API の完全仕様は {doc}`api-reference`.
入力 ↔ 出力の対応関係は {doc}`appendix-sensitivity` へ.
```

The 4-group split (使い方ガイド / リファレンス / 内部情報 / 付録) maps to 4 sidebar captions and 4 H2 sections so right-sidebar TOC has all groups.

## parameters.md — required sections

Always start with:

```markdown
# サポートされている入力パラメータ

`<mod>/<mod>_param_registry.f90` に登録されているパラメータを論理グループ別に
示します. 既定値は `<mod>/<init-source>.f90` で設定されます.

## 必須・推奨パラメータ

### 必須 (条件付き)

| 条件 | 必須パラメータ | 理由 |
|---|---|---|
| <condition> | **`<NAME>`** | <reason> |

### 強く推奨 (既定値が generic すぎる)

| 名前 | 既定値 | 推奨上書き例 (ITER 想定) |
|---|---|---|
| `RR` | <default> | <iter-value> |
...

### 推奨ワークフロー

```python
from <mod>lib import <Class>, <Class>DiagCode

with <Class>() as <handle>:
    <handle>.set_params(...)            # 必須項目
    diags = <handle>.validate()         # 事前検証
    if diags:
        raise SystemExit("fix diagnostics before running")
    <handle>.run(...)
    state = <handle>.get_state()
```
```

Then logical groups (numbered `## 1. 幾何・装置`, `## 2. ...`, etc.) with this column layout:

```
| 名前 | 型 | 既定値 | 単位 | 意味 |
```

For switch parameters (e.g. `MDLKAI`), inline a sub-table:

```
`MODELG` の許容値:

| 値 | 挙動 |
|---|---|
| <int> (既定) | <description> |
```

If a switch has too many values for an inline table (10+), put it in `appendix-<switch>.md`.

## state.md — required sections

```markdown
# 出力されるパラメータ・物理量 (`<MOD>State`)

`<handle>.get_state()` は `<MOD>State` dataclass を返します. これがシミュレーション
結果として取得できる量の全リストです.

## 次元情報 (dimension fields)

| フィールド | 意味 |
|---|---|
| `state.<dim1>` | <meaning> |

## スカラー量 (<N> 個, `state.scalars` 辞書)

| キー | 単位 | 意味 |
|---|---|---|
| `<key>` | <unit> | <meaning + formula if known> |

## プロファイル量 (radial profiles)

```python
state.<array>[i]      # <description> [<unit>]
```

## 補助メソッド

```python
state.to_dict()       # JSON-ready dict
```
```

## appendix-sensitivity.md — required structure

Two sections only:

1. **代数的・直接的に決まる関係** — algebraic / 100 % deterministic
2. **物理スケーリングとして既知の傾向** — qualitative ↑/↓ from physics literature

DO NOT include model-dependent sensitivity (e.g. how MDLKAI choice changes WPT). That's research territory and belongs in user simulations.

Use the legend admonition:
```markdown
- **↑**: 入力を増やすと出力も増える (単調増加)
- **↓**: 入力を増やすと出力は減る (単調減少)
- **=**: 入力に等しい / 直接決まる
- **⊕**: 入力を ON にすると追加項として現れる
- **〜**: 概ね成り立つ (高次効果で逆転しうる)
```

Column layout for tables:

```
| 入力 | 主に影響する出力 | 方向 | 物理的根拠 |
```

DO NOT put arrows in the "主に影響する出力" column — only in "方向".

## design.md — required sections

```markdown
# Fortran 設計

## エントリ層 (`<mod>_api.f90`)
| C シンボル | Fortran 側 | 役割 |

### C 構造体レイアウト (`<mod>_state_t`)

## パラメータレジストリ (`<mod>_param_registry.f90`)

## ライブラリ内部のソース構成
| グループ | 主なファイル | 役割 |

## PIC ビルドの依存関係
```

If the module went through F90 modernisation phases (F-1..F-5), include that table.

## testing.md — required sections

```markdown
# テスト

## 4 層の役割

| 層 | ターゲット | 何を検証するか | tolerance |
|---|---|---|---|
| **Layer 1** | `<mod>lib_equivalence` | <baselines>と完全一致 | **1e-10** (厳守) |
| **Layer 2** | `<mod>lib_c_abi` | C ABI の ierr | — |
| **Layer 3** | `<mod>lib_ffi`, `<mod>lib_wrapper` | ctypes / lifecycle | — |
| **Layer 4** | `<mod>lib_sweep` | 9 ケース smoke | — |

## Layer 1 (等価性テスト) の中身

<5-step procedure>

## よく使うファイル

- `python/<mod>lib/tests/test_*.py`
- `test_run/baselines/<case>/metrics.json`
- `test_run/test_definitions.conf`
```

Always include the `@pytest.mark.skip` 禁止 admonition.

## mcp.md — required sections

```markdown
# MCP サーバ (`<mod>_mcp`)

## アーキテクチャ
<ascii diagram>

## 前提条件 / インストール / 動作確認

## LLM クライアントへの登録
- Claude Desktop (claude_desktop_config.json)
- Claude Code (claude mcp add ...)
- Cursor (.cursor/mcp.json)

## 提供ツール一覧
| ツール | 目的 | 主な引数 |

## 使い方の例
<3-4 natural language examples>

## アーキテクチャ的な注意点
- シングルトン制約
- ファイル依存
- ログ・デバッグ

## トラブルシューティング (要約)
| 症状 | 対処 |
```

Defer to `python/mcp-servers/<mod>_mcp/README.md` for the full guide; the Sphinx page is a focused summary.

## Cross-references

Always use intersphinx to portal for the common architecture chapter:

```markdown
{ref}`共通アーキテクチャ <portal:common-architecture>`
```

Never use `{doc}\`../common/architecture\`` (that path no longer exists in the hybrid layout).

### Cross-module references DO NOT WORK

Each module is its own Sphinx project; the only intersphinx mapping is to the **portal**. So `{ref}\`<tr/mcp>\`` and `{doc}\`tr:appendix-mdlkai\`` will produce `undefined label` warnings.

When you need to refer the reader to another module's documentation, use **plain text with the source path**:

```markdown
詳細は `tr` モジュールの MCP サーバページ
(`docs/sphinx/modules/tr/ja/mcp.md`) を参照.
```

(Adding inter-module intersphinx mappings is possible but adds build-order dependencies — defer until needed.)

## Math notation

`dollarmath` and `amsmath` are enabled, so use:
- Inline: `$\beta_N$`, `$q \propto B/I_p$`
- Display: `$$X(\rho) = (X_0 - X_S)(1 - \rho^P)^Q + X_S$$`

## Build verification

After any change run:

```bash
cd docs/sphinx
make SPHINXOPTS="" <mod>-<lang>      # tolerant build
make SPHINXOPTS="-W --keep-going" <mod>-<lang>   # strict
```

Both should succeed. The strict build catches broken intersphinx refs and missing toctree entries.

For viewing locally:

```bash
cd docs/sphinx/_build && python3 -m http.server 8787
# http://localhost:8787/<mod>/<lang>/index.html
```

The `file://` protocol blocks `../../` relative paths in browsers — use the HTTP server.

## Source-of-truth research before writing

Before drafting a module manual, gather these from the source:

1. **C ABI functions**: `grep "BIND(C" <mod>/<mod>_api.f90`
2. **Registered parameters + defaults**: read `<mod>/<mod>_param_registry.f90` and `<mod>/<init-source>.f90`
3. **State fields**: read `python/<mod>lib/state.py` (`SCALAR_FIELDS` and dataclass)
4. **MCP tools**: `grep "@mcp.tool()" python/mcp-servers/<mod>_mcp/server.py`
5. **Test definitions**: `grep "<mod>lib_" test_run/test_definitions.conf`
6. **Switch enumerations**: usually in `<init-source>.f90` block comments (e.g. tr/trinit.f90:211-276 for MDLKAI)

If a switch's allowed values are not enumerated in source comments, write a `{note}` admonition acknowledging that, rather than inventing values.

## Cross-language synchronisation

When syncing en ↔ ja:

1. Keep file structure identical (same filenames, same H2 hierarchy)
2. Translate prose; preserve code blocks, tables, and admonition class names verbatim
3. Translate admonition titles ("注意" ↔ "Warning", "補足" ↔ "Note") to match `:class:` semantics
4. The `(common-architecture)=` label is shared, so `{ref}` syntax is identical across languages
5. Math notation is language-agnostic — same LaTeX in both

## Things to NOT do

- Do not include 変更履歴 / changelog tables in module pages — git log is the source of truth
- Do not put autodoc-generated symbols (class members) in the right-sidebar TOC (`toc_object_entries=False` is set)
- Do not nest H3 subsections so deep that they overwhelm the right sidebar (CSS hides H3+ but it still bloats the source)
- Do not duplicate content between `python/<mod>lib/README.md` and the Sphinx pages — let the README be exhaustive and the Sphinx pages curated
- Do not use `:hidden:` on the index toctree — make all child pages visible in left sidebar
- Do not add inline `{contents}` directives on pages — furo's right sidebar replaces them
- Do not write LaTeX `\(...\)` or `\[...\]` — use `$...$` / `$$...$$` (dollarmath)
- Do not put arrows (↑/↓/⊕) in non-direction columns of sensitivity tables
- Do not use `jsonc` as a Pygments lexer name — use `json` (jsonc is not registered)
- Do not use `{ref}\`...<tr/foo>\``-style cross-module references — they emit `undefined label` warnings; use plain text
