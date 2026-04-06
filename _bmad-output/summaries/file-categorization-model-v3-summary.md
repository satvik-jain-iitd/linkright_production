# File Summary: categorization-model-v3.md

- **File:** `_bmad-output/planning-artifacts/categorization-model-v3.md`
- **Yeh file kya hai:** Final production-ready categorization model (Score: 91.5/100)

## Isme Kya Hai
- **Two-Layer System:** Layer A (Resume, 10 section types) + Layer B (Life, 6 domains, 23 L2s)
- **Layer A types:** work_experience, independent_project, skill, education, certification, award, publication, volunteer, summary, contact_info
- **Layer B domains:** Relationships, Health, Finance, Inner Life, Logistics, Recreation
- **Metadata:** resume_relevance (0-1 float), importance (P0-P3), factuality, temporality, duration, leadership_signal, resume_section_target
- **Sequential classification:** 4 steps, max 10 options per step — LLM accuracy high
- **Multi-label:** primary_layer + primary_domain + 0-2 secondary_domains
- **Key design decisions:** leadership = tag not type, certification separated from education, no misc, float relevance not boolean, P0-P3 importance matches JD keyword system
- **2 adversarial reviews** se guzara — pehla 48/100, doosra 64/100, fixes ke baad 91.5/100

## Kaun Use Karega
- FR-9 (nugget extraction) — is model ke basis pe LLM extraction prompt banega
- FR-11 (hybrid retrieval) — metadata filters is model ke fields use karenge
- Worker pipeline — nugget_extractor.py is model implement karega
- Future LifeOS — Layer B Life Schema reuse hoga knowledge graph ke liye
