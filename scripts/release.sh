#!/usr/bin/env bash
set -euo pipefail
[ $# -eq 1 ] || { echo "usage: $0 vX.Y.Z"; exit 1; }
V="$1"
cd "$(git rev-parse --show-toplevel)"
git diff --quiet || { echo "working tree not clean"; exit 1; }
git tag -a "$V" -m "$V"
git push && git push --tags
echo "tagged $V — approve the pypi environment in GitHub Actions"
