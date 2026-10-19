# Quote-stripping spot check

`scripts/strip_check.py` draws 20 random unique messages (seed 7, bodies over 200 characters) and prints the text kept and the start of the text cut.

Result of reading all 20 (done by a Claude session): **cut point correct in 20 of 20**.

- 8 of 20 had a quoted or forwarded block; in every case the cut landed on the `-----Original Message-----`, `Forwarded by ... on` or Lotus Notes header line, and nothing from the new reply was lost.
- 3 of the 8 were pure forwards with no added text, so they correctly contribute no new text.
- 12 of 20 had nothing to cut and nothing was cut.

Known limits: newsletters, spam and HTML mail are kept as new text (they are not quotes); inline replies written between quoted lines lose the quoted context only.
