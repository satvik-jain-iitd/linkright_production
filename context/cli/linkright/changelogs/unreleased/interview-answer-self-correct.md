# Interview, self-correcting ideal answers

## Added

- **`coach/answer_quality.py`**: a deterministic per-answer gate. Checks first-person ownership, a concrete number, enough structure for a situation/action/result, and real grounding in the candidate's career facts. No LLM, no network.
- **`generate_ideal_answer_checked()`** in `coach/answer_gen.py`: a self-correcting wrapper. Generates the ideal answer, gates it against the candidate's grounding facts, and revises up to two times until it clears the gate. Same return shape as `generate_ideal_answer`. This brings the interview pillar to the same ground-then-gate-then-revise discipline the content harness uses.

## Changed

- **`generate_ideal_answer()`** gained an optional `feedback` kwarg, appended to the prompt so a revision pass can fix named issues. Omitting it preserves the original behaviour.
- **`coach/session.py`**: the three ideal-answer call sites now use `generate_ideal_answer_checked`, so practice and sim answers self-correct before they are shown or logged.
