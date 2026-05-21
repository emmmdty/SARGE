#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

/home/tjk/.codex/venvs/codex-tools/bin/python scripts/build_assets.py

TEXINPUTS=".:style:" BSTINPUTS=".:style:" latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
