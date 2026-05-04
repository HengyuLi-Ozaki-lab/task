# 既知の制約と参考資料

```{admonition} このページの位置付け
:class: note

`tr` ライブラリで「できないこと」のまとめと,
関連する輸送コードや上流 TASK グループへのポインタです.
ここに挙げる制約は現実装の安定した契約事項です.
参考資料の表は文脈情報として上流の公開ドキュメントを要約しています.
```

---

## 既知の制約

### プロセスあたり 1 インスタンス

`Trlib` は 1 プロセスにつき 1 つだけインスタンスを許します.
別の `Trlib()` がまだ生きているうちに 2 つ目を作ろうとすると
`TrlibError` を送出します. これは TR が安全に分割できない
モジュールレベル COMMON ブロックを使っているためで, 並列化したい
場合は別プロセスを起動してください ({doc}`applications` 参照).

ユーザ向けの詳細と内部の weakref ガード (#171 で導入) については
{ref}`faq-singleton` を参照してください.

### モジュール状態の再初期化

同一プロセス内で `tr_finalize` の後に `tr_init` をやり直しても,
モジュールレベルの Fortran 状態の一部はリセットされません.
再初期化を伴うテストはプロセス分離 (`pytest --forked`) するか,
`multiprocessing` で worker を新規起動してください.
詳細は {ref}`reinit-constraints` を参照.

### スレッド安全性

`tr` はスレッドセーフではありません. モジュールレベルの COMMON
ブロックを同一プロセス内のすべての呼び出しが共有するため,
`threading.Thread` などプロセス内スレッドからの同時呼び出しは
状態競合を起こします. 並列スイープには別プロセスを使ってください.
{doc}`applications` の `sweep()` で示している
`multiprocessing.Pool` パターンが推奨です.

### コンパイル時上限 (state バッファ)

`tr/tr_api.h` で定義される `TR_MAX_NRMAX = 500`,
`TR_MAX_NSMAX = 8` は **エクスポートされる** `tr_state_t`
バッファの次元 (`tr_get_state` が埋める `RN`, `RT`, `AJ`,
`QP` 配列, {doc}`state` 参照) のみを bound するもので,
TR プロセスの総 resident set size は bound しません.
TRCOMM は実行時に追加の内部配列を allocate し, 動的にリンクされた
ライブラリ (BPSD, 行列ソルバ等) もここに含まれない追加メモリを
使います. 本ページでは RSS の上限を断言しません — 必要なら
自分のデプロイで測定してください.

---

## 参考資料

### TASK の原論文

TASK code suite (`tr` を含む) は京都大学の福山淳教授グループに
よって開発されています. 上流ソースは
<https://github.com/ats-fukuyama> にあります. 出版物については
同グループの bibliography を直接参照してください — 本ページでは
個別の論文 citation を載せていません.

### 関連輸送コード

以下の表は新しいユーザの方向付けのために, TASK/tr とあわせて
いくつかの輸送コードを要約しています. アクセス形態はコードに
よって異なり, オープンソース / 共同研究ベース / コンソーシアム
限定の混合です. TASK 以外の行はページ作成時点での公開ドキュメント
の要約で, 各コードの正式な範囲とアクセスポリシーについてはリンク
先を参照してください.

| Code | Spatial | Time mode | Heating coverage | Access / URL |
|---|---|---|---|---|
| **TASK/tr** (this) | 1D radial | Predictive (time-evolving) | NB / EC / LH / ICRF source selectors registered via `MDLNB` / `MDLEC` / `MDLLH` / `MDLIC` | Open — <https://github.com/ats-fukuyama> |
| ASTRA | 1.5D | Predictive + interpretive | Modular | Collaboration-based — see upstream documentation |
| JETTO-SANCO | 1D transport + impurity | Predictive + interpretive | NB / EC / ICRH | EUROfusion-restricted — see upstream documentation |
| TRANSP | 1.5D | Interpretive primary; predictive available | NUBEAM, TORAY, etc. | Documentation: <https://transp.pppl.gov/>; source via PPPL collaboration |

この表は参考情報であり, 権威的な技術評価ではありません.
コードごとの詳細 (対応する個別の輸送モデルライブラリ, 加熱モジュール
の正確なカバレッジ, バージョン履歴等) については, リンク先のソースを
追ってください.
