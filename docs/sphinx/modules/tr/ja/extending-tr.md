# TR の拡張

```{admonition} 想定読者
:class: note

このページは **maintainer 向け** です. 読者はソースツリー
を checkout していて Fortran 編集と `libtrapi.so` の
リビルドに慣れているものとします. 3 つの具体的な
walkthrough を扱います — スカラーパラメータ追加,
`MDLKAI` 配下の transport model 追加, `TrState` field
追加. 各々レシピであり, 導出ではありません.
```

---

## Walkthrough A — 新規スカラーパラメータの追加

TR のパラメータレジストリは `tr/tr_param_registry.f90:76+`
の `SELECT CASE` 手書き dispatch を使っています. 新規
パラメータ `FOO` の追加は dispatch の 1 個の新規 `CASE`
行 + `tr/trinit.f90` のデフォルトで完了します.

**レシピ (5 ステップ):**

1. **変数を宣言する.** 新規パラメータの場合 (まだ TRCOMM
   にない場合), 該当する `tr/trcomm*.f90` モジュールに
   類似パラメータと並べて宣言する. 既存ならスキップ.
2. **registry の case を追加する.**
   `tr/tr_param_registry.f90:76` から始まる
   `SELECT CASE (TRIM(b))` ブロックに
   `CASE ("FOO"); FOO = value` のような行を追加.
   per-section のグループ化規約を保つため, 類似パラメータ
   のすぐ近くに置く.
3. **デフォルトを設定する.** 他の初期化と並べて
   `tr/trinit.f90` に `FOO = ...` を追加.
4. **リビルド.** `make -C tr libtrapi.so`.
5. **Python から使う.** `tr.set_param("FOO", x)` で即座に
   動きます. `tr_set_param` は文字列キーで動作するため
   (`tr/tr_api.f90:124-128,136-148` で確認), C ABI 変更は
   不要です.

配列値パラメータについては, `tr/tr_param_registry.f90:101-106`
の bounds-check 付きイディオムをテンプレートに使います.
既存の `PA[i]` / `PN[i]` / `PNS[i]` / `PT[i]` ケースが
パターンを示しています: 各 `CASE` で `idx` を `SIZE(...)`
と比較し, 代入するか `ierr = 1` を立てるかを分岐します.

---

## Walkthrough B — `MDLKAI` 配下に新規 transport model を追加

乱流熱輸送係数は `tr/trcoef_turbulence.f90:400` の
`SELECT CASE(MDLKAI)` で dispatch されます. (line 64 の
別の `select case` はグラフラベル割り当て用で, 係数計算
自体ではありません.) 各 `MDLKAI` 値が異なるモデルを呼び
ます.

numbering 規約 (`tr/trcoef_turbulence.f90:392-398` の
ソース側コメントより):

- `MDLKAI < 10` — 定数係数の toy model.
- `10 ≤ MDLKAI < 20` — ドリフト波 (+ITG / +ETG) モデル.
- `20 ≤ MDLKAI < 30` — Rebu-Lalla 系.
- `30 ≤ MDLKAI < 40` — 電流拡散駆動 (CDBM) 系.
- `40 ≤ MDLKAI < 60` — ドリフト波バルーニングモデル.
- `MDLKAI ≥ 60` — ITG / TEM / ETG モデル群.

**レシピ (4 ステップ):**

1. **`MDLKAI` 値を選ぶ.** 該当範囲内で次に空いている整数を
   選ぶ (既存モデルの隣に追加する場合).
2. **`CASE (N)` ブロックを追加する.**
   `tr/trcoef_turbulence.f90` の line 400 の後に追加.
   ブロックは適切な輸送係数配列を埋める — `AKDW` (熱
   anomalous), `ADDW` (粒子 anomalous), `AVK` (熱 pinch /
   convective).
3. **必要なら補助 loader を追加する.** モデルが補助
   データ (lookup table, 追加パラメータ検証) を要する
   場合, 既存の family-別ファイル分割に従う —
   `tr/trcoef_neoclassical.f90`,
   `tr/trcoef_resistivity.f90` 等の隣接 `trcoef_*.f90`
   ファイルがテンプレート.
4. **{doc}`appendix-mdlkai` を更新.** カタログでユーザが
   新 case を見つけられるように.

同じ dispatch パターンが他の selector 軸 — `MDLAD`
(粒子拡散), `MDLAVK` (熱 pinch), `MDLETA` (抵抗率) —
にも適用され, それぞれ対応する `trcoef_*.f90` ファイルに
あります. レシピは一般化します.

---

## Walkthrough C — 新規 `TrState` field の追加 (ABI 影響レシピ)

3 つの walkthrough の中で最も影響範囲が広いものです.
`tr_state_t` への field 追加は C ABI を変えるので, 外部の
バイナリ consumer はリビルドあるいはバージョンチェック
が必要になります.

**レシピ (8 ステップ):**

1. **量を計算する.** 値がまだ TRCOMM になければ, 該当
   する `tr/trcomm*.f90` モジュールに TRCOMM 変数を追加
   し, 自然に該当するルーチンで代入する. 新しい派生
   診断量は `tr/trrslt_globals.f90` または
   `tr/trrslt_print.f90` に置くのが普通.
