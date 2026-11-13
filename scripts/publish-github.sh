#!/usr/bin/env bash
set -euo pipefail
if ! command -v gh >/dev/null 2>&1; then
  echo 'GitHub CLI missing. Install: https://cli.github.com/' >&2
  exit 1
fi
cd "$(dirname "$0")/.."
# Defaults to PRIVATE because the project involves voice and avatar identity.
gh repo create "${1:-ai-avatar-loom}" --private --source=. --remote=origin --push
