#!/bin/bash
set -euo pipefail
grep -qF -- 'cut by 6,599 MMBtu' '/app/mailbox/inbox/156.'
cat > /app/answer.json <<'JSON'
{
  "cut_mmbtu": 6599,
  "siq_purchase_mmbtu": 118401,
  "evidence_message_ids": [
    "<17363956.1075845378680.JavaMail.evans@thyme>"
  ]
}
JSON
