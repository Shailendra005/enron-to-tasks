#!/bin/bash
set -uo pipefail

mkdir -p /logs/verifier
chmod 700 /logs/verifier
echo 0 > /logs/verifier/reward.txt
cat > /logs/verifier/ctrf.json <<'JSON'
{"results": {"tool": {"name": "pytest"}, "summary": {"tests": 1, "passed": 0, "failed": 1, "pending": 0, "skipped": 0, "other": 0, "start": 0, "stop": 0}, "tests": [{"name": "verifier_did_not_complete", "status": "failed", "duration": 0}]}}
JSON

/opt/grade-venv/bin/python -I -m pytest -p no:cacheprovider -rA --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py
status=$?

if [ "$status" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
