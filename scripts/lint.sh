#!/bin/sh
# The one lint command. CI runs it, and so do the git hooks in .githooks.
# Usage: scripts/lint.sh [--fix]
set -e
cd "$(dirname "$0")/.."
if [ -x .venv/bin/ruff ]; then R=.venv/bin/ruff
elif command -v ruff >/dev/null 2>&1; then R=ruff
elif [ -x "$HOME/dianoia-data/venv/Scripts/ruff.exe" ]; then R="$HOME/dianoia-data/venv/Scripts/ruff.exe"
else
  echo "lint: ruff not found. Run: python -m pip install -e .[dev]" >&2
  exit 1
fi
if [ "$1" = "--fix" ]; then "$R" format . && "$R" check --fix .; fi
"$R" check . && "$R" format --check . || {
  echo "lint: failed. Fix with: scripts/lint.sh --fix" >&2
  exit 1
}
