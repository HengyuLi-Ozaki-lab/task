# TASK プラズマ輸送コード ライブラリ化プロジェクト — 変更内容と使い方

**発表日:** 2026 年 4 月 19 日
**想定時間:** 20 分 (Q&A は別途)
**スライド枚数:** 18 枚
**スライドファイル:** [`2026-04-19-task-library-ization-overview.pptx`](2026-04-19-task-library-ization-overview.pptx)
**生成スクリプト:** [`_build_pptx.py`](_build_pptx.py) / [`_build_assets.py`](_build_assets.py)

このドキュメントは、上記 pptx の発表用 outline (各スライドの要点 + speaker
notes) です。pptx 本体には全スライドにスピーカーノートが埋め込まれて
いますが、こちらでも一覧できるように整理しています。**本文・タイトル・
notes すべて日本語 (です・ます調)** です。

---

## スライド一覧と想定時間配分 (合計 約 20 分)

| # | タイトル | 想定時間 |
|---|----------|----------|
| 1 | タイトル | 0:30 |
| 2 | 背景・モチベーション | 1:00 |
| 3 | 対象モジュール一覧 | 1:00 |
| 4 | アーキテクチャ全体図 *(図)* | 1:30 |
| 5 | Phase L 概要 (8 フェーズ) | 1:30 |
| 6 | Phase F (eq F90 近代化) | 1:00 |
| 7 | テスト戦略: 4 層構成 *(図)* | 1:30 |
| 8 | 使い方 1: Python hello world *(コード + 図)* | 1:00 |
| 9 | 使い方 2: TOML config runner *(図)* | 1:00 |
| 10 | TOML schema 例 *(コード)* | 0:50 |
| 11 | 使い方 3: 可視化 API *(プロット画像)* | 0:50 |
| 12 | 使い方 4: MCP server (LLM 連携) *(図)* | 1:30 |
| 13 | MCP ツール一覧 (9 ツール) | 1:00 |
| 14 | 成果サマリ (インフォグラフィック) | 1:00 |
| 15 | 残作業 | 1:00 |
| 16 | 今後の発展 | 1:00 |
| 17 | Q&A 用補足: 設計上の工夫 | 1:00 |
| 18 | まとめ・参考資料 | 0:30 |

合計: 約 18 分。導入と質疑のオーバヘッドを足して 20 分枠に収まる構成です。

---

## スライド 1: タイトル

- 演題: 「TASK プラズマ輸送コード ライブラリ化プロジェクト — 変更内容と使い方」
- 発表日 / 発表者プレースホルダ
- 副題: Phase L-0 〜 L-7 / Phase F-1 〜 F-4 / MCP サーバ / 86 PR merge

**Speaker notes:** こんにちは。本日は TASK プラズマ輸送コードの
ライブラリ化プロジェクトについて、「どのような変更を入れたのか」と
「どのように使えるのか」を 20 分でお話しします。対象は tr / fp / ti / wr /
wrx / eq / tot の 7 モジュールで、約 86 件の PR をマージしています。

## スライド 2: 背景・モチベーション

- TASK は CLI ベースの Fortran コードで、対話メニュー + namelist 入力。
- Python から呼びたい (パラメータスイープ・最適化・データ同化)。
- LLM (Claude / Cursor) からも自然言語で計算したい (MCP)。
- 既存 CLI バイナリを壊さず追加機能として提供。

**Speaker notes:** これまでの TASK は CLI と namelist 入力が基本でしたが、
近年はパラメータスイープや LLM 連携の需要が高まっています。今回の
ライブラリ化はこれらに応えるもので、既存 CLI バイナリは一切壊さず追加
機能として提供します。

## スライド 3: 対象モジュール一覧

| モジュール | 役割 | L-0..L-7 | Phase F | MCP |
|---|---|---|---|---|
| tr | 1 次元輸送 | 完了 | (対象外) | 完了 |
| fp | Fokker-Planck 解析 | 完了 | (対象外) | 完了 |
| ti | 不純物輸送 | 完了 | (対象外) | 完了 |
| wr | 波動レイトレーシング | 完了 | (対象外) | 完了 |
| wrx | 拡張レイトレーシング | 完了 | (対象外) | 完了 |
| eq | MHD 平衡 | L-0..L-5 | F-1..F-3 完了 | 未着手 |
| tot | 統合輸送 | L-0..L-4 | (対象外) | 未着手 |

**Speaker notes:** 7 モジュール中 5 つが Phase L 全完了 + MCP サーバまで
完了。eq は F90 近代化 (Phase F) 並行で L-5 まで、tot は L-4 まで。

## スライド 4: アーキテクチャ全体図 *(図)*

横方向 4 層構成 (色分け):

```
[Fortran 計算本体] -> [C ABI (BIND(C))] -> [Python ラッパ (ctypes)] -> [MCP サーバ]
       青                  緑                     オレンジ                  紫
```

