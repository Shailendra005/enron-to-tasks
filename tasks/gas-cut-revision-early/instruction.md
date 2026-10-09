# How much gas was cut?

`/app/mailbox/` holds the email of Jason Williams (Enron gas trading) at Enron as it stood at **Thursday 31 May 2001, 12:30 Houston time (2001-05-31 17:30 UTC)**. It covers the 90 days before that moment in the original folder layout, one RFC 822 message per file. Nothing written after that moment is included.

Peoples Gas had supply cut on its ANR contract 104684 for gas day May 30, 2001, and reduced its SIQ purchase for that day. According to this mailbox at the moment above, how many MMBtu were cut for that gas day, and what is Peoples' SIQ purchase for May 30 after the reduction?

Write your answer to `/app/answer.json`:

```json
{
  "cut_mmbtu": 0,
  "siq_purchase_mmbtu": 0,
  "evidence_message_ids": [
    "<message-id>"
  ]
}
```

- `cut_mmbtu`: volume cut for gas day May 30, 2001, in MMBtu, as an integer without commas.
- `siq_purchase_mmbtu`: Peoples' SIQ purchase for gas day May 30, 2001 after the reduction, in MMBtu, as an integer without commas.
- `evidence_message_ids`: 1 to 5 `Message-ID` header values, copied exactly including the angle brackets, of the emails that establish your answer.
- Plans or terms that were proposed and later replaced do not count. Report what stands at the moment given above, according to the mailbox.
