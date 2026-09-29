#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"
if [[ ! -x .venv/bin/python ]]; then
  echo "Once ./install_kali.sh calistirin." >&2
  exit 1
fi
exec .venv/bin/python jarvis_claude.py
