#!/bin/bash
set -euo pipefail
grep -qF -- '3:00 pm - Friday, June 8' '/app/mailbox/all_documents/11465.'
cat > /app/answer.json <<'JSON'
{
  "meeting_date": "2001-06-08",
  "start_time": "15:00",
  "evidence_message_ids": [
    "<12052516.1075844763136.JavaMail.evans@thyme>"
  ]
}
JSON
