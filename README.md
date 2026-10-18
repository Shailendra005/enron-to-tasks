# enron-to-tasks

**From "estimated tokens" to "estimated verifiable tasks": an end-to-end measurement on the public Enron email archive.**

An archive assessment usually starts with size: items, storage, tokens. Buyers price something narrower. AI labs mostly pay for finished tasks where an agent's answer can be checked, and the builders who buy whole archives price them on the tasks they can make from them. This repo measures the gap between size and buildable tasks on a real archive of 517,401 emails, then builds four gradable agent tasks out of real threads and audits them for leakage and shortcuts.

Built with Claude Code.

## Headline numbers

| Measurement | Result | Source |
|---|---|---|
| Email files / mailboxes | 517,401 / 150 | `results/profile.json` |
| Distinct Message-IDs | 517,401: **de-duplicating by Message-ID removes nothing** | `results/profile.json` |
| Content-unique messages | **253,821 (49%)**: the rest are copies across folders and mailboxes | `results/dedupe.json` |
| Tokens: raw files → bodies → unique bodies → new text | **426.6M → 243.4M → 123.1M → 64.7M** (new text is 15% of the raw count) | `results/tokens.json` |
| Candidate task threads (simple miner) | 136 of 176,459 threads | `results/candidates_summary.json` |
| Usable candidates in an independently labelled random sample | 5 / 20 (strict rule: 1 / 20) | `episodes/yield_labels.json` |
| **Estimated verifiable task seeds in the archive** | **~34 (95% CI 15–64)**, strict ~7: about 0.5 per million tokens of new text | `results/yield.json` |
| Tasks built | 4 (2 real threads × 2 cut times) | `tasks/` |
| Ground-truth checks | blind re-derivation agrees 4/4; grader self-test 42/42; oracle 1.0 and empty agent 0.0 on all 4 | `results/` |
| Leakage audit | all 4 tasks pass L1–L6 | `results/audit.md` |
| Shortcut baselines | 1 of 20 strategy × task pairs passes (see below) | `results/baselines.md` |
| Claude Sonnet 5.5 and Claude Haiku 5.5 (Claude Code agent, 5 attempts per task each) | **40 / 40 passed**: these tasks are easy for current agents (see below) | `results/summary.md` |

Token counts use OpenAI's `o200k_base` tokenizer (`cl100k_base` agrees within 1.1%). Other tokenizers, including Claude's, give different absolute numbers; **the ratios between levels are the finding.**

## What a task looks like

```
 mailbox of one employee, frozen at time t          question about a fact that changed
 (all folders, 60–90 days, nothing written after t)  ("what is the meeting time now?")
                     │                                            │
                     └──────────────► agent ◄─────────────────────┘
                                        │
                              /app/answer.json
                     {"meeting_date": "...", "start_time": "...",
                      "evidence_message_ids": ["<...>"]}
                                        │
                 separate grader container, no network
       exact field match + 1–5 real Message-IDs, at least one decisive
```

Each real thread is cut twice: once before its final revision and once after. The answer changes between the two cuts, so a memorised or "last value in the thread" answer cannot pass both.

| Task | Question | Answer at the cut | Traps | Difficulty (set before any run) |
|---|---|---|---|---|
| `meeting-reschedule-early` | When does Sara Shackleton's meeting with Mark Taylor start? | 2001-06-07 15:30 | first booking "3:00 PM ... today's" was a mistake; Portland times beside Houston times | medium |
| `meeting-reschedule-late` | same | 2001-06-08 15:00 | Thursday booking superseded after a conflict; confirmation under a shortened subject; last note gives only the Portland time | medium |
| `gas-cut-revision-early` | How much gas was cut on Peoples' contract 104684 for May 30, and the SIQ after? | 6,599 / 118,401 | control: one relevant email so far | easy |
| `gas-cut-revision-late` | same | 4,856 / 120,144 | first report revised; per-contract pieces; delivered amounts; look-alike emails for June 3 and June 5 | hard |

Full timelines, rejected readings and quotes: [`episodes/episodes.md`](episodes/episodes.md).

## Pipeline

| Step | Command | Output |
|---|---|---|
| Parse 517k files | `python -m pipeline.parse` | `messages.jsonl.gz` (local) |
| Profile | `python -m pipeline.profile` | `results/profile.json` |
| De-duplicate by content (sender + subject + minute + body hash) | `python -m pipeline.dedupe` | `results/dedupe.json` |
| Strip quoted replies, forwards and boilerplate | `python -m pipeline.strip_quotes` | `results/strip.json`, hand check `results/strip_check.md` (20/20) |
| Count tokens at four levels | `python -m pipeline.tokens` | `results/tokens.json`, `results/tokens_per_mailbox.json` |
| Mine threads where a meeting time or a volume/price changes | `python -m pipeline.mine_episodes` | `results/candidates_summary.json` |
| Estimate yield from a labelled random sample | `python -m pipeline.yield_estimate estimate` | `results/yield.json` |
| Build Harbor tasks from an episode file | `python -m pipeline.build_task episodes/<id>.json` | `tasks/<slug>/` |

`scripts/run_pipeline.sh` runs all of it (about 10 minutes on a laptop after the 443 MB download).

## Checks

