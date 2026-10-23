#!/bin/bash
set -e
cd -- "$(dirname -- "$0")"
if [ ! -x .venv/bin/python ]; then
  echo "请先按 README.md 安装项目依赖。"
  exit 1
fi
exec .venv/bin/python run.py
