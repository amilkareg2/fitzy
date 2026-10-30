---
name: add-exercise-mapping
description: Use when adding a new exercise or correcting which muscles an exercise trains in data/exercise_muscle_map.csv.
---

1. Muscles must exist in `data/muscles.csv`; add a new muscle there only if no existing one fits, and explain why in the PR.
2. Fill `primary_muscles` (counted as 1.0 set) and `secondary_muscles` (0.5), separated by `;`. Keep primaries to the 1–3 muscles that limit the set.
3. Set `load_type`: `external`, `bodyweight` (no load logged), `bodyweight_plus` (body weight logged as load, or belt/vest added) or `assisted`.
4. Set `import_load_rule` when the logged weight needs interpreting: `bw_threshold_60` (pull-ups, chin-ups, dips, donkey calf raises, ATG split squats: >= 60 kg logged = body weight, < 60 kg = belt load) `zero_is_machine_base` (0 kg on a machine = its own resistance, not missing data) or `zero_is_missing` (weight was not logged: count sets, skip load-based analytics).
5. Programs such as KneesOverToesGuy or GST go in `tags`, never as muscles.
6. Set `confidence` and leave a `review_note` when unsure; low-confidence rows need the owner's confirmation.
7. Changing a mapping changes historical volume numbers. Say so in the PR description.
