# Leakage audit

## gas-cut-revision-early  (496 files)  PASS

- L1_files_after_t_or_undated: 0
- L2_clusters_straddling_t: 0
- L3_quoted_dates_after_t: 0
- L5_canary_in_agent_image: 0
- L6_instruction_leaks: 0
- L4_post_t_value_hits_for_review: 0
- L7_files_containing_answer_value: {'cut_mmbtu': 2, 'siq_purchase_mmbtu': 1}

## gas-cut-revision-late  (583 files)  PASS

- L1_files_after_t_or_undated: 0
- L2_clusters_straddling_t: 0
- L3_quoted_dates_after_t: 0
- L5_canary_in_agent_image: 0
- L6_instruction_leaks: 0
- L4_post_t_value_hits_for_review: 0
- L7_files_containing_answer_value: {'cut_mmbtu': 2, 'siq_purchase_mmbtu': 1}

## meeting-reschedule-early  (2109 files)  PASS

- L1_files_after_t_or_undated: 0
- L2_clusters_straddling_t: 0
- L3_quoted_dates_after_t: 0
- L5_canary_in_agent_image: 0
- L6_instruction_leaks: 0
- L4_post_t_value_hits_for_review: 8
  - Friday, June 8 :: environment/mailbox/all_documents/11344.
  - Friday, June 8 :: environment/mailbox/all_documents/11386.
  - Friday, June 8 :: environment/mailbox/all_documents/11398.
  - Friday, June 8 :: environment/mailbox/notes_inbox/2022.
  - Friday, June 8 :: environment/mailbox/notes_inbox/2026.
  - Friday, June 8 :: environment/mailbox/notes_inbox/2048.
  - 3 pm Houston :: environment/mailbox/all_documents/10521.
  - 3 pm Houston :: environment/mailbox/sent/6030.
  - review: All 8 hits reviewed by hand: NYMEX/COMEX exchange notices dated 31 May and 4 Jun, an internal newsletter event on 8 June, and an April ISDA email ('until about 3 pm Houston'). None concerns this meeting; they act as natural distractors, not leaks.
- L7_files_containing_answer_value: {'meeting_date': 20, 'start_time': 8}

## meeting-reschedule-late  (2234 files)  PASS

- L1_files_after_t_or_undated: 0
- L2_clusters_straddling_t: 0
- L3_quoted_dates_after_t: 0
- L5_canary_in_agent_image: 0
- L6_instruction_leaks: 0
- L4_post_t_value_hits_for_review: 0
- L7_files_containing_answer_value: {'meeting_date': 16, 'start_time': 66}

