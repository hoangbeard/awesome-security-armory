#!/usr/bin/env bash
# Publish listed paths to a weekly/* branch. Never updates main and never force-pushes.
set -euo pipefail

dry=0
if [[ "${1:-}" == "--dry-run" ]]; then
  dry=1
  shift
fi

branch="${1:?branch required}"
message="${2:?commit message required}"
shift 2

case "$branch" in
  main|master|refs/heads/main|refs/heads/master)
    echo "refusing to push to ${branch}" >&2
    exit 1
    ;;
  weekly/*)
    ;;
  *)
    echo "refusing to push to unexpected branch ${branch}" >&2
    exit 1
    ;;
esac

if [[ "$#" -lt 1 ]]; then
  echo "pass at least one path to publish" >&2
  exit 1
fi

if [[ "$dry" -eq 1 ]]; then
  echo "would commit and push to ${branch}"
  exit 0
fi

git add -- "$@"
if git diff --cached --quiet; then
  echo "no changes to publish"
  exit 0
fi

git -c user.name="github-actions[bot]" \
  -c user.email="41898282+github-actions[bot]@users.noreply.github.com" \
  commit -m "$message"
git push origin "HEAD:${branch}"
