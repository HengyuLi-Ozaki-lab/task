# TXnew Documentation / TXnew ドキュメント

Sphinx documentation for the TASK/TXnew module.

TASK/TXnewモジュールのSphinxドキュメントです。

## Directory Structure / ディレクトリ構成

```
docs/
├── ja/          # Japanese documentation (日本語)
├── en/          # English documentation
└── README.md    # This file
```

## Requirements / 必要条件

- Python 3.6+
- Sphinx 4.0+
- sphinx-rtd-theme

## Installation / インストール

### Ubuntu/Debian

```bash
sudo apt-get install python3-sphinx python3-sphinx-rtd-theme
```

### pip

```bash
pip install sphinx sphinx-rtd-theme
```

## Build / ビルド

### Japanese (日本語)

```bash
cd docs/ja
make html
firefox _build/html/index.html
```

### English

```bash
cd docs/en
make html
firefox _build/html/index.html
```

### PDF (via LaTeX)

```bash
# Requires LaTeX / LaTeX環境が必要
sudo apt-get install texlive-latex-recommended texlive-fonts-recommended texlive-latex-extra latexmk

cd docs/ja  # or docs/en
make latexpdf
```

## Contents / 内容

- Overview / 概要
- Installation / インストール
- Input Parameters / 入力パラメータ
- Output Variables / 出力物理量
- Basic Equations / 基礎方程式
- Examples / 使用例
- References / 参考文献
