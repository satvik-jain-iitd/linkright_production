---
name: evaluate-job
description: Score a job description across 10 dimensions (role alignment, skill match, level fit, comp, growth, remote quality, company rep, tech stack, speed to offer, culture) and produce an A-F grade plus apply/consider/skip recommendation. Use when the user pastes a JD / JD URL and asks whether to apply, "is this job good for me?", "evaluate this role", or wants to rank multiple JDs.
---

# Evaluate Job — LinkRight Pillar 2 skill

Your job: take a JD (text, file path, or URL) and produce a 10-dimension A-F scorecard + apply/consider/skip recommendation, persisted to MongoDB for later `recommend` / `apply` queries.

## When to invoke

User says things like:
- "is this job worth applying to?"
- "evaluate this JD"
- "rank these 5 JDs for me"
- "score this role against my profile"
- Pastes a JD link/text and asks for an opinion

## How to execute

1. **Capture the JD** — ask for a file path if the user only pasted text; save to a tmp file (e.g. `/tmp/jd.md`).
2. **Run the CLI**:
   ```bash
   linkright jobsearch evaluate --jd /tmp/jd.md [--jd-url <url>]
   ```
   The command loads the user profile from MongoDB (`nuggets` + `user_context`) — or falls back to `~/.linkright/profile/profile.yaml`.
3. **Show the output** — overall grade + score, dimension breakdown with one-line reasons, and the recommendation.
4. **Follow-up actions**:
   - `linkright jobsearch recommend --top 5` — compare against prior evaluations.
   - `linkright jobsearch apply <jd_hash>` — mark an application once the user submits.

## Dimensions (all weighted 0.1)

role_alignment, skill_match, level_fit, compensation_fit, growth_potential, remote_quality, company_reputation, tech_stack, speed_to_offer, culture_signals

## Constraints

- Synchronous; no long-running jobs.
- Uses Gemini 2.0 Flash Lite with a JSON response schema (free tier). Falls back to the Groq/Gemini/Cerebras cascade if `GEMINI_API_KEY*` envs are missing.
- If MongoDB is down, results are dumped to `~/.linkright/runs/<ts>/evaluation.json` — still usable, just not queryable via `recommend`.

## Grade → recommendation map

- **A (≥90)** / **B (≥80)** → `apply`
- **C (≥70)** / top of **D** → `consider`
- **D (<65)** / **F** → `skip`
