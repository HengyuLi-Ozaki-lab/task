# TXnew ドキュメント

TASK/TXnewモジュールのSphinxドキュメントです。

## 必要条件

- Python 3.6以上
- Sphinx 4.0以上
- sphinx-rtd-theme

## インストール

### Ubuntu/Debian

```bash
sudo apt-get install python3-sphinx python3-sphinx-rtd-theme
```

### pip

```bash
pip install -r requirements.txt
```

## ビルド

### HTML

```bash
cd /home/k-yoshimi/program/task/txnew/docs
make html
```

ビルド結果は `_build/html/` に出力されます。

ブラウザで開く:
```bash
firefox _build/html/index.html
```

### PDF (LaTeX経由)

```bash
make latexpdf
```

LaTeX環境が必要です:
```bash
sudo apt-get install texlive-latex-recommended texlive-fonts-recommended texlive-latex-extra latexmk
```

## ファイル構成

```
docs/
├── conf.py              # Sphinx設定
├── index.rst            # メインインデックス
├── overview.rst         # 概要
├── installation.rst     # インストール手順
├── input_parameters.rst # 入力パラメータ
├── output_variables.rst # 出力物理量
├── equations.rst        # 基礎方程式
├── examples.rst         # 使用例
├── references.rst       # 参考文献
├── Makefile             # ビルド用Makefile
└── requirements.txt     # Python依存関係
```

## 開発モード

ライブリロードで編集しながらプレビュー:

```bash
pip install sphinx-autobuild
make livehtml
```

http://localhost:8000 でプレビューできます。