| Check | Guards against | Result |
|---|---|---|
| L1 every snapshot file dated ≤ t | future emails in the snapshot | 0 on all 4 |
| L2 no duplicate cluster straddles t | a later copy hiding in another folder | 0 |
| L3 no quoted header timestamps after t | replies quoting future messages | 0 |
| L4 later answer values visible before t | the future state leaking through other mail | 8 hits in one task, reviewed by hand: unrelated exchange notices, a newsletter, an April email |
| L5 canary | the answer key reaching the agent's container | a random ID planted in `tests/expected.json` is absent from every agent image |
| L6 instruction | the question leaking the answer or the decisive subject line | 0 |
| L7 answer frequency | (difficulty signal) | the meeting date appears in 16–20 snapshot files |
| Baselines (`audit/baselines.py`) | shortcut strategies passing | first mention, latest mention, most frequent, latest in the uncut archive, latest "confirm" email: **1/20 pass** (latest mention on the early meeting cut, where it is genuinely the answer) |
| Grader self-test (`scripts/grader_selftest.py`) | a lenient grader | true answer 1; superseded 0; invented or non-decisive IDs 0; duplicate copy of the decisive email 1; 30 citations 0; malformed, missing, symlinked or oversized 0 |
| Blind re-derivation | a wrong answer key | a separate Claude session given only the instruction and the visible thread, never the key, matched all 4 with high confidence |
| Oracle / no-op agent | broken plumbing | 1.0 / 0.0 on all 4 |
| L8 agent transcripts (`audit/transcripts.py`) | the agent fetching the public corpus | 40 trials: web tools never offered, 0 network-like shell commands |

## Model results

| Model (Claude Code agent, web tools disabled) | meeting early | meeting late | gas early | gas late | Median time per trial | Median cost per trial |
|---|---|---|---|---|---|---|
| Claude Sonnet 5.5 | 5/5 | 5/5 | 5/5 | 5/5 | 73 s | $0.051 |
| Claude Haiku 5.5 | 5/5 | 5/5 | 5/5 | 5/5 | 93 s | $0.007 |

Per-trial rows are in `results/trials.csv`. Raw job folders are not published because they contain agent credentials.

**Both models solve every task.** The traps defeat the naive baselines (1 of 20 strategy and task pairs passes) but not an agent that can search and read in order. The transcripts show why: the question names something unique (contract 104684; Mark Taylor and Christian Yoder), so finding the thread is a single `grep`, and the agent then reads the thread in date order and keeps the last settled value. The difficulty labels written down before the runs (one "hard", two "medium") were wrong for current agents, and pre-registering them is what makes that visible.

This matters for valuing an archive. Labs training with RL want tasks a model sometimes fails, roughly between a few percent and most of the time, because tasks every model passes carry no learning signal. So the useful number is not only how many verifiable tasks an archive yields, but how many hard ones.

### Next: making archive tasks hard enough to train on

- **Don't hand over the search key.** Describe the situation the way an operator would, not by contract number or names, so the agent has to identify the right thread among look-alikes.
- **Require aggregation across threads.** For example, the total volume cut across every gas day in a period after all revisions, which fails on any missed or unrevised email.
- **Grade against what happened next.** Freeze the mailbox before a decision and score the agent's action against the decision actually recorded later, as in the t / t+1 design.
- **Calibrate to a pass band.** The harness here already measures pass rates per model, so each new design can be checked against a target band before it is counted as yield.

## What this shows

- **Token counts overstate content.** In this archive, only 15% of the raw token count is new writing. Half the files are copies, and Message-IDs cannot find them because every copy has its own ID.
- **Tasks, not tokens, are the scarce part.** A simple miner finds 136 candidates in 176,459 threads, and about a quarter of those survive an independent check. That is a measurable number with an error bar, which is a better input for valuing an archive than a token count.
- **A real thread can be turned into tasks that are hard to fake.** Time-split snapshots, exact fields and required evidence IDs make shortcuts and memorised answers fail, and every one of those claims is tested above.
- **Hard to fake is not the same as hard to solve.** Single-thread "what stands now" questions are easy for today's agents (40 of 40). The next lever is task design, and the same harness measures it.

## What I did not verify

- Four tasks is a demonstration, not a benchmark; pass rates on four tasks are anecdotes. Only two Claude models were run.
- The miner's recall (good threads it misses) is not measured; the yield estimate is a floor for this miner, from a sample of 20.
- Token counts are estimates with an OpenAI tokenizer.
- The corpus has no attachments or CRM data, so it cannot test linked chains such as quote → purchase order → invoice; a real small-business archive could yield more tasks or fewer. It is also very likely in model pretraining data (agent web tools were disabled).
- Removing personal data (redaction quality) was not measured here.
- The corpus renders every Date header in Pacific time; cuts use the headers exactly as stored.

## Reproduce

```bash
uv venv -p 3.13 .venv && uv pip install --python .venv/bin/python -r requirements-pipeline.txt
scripts/run_pipeline.sh                                 # download, parse, measure, rebuild tasks
.venv/bin/python audit/leakage.py && .venv/bin/python audit/baselines.py
.venv/bin/python scripts/grader_selftest.py
harbor run -p tasks -a oracle                           # 1.0 on every task
harbor run -p tasks -a claude-code -m claude-sonnet-5-5 -k 5 --ak disallowed_tools="WebSearch,WebFetch"
.venv/bin/python scripts/summarize.py <jobs-dir>
```

Mailbox snapshots are not committed. `python -m pipeline.build_task --rebuild` recreates them from your copy of the corpus and checks every SHA-256 in `snapshot_manifest.json`. See [`DATA.md`](DATA.md).
