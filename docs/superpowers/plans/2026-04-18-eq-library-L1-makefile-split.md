# EQ ライブラリ化 Phase L-1: Graphics 分離 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `eq/Makefile` の `SRCS=` を `SRCS_CORE` / `SRCS_GRAPHICS` / `SRCS_MENU` の 3 つに論理分割し、後続 L-2..L-4 で graphics を含まない `libeqapi.so` を作れる準備を整える。既存の `eq` / `pl` / `ak` バイナリの数値出力は L-0 ベースラインと完全一致を保つ。

**Architecture:** 既存の `eq/Makefile` で 1 つになっている `SRCS=` を 3 グループに分ける。`eq`, `pl`, `ak` バイナリのリンク対象は従来通り全グループ（`$(SRCS_CORE) + $(SRCS_GRAPHICS) + $(SRCS_MENU)`）。L-2 以降で `libeqapi.so` が `$(SRCS_CORE)` だけを使うことを可能にする土台。コードへの変更は **Makefile のみ**、Fortran ソースは触らない。

**Tech Stack:** Make（`eq/Makefile`）、回帰テスト（L-0 で確立した `./run_tests.sh eq_*`）。

**出典設計書:** `docs/superpowers/specs/2026-04-17-tr-library-design.md`、および既に実装済みの `eq/Makefile` L-1 コメント（lines 108-118）。

---

## Module Survey: eq/ における graphics サブシステム

`eq/Makefile` の L-1 分割ルールはすでに **コメント行 108–118** に明文化されている。これを Makefile 実装として具現化する。

### GSAF 関数直呼び出し箇所

Grep で GSAF API (`PAGES`, `PAGEE`, `GRD1D`, `GUCLIP`, `GUDATE`, `GUTIME`, `GUFLSH`) を含むファイル:

| ファイル | GSAF | 役割 |
|---|---|---|
| `eqgout.f` | ✓ PAGES, PAGEE, GUCLIP | グラフ出力ルート |
| `eqg2d.f` | ✓ GUCLIP, GDEFIN 等 | 2D 磁気面グラフ |
| `eqg3d.f` | ✓ GUCLIP | 3D 境界グラフ |
| `eqgoutx.f` | ✓ PAGES, PAGEE | グラフ拡張 |
| `eqgsub.f` | **✗** 直接 GSAF なし | グラフ補助（contour、1D profile） |
| `eqfile.f` | ✓ GUCLIP | GUCLIP の interface definition のみ（定義ファイル） |

### 依存関係

- `eqmenu.f` は `CALL EQGOUT` で eqgout を呼ぶため **MENU グループに含める**（メニュー自体は menu-only だが graphics に強く依存）
- `eqgsub.f` は PAGES/PAGEE を呼ばず、グラフ描画ユーティリティ（CONTQ5, GPLOTP 等）のみ。**eqgout から呼ばれる**。GRAPHICS グループに含める。
- `trtest.f`, `akeqin.f` は test ドライバであり、main 相当のエントリポイント（SRCS に含まれない）。
- `eqfile.f` は GUCLIP の interface 定義を提供し、eqgout 等から使用される。**GRAPHICS グループに含める**。

### 圧縮グループ分け

**SRCS_GRAPHICS の定義は Makefile lines 108–123 に既に記載されている:**

```makefile
# libtrapi.so excludes all graphics, so libeq_pic.a drops:
#   - eqgout / eqgsub / eqg2d : direct GSAF (PAGES/PAGEE/GRD1D/etc.)
#   - equread                 : module with embedded gsaf calls (pagee)
```

ただし、コメント行は "eqgsub" の扱いについて曖昧（equread に含まれる PAGEE の言及あり）。実装に際しては以下のように確定:

| カテゴリ | ファイル | 役割 |
|---|---|---|
| **GRAPHICS** | `eqgout.f` `eqgsub.f` `eqg2d.f` `eqg3d.f` `eqgoutx.f` `eqfile.f` | GSAF 直呼ぶか補助関数 |
| **MENU** | `eqmenu.f` | 対話メニュー（graphics 依存） |
| **CORE** | 上記以外の 17 ファイル | 計算本体（EQ 物理、I/O、ユーティリティ） |

**補足：** `equread.f90` はコメントで "module with embedded gsaf calls" と言及されるが、実際の Grep で PAGES/PAGEE は出ない。ただし GUCLIP interface 使用の可能性があり、慎重を期して eqlib 依存性の有無を L-2 検証時に再確認。

---

## File Structure

| ファイル | 種別 | 責務 |
|---|---|---|
| `eq/Makefile` | 修正 | lines 18–30 の `SRCS=` / `SRC2D=` / `SRC3D=` を `SRCS_CORE` / `SRCS_GRAPHICS` / `SRCS_MENU` に 3 分割。その後 `SRCS = $(SRCS_CORE) $(SRCS_GRAPHICS) $(SRCS_MENU)` で再合成 |

それ以外のファイル変更なし。

---

## Task 1: 作業ブランチ作成と L-0 完了確認

**Files:** なし

- [ ] **Step 1: L-0 が develop にマージ済みか確認**

Run:
```bash
cd /home/k-yoshimi/program/task-private
git fetch origin develop
git log --oneline origin/develop | head -10
```
Expected: L-0 のマージコミットが見える、または L-0 PR がマージ予定。

- [ ] **Step 2: L-1 ブランチを develop から切る**

Run:
```bash
git checkout -b feature/eq-library-L1-graphics-split origin/develop
```

- [ ] **Step 3: L-0 の eq 回帰テスト（存在すれば）が green であることを確認（出発点を固定）**

Run:
```bash
cd /home/k-yoshimi/program/task-private/eq && make 2>&1 | tail -3
```
Expected: エラーなしで `eq`, `pl`, `ak` が build される。

