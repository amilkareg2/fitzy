---
name: add-exercise-mapping
description: Use when adding a new exercise or correcting which muscles an exercise trains in data/exercise_muscle_map.csv.
---

1. Muscles must exist in `data/muscles.csv`; add a new muscle there only if no existing one fits, and explain why in the PR.
2. Fill `primary_muscles` (counted as 1.0 set) and `secondary_muscles` (0.5), separated by `;`. Keep primaries to the 1–3 muscles that limit the set.
3. Set `load_type`: `external`, `bodyweight` (no load logged), `bodyweight_plus` (body weight logged as load, or belt/vest added) or `assisted`.
4. Programs such as KneesOverToesGuy or GST go in `tags`, never as muscles.
5. Set `confidence` and leave a `review_note` when unsure; low-confidence rows need the owner's confirmation.
6. Changing a mapping changes historical volume numbers. Say so in the PR description.
