#!/bin/bash
set -euo pipefail

repo="$(cd "$(dirname "$0")/.." && pwd)"
cd "$repo"
export ENRON_DATA="${ENRON_DATA:-$HOME/enron-data}"
export TIKTOKEN_CACHE_DIR="${TIKTOKEN_CACHE_DIR:-$ENRON_DATA/tiktoken}"
py="${PYTHON:-.venv/bin/python}"

if [ ! -d "$ENRON_DATA/raw/maildir" ]; then
  mkdir -p "$ENRON_DATA/raw"
  curl -sS -o "$ENRON_DATA/raw/enron_mail_20150507.tar.gz" https://www.cs.cmu.edu/~enron/enron_mail_20150507.tar.gz
  tar -xzf "$ENRON_DATA/raw/enron_mail_20150507.tar.gz" -C "$ENRON_DATA/raw"
fi

"$py" -m pipeline.parse
"$py" -m pipeline.profile
"$py" -m pipeline.dedupe
"$py" -m pipeline.strip_quotes
"$py" -m pipeline.tokens
"$py" -m pipeline.mine_episodes
"$py" -m pipeline.yield_estimate estimate
for ep in episodes/*.json; do
  case "$ep" in *yield_labels.json) continue ;; esac
  "$py" -m pipeline.build_task "$ep"
done