2. **C 側 field を追加する.**
   `tr/tr_state.f90:43-67` の `tr_state_c` 派生型に
   `REAL(C_DOUBLE)` (適切な kind) を **末尾** に追加.
   既存の field offset を維持するためで, バイナリ
   consumer に与える影響を最小化します.
3. **`tr/tr_api.h:49-60` にミラー** する. 対応する
   `double` (適切な C 型) を, やはり struct の末尾に追加.
4. **`tr_api_get_state` 内で field を埋める.**
   `tr/tr_api.f90` には 3 ブロックある:
   - **zero-init** が `:263-283` (新 field に compute-time
     ゼロベースラインがなければここにも追加).
   - **scalar copy** が `:299-315` — AJRFT 先例はここ.
     新スカラーはこのパターンに従う.
   - **per-radius / per-species profile loops** が
     `:321-330` — 新配列 field は `RN` / `RT` / `AJ` /
     `QP` の loop パターンに従う.
5. **`TR_STATE_ABI_VERSION` を bump する.**
   `tr/tr_api.h:38` で. 現値は `2`; 次の整数 (現在の
   流れだと `3`) に上げる.
6. **ctypes 側にミラー.**
   `python/trlib/_ffi.py:94-120` の `TrStateC._fields_` に
   tuple を append. BIND-C struct と同じ field 順を使う
   ことで両 layout が byte-compatible に保たれる.
7. **Python `TrState` dataclass に表面化.**
   `python/trlib/state.py`. 2 ケース:
   - *スカラー field*: field 名を `SCALAR_FIELDS` リスト
     (`python/trlib/state.py:22-28`) に追加. `from_c`
     (`:74` から始まる) 内で scalar dict-comprehension
     (`:87`) が `SCALAR_FIELDS` を走査して
     `state.scalars["YOUR_FIELD"]` を自動で埋める;
     dimension dict-comprehension (`:81-84`) は
     `nrmax` / `nsmax` を扱う別 stage. dataclass 構築
     (`:92-100`) が組み立てた `TrState` を返す. 新 field
     は `state.scalars["YOUR_FIELD"]` で他の変更なしに
     アクセス可能になる.
   - *配列 / profile field* (1 次元または 2 次元,
     `nrmax` または `nrmax × nsmax` で indexing): `TrState`
     dataclass に top-level 属性を追加し, `from_c` 内に
     対応する parser 行を手で書く. `AJ` / `RN` / `RT` の
     扱いがテンプレート.
8. **{doc}`state` を更新.** 新 attribute あるいは scalar
   key を載せる.

### 落とし穴: Fortran/C 配列 order ミラーリング (2 次元 field)

Fortran は column-major, C は row-major です. 既存の
`RN` / `RT` field は Fortran 宣言と C 宣言の間で index 順
を **転置** することでこの差を吸収しています:

- Fortran: `RN(TR_MAX_NSMAX, TR_MAX_NRMAX)` を
  `tr/tr_state.f90:60-61` で宣言.
- C: `RN[TR_MAX_NRMAX][TR_MAX_NSMAX]` を
  `tr/tr_api.h:53-54` で宣言.
- `python/trlib/_ffi.py:112-113` の ctypes ミラーは C
  layout に従う.

新規 2 次元 field も同じ転置パターンに従わないと, バイト
列が誤って再解釈されます.

### テスト計画

8 ステップ完了後:

1. `make -C tr libtrapi.so` — リビルド.
2. Smoke test:
   ```python
   from trlib import Trlib
   with Trlib() as tr:
       state = tr.get_state()
       print(state.scalars["YOUR_FIELD"])  # スカラーの場合
       # あるいは print(state.YOUR_FIELD)  # profile の場合
   ```
3. Canonical な pytest sweep:
   ```bash
   PYTHONPATH=python python3 -m pytest --forked \
       --timeout=120 --timeout-method=signal \
       python/trlib/tests/
   ```
   で regression がないことを確認.

### 動作する例: AJRFT (L-7b-i)

L-7b-i の PR — `#187`, merge commit `e049a1e4` — が
canonical な worked example です. 真似るべき具体的
タッチポイント:

- `tr/tr_state.f90:64-66` — BIND-C field
- `tr/tr_api.h:57-59` — C field
- `python/trlib/_ffi.py:116-119` — ctypes field
- `python/trlib/state.py:27` — `SCALAR_FIELDS` への
  スカラー登録

その PR は `TR_STATE_ABI_VERSION` を `1` → `2` に bump
していて, これがレシピ C のステップ 5 と同じ操作です.

---

## 関連項目

- {doc}`design` — Fortran 側の全体アーキテクチャと
  ビルド依存.
- {doc}`appendix-mdlkai` — 既存 `MDLKAI` ケースのカタログ.
- {doc}`state` — ユーザ向け `TrState` リファレンス.
- {doc}`physics-overview` — selector landscape
  (`MDLKAI` / `MDLETA` / `MDLAD` / `MDLAVK` /
  `MDLKNC` / `MDNCLS`) のオリエンテーション.
