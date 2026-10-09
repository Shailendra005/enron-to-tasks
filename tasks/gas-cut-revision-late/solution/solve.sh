#!/bin/bash
set -euo pipefail
grep -qF -- 'becomes 120,144 for May 30th' '/app/mailbox/inbox/160.'
cat > /app/answer.json <<'JSON'
{
  "cut_mmbtu": 4856,
  "siq_purchase_mmbtu": 120144,
  "evidence_message_ids": [
    "<14256877.1075845378787.JavaMail.evans@thyme>"
  ]
}
JSON