下段に利用側のエントリポイント (CLI / C++ / Python / LLM)。

**Speaker notes:** 4 層構成が今回の核心です。Fortran のコア計算が唯一の
真実のソースで、C ABI で薄く包み、Python で扱いやすくし、MCP で LLM から
触れる構造になっています。

## スライド 5: Phase L 概要 (8 フェーズ)

| フェーズ | 内容 | 成果物 |
|---|---|---|
| L-0 | 回帰テスト基盤 | test_run/baselines/ |
| L-1 | Makefile 分割 | <mod>/Makefile |
| L-2 | C ABI 雛形 | <mod>_api.f90 / .h |
| L-3 | パラメータレジストリ | <mod>_param_registry.f90 |
| L-4 | .so ビルド | lib<mod>api.so |
| L-5 | Python ラッパ | python/<mod>lib/ |
| L-6 | 4 層テスト | test_run/test_definitions.conf |
| L-7 | ドキュメント | README + examples + architecture.md |

**Speaker notes:** 1 フェーズ 1 PR で進め、各 PR で Cursor Bugbot レビュー
完了を待ってから次へ。SKILL.md (PR #84) として方法論を文書化済み。

## スライド 6: Phase F (eq F90 近代化)

- F-1: COMMON → MODULE 化 (PR #71)
- F-2: LOW tier .f → .f90 (PR #79)
- F-3: MED tier (INCLUDE shim, 9 ファイル, PR #81)
- F-4: HIGH tier (driver / file I/O) — 進行中
- F-5: shim removal + grep clean-up — 予定

**Speaker notes:** eq は F77 の資産が多く Phase L と並行して F90 化を実施。
shim policy で新旧コードを共存させ、grep ゼロ確認後に撤去。

## スライド 7: テスト戦略: 4 層構成 *(図)*

| 層 | 内容 | 例 |
|---|---|---|
| Layer 1 | 等価性 (Phase 0 baseline 比較, 1e-10) | trlib_equivalence |
| Layer 2 | C ABI スモーク | trlib_c_abi |
| Layer 3 | Python ラッパ単体 | trlib_ffi / trlib_wrapper |
| Layer 4 | スイープ (3×3 RR×BB) | trlib_sweep |

すべて `test_run/test_definitions.conf` に登録され CI で自動実行。

**Speaker notes:** 数値同等性 (1e-10) を Layer 1 で保証した上で、上位層で
API 安全性を順次確認します。tr_m0904 のように元コードが揺らぐケースは
baseline を pin する運用です。

## スライド 8: 使い方 1: Python hello world *(コード + 図)*

```python
from trlib import Trlib

with Trlib() as tr:
    tr.set_params(RR=8.5, RA=2.0, BB=5.3, NSMAX=2, DT=0.1)
    tr.run(ntmax=50)
    state = tr.get_state()

print(state.scalars['T'], state.scalars['WPT'])
```

5 段階フロー (init → set_param → run → get_state → close) を右側に図示。

**Speaker notes:** with でコンテキストマネージャに入ると tr_init、抜けると
finalize。配列要素は `set_param('PN[1]', 1.0)` で 1-origin 指定。
ierr (0..4) は `TrlibParamError` などの例外にマップ。

## スライド 9: 使い方 2: TOML config runner *(図)*

3 段階フローチャート (今後の機能):

```
[1. TOML ファイル iter01.toml]
       --(parse + validate)-->
[2. python -m trlib config.toml]
       --(auto-plot)-->
[3. プロット生成 PNG / PDF]
```

**Speaker notes:** TOML で版管理しやすいケース定義を一発実行。MCP からも
同じ TOML を渡せるため LLM ワークフローと整合。現状 deferred。

## スライド 10: TOML schema 例 *(コード)*

```toml
[run]
module = "tr"
ntmax  = 50

[geometry]
RR    = 8.5
RA    = 2.0
RKAP  = 1.7
BB    = 5.3

[plasma]
NSMAX = 2
PN    = [1.0, 1.0]
PT    = [1.5, 1.5]

[transport]
MDLKAI = 60
CK0    = 12.0
CK1    = 12.0

[plot]
vars   = ["RN", "RT", "AJ", "QP"]
format = "png"
outdir = "./out"
```

**Speaker notes:** 配列を自然な構文で書け、未指定キーは namelist 既定値が
継続。差分だけ書けば良い運用。

## スライド 11: 使い方 3: 可視化 API *(プロット画像)*

```python
with Trlib() as tr:
    ...
    fig = tr.plot("RN")
    fig.savefig("density.png")
    tr.plot("RT", show=True)
```

右側に模擬 RN プロット (electron / deuteron / tritium 密度プロファイル)。

**Speaker notes:** matplotlib.figure.Figure を返すので Jupyter で対話的に
扱える。MCP からは base64 PNG 返却に拡張予定 (visualization followup)。

## スライド 12: 使い方 4: MCP server (LLM 連携) *(図)*

```
[ユーザー] --自然言語--> [LLM (Claude)] --JSON-RPC--> [MCP サーバ] --Python 呼出--> [ライブラリ + .so]
```

戻りは逆向き: ライブラリ → MCP (dict) → LLM (要約) → ユーザー (自然言語)

```bash
$ claude mcp add task-tr -- python -m tr_mcp.server
```

**Speaker notes:** ユーザは自然言語でリクエスト、LLM が適切な MCP ツールを
選択して呼び出す。登録は claude mcp add 一行で完結。

## スライド 13: MCP ツール一覧 (9 ツール)

| ツール | 目的 |
|---|---|
| init / finalize | ライフサイクル |
| set_param / set_params | パラメータ設定 |
| run | 時間ステップ進行 |
| get_state | 状態取得 |
| describe_parameters | パラメータ自己発見 |
| describe_state_schema | 状態スキーマ自己発見 |
| run_and_get_state | 複合 (init+set+run+get_state) |

**Speaker notes:** 全モジュール (tr/fp/ti/wr/wrx) で同じ 9 ツール構成。
describe_* は LLM 自己発見用、run_and_get_state は会話ターン削減用。

## スライド 14: 成果サマリ (インフォグラフィック)

- **86** merged PR (PR #1 〜 #86)
- **7** 対象モジュール
- **28+** tests / module
- **9** MCP ツール × 5 モジュール
- ドキュメント: SKILL.md + 日本語マニュアル PDF
- 互換性: 既存 CLI バイナリは無変更

**Speaker notes:** 約 86 件 PR、7 モジュール、4 層 × 7 モジュールのテスト、
MCP は 5 モジュールに横展開済み。CLI 互換性は完全保持。

## スライド 15: 残作業

- eq モジュール: L-6 / L-7
- tot モジュール: L-5 / L-6 / L-7
- Phase F-4 / F-5 (eq HIGH tier + shim 撤去)
- 可視化 API 横展開 (TR 先行 → fp / ti / wr)
- TOML config runner 全モジュールへ
- MCP plot ツール (base64 PNG)
- Tutorial notebooks (Jupyter)
- draft の plan PR 6 件のリベース

**Speaker notes:** Phase L 完遂と横展開タスクが中心。draft PR 6 件の
リベースも控えています。

## スライド 16: 今後の発展

- Tutorial notebooks (Jupyter)
- 可視化レイヤ拡張 (matplotlib + plotly)
- MCP 利用マニュアル (Claude Desktop / Code / Cursor)
- パラメータ最適化 (scipy.optimize / bayesian-optimization)
- データ同化 (実機計測との突合)
- モジュール間結合 (tot を介した tr ↔ wr ↔ fp)
- MCP マルチエージェント

**Speaker notes:** ライブラリ化を起点に応用展開。Jupyter チュートリアル、
最適化、データ同化、マルチエージェント協調などが見えています。

## スライド 17: Q&A 用補足: 設計上の工夫

1. **shim policy (Phase F):** COMMON ↔ MODULE 共存 → grep ゼロ後撤去
2. **RTLD_LAZY + --unresolved-symbols:** graphics 未解決でも .so 可
3. **Name collision:** `BIND(C, NAME=...)` + `USE module, only: ... => alias`
4. **Error code 0..4:** ParamError / StateError / RunError / NotImplemented

**Speaker notes:** 4 つの設計判断を Q&A 用に整理。詳細は
`docs/superpowers/specs/` と SKILL.md (PR #84) を参照。

## スライド 18: まとめ・参考資料

- TASK 7 モジュールを共有ライブラリ + Python + MCP で利用可能化
- 既存 CLI 無変更で安全に拡張
- 4 層テストで 1e-10 の数値等価性
- SKILL.md と日本語マニュアルで横展開容易

| 種別 | 場所 |
|---|---|
| SKILL.md | `docs/superpowers/skills/module-library-ization/SKILL.md` |
| 日本語マニュアル | `docs/manual/task-library-manual.tex` (.pdf) |
| TR ラッパ README | `python/trlib/README.md` |
| TR MCP README | `python/mcp-servers/tr_mcp/README.md` |
| 設計仕様 | `docs/superpowers/specs/2026-04-17-tr-library-design.md` |
| 変更履歴 | `CHANGELOG.md` |

**Speaker notes:** ご清聴ありがとうございました。質問は次の Q&A スライド
で承ります。

---

## 補足: pptx 再生成手順

```bash
cd <repo root>
python3 docs/presentations/_build_assets.py   # 模擬プロット PNG 生成
python3 docs/presentations/_build_pptx.py     # pptx 本体生成
```

依存: `python-pptx >= 1.0`、`matplotlib >= 3.0`、`numpy`、Noto Sans CJK
JP フォント (`/usr/share/fonts/opentype/noto/`)。
