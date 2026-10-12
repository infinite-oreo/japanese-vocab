#!/bin/bash
# 仅生成网页版 dist/index.html
cd "$(dirname "$0")" || exit 1
python3 build.py
