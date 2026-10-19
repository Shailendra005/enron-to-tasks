# Episodes and ground truth

Two real threads, each cut at two moments, give four tasks. Difficulty was written into the episode JSON files and each `task.toml` before any model run: Harbor recorded one task checksum per task, unchanged from the oracle run through every model trial. The JSON files were committed in `fe0fc5e` (10 Oct); this file and the model results were added in `c266c4d` (12 Oct). Full timelines with message paths are in `meeting-reschedule.json` and `gas-cut-revision.json`.

## Thread 1: a meeting that moved (mailbox `shackleton-s`)

Sara Shackleton (ENA Legal) wants an hour with Mark Taylor, with Christian Yoder joining from Portland, about Washington State PUDs.

| UTC (Date header) | Who | What it says | State after |
|---|---|---|---|
| Jun 4 18:12 | Sara | asks for Thursday June 7, afternoon | requested |
| Jun 5 07:34 | Holly (assistant) | "I've scheduled 3:00 PM following today's Legal/Credit meeting." | booked on the wrong day |
| Jun 5 08:19 | Sara | "I'd like to meet Thursday, June 7" | corrected |
| Jun 5 08:36 | Holly | "3:30 pm on Thursday." | **Thu Jun 7, 15:30** |
| Jun 5 09:06 | Sara to Christian | "3:30 Houston/1:30 Portland." | Thu 15:30 |
| Jun 5 11:07 | Christian | "I cannot move that time. Can we go earlier or move it to Friday?" | conflict |
| Jun 5 11:18 | Holly | "How about 3:00 pm on Friday??" | proposal |
| Jun 5 16:30 | Sara to Christian | "How is 3 pm Houston/1 pm Portland on Friday?" | proposal |
| Jun 5 17:45 | Christian | "Good." | **Fri Jun 8, 15:00** |
| Jun 6 07:56 | Holly (shortened subject) | "it's on Mark's calendar (3:00 pm - Friday, June 8)" | booked |
| Jun 6 09:30 | Sara to Christian | "1 pm Portland time on Friday" | Portland time only |

| Task | Cut (UTC) | Answer | Pre-registered | Main traps |
|---|---|---|---|---|
| `meeting-reschedule-early` | 2001-06-05 10:00 | 2001-06-07 15:30 | medium | first booking "3:00 PM ... today's" is a mistake; Portland 1:30 next to Houston 3:30 |
| `meeting-reschedule-late` | 2001-06-07 14:00 | 2001-06-08 15:00 | medium | Thursday booking superseded; confirmation under a different subject; last note gives only "1 pm Portland" |

Rejected readings: Tuesday 15:00 (misread day, corrected within the hour); 13:00 or 13:30 (Portland times); Thursday 15:30 after the conflict (superseded).

## Thread 2: a gas volume that was revised (mailbox `williams-j`)

Peoples Gas lost supply on ANR contract 104684 for gas day May 30, 2001.

| UTC (Date header) | Who | What it says | State after |
|---|---|---|---|
| May 31 15:44 | Jer (Peoples) | "cut by 6,599 MMBtu"; SIQ "from 125,000 to 118,401" | **cut 6,599; SIQ 118,401** |
| May 31 19:28 | Cora (Enron) | Northern Border cuts R0255F (1,131) + T1061F (3,725) = "(4,856)" | Enron's own numbers |
| May 31 19:50 | Jer | "is now 4,856 MMBtu"; "125,000 of SIQ becomes 120,144" | **cut 4,856; SIQ 120,144** |
| Jun 4 18:50 | Jer | June 3: cut 295, SIQ 124,705 | other gas day |
| Jun 6 16:17 | Jer | June 5: cut 423, SIQ 44,577 | other gas day |

| Task | Cut (UTC) | Answer | Pre-registered | Main traps |
|---|---|---|---|---|
| `gas-cut-revision-early` | 2001-05-31 17:30 | cut 6,599; SIQ 118,401 | easy (control) | only one relevant email exists yet |
| `gas-cut-revision-late` | 2001-06-07 17:00 | cut 4,856; SIQ 120,144 | hard | first report superseded; per-contract pieces; delivered amounts 33,401 and 35,144; June 3 and June 5 look-alikes |

## Checks on the ground truth

- **Blinded re-derivation** (`results/rederivation.json`): a separate Claude session given only the instruction and the thread emails visible at each cut, never the answer key, reached the same answer on all four tasks with high confidence.
- **Evidence present at the cut**: each `solution/solve.sh` first checks that the decisive sentence is in the snapshot file it cites.
- **Timestamps**: the corpus renders every Date header with a Pacific offset (-0700/-0800). In `williams-j` (an Outlook export) the headers match the times quoted inside the emails. In `shackleton-s` (a Lotus Notes export) they run about 5 hours behind: `all_documents/11429.` is stored as 08:36 UTC and quoted as 08:36 AM Houston, so the meeting table above shows stored-header times. Cuts are applied to the headers exactly as stored, so the snapshot boundary and email order are consistent and no answer depends on true send times. The "Houston time" printed in the two meeting instructions is header time, about 5 hours earlier than the clock time inside the emails.
