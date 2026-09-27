#!/usr/bin/env bash
set -euo pipefail
PROJ="${1:?usage: verify.sh <project> [version]}"
VER="${2:-}"
if [ -z "$VER" ]; then
  curl -s "https://pypi.org/pypi/$PROJ/json" | python3 -c "import sys,json; print(json.load(sys.stdin)['info']['version'])"
  exit 0
fi
pip install --no-cache-dir --no-deps "$PROJ==$VER"
curl -s "https://pypi.org/integrity/$PROJ/$VER/" | python3 -m json.tool
