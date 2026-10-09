#!/bin/bash
set -uo pipefail

repo="$(cd "$(dirname "$0")/.." && pwd)"
private="${ENRON_PRIVATE_PATTERNS:-$HOME/enron-tasks-notes/private_patterns.txt}"
status=0

patterns=('sk-ant-[A-Za-z0-9_-]{8,}' 'oat01-[A-Za-z0-9_-]{8,}' 'CLAUDE_CODE_OAUTH_TOKEN=[^ "$]' 'ANTHROPIC_API_KEY=[^ "$]' 'e2b_[A-Za-z0-9]{16,}' '/Users/[A-Za-z]')
if [ -f "$private" ]; then
  while IFS= read -r line; do
    [ -n "$line" ] && patterns+=("$line")
  done < "$private"
fi

cd "$repo" || exit 1
for p in "${patterns[@]}"; do
  if git ls-files -z | xargs -0 grep -nIE -- "$p" 2>/dev/null | grep -v '^scripts/check_public.sh:'; then
    echo "FAIL: tracked file matches a secret or private pattern"
    status=1
  fi
  if git log -p --all 2>/dev/null | grep -v 'check_public.sh' | grep -qE -- "$p"; then
    echo "FAIL: git history matches a secret or private pattern"
    status=1
  fi
done

if git ls-files | grep -q '/mailbox/'; then
  echo "FAIL: mailbox snapshot files are tracked"
  status=1
fi

while IFS= read -r f; do
  if [ -f "$f" ] && [ "$(wc -c < "$f")" -gt 1048576 ]; then
    echo "FAIL: tracked file over 1 MB: $f"
    status=1
  fi
done < <(git ls-files)

if [ "$status" -eq 0 ]; then
  echo "check_public: clean"
fi
exit "$status"