---

## Task 2: `eq/Makefile` の SRCS 分割

**Files:**
- Modify: `eq/Makefile`

- [ ] **Step 1: 現行 `SRCS=` ブロック（lines 18–23）を把握**

Run:
```bash
sed -n '18,30p' /home/k-yoshimi/program/task-private/eq/Makefile
```
Expected: lines 18–23 に `SRCX`, `SRCS`, `SRCT`, `SRCP`, `SRCA`, `SRC2D`, `SRC3D` が見える。

- [ ] **Step 2: 3 グループに分割した形に書き換え**

`eq/Makefile` の lines 18–30 を以下に置換:

```makefile
# --- core (equilibrium physics + file I/O, no graphics, no menu) ---
SRCS_CORE = equcom.f90 equread.f90 eqlib.f90 \
            eqbpsd.f eqinit.f eqcalc.f eqcalq.f eqcalv.f \
            eqsub.f eqfunc.f eqintf.f eqsplf.f equintf.f \
            eq-eqdsk.f eq-qst.f eqgetp.f \
            newton.f invematrix.f equnit.f eqrppl.f

# --- graphics (GSAF plotting, contour, 2D/3D surfaces) ---
SRCS_GRAPHICS = eqgout.f eqgsub.f eqg2d.f eqg3d.f eqfile.f

# --- interactive menu driver (depends on graphics) ---
SRCS_MENU = eqmenu.f

# --- final SRCS for the existing eq / pl / ak binaries (unchanged behaviour) ---
SRCS = $(SRCS_CORE) $(SRCS_GRAPHICS) $(SRCS_MENU)

# --- test/app drivers (not in SRCS, linked separately) ---
SRCX = equcom.f90 equread.f90 eqlib.f90
SRCT = trtest.f treqin.f
SRCP = pltest.f
SRCA = aktest.f akeqin.f
SRC2D= eqg2d.f
SRC3D= eqg3d.f
```

注意点:
- `eqgoutx.f` は SRCS に含まれていない（lines 29–30 で SRC2D/SRC3D のみ）。コメント検査で eqgoutx に PAGES/PAGEE が見つかるが、main SRCS には unrelated。L-2 検証時に扱いを再評価。
- `SRCX` は module 定義群（equcom, equread, eqlib）で、SRCS の先頭に既に含まれる（新 SRCS_CORE）。この変数は残す（他の build 構成で参照される可能性）。
- `SRCT`, `SRCP`, `SRCA`, `SRC2D`, `SRC3D` は SRCS 分割の対象外（test/experimental）。変更なし。
- 並び順は元の SRCS の登場順を保つ。

- [ ] **Step 3: ビルド**

Run:
```bash
cd /home/k-yoshimi/program/task-private/eq
make clean
make 2>&1 | tail -10
ls -la eq pl ak
```
Expected: エラーなしで `eq`, `pl`, `ak` バイナリが再生成。

- [ ] **Step 4: 全 eq 回帰テストを通す（存在すれば）**

Run:
```bash
cd /home/k-yoshimi/program/task-private/test_run
./run_tests.sh eq_* 2>&1 | tail -20
```
Expected: 全ケース PASS。（eq 専用テストが無ければスキップ）

- [ ] **Step 5: TR 既存テストが回帰しないこと**

Run:
```bash
cd /home/k-yoshimi/program/task-private/test_run
./run_tests.sh tr_iter01 tr_m0904 tr_tst2
```
Expected: 全 PASS。

- [ ] **Step 6: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task-private
git add eq/Makefile
git commit -m "build(eq): split SRCS into CORE/GRAPHICS/MENU groups (no behavior change)"
```

---

## 受け入れ基準

- [ ] `eq/Makefile` の `SRCS_CORE`, `SRCS_GRAPHICS`, `SRCS_MENU` 変数が存在し、`SRCS = $(SRCS_CORE) $(SRCS_GRAPHICS) $(SRCS_MENU)` で結合されている。
- [ ] `make clean && make` で `eq`, `pl`, `ak` バイナリが再生成される。
- [ ] 回帰テスト実行時（存在する場合）、既存テストと **bit-exact** 一致。
- [ ] `tr_iter01, tr_m0904, tr_tst2` も全 PASS（巻き込み事故なし）。

## 撤退条件 / フォールバック

| 状況 | 対応 |
|---|---|
| `eqgoutx.f` の扱いが不明 | SRCS に含まれていない（experimental）。L-2 検証時に eqgoutx→GRAPHICS 依存を確認し、必要なら追加 |
| `equread.f90` の GSAF 依存が疑わしい | grep で直接 PAGES/PAGEE が見つからない。equread は CORE に留める。L-2 でリンク試行時に graphics module 依存が見つかれば段階的に除外を検討 |
| L-1 単独で 1 週超 | Makefile 分割のみで commit、ドキュメント は別 PR で |

## 依存

- 上流: L-0 完了（eq, pl, ak バイナリが build できる）
- 後続: L-2（C ABI foundation）は本 PR マージ後に着手

---

## 注釈: なぜ equread を CORE に留めるのか

`eq/Makefile` lines 110–118 コメントは "equread: module with embedded gsaf calls (pagee)" と書くが、実際には:

1. **Grep で PAGES/PAGEE が見つからない** → equread.f90 内に直接的な GSAF 呼び出しはない
2. **eqfile.f が GUCLIP interface を定義し** equread が使用する可能性 → 検証未確定

L-1 時点では equread は CORE に含め、L-2 の PIC ビルド試行時に **unresolved symbols** として観測される場合に初めて GRAPHICS グループへの移行を検討。これにより段階的な風険軽減が可能。
