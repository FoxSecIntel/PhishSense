#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

echo "[1/3] Python syntax"
python3 -m py_compile src/phishsense.py

echo "[2/3] tests"
if command -v pytest >/dev/null 2>&1; then
  PYTHONPATH=. pytest -q
else
  echo "pytest not installed; skipping"
fi

echo "[3/3] basic template check"
[[ -f src/prompt_template.txt ]] || { echo "Missing src/prompt_template.txt"; exit 1; }

echo "QA checks complete."
