## [type: Added]
<!-- pr: TBD -->
- **S5.6 (Cross-bullet verb coherence enforcer):** Added `resume/lib/coherence.py` with `enforce_verb_coherence()` that detects duplicate leading verbs within a section, rephrases via Oracle gemma3:1b, and reverts if the rephrase is structurally unsound. Runs after step_11 ranking, before step_12. Oracle unavailable → skips silently.
