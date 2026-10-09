#!/bin/bash
set -euo pipefail
grep -qF -- '3:30 pm on Thursday.' '/app/mailbox/all_documents/11429.'
cat > /app/answer.json <<'JSON'
{
  "meeting_date": "2001-06-07",
  "start_time": "15:30",
  "evidence_message_ids": [
    "<27761198.1075844762079.JavaMail.evans@thyme>"
  ]
}
JSON
