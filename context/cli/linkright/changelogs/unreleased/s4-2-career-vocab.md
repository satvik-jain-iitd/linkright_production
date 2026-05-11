## [type: Added]
<!-- pr: TBD -->

- **S4.2 (Career-level vocabulary profile):** Extended `verb_taxonomy.yaml` with a new
  `career_level_preferences` top-level section defining three verb buckets — authority,
  credibility, and energy — for five career levels (fresher / early_career / mid / senior /
  executive). Added `get_career_level_verb_prefs(career_level)` and
  `format_career_vocab_guidance(career_level)` to `verb_taxonomy.py` with alias
  normalisation (e.g. "entry" → early_career). Injected the formatted guidance into the
  `step_10_verbose_bullets` system prompt so the LLM calibrates verb tone by seniority:
  executives get "Oversaw / Governed / Stewarded", mid-level gets "Drove / Optimized /
  Scaled", freshers get "Built / Shipped / Launched". The existing `load_verb_taxonomy`
  is protected from the new section via an explicit skip guard.
