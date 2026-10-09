# When does the meeting start?

`/app/mailbox/` holds the email of Sara Shackleton (Enron North America, Legal) at Enron as it stood at **Tuesday 05 June 2001, 05:00 Houston time (2001-06-05 10:00 UTC)**. It covers the 60 days before that moment in the original folder layout, one RFC 822 message per file. Nothing written after that moment is included.

Sara Shackleton asked for a one-hour meeting with Mark Taylor, with Christian Yoder joining by phone from Portland, to talk about Washington State PUDs. According to this mailbox at the moment above, on what date and at what Houston time is that meeting set to start?

Write your answer to `/app/answer.json`:

```json
{
  "meeting_date": "YYYY-MM-DD",
  "start_time": "HH:MM",
  "evidence_message_ids": [
    "<message-id>"
  ]
}
```

- `meeting_date`: date of the meeting, `YYYY-MM-DD`.
- `start_time`: start time in Houston local time, 24-hour `HH:MM`.
- `evidence_message_ids`: 1 to 5 `Message-ID` header values, copied exactly including the angle brackets, of the emails that establish your answer.
- Plans or terms that were proposed and later replaced do not count. Report what stands at the moment given above, according to the mailbox.
