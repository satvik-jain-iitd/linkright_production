
```text
[2026-04-24T03:24:40Z] step_14_assemble_html — starting
context: loading template cv-a4-mid-career.html; substituting header, contact, summary, per-company sections, skills, education, certifications, interests; applying theme colors
```

```text
[2026-04-24T03:24:40Z] step_14_assemble_html — filter
context: dropped 2 companies with <2 bullets
```

- SampleCo (had 0 bullets)
- Sample NGO (had 0 bullets)

```text
[2026-04-24T03:24:40Z] step_14_assemble_html — eval
context: assembly pass; bullets=10; placeholders_left=0
```

**Artifact:** `artifacts/14_final_resume.html` (14021 chars)

**Metrics:**
- Total bullets in HTML: 10
- Residual `<!-- PLACEHOLDER -->` comments: 0
- Companies rendered: 4
- Skills categories: 4
- Education entries: 1

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-04-24T03:26:06Z] step_14_assemble_html — starting
context: loading template cv-a4-mid-career.html; substituting header, contact, summary, per-company sections, skills, education, certifications, interests; applying theme colors
```

```text
[2026-04-24T03:26:06Z] step_14_assemble_html — filter
context: dropped 2 companies with <2 bullets
```

- SampleCo (had 0 bullets)
- Sample NGO (had 0 bullets)

```text
[2026-04-24T03:26:06Z] step_14_assemble_html — eval
context: assembly pass; bullets=10; placeholders_left=0
```

**Artifact:** `artifacts/14_final_resume.html` (13666 chars)

**Metrics:**
- Total bullets in HTML: 10
- Residual `<!-- PLACEHOLDER -->` comments: 0
- Companies rendered: 4
- Skills categories: 4
- Education entries: 1

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-04-24T03:26:19Z] step_15_pdf — starting
context: launching headless Chromium via Playwright; loading HTML; rendering to A4 PDF with print_background=true; expecting 1-page output
```

```text
[2026-04-24T03:26:25Z] step_15_pdf — eval
context: pdf pass; 1 pages; 242749 bytes
```

**Artifact:** `artifacts/15_final_resume.pdf`

**Metrics:**
- Page count: 1
- File size: 242749 bytes (237.1 KB)

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-04-24T04:33:20Z] step_14_assemble_html — starting
context: loading template cv-a4-mid-career.html; substituting header, contact, summary, per-company sections, skills, education, certifications, interests; applying theme colors
```

```text
[2026-04-24T04:33:20Z] step_14_assemble_html — fallback
context: reconstructed companies list from parsed_resume.experiences (step_07 returned empty); using 4
```

```text
[2026-04-24T04:33:20Z] step_14_assemble_html — fallback
context: filled 4 sparse companies from raw nuggets (generic-impact fallback)
```

- Acme Bank: had 0 JD-aligned bullets, synthesized 2 more from top-importance raw nuggets
- TechCo SaaS: had 0 JD-aligned bullets, synthesized 2 more from top-importance raw nuggets
- SampleCo: had 0 JD-aligned bullets, synthesized 2 more from top-importance raw nuggets
- Sample NGO: had 0 JD-aligned bullets, synthesized 2 more from top-importance raw nuggets

```text
[2026-04-24T04:33:22Z] step_14_assemble_html — eval
context: assembly partial; bullets=0; placeholders_left=0
```

**Artifact:** `artifacts/14_final_resume.html` (13090 chars)

**Metrics:**
- Total bullets in HTML: 0
- Residual `<!-- PLACEHOLDER -->` comments: 0
- Companies rendered: 0
- Skills categories: 0
- Education entries: 0

**Evaluation:** PARTIAL

**Gaps:**
- 0 bullets in final HTML — resume will look blank

```text
[2026-04-24T04:33:56Z] step_15_pdf — starting
context: launching headless Chromium via Playwright; loading HTML; rendering to A4 PDF with print_background=true; expecting 1-page output
```

```text
[2026-04-24T04:34:03Z] step_15_pdf — eval
context: pdf pass; 1 pages; 173512 bytes
```

**Artifact:** `artifacts/15_final_resume.pdf`

**Metrics:**
- Page count: 1
- File size: 173512 bytes (169.4 KB)

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-05-01T06:35:40Z] step_00_ingest_pdf — starting
context: extracting plain text from inputs/resume.pdf via pypdf; expecting > 1.5KB text, name Jane Doe, email + phone present
```

```text
[2026-05-01T06:35:41Z] step_00_ingest_pdf — eval
context: extraction pass; 2996 chars; gaps=0
```

**Artifact:** `artifacts/00_resume_raw_text.txt` (2996 chars)

**Metrics:**
- Character count: 2996
- Contains name (case-insensitive): True
- Email extracted: `jane.doe@example.com`
- Phone extracted: `+1-555-0123`
- Bullet chars (• or ●): 15
- pypdf corruption hits (acronym-splitting artifacts): 0
- Sample corruption: `[]`

**Evaluation:** PASS

**Gaps found:**
- none

**Root-cause hypothesis:**
pypdf is inserting a space after certain capital letters (M, L, etc.) when the source
PDF uses bold or kerned glyphs. This is a KNOWN limitation of pypdf vs. production's
`unpdf` (JS library) — we need to verify whether unpdf handles this better, or if the
LLM in Step 1 handles "AM L" as "AML" via context. If the LLM cannot recover, this is
a P0 upstream finding that corrupts every downstream phase (nuggets extracted as
"AM L" won't cosine-match JD requirement "AML" or "anti money laundering").

**First 500 chars of extracted text:**
```
JANE DOE SENIOR PRODUCT MANAGER — AML & FINANCIAL CRIME Phone: +1-555-0123 Email: jane.doe@example.com LinkedIn: linkedin.com/in/janedoe-example Professional Experience Acme Bank — Senior Associate Product Manager Gurugram | Jul 2024 – Present • Architected AML risk engine for 100M+ accounts across 40+ markets, cutting speed-to-market by 70% • Secured in-house platform sign-off over NICE Actimize and SAS by evaluating 3 vendors on AML configurability • Delivered 60+ features 
```

```text
[2026-05-01T06:35:41Z] step_01_parse_resume — starting
context: calling Groq 70B with vendored RESUME_PARSE_FALLBACK prompt (same prompt as website /api/onboarding/parse-resume Langfuse key 'resume-parse-structured'); input is 2996-char text from Step 0; temp=0.2; expecting markdown with ## EDUCATION / ## SKILLS / ## EXPERIENCE / ## PROJECTS sections
```

```text
[2026-05-01T06:35:43Z] step_01_parse_resume — eval
context: parse pass; 4 companies; gaps=0
```

**Artifact:** `artifacts/01_resume_parsed.json` (markdown + parsed dict)

**Metrics:**
- Companies parsed: ['Acme Bank', 'TechCo SaaS', 'SampleCo', 'Sample NGO']
- Experience blocks: 4
- Total bullets: 12
- Total projects (in-role + top-level): 2
- Skills count: 20
- Education entries: 1
- Certifications: 1
- LLM usage: {'provider': 'groq', 'model': 'llama-3.3-70b-versatile', 'latency_s': 1.89, 'prompt_tokens': 1165, 'completion_tokens': 671, 'total_tokens': 1836, 'fallback_used': False}
- "AM L"/"M anager" corruption propagated into bullets: False

**Evaluation:** PASS

**Gaps:**
- none

**Root-cause hypothesis:**
Groq 70B cleanly extracted the Markdown structure. Corruption from Step 0 did NOT propagate verbatim — LLM may have normalized, OR parsing lost those bullets. Check markdown raw output in artifact.

**Sample bullets (first role, first 3):**
```
- Architected AML risk engine for 100M+ accounts across 40+ markets, cutting speed-to-market by 70%
- Secured in-house platform sign-off over NICE Actimize and SAS by evaluating 3 vendors on AML configurability
- Delivered 60+ features across 4 zero-spillover PIs leading 18-member team through 2 strategy pivots under SAFe
```

```text
[2026-05-01T06:35:43Z] step_02_extract_nuggets — starting
context: calling Groq 70B with vendored NUGGET_EXTRACT_MD prompt (same as worker/app/tools/nugget_extractor.py Langfuse key 'nugget_extractor_md'); input is the raw resume text; expecting 20-40 atomic ## nugget blocks each tagged with company, role, importance, answer, tags
```

```text
[2026-05-01T06:35:45Z] step_02_extract_nuggets — eval
context: nuggets pass; 16 extracted; gaps=0
```

**Artifact:** `artifacts/02_nuggets_extracted.json`

**Metrics:**
- Total nuggets: 16
- Per-company distribution: {'american express': 6, 'techco_saas': 4, 'none': 5, 'indian institute of technology, delhi': 1}
- Importance distribution: {'P0': 1, 'P1': 6, 'P2': 4, 'P3': 5}
- LLM usage: {'provider': 'groq', 'model': 'llama-3.3-70b-versatile', 'latency_s': 2.77, 'prompt_tokens': 1440, 'completion_tokens': 1151, 'total_tokens': 2591, 'fallback_used': False}

**Evaluation:** PASS

**Gaps:**
- none

**Sample nugget (#0):**
```
answer: Architected AML risk engine for 100M+ accounts at Acme Bank across 40+ markets, cutting speed-to-market by 70%.
company: Acme Bank  role: Senior Associate Product Manager
importance: P0  tags: aml, product management, risk engine
id: 623426F5
```

**Root-cause hypothesis:**
Atomization prompt is working as intended.

```text
[2026-05-01T06:35:45Z] step_03_embed_nuggets — starting
context: embedding 16 nuggets via POST oracle.linkright.in/lifeos/embed (nomic-embed-text, 768-dim); one request per nugget, sequential; expecting all to return 768-dim vectors
```

```text
[2026-05-01T06:35:47Z] step_03_embed_nuggets — eval
context: embed partial; 16/16 ok; failures=0
```

**Artifact:** `artifacts/03_nuggets_embedded.jsonl` (one nugget per line with embedding)

**Metrics:**
- Embedded: 16/16
- Failed: 0
- Dimensions (sample): 384

**Pairwise cosine sample (5 random nuggets, C(5,2)=10 pairs):**
```
  0.482  Built on-chain AML risk scorer using OFAC sanction ↔ Graduated with B.Tech in Civil Engineering from In
  0.560  Built on-chain AML risk scorer using OFAC sanction ↔ Built GenAI root-cause product at TechCo SaaS, cuttin
  0.671  Built on-chain AML risk scorer using OFAC sanction ↔ Architected AML risk engine for 100M+ accounts at 
  0.474  Built on-chain AML risk scorer using OFAC sanction ↔ Conducted 20+ UX sessions with compliance analysts
  0.405  Graduated with B.Tech in Civil Engineering from In ↔ Built GenAI root-cause product at TechCo SaaS, cuttin
  0.377  Graduated with B.Tech in Civil Engineering from In ↔ Architected AML risk engine for 100M+ accounts at 
  0.376  Graduated with B.Tech in Civil Engineering from In ↔ Conducted 20+ UX sessions with compliance analysts
  0.540  Built GenAI root-cause product at TechCo SaaS, cuttin ↔ Architected AML risk engine for 100M+ accounts at 
  0.401  Built GenAI root-cause product at TechCo SaaS, cuttin ↔ Conducted 20+ UX sessions with compliance analysts
  0.571  Architected AML risk engine for 100M+ accounts at  ↔ Conducted 20+ UX sessions with compliance analysts
```

**Evaluation:** PARTIAL

**Gaps:**
- some embeddings are not 768-dim

**Root-cause hypothesis:**
Embeddings generated cleanly via Oracle /lifeos/embed. Pairwise scores should show semantic clustering — similar-domain nuggets (e.g., two AML nuggets) score higher than cross-domain (e.g., AML vs. education). If scores look flat (all ~0.4-0.6), nomic-embed-text is producing undifferentiated vectors for this domain — known nomic behavior; our 0.50 threshold was calibrated for this.

```text
[2026-05-01T08:13:41Z] step_00_ingest_pdf — starting
context: extracting plain text from inputs/resume.pdf via pypdf; expecting > 1.5KB text, name Jane Doe, email + phone present
```

```text
[2026-05-01T08:13:42Z] step_00_ingest_pdf — eval
context: extraction pass; 2996 chars; gaps=0
```

**Artifact:** `artifacts/00_resume_raw_text.txt` (2996 chars)

**Metrics:**
- Character count: 2996
- Contains name (case-insensitive): True
- Email extracted: `jane.doe@example.com`
- Phone extracted: `+1-555-0123`
- Bullet chars (• or ●): 15
- pypdf corruption hits (acronym-splitting artifacts): 0
- Sample corruption: `[]`

**Evaluation:** PASS

**Gaps found:**
- none

**Root-cause hypothesis:**
pypdf is inserting a space after certain capital letters (M, L, etc.) when the source
PDF uses bold or kerned glyphs. This is a KNOWN limitation of pypdf vs. production's
`unpdf` (JS library) — we need to verify whether unpdf handles this better, or if the
LLM in Step 1 handles "AM L" as "AML" via context. If the LLM cannot recover, this is
a P0 upstream finding that corrupts every downstream phase (nuggets extracted as
"AM L" won't cosine-match JD requirement "AML" or "anti money laundering").

**First 500 chars of extracted text:**
```
JANE DOE SENIOR PRODUCT MANAGER — AML & FINANCIAL CRIME Phone: +1-555-0123 Email: jane.doe@example.com LinkedIn: linkedin.com/in/janedoe-example Professional Experience Acme Bank — Senior Associate Product Manager Gurugram | Jul 2024 – Present • Architected AML risk engine for 100M+ accounts across 40+ markets, cutting speed-to-market by 70% • Secured in-house platform sign-off over NICE Actimize and SAS by evaluating 3 vendors on AML configurability • Delivered 60+ features 
```

```text
[2026-05-01T08:13:42Z] step_01_parse_resume — starting
context: calling Groq 70B with vendored RESUME_PARSE_FALLBACK prompt (same prompt as website /api/onboarding/parse-resume Langfuse key 'resume-parse-structured'); input is 2996-char text from Step 0; temp=0.2; expecting markdown with ## EDUCATION / ## SKILLS / ## EXPERIENCE / ## PROJECTS sections
```

```text
[2026-05-01T08:13:44Z] step_01_parse_resume — eval
context: parse pass; 4 companies; gaps=0
```

**Artifact:** `artifacts/01_resume_parsed.json` (markdown + parsed dict)

**Metrics:**
- Companies parsed: ['Acme Bank', 'TechCo SaaS', 'SampleCo', 'Sample NGO']
- Experience blocks: 4
- Total bullets: 12
- Total projects (in-role + top-level): 2
- Skills count: 20
- Education entries: 1
- Certifications: 1
- LLM usage: {'provider': 'groq', 'model': 'llama-3.3-70b-versatile', 'latency_s': 2.79, 'prompt_tokens': 1165, 'completion_tokens': 671, 'total_tokens': 1836, 'fallback_used': False}
- "AM L"/"M anager" corruption propagated into bullets: False

**Evaluation:** PASS

**Gaps:**
- none

**Root-cause hypothesis:**
Groq 70B cleanly extracted the Markdown structure. Corruption from Step 0 did NOT propagate verbatim — LLM may have normalized, OR parsing lost those bullets. Check markdown raw output in artifact.

**Sample bullets (first role, first 3):**
```
- Architected AML risk engine for 100M+ accounts across 40+ markets, cutting speed-to-market by 70%
- Secured in-house platform sign-off over NICE Actimize and SAS by evaluating 3 vendors on AML configurability
- Delivered 60+ features across 4 zero-spillover PIs leading 18-member team through 2 strategy pivots under SAFe
```

```text
[2026-05-01T08:13:44Z] step_02_extract_nuggets — starting
context: calling Groq 70B with vendored NUGGET_EXTRACT_MD prompt (same as worker/app/tools/nugget_extractor.py Langfuse key 'nugget_extractor_md'); input is the raw resume text; expecting 20-40 atomic ## nugget blocks each tagged with company, role, importance, answer, tags
```

```text
[2026-05-01T08:13:47Z] step_02_extract_nuggets — eval
context: nuggets partial; 17 extracted; gaps=1
```

**Artifact:** `artifacts/02_nuggets_extracted.json`

**Metrics:**
- Total nuggets: 17
- Per-company distribution: {'american express': 6, 'techco_saas': 4, 'sampleco': 1, 'sample_ngo': 1, 'none': 4, 'indian institute of technology, delhi': 1}
- Importance distribution: {'P0': 2, 'P1': 5, 'P2': 4, 'P3': 6}
- LLM usage: {'provider': 'groq', 'model': 'llama-3.3-70b-versatile', 'latency_s': 2.64, 'prompt_tokens': 1440, 'completion_tokens': 1215, 'total_tokens': 2655, 'fallback_used': False}

**Evaluation:** PARTIAL

**Gaps:**
- 1 nuggets appear multi-signal (should be atomized): ['83CA690D']

**Sample nugget (#0):**
```
answer: Architected AML risk engine for 100M+ accounts at Acme Bank across 40+ markets, cutting speed-to-market by 70%.
company: Acme Bank  role: Senior Associate Product Manager
importance: P0  tags: aml, product_management, risk_engine
id: 623426F5
```

**Root-cause hypothesis:**
If count is low, prompt may be too conservative at temp 0.3. If multi-signal is high, single-signal rule isn't firing — enforce via stricter prompt language. If AcmeBank missing, company-tagging rule is failing on 'Acme Bank — Senior Associate Product M anager' header (note pypdf 'M anager' corruption).

```text
[2026-05-01T08:13:47Z] step_03_embed_nuggets — starting
context: embedding 17 nuggets via POST oracle.linkright.in/lifeos/embed (nomic-embed-text, 768-dim); one request per nugget, sequential; expecting all to return 768-dim vectors
```

```text
[2026-05-01T08:13:48Z] step_03_embed_nuggets — eval
context: embed partial; 17/17 ok; failures=0
```

**Artifact:** `artifacts/03_nuggets_embedded.jsonl` (one nugget per line with embedding)

**Metrics:**
- Embedded: 17/17
- Failed: 0
- Dimensions (sample): 384

**Pairwise cosine sample (5 random nuggets, C(5,2)=10 pairs):**
```
  0.623  Built on-chain AML risk scorer using OFAC sanction ↔ Engineered resume MCP server with 8 Python tools a
  0.671  Built on-chain AML risk scorer using OFAC sanction ↔ Architected AML risk engine for 100M+ accounts at 
  0.474  Built on-chain AML risk scorer using OFAC sanction ↔ Conducted 20+ UX sessions with compliance analysts
  0.484  Built on-chain AML risk scorer using OFAC sanction ↔ Grew product adoption from 35% to 85% at TechCo SaaS 
  0.445  Engineered resume MCP server with 8 Python tools a ↔ Architected AML risk engine for 100M+ accounts at 
  0.477  Engineered resume MCP server with 8 Python tools a ↔ Conducted 20+ UX sessions with compliance analysts
  0.443  Engineered resume MCP server with 8 Python tools a ↔ Grew product adoption from 35% to 85% at TechCo SaaS 
  0.560  Architected AML risk engine for 100M+ accounts at  ↔ Conducted 20+ UX sessions with compliance analysts
  0.545  Architected AML risk engine for 100M+ accounts at  ↔ Grew product adoption from 35% to 85% at TechCo SaaS 
  0.429  Conducted 20+ UX sessions with compliance analysts ↔ Grew product adoption from 35% to 85% at TechCo SaaS 
```

**Evaluation:** PARTIAL

**Gaps:**
- some embeddings are not 768-dim

**Root-cause hypothesis:**
Embeddings generated cleanly via Oracle /lifeos/embed. Pairwise scores should show semantic clustering — similar-domain nuggets (e.g., two AML nuggets) score higher than cross-domain (e.g., AML vs. education). If scores look flat (all ~0.4-0.6), nomic-embed-text is producing undifferentiated vectors for this domain — known nomic behavior; our 0.50 threshold was calibrated for this.

```text
[2026-05-01T11:59:04Z] step_00_ingest_pdf — cache_hit
context: reusing 00_resume_raw_text.txt (3073 bytes)
```

```text
[2026-05-01T11:59:04Z] step_01_parse_resume — starting
context: calling Groq 70B with vendored RESUME_PARSE_FALLBACK prompt (same prompt as website /api/onboarding/parse-resume Langfuse key 'resume-parse-structured'); input is 2996-char text from Step 0; temp=0.2; expecting markdown with ## EDUCATION / ## SKILLS / ## EXPERIENCE / ## PROJECTS sections
```

```text
[2026-05-01T11:59:20Z] step_01_parse_resume — eval
context: parse pass; 4 companies; gaps=0
```

**Artifact:** `artifacts/01_resume_parsed.json` (markdown + parsed dict)

**Metrics:**
- Companies parsed: ['Acme Bank', 'TechCo SaaS', 'SampleCo', 'Sample NGO']
- Experience blocks: 4
- Total bullets: 12
- Total projects (in-role + top-level): 2
- Skills count: 20
- Education entries: 1
- Certifications: 0
- LLM usage: {'provider': 'agent_claude', 'fallback_used': False, 'prompt_tokens': 46762, 'completion_tokens': 1029, 'input_tokens': 6, 'output_tokens': 1029, 'cache_creation_input_tokens': 29996, 'cache_read_input_tokens': 16760, 'total_tokens': 47791, 'cost_usd': 0.22161, 'duration_ms': 10382, 'deterministic_applied': False, 'deterministic_seed_supported': False, 'klass': 'A', 'intent': 'step_01_parse_resume'}
- "AM L"/"M anager" corruption propagated into bullets: False

**Evaluation:** PASS

**Gaps:**
- none

**Root-cause hypothesis:**
Groq 70B cleanly extracted the Markdown structure. Corruption from Step 0 did NOT propagate verbatim — LLM may have normalized, OR parsing lost those bullets. Check markdown raw output in artifact.

**Sample bullets (first role, first 3):**
```
- Architected AML risk engine for 100M+ accounts across 40+ markets, cutting speed-to-market by 70%
- Secured in-house platform sign-off over NICE Actimize and SAS by evaluating 3 vendors on AML configurability
- Delivered 60+ features across 4 zero-spillover PIs leading 18-member team through 2 strategy pivots under SAFe
```

```text
[2026-05-01T11:59:20Z] step_02_extract_nuggets — starting
context: calling Groq 70B with vendored NUGGET_EXTRACT_MD prompt (same as worker/app/tools/nugget_extractor.py Langfuse key 'nugget_extractor_md'); input is the raw resume text; expecting 20-40 atomic ## nugget blocks each tagged with company, role, importance, answer, tags
```

```text
[2026-05-01T11:59:45Z] step_02_extract_nuggets — eval
context: nuggets partial; 21 extracted; gaps=1
```

**Artifact:** `artifacts/02_nuggets_extracted.json`

**Metrics:**
- Total nuggets: 21
- Per-company distribution: {'american express': 7, 'techco_saas': 5, 'sampleco': 1, 'sample_ngo': 1, 'none': 6, 'indian institute of technology, delhi': 1}
- Importance distribution: {'P0': 3, 'P1': 8, 'P2': 10}
- LLM usage: {'provider': 'agent_claude', 'fallback_used': False, 'prompt_tokens': 47141, 'completion_tokens': 2275, 'input_tokens': 6, 'output_tokens': 2275, 'cache_creation_input_tokens': 30375, 'cache_read_input_tokens': 16760, 'total_tokens': 49416, 'cost_usd': 0.25512875, 'duration_ms': 20710, 'deterministic_applied': False, 'deterministic_seed_supported': False, 'klass': 'A', 'intent': 'step_02_extract_nuggets'}

**Evaluation:** PARTIAL

**Gaps:**
- 2 nuggets appear multi-signal (should be atomized): ['E6D29827', 'F8D78939']

**Sample nugget (#0):**
```
answer: Architected AML risk engine for 100M+ accounts across 40+ markets at Acme Bank, cutting speed-to-market by 70%.
company: Acme Bank  role: Senior Associate Product Manager
importance: P0  tags: aml, risk-engine, platform, fincrime
id: 26A54BE7
```

**Root-cause hypothesis:**
If count is low, prompt may be too conservative at temp 0.3. If multi-signal is high, single-signal rule isn't firing — enforce via stricter prompt language. If AcmeBank missing, company-tagging rule is failing on 'Acme Bank — Senior Associate Product M anager' header (note pypdf 'M anager' corruption).

```text
[2026-05-01T11:59:45Z] step_03_embed_nuggets — cache_hit
context: reusing 03_nuggets_embedded.jsonl
```

```text
[2026-05-01T12:02:39Z] step_00_ingest_pdf — cache_hit
context: reusing 00_resume_raw_text.txt (3073 bytes)
```

```text
[2026-05-01T12:02:39Z] step_01_parse_resume — cache_hit
context: reusing 01_resume_parsed.json
```

```text
[2026-05-01T12:02:39Z] step_02_extract_nuggets — cache_hit
context: reusing 02_nuggets_extracted.json
```

```text
[2026-05-01T12:02:39Z] step_03_embed_nuggets — starting
context: embedding 21 nuggets via POST oracle.linkright.in/lifeos/embed (nomic-embed-text, 768-dim); one request per nugget, sequential; expecting all to return 768-dim vectors
```

```text
[2026-05-01T12:02:40Z] step_03_embed_nuggets — eval
context: embed partial; 21/21 ok; failures=0
```

**Artifact:** `artifacts/03_nuggets_embedded.jsonl` (one nugget per line with embedding)

**Metrics:**
- Embedded: 21/21
- Failed: 0
- Dimensions (sample): 384

**Pairwise cosine sample (5 random nuggets, C(5,2)=10 pairs):**
```
  0.774  Building on-chain AML risk scorer using OFAC sanct ↔ Designed blockchain risk pipeline against global w
  0.677  Building on-chain AML risk scorer using OFAC sanct ↔ Secured in-house AML platform sign-off over NICE A
  0.485  Building on-chain AML risk scorer using OFAC sanct ↔ Grew product adoption from 35% to 85% across 1,500
  0.399  Building on-chain AML risk scorer using OFAC sanct ↔ Felicitated by Union Education Minister for CBSE S
  0.635  Designed blockchain risk pipeline against global w ↔ Secured in-house AML platform sign-off over NICE A
  0.468  Designed blockchain risk pipeline against global w ↔ Grew product adoption from 35% to 85% across 1,500
  0.381  Designed blockchain risk pipeline against global w ↔ Felicitated by Union Education Minister for CBSE S
  0.478  Secured in-house AML platform sign-off over NICE A ↔ Grew product adoption from 35% to 85% across 1,500
  0.374  Secured in-house AML platform sign-off over NICE A ↔ Felicitated by Union Education Minister for CBSE S
  0.451  Grew product adoption from 35% to 85% across 1,500 ↔ Felicitated by Union Education Minister for CBSE S
```

**Evaluation:** PARTIAL

**Gaps:**
- some embeddings are not 768-dim

**Root-cause hypothesis:**
Embeddings generated cleanly via Oracle /lifeos/embed. Pairwise scores should show semantic clustering — similar-domain nuggets (e.g., two AML nuggets) score higher than cross-domain (e.g., AML vs. education). If scores look flat (all ~0.4-0.6), nomic-embed-text is producing undifferentiated vectors for this domain — known nomic behavior; our 0.50 threshold was calibrated for this.

```text
[2026-05-01T16:05:52Z] step_14_assemble_html — starting
context: loading template cv-a4-mid-career.html; substituting header, contact, summary, per-company sections, skills, education, certifications, interests; applying theme colors
```

```text
[2026-05-01T16:05:52Z] step_14_assemble_html — fallback
context: reconstructed companies list from parsed_resume.experiences (step_07 returned empty); using 4
```

```text
[2026-05-01T16:05:52Z] step_14_assemble_html — acronym_expansion
context: learned 5 acronym pair(s) from source text; expanded 2 on first use: ['AML', 'TCV']
```

Learned dict: Team=Integrations focus, AML=Anti-Money Laundering, CDL=Common Data Layer, TCV=Total Contract Value, Award=SVP Risk Management

```text
[2026-05-01T16:05:52Z] step_14_assemble_html — eval
context: assembly pass; bullets=10; placeholders_left=0
```

**Artifact:** `artifacts/14_final_resume.html` (13090 chars)

**Metrics:**
- Total bullets in HTML: 10
- Residual `<!-- PLACEHOLDER -->` comments: 0
- Companies rendered: 0
- Skills categories: 0
- Education entries: 0

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-05-01T16:05:52Z] step_15_pdf — starting
context: launching headless Chromium via Playwright; loading HTML; rendering to A4 PDF with print_background=true; expecting 1-page output
```

```text
[2026-05-01T16:05:54Z] step_15_pdf — eval
context: pdf pass; 1 pages; 193207 bytes
```

**Artifact:** `artifacts/15_final_resume.pdf`

**Metrics:**
- Page count: 1
- File size: 193207 bytes (188.7 KB)

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-05-01T18:18:55Z] step_14_assemble_html — starting
context: loading template cv-a4-mid-career.html; substituting header, contact, summary, per-company sections, skills, education, certifications, interests; applying theme colors
```

```text
[2026-05-01T18:18:55Z] step_14_assemble_html — fallback
context: reconstructed companies list from parsed_resume.experiences (step_07 returned empty); using 4
```

```text
[2026-05-01T18:18:55Z] step_14_assemble_html — acronym_expansion
context: learned 5 acronym pair(s) from source text; expanded 2 on first use: ['AML', 'TCV']
```

Learned dict: Team=Integrations focus, AML=Anti-Money Laundering, CDL=Common Data Layer, TCV=Total Contract Value, Award=SVP Risk Management

```text
[2026-05-01T18:18:55Z] step_14_assemble_html — eval
context: assembly pass; bullets=9; placeholders_left=0
```

**Artifact:** `artifacts/14_final_resume.html` (12810 chars)

**Metrics:**
- Total bullets in HTML: 9
- Residual `<!-- PLACEHOLDER -->` comments: 0
- Companies rendered: 0
- Skills categories: 0
- Education entries: 0

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-05-01T18:18:55Z] step_15_pdf — starting
context: launching headless Chromium via Playwright; loading HTML; rendering to A4 PDF with print_background=true; expecting 1-page output
```

```text
[2026-05-01T18:18:57Z] step_15_pdf — eval
context: pdf pass; 1 pages; 191170 bytes
```

**Artifact:** `artifacts/15_final_resume.pdf`

**Metrics:**
- Page count: 1
- File size: 191170 bytes (186.7 KB)

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-05-01T18:21:32Z] step_14_assemble_html — starting
context: loading template cv-a4-mid-career.html; substituting header, contact, summary, per-company sections, skills, education, certifications, interests; applying theme colors
```

```text
[2026-05-01T18:21:32Z] step_14_assemble_html — fallback
context: reconstructed companies list from parsed_resume.experiences (step_07 returned empty); using 4
```

```text
[2026-05-01T18:21:32Z] step_14_assemble_html — acronym_expansion
context: learned 5 acronym pair(s) from source text; expanded 2 on first use: ['AML', 'TCV']
```

Learned dict: Team=Integrations focus, AML=Anti-Money Laundering, CDL=Common Data Layer, TCV=Total Contract Value, Award=SVP Risk Management

```text
[2026-05-01T18:21:32Z] step_14_assemble_html — eval
context: assembly pass; bullets=9; placeholders_left=0
```

**Artifact:** `artifacts/14_final_resume.html` (12835 chars)

**Metrics:**
- Total bullets in HTML: 9
- Residual `<!-- PLACEHOLDER -->` comments: 0
- Companies rendered: 0
- Skills categories: 0
- Education entries: 0

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-05-01T18:21:32Z] step_15_pdf — starting
context: launching headless Chromium via Playwright; loading HTML; rendering to A4 PDF with print_background=true; expecting 1-page output
```

```text
[2026-05-01T18:21:34Z] step_15_pdf — eval
context: pdf pass; 1 pages; 191224 bytes
```

**Artifact:** `artifacts/15_final_resume.pdf`

**Metrics:**
- Page count: 1
- File size: 191224 bytes (186.7 KB)

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-05-01T18:28:24Z] step_14_assemble_html — starting
context: loading template cv-a4-mid-career.html; substituting header, contact, summary, per-company sections, skills, education, certifications, interests; applying theme colors
```

```text
[2026-05-01T18:28:24Z] step_14_assemble_html — fallback
context: reconstructed companies list from parsed_resume.experiences (step_07 returned empty); using 4
```

```text
[2026-05-01T18:28:24Z] step_14_assemble_html — acronym_expansion
context: learned 5 acronym pair(s) from source text; expanded 2 on first use: ['AML', 'TCV']
```

Learned dict: Team=Integrations focus, AML=Anti-Money Laundering, CDL=Common Data Layer, TCV=Total Contract Value, Award=SVP Risk Management

```text
[2026-05-01T18:28:24Z] step_14_assemble_html — eval
context: assembly pass; bullets=9; placeholders_left=0
```

**Artifact:** `artifacts/14_final_resume.html` (12835 chars)

**Metrics:**
- Total bullets in HTML: 9
- Residual `<!-- PLACEHOLDER -->` comments: 0
- Companies rendered: 0
- Skills categories: 0
- Education entries: 0

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-05-01T18:28:24Z] step_15_pdf — starting
context: launching headless Chromium via Playwright; loading HTML; rendering to A4 PDF with print_background=true; expecting 1-page output
```

```text
[2026-05-01T18:28:26Z] step_15_pdf — eval
context: pdf pass; 1 pages; 191224 bytes
```

**Artifact:** `artifacts/15_final_resume.pdf`

**Metrics:**
- Page count: 1
- File size: 191224 bytes (186.7 KB)

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-05-01T18:29:48Z] step_14_assemble_html — starting
context: loading template cv-a4-mid-career.html; substituting header, contact, summary, per-company sections, skills, education, certifications, interests; applying theme colors
```

```text
[2026-05-01T18:29:48Z] step_14_assemble_html — acronym_expansion
context: learned 5 acronym pair(s) from source text; expanded 2 on first use: ['AML', 'TCV']
```

Learned dict: Team=Integrations focus, AML=Anti-Money Laundering, CDL=Common Data Layer, TCV=Total Contract Value, Award=SVP Risk Management

```text
[2026-05-01T18:29:48Z] step_14_assemble_html — eval
context: assembly pass; bullets=9; placeholders_left=0
```

**Artifact:** `artifacts/14_final_resume.html` (14346 chars)

**Metrics:**
- Total bullets in HTML: 9
- Residual `<!-- PLACEHOLDER -->` comments: 0
- Companies rendered: 4
- Skills categories: 1
- Education entries: 1

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-05-01T18:29:48Z] step_15_pdf — starting
context: launching headless Chromium via Playwright; loading HTML; rendering to A4 PDF with print_background=true; expecting 1-page output
```

```text
[2026-05-01T18:29:50Z] step_15_pdf — eval
context: pdf pass; 1 pages; 244126 bytes
```

**Artifact:** `artifacts/15_final_resume.pdf`

**Metrics:**
- Page count: 1
- File size: 244126 bytes (238.4 KB)

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-05-01T18:35:23Z] step_14_assemble_html — starting
context: loading template cv-a4-mid-career.html; substituting header, contact, summary, per-company sections, skills, education, certifications, interests; applying theme colors
```

```text
[2026-05-01T18:35:23Z] step_14_assemble_html — acronym_expansion
context: learned 5 acronym pair(s) from source text; expanded 2 on first use: ['AML', 'TCV']
```

Learned dict: Team=Integrations focus, AML=Anti-Money Laundering, CDL=Common Data Layer, TCV=Total Contract Value, Award=SVP Risk Management

```text
[2026-05-01T18:35:23Z] step_14_assemble_html — eval
context: assembly pass; bullets=9; placeholders_left=0
```

**Artifact:** `artifacts/14_final_resume.html` (14336 chars)

**Metrics:**
- Total bullets in HTML: 9
- Residual `<!-- PLACEHOLDER -->` comments: 0
- Companies rendered: 4
- Skills categories: 1
- Education entries: 1

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-05-01T18:35:23Z] step_15_pdf — starting
context: launching headless Chromium via Playwright; loading HTML; rendering to A4 PDF with print_background=true; expecting 1-page output
```

```text
[2026-05-01T18:35:25Z] step_15_pdf — eval
context: pdf pass; 1 pages; 244094 bytes
```

**Artifact:** `artifacts/15_final_resume.pdf`

**Metrics:**
- Page count: 1
- File size: 244094 bytes (238.4 KB)

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-05-01T18:36:35Z] step_14_assemble_html — starting
context: loading template cv-a4-mid-career.html; substituting header, contact, summary, per-company sections, skills, education, certifications, interests; applying theme colors
```

```text
[2026-05-01T18:36:35Z] step_14_assemble_html — acronym_expansion
context: learned 5 acronym pair(s) from source text; expanded 2 on first use: ['AML', 'TCV']
```

Learned dict: Team=Integrations focus, AML=Anti-Money Laundering, CDL=Common Data Layer, TCV=Total Contract Value, Award=SVP Risk Management

```text
[2026-05-01T18:36:35Z] step_14_assemble_html — eval
context: assembly pass; bullets=9; placeholders_left=0
```

**Artifact:** `artifacts/14_final_resume.html` (14559 chars)

**Metrics:**
- Total bullets in HTML: 9
- Residual `<!-- PLACEHOLDER -->` comments: 0
- Companies rendered: 4
- Skills categories: 1
- Education entries: 1

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-05-01T18:36:35Z] step_15_pdf — starting
context: launching headless Chromium via Playwright; loading HTML; rendering to A4 PDF with print_background=true; expecting 1-page output
```

```text
[2026-05-01T18:36:37Z] step_15_pdf — eval
context: pdf pass; 1 pages; 245819 bytes
```

**Artifact:** `artifacts/15_final_resume.pdf`

**Metrics:**
- Page count: 1
- File size: 245819 bytes (240.1 KB)

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-05-01T19:17:18Z] step_14_assemble_html — starting
context: loading template cv-a4-mid-career.html; substituting header, contact, summary, per-company sections, skills, education, certifications, interests; applying theme colors
```

```text
[2026-05-01T19:17:18Z] step_14_assemble_html — acronym_expansion
context: learned 5 acronym pair(s) from source text; expanded 2 on first use: ['AML', 'TCV']
```

Learned dict: Team=Integrations focus, AML=Anti-Money Laundering, CDL=Common Data Layer, TCV=Total Contract Value, Award=SVP Risk Management

```text
[2026-05-01T19:17:18Z] step_14_assemble_html — eval
context: assembly pass; bullets=9; placeholders_left=0
```

**Artifact:** `artifacts/14_final_resume.html` (14782 chars)

**Metrics:**
- Total bullets in HTML: 9
- Residual `<!-- PLACEHOLDER -->` comments: 0
- Companies rendered: 4
- Skills categories: 1
- Education entries: 1

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-05-01T19:17:18Z] step_15_pdf — starting
context: launching headless Chromium via Playwright; loading HTML; rendering to A4 PDF with print_background=true; expecting 1-page output
```

```text
[2026-05-01T19:17:21Z] step_15_pdf — eval
context: pdf pass; 1 pages; 248464 bytes
```

**Artifact:** `artifacts/15_final_resume.pdf`

**Metrics:**
- Page count: 1
- File size: 248464 bytes (242.6 KB)

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-05-01T19:27:47Z] step_14_assemble_html — starting
context: loading template cv-a4-mid-career.html; substituting header, contact, summary, per-company sections, skills, education, certifications, interests; applying theme colors
```

```text
[2026-05-01T19:27:47Z] step_14_assemble_html — acronym_expansion
context: learned 5 acronym pair(s) from source text; expanded 2 on first use: ['AML', 'TCV']
```

Learned dict: Team=Integrations focus, AML=Anti-Money Laundering, CDL=Common Data Layer, TCV=Total Contract Value, Award=SVP Risk Management

```text
[2026-05-01T19:27:47Z] step_14_assemble_html — eval
context: assembly pass; bullets=9; placeholders_left=0
```

**Artifact:** `artifacts/14_final_resume.html` (14794 chars)

**Metrics:**
- Total bullets in HTML: 9
- Residual `<!-- PLACEHOLDER -->` comments: 0
- Companies rendered: 4
- Skills categories: 1
- Education entries: 1

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-05-01T19:27:47Z] step_15_pdf — starting
context: launching headless Chromium via Playwright; loading HTML; rendering to A4 PDF with print_background=true; expecting 1-page output
```

```text
[2026-05-01T19:27:49Z] step_15_pdf — eval
context: pdf pass; 1 pages; 248482 bytes
```

**Artifact:** `artifacts/15_final_resume.pdf`

**Metrics:**
- Page count: 1
- File size: 248482 bytes (242.7 KB)

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-05-01T19:36:21Z] step_14_assemble_html — starting
context: loading template cv-a4-mid-career.html; substituting header, contact, summary, per-company sections, skills, education, certifications, interests; applying theme colors
```

```text
[2026-05-01T19:36:21Z] step_14_assemble_html — acronym_expansion
context: learned 5 acronym pair(s) from source text; expanded 2 on first use: ['AML', 'TCV']
```

Learned dict: Team=Integrations focus, AML=Anti-Money Laundering, CDL=Common Data Layer, TCV=Total Contract Value, Award=SVP Risk Management

```text
[2026-05-01T19:36:21Z] step_14_assemble_html — eval
context: assembly pass; bullets=9; placeholders_left=0
```

**Artifact:** `artifacts/14_final_resume.html` (14809 chars)

**Metrics:**
- Total bullets in HTML: 9
- Residual `<!-- PLACEHOLDER -->` comments: 0
- Companies rendered: 4
- Skills categories: 1
- Education entries: 1

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-05-01T19:36:21Z] step_15_pdf — starting
context: launching headless Chromium via Playwright; loading HTML; rendering to A4 PDF with print_background=true; expecting 1-page output
```

```text
[2026-05-01T19:36:23Z] step_15_pdf — eval
context: pdf pass; 1 pages; 248568 bytes
```

**Artifact:** `artifacts/15_final_resume.pdf`

**Metrics:**
- Page count: 1
- File size: 248568 bytes (242.7 KB)

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-05-01T20:15:04Z] step_14_assemble_html — starting
context: loading template cv-a4-mid-career.html; substituting header, contact, summary, per-company sections, skills, education, certifications, interests; applying theme colors
```

```text
[2026-05-01T20:15:04Z] step_14_assemble_html — acronym_expansion
context: learned 5 acronym pair(s) from source text; expanded 2 on first use: ['AML', 'TCV']
```

Learned dict: Team=Integrations focus, AML=Anti-Money Laundering, CDL=Common Data Layer, TCV=Total Contract Value, Award=SVP Risk Management

```text
[2026-05-01T20:15:04Z] step_14_assemble_html — eval
context: assembly pass; bullets=9; placeholders_left=0
```

**Artifact:** `artifacts/14_final_resume.html` (15247 chars)

**Metrics:**
- Total bullets in HTML: 9
- Residual `<!-- PLACEHOLDER -->` comments: 0
- Companies rendered: 4
- Skills categories: 1
- Education entries: 1

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-05-01T20:15:04Z] step_15_pdf — starting
context: launching headless Chromium via Playwright; loading HTML; rendering to A4 PDF with print_background=true; expecting 1-page output
```

```text
[2026-05-01T20:15:08Z] step_15_pdf — eval
context: pdf pass; 1 pages; 235316 bytes
```

**Artifact:** `artifacts/15_final_resume.pdf`

**Metrics:**
- Page count: 1
- File size: 235316 bytes (229.8 KB)

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-05-01T20:16:11Z] step_14_assemble_html — starting
context: loading template cv-a4-mid-career.html; substituting header, contact, summary, per-company sections, skills, education, certifications, interests; applying theme colors
```

```text
[2026-05-01T20:16:11Z] step_14_assemble_html — acronym_expansion
context: learned 5 acronym pair(s) from source text; expanded 2 on first use: ['AML', 'TCV']
```

Learned dict: Team=Integrations focus, AML=Anti-Money Laundering, CDL=Common Data Layer, TCV=Total Contract Value, Award=SVP Risk Management

```text
[2026-05-01T20:16:11Z] step_14_assemble_html — eval
context: assembly pass; bullets=9; placeholders_left=0
```

**Artifact:** `artifacts/14_final_resume.html` (15247 chars)

**Metrics:**
- Total bullets in HTML: 9
- Residual `<!-- PLACEHOLDER -->` comments: 0
- Companies rendered: 4
- Skills categories: 1
- Education entries: 1

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-05-01T20:16:11Z] step_15_pdf — starting
context: launching headless Chromium via Playwright; loading HTML; rendering to A4 PDF with print_background=true; expecting 1-page output
```

```text
[2026-05-01T20:16:13Z] step_15_pdf — eval
context: pdf pass; 1 pages; 235316 bytes
```

**Artifact:** `artifacts/15_final_resume.pdf`

**Metrics:**
- Page count: 1
- File size: 235316 bytes (229.8 KB)

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-05-01T20:20:33Z] step_14_assemble_html — starting
context: loading template cv-a4-mid-career.html; substituting header, contact, summary, per-company sections, skills, education, certifications, interests; applying theme colors
```

```text
[2026-05-01T20:20:33Z] step_14_assemble_html — acronym_expansion
context: learned 5 acronym pair(s) from source text; expanded 2 on first use: ['AML', 'TCV']
```

Learned dict: Team=Integrations focus, AML=Anti-Money Laundering, CDL=Common Data Layer, TCV=Total Contract Value, Award=SVP Risk Management

```text
[2026-05-01T20:20:33Z] step_14_assemble_html — eval
context: assembly pass; bullets=9; placeholders_left=0
```

**Artifact:** `artifacts/14_final_resume.html` (15247 chars)

**Metrics:**
- Total bullets in HTML: 9
- Residual `<!-- PLACEHOLDER -->` comments: 0
- Companies rendered: 4
- Skills categories: 1
- Education entries: 1

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-05-01T20:20:33Z] step_15_pdf — starting
context: launching headless Chromium via Playwright; loading HTML; rendering to A4 PDF with print_background=true; expecting 1-page output
```

```text
[2026-05-01T20:20:35Z] step_15_pdf — eval
context: pdf pass; 1 pages; 234225 bytes
```

**Artifact:** `artifacts/15_final_resume.pdf`

**Metrics:**
- Page count: 1
- File size: 234225 bytes (228.7 KB)

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-05-01T20:23:14Z] step_14_assemble_html — starting
context: loading template cv-a4-mid-career.html; substituting header, contact, summary, per-company sections, skills, education, certifications, interests; applying theme colors
```

```text
[2026-05-01T20:23:14Z] step_14_assemble_html — acronym_expansion
context: learned 5 acronym pair(s) from source text; expanded 2 on first use: ['AML', 'TCV']
```

Learned dict: Team=Integrations focus, AML=Anti-Money Laundering, CDL=Common Data Layer, TCV=Total Contract Value, Award=SVP Risk Management

```text
[2026-05-01T20:23:14Z] step_14_assemble_html — eval
context: assembly pass; bullets=9; placeholders_left=0
```

**Artifact:** `artifacts/14_final_resume.html` (15192 chars)

**Metrics:**
- Total bullets in HTML: 9
- Residual `<!-- PLACEHOLDER -->` comments: 0
- Companies rendered: 4
- Skills categories: 1
- Education entries: 1

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-05-01T20:23:14Z] step_15_pdf — starting
context: launching headless Chromium via Playwright; loading HTML; rendering to A4 PDF with print_background=true; expecting 1-page output
```

```text
[2026-05-01T20:23:16Z] step_15_pdf — eval
context: pdf pass; 1 pages; 230786 bytes
```

**Artifact:** `artifacts/15_final_resume.pdf`

**Metrics:**
- Page count: 1
- File size: 230786 bytes (225.4 KB)

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-05-01T20:35:59Z] step_14_assemble_html — starting
context: loading template cv-a4-mid-career.html; substituting header, contact, summary, per-company sections, skills, education, certifications, interests; applying theme colors
```

```text
[2026-05-01T20:35:59Z] step_14_assemble_html — acronym_expansion
context: learned 5 acronym pair(s) from source text; expanded 2 on first use: ['AML', 'TCV']
```

Learned dict: Team=Integrations focus, AML=Anti-Money Laundering, CDL=Common Data Layer, TCV=Total Contract Value, Award=SVP Risk Management

```text
[2026-05-01T20:35:59Z] step_14_assemble_html — eval
context: assembly pass; bullets=9; placeholders_left=0
```

**Artifact:** `artifacts/14_final_resume.html` (14936 chars)

**Metrics:**
- Total bullets in HTML: 9
- Residual `<!-- PLACEHOLDER -->` comments: 0
- Companies rendered: 4
- Skills categories: 1
- Education entries: 1

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-05-01T20:35:59Z] step_15_pdf — starting
context: launching headless Chromium via Playwright; loading HTML; rendering to A4 PDF with print_background=true; expecting 1-page output
```

```text
[2026-05-01T20:36:02Z] step_15_pdf — eval
context: pdf pass; 1 pages; 229190 bytes
```

**Artifact:** `artifacts/15_final_resume.pdf`

**Metrics:**
- Page count: 1
- File size: 229190 bytes (223.8 KB)

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-05-01T20:45:02Z] step_14_assemble_html — starting
context: loading template cv-a4-mid-career.html; substituting header, contact, summary, per-company sections, skills, education, certifications, interests; applying theme colors
```

```text
[2026-05-01T20:45:02Z] step_14_assemble_html — acronym_expansion
context: learned 5 acronym pair(s) from source text; expanded 2 on first use: ['AML', 'TCV']
```

Learned dict: Team=Integrations focus, AML=Anti-Money Laundering, CDL=Common Data Layer, TCV=Total Contract Value, Award=SVP Risk Management

```text
[2026-05-01T20:45:02Z] step_14_assemble_html — eval
context: assembly pass; bullets=9; placeholders_left=0
```

**Artifact:** `artifacts/14_final_resume.html` (14936 chars)

**Metrics:**
- Total bullets in HTML: 9
- Residual `<!-- PLACEHOLDER -->` comments: 0
- Companies rendered: 4
- Skills categories: 1
- Education entries: 1

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-05-01T20:45:02Z] step_15_pdf — starting
context: launching headless Chromium via Playwright; loading HTML; rendering to A4 PDF with print_background=true; expecting 1-page output
```

```text
[2026-05-01T20:45:04Z] step_15_pdf — eval
context: pdf pass; 1 pages; 228599 bytes
```

**Artifact:** `artifacts/15_final_resume.pdf`

**Metrics:**
- Page count: 1
- File size: 228599 bytes (223.2 KB)

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-05-01T20:46:21Z] step_14_assemble_html — starting
context: loading template cv-a4-mid-career.html; substituting header, contact, summary, per-company sections, skills, education, certifications, interests; applying theme colors
```

```text
[2026-05-01T20:46:21Z] step_14_assemble_html — acronym_expansion
context: learned 5 acronym pair(s) from source text; expanded 0 on first use: []
```

Learned dict: Team=Integrations focus, AML=Anti-Money Laundering, CDL=Common Data Layer, TCV=Total Contract Value, Award=SVP Risk Management

```text
[2026-05-01T20:46:21Z] step_14_assemble_html — eval
context: assembly pass; bullets=9; placeholders_left=0
```

**Artifact:** `artifacts/14_final_resume.html` (14889 chars)

**Metrics:**
- Total bullets in HTML: 9
- Residual `<!-- PLACEHOLDER -->` comments: 0
- Companies rendered: 4
- Skills categories: 1
- Education entries: 1

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-05-01T20:46:21Z] step_15_pdf — starting
context: launching headless Chromium via Playwright; loading HTML; rendering to A4 PDF with print_background=true; expecting 1-page output
```

```text
[2026-05-01T20:46:23Z] step_15_pdf — eval
context: pdf pass; 1 pages; 228475 bytes
```

**Artifact:** `artifacts/15_final_resume.pdf`

**Metrics:**
- Page count: 1
- File size: 228475 bytes (223.1 KB)

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-05-02T01:32:08Z] step_14_assemble_html — starting
context: loading template cv-a4-mid-career.html; substituting header, contact, summary, per-company sections, skills, education, certifications, interests; applying theme colors
```

```text
[2026-05-02T01:32:08Z] step_14_assemble_html — acronym_expansion
context: learned 5 acronym pair(s) from source text; expanded 0 on first use: []
```

Learned dict: Team=Integrations focus, AML=Anti-Money Laundering, CDL=Common Data Layer, TCV=Total Contract Value, Award=SVP Risk Management

```text
[2026-05-02T01:32:08Z] step_14_assemble_html — eval
context: assembly pass; bullets=9; placeholders_left=0
```

**Artifact:** `artifacts/14_final_resume.html` (14889 chars)

**Metrics:**
- Total bullets in HTML: 9
- Residual `<!-- PLACEHOLDER -->` comments: 0
- Companies rendered: 4
- Skills categories: 1
- Education entries: 1

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-05-02T01:32:08Z] step_15_pdf — starting
context: launching headless Chromium via Playwright; loading HTML; rendering to A4 PDF with print_background=true; expecting 1-page output
```

```text
[2026-05-02T01:32:11Z] step_15_pdf — eval
context: pdf pass; 1 pages; 228478 bytes
```

**Artifact:** `artifacts/15_final_resume.pdf`

**Metrics:**
- Page count: 1
- File size: 228478 bytes (223.1 KB)

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-05-02T01:33:24Z] step_14_assemble_html — starting
context: loading template cv-a4-mid-career.html; substituting header, contact, summary, per-company sections, skills, education, certifications, interests; applying theme colors
```

```text
[2026-05-02T01:33:24Z] step_14_assemble_html — acronym_expansion
context: learned 5 acronym pair(s) from source text; expanded 0 on first use: []
```

Learned dict: Team=Integrations focus, AML=Anti-Money Laundering, CDL=Common Data Layer, TCV=Total Contract Value, Award=SVP Risk Management

```text
[2026-05-02T01:33:24Z] step_14_assemble_html — eval
context: assembly pass; bullets=9; placeholders_left=0
```

**Artifact:** `artifacts/14_final_resume.html` (14889 chars)

**Metrics:**
- Total bullets in HTML: 9
- Residual `<!-- PLACEHOLDER -->` comments: 0
- Companies rendered: 4
- Skills categories: 1
- Education entries: 1

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-05-02T01:33:24Z] step_15_pdf — starting
context: launching headless Chromium via Playwright; loading HTML; rendering to A4 PDF with print_background=true; expecting 1-page output
```

```text
[2026-05-02T01:33:26Z] step_15_pdf — eval
context: pdf pass; 1 pages; 228515 bytes
```

**Artifact:** `artifacts/15_final_resume.pdf`

**Metrics:**
- Page count: 1
- File size: 228515 bytes (223.2 KB)

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-05-02T01:34:54Z] step_14_assemble_html — starting
context: loading template cv-a4-mid-career.html; substituting header, contact, summary, per-company sections, skills, education, certifications, interests; applying theme colors
```

```text
[2026-05-02T01:34:54Z] step_14_assemble_html — acronym_expansion
context: learned 5 acronym pair(s) from source text; expanded 0 on first use: []
```

Learned dict: Team=Integrations focus, AML=Anti-Money Laundering, CDL=Common Data Layer, TCV=Total Contract Value, Award=SVP Risk Management

```text
[2026-05-02T01:34:54Z] step_14_assemble_html — eval
context: assembly pass; bullets=9; placeholders_left=0
```

**Artifact:** `artifacts/14_final_resume.html` (14889 chars)

**Metrics:**
- Total bullets in HTML: 9
- Residual `<!-- PLACEHOLDER -->` comments: 0
- Companies rendered: 4
- Skills categories: 1
- Education entries: 1

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-05-02T01:34:54Z] step_15_pdf — starting
context: launching headless Chromium via Playwright; loading HTML; rendering to A4 PDF with print_background=true; expecting 1-page output
```

```text
[2026-05-02T01:34:55Z] step_15_pdf — eval
context: pdf pass; 1 pages; 228479 bytes
```

**Artifact:** `artifacts/15_final_resume.pdf`

**Metrics:**
- Page count: 1
- File size: 228479 bytes (223.1 KB)

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-05-02T03:02:57Z] step_14_assemble_html — starting
context: loading template cv-a4-mid-career.html; substituting header, contact, summary, per-company sections, skills, education, certifications, interests; applying theme colors
```

```text
[2026-05-02T03:02:58Z] step_14_assemble_html — acronym_expansion
context: learned 5 acronym pair(s) from source text; expanded 0 on first use: []
```

Learned dict: Team=Integrations focus, AML=Anti-Money Laundering, CDL=Common Data Layer, TCV=Total Contract Value, Award=SVP Risk Management

```text
[2026-05-02T03:02:58Z] step_14_assemble_html — eval
context: assembly pass; bullets=9; placeholders_left=0
```

**Artifact:** `artifacts/14_final_resume.html` (14900 chars)

**Metrics:**
- Total bullets in HTML: 9
- Residual `<!-- PLACEHOLDER -->` comments: 0
- Companies rendered: 4
- Skills categories: 1
- Education entries: 1

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-05-02T03:02:58Z] step_15_pdf — starting
context: launching headless Chromium via Playwright; loading HTML; rendering to A4 PDF with print_background=true; expecting 1-page output
```

```text
[2026-05-02T03:03:00Z] step_15_pdf — eval
context: pdf pass; 1 pages; 230744 bytes
```

**Artifact:** `artifacts/15_final_resume.pdf`

**Metrics:**
- Page count: 1
- File size: 230744 bytes (225.3 KB)

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-05-02T03:03:22Z] step_14_assemble_html — starting
context: loading template cv-a4-mid-career.html; substituting header, contact, summary, per-company sections, skills, education, certifications, interests; applying theme colors
```

```text
[2026-05-02T03:03:22Z] step_14_assemble_html — acronym_expansion
context: learned 5 acronym pair(s) from source text; expanded 0 on first use: []
```

Learned dict: Team=Integrations focus, AML=Anti-Money Laundering, CDL=Common Data Layer, TCV=Total Contract Value, Award=SVP Risk Management

```text
[2026-05-02T03:03:22Z] step_14_assemble_html — eval
context: assembly pass; bullets=9; placeholders_left=0
```

**Artifact:** `artifacts/14_final_resume.html` (14889 chars)

**Metrics:**
- Total bullets in HTML: 9
- Residual `<!-- PLACEHOLDER -->` comments: 0
- Companies rendered: 4
- Skills categories: 1
- Education entries: 1

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-05-02T03:03:22Z] step_15_pdf — starting
context: launching headless Chromium via Playwright; loading HTML; rendering to A4 PDF with print_background=true; expecting 1-page output
```

```text
[2026-05-02T03:03:24Z] step_15_pdf — eval
context: pdf pass; 1 pages; 228479 bytes
```

**Artifact:** `artifacts/15_final_resume.pdf`

**Metrics:**
- Page count: 1
- File size: 228479 bytes (223.1 KB)

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-05-02T04:18:12Z] step_14_assemble_html — starting
context: loading template cv-a4-mid-career.html; substituting header, contact, summary, per-company sections, skills, education, certifications, interests; applying theme colors
```

```text
[2026-05-02T04:18:12Z] step_14_assemble_html — acronym_expansion
context: learned 5 acronym pair(s) from source text; expanded 0 on first use: []
```

Learned dict: Team=Integrations focus, AML=Anti-Money Laundering, CDL=Common Data Layer, TCV=Total Contract Value, Award=SVP Risk Management

```text
[2026-05-02T04:18:12Z] step_14_assemble_html — eval
context: assembly pass; bullets=9; placeholders_left=0
```

**Artifact:** `artifacts/14_final_resume.html` (14889 chars)

**Metrics:**
- Total bullets in HTML: 9
- Residual `<!-- PLACEHOLDER -->` comments: 0
- Companies rendered: 4
- Skills categories: 1
- Education entries: 1

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-05-02T04:18:12Z] step_15_pdf — starting
context: launching headless Chromium via Playwright; loading HTML; rendering to A4 PDF with print_background=true; expecting 1-page output
```

```text
[2026-05-02T04:18:14Z] step_15_pdf — eval
context: pdf pass; 1 pages; 228479 bytes
```

**Artifact:** `artifacts/15_final_resume.pdf`

**Metrics:**
- Page count: 1
- File size: 228479 bytes (223.1 KB)

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-05-02T04:22:53Z] step_14_assemble_html — starting
context: loading template cv-a4-mid-career.html; substituting header, contact, summary, per-company sections, skills, education, certifications, interests; applying theme colors
```

```text
[2026-05-02T04:22:53Z] step_14_assemble_html — acronym_expansion
context: learned 5 acronym pair(s) from source text; expanded 0 on first use: []
```

Learned dict: Team=Integrations focus, AML=Anti-Money Laundering, CDL=Common Data Layer, TCV=Total Contract Value, Award=SVP Risk Management

```text
[2026-05-02T04:22:53Z] step_14_assemble_html — eval
context: assembly pass; bullets=9; placeholders_left=0
```

**Artifact:** `artifacts/14_final_resume.html` (14889 chars)

**Metrics:**
- Total bullets in HTML: 9
- Residual `<!-- PLACEHOLDER -->` comments: 0
- Companies rendered: 4
- Skills categories: 1
- Education entries: 1

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-05-02T04:22:53Z] step_15_pdf — starting
context: launching headless Chromium via Playwright; loading HTML; rendering to A4 PDF with print_background=true; expecting 1-page output
```

```text
[2026-05-02T04:22:55Z] step_15_pdf — eval
context: pdf pass; 1 pages; 228479 bytes
```

**Artifact:** `artifacts/15_final_resume.pdf`

**Metrics:**
- Page count: 1
- File size: 228479 bytes (223.1 KB)

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-05-02T04:27:08Z] step_14_assemble_html — starting
context: loading template cv-a4-mid-career.html; substituting header, contact, summary, per-company sections, skills, education, certifications, interests; applying theme colors
```

```text
[2026-05-02T04:27:08Z] step_14_assemble_html — acronym_expansion
context: learned 5 acronym pair(s) from source text; expanded 0 on first use: []
```

Learned dict: Team=Integrations focus, AML=Anti-Money Laundering, CDL=Common Data Layer, TCV=Total Contract Value, Award=SVP Risk Management

```text
[2026-05-02T04:27:08Z] step_14_assemble_html — eval
context: assembly pass; bullets=9; placeholders_left=0
```

**Artifact:** `artifacts/14_final_resume.html` (14362 chars)

**Metrics:**
- Total bullets in HTML: 9
- Residual `<!-- PLACEHOLDER -->` comments: 0
- Companies rendered: 4
- Skills categories: 1
- Education entries: 1

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-05-02T04:27:08Z] step_15_pdf — starting
context: launching headless Chromium via Playwright; loading HTML; rendering to A4 PDF with print_background=true; expecting 1-page output
```

```text
[2026-05-02T04:27:10Z] step_15_pdf — eval
context: pdf pass; 1 pages; 230880 bytes
```

**Artifact:** `artifacts/15_final_resume.pdf`

**Metrics:**
- Page count: 1
- File size: 230880 bytes (225.5 KB)

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-05-02T04:29:00Z] step_14_assemble_html — starting
context: loading template cv-a4-mid-career.html; substituting header, contact, summary, per-company sections, skills, education, certifications, interests; applying theme colors
```

```text
[2026-05-02T04:29:00Z] step_14_assemble_html — acronym_expansion
context: learned 5 acronym pair(s) from source text; expanded 0 on first use: []
```

Learned dict: Team=Integrations focus, AML=Anti-Money Laundering, CDL=Common Data Layer, TCV=Total Contract Value, Award=SVP Risk Management

```text
[2026-05-02T04:29:00Z] step_14_assemble_html — eval
context: assembly pass; bullets=9; placeholders_left=0
```

**Artifact:** `artifacts/14_final_resume.html` (14582 chars)

**Metrics:**
- Total bullets in HTML: 9
- Residual `<!-- PLACEHOLDER -->` comments: 0
- Companies rendered: 4
- Skills categories: 1
- Education entries: 1

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-05-02T04:29:00Z] step_15_pdf — starting
context: launching headless Chromium via Playwright; loading HTML; rendering to A4 PDF with print_background=true; expecting 1-page output
```

```text
[2026-05-02T04:29:02Z] step_15_pdf — eval
context: pdf pass; 1 pages; 234867 bytes
```

**Artifact:** `artifacts/15_final_resume.pdf`

**Metrics:**
- Page count: 1
- File size: 234867 bytes (229.4 KB)

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-05-02T04:32:49Z] step_14_assemble_html — starting
context: loading template cv-a4-mid-career.html; substituting header, contact, summary, per-company sections, skills, education, certifications, interests; applying theme colors
```

```text
[2026-05-02T04:32:49Z] step_14_assemble_html — acronym_expansion
context: learned 5 acronym pair(s) from source text; expanded 0 on first use: []
```

Learned dict: Team=Integrations focus, AML=Anti-Money Laundering, CDL=Common Data Layer, TCV=Total Contract Value, Award=SVP Risk Management

```text
[2026-05-02T04:32:49Z] step_14_assemble_html — eval
context: assembly pass; bullets=9; placeholders_left=0
```

**Artifact:** `artifacts/14_final_resume.html` (14582 chars)

**Metrics:**
- Total bullets in HTML: 9
- Residual `<!-- PLACEHOLDER -->` comments: 0
- Companies rendered: 4
- Skills categories: 1
- Education entries: 1

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-05-02T04:32:49Z] step_15_pdf — starting
context: launching headless Chromium via Playwright; loading HTML; rendering to A4 PDF with print_background=true; expecting 1-page output
```

```text
[2026-05-02T04:32:51Z] step_15_pdf — eval
context: pdf pass; 1 pages; 234867 bytes
```

**Artifact:** `artifacts/15_final_resume.pdf`

**Metrics:**
- Page count: 1
- File size: 234867 bytes (229.4 KB)

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-05-02T04:33:49Z] step_14_assemble_html — starting
context: loading template cv-a4-mid-career.html; substituting header, contact, summary, per-company sections, skills, education, certifications, interests; applying theme colors
```

```text
[2026-05-02T04:33:49Z] step_14_assemble_html — acronym_expansion
context: learned 5 acronym pair(s) from source text; expanded 0 on first use: []
```

Learned dict: Team=Integrations focus, AML=Anti-Money Laundering, CDL=Common Data Layer, TCV=Total Contract Value, Award=SVP Risk Management

```text
[2026-05-02T04:33:49Z] step_14_assemble_html — eval
context: assembly pass; bullets=9; placeholders_left=0
```

**Artifact:** `artifacts/14_final_resume.html` (14582 chars)

**Metrics:**
- Total bullets in HTML: 9
- Residual `<!-- PLACEHOLDER -->` comments: 0
- Companies rendered: 4
- Skills categories: 1
- Education entries: 1

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-05-02T04:33:49Z] step_15_pdf — starting
context: launching headless Chromium via Playwright; loading HTML; rendering to A4 PDF with print_background=true; expecting 1-page output
```

```text
[2026-05-02T04:33:51Z] step_15_pdf — eval
context: pdf pass; 1 pages; 234867 bytes
```

**Artifact:** `artifacts/15_final_resume.pdf`

**Metrics:**
- Page count: 1
- File size: 234867 bytes (229.4 KB)

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-05-02T04:38:25Z] step_14_assemble_html — starting
context: loading template cv-a4-mid-career.html; substituting header, contact, summary, per-company sections, skills, education, certifications, interests; applying theme colors
```

```text
[2026-05-02T04:38:26Z] step_14_assemble_html — acronym_expansion
context: learned 5 acronym pair(s) from source text; expanded 0 on first use: []
```

Learned dict: Team=Integrations focus, AML=Anti-Money Laundering, CDL=Common Data Layer, TCV=Total Contract Value, Award=SVP Risk Management

```text
[2026-05-02T04:38:26Z] step_14_assemble_html — eval
context: assembly pass; bullets=9; placeholders_left=0
```

**Artifact:** `artifacts/14_final_resume.html` (14582 chars)

**Metrics:**
- Total bullets in HTML: 9
- Residual `<!-- PLACEHOLDER -->` comments: 0
- Companies rendered: 4
- Skills categories: 1
- Education entries: 1

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-05-02T04:38:26Z] step_15_pdf — starting
context: launching headless Chromium via Playwright; loading HTML; rendering to A4 PDF with print_background=true; expecting 1-page output
```

```text
[2026-05-02T04:38:29Z] step_15_pdf — eval
context: pdf pass; 1 pages; 234867 bytes
```

**Artifact:** `artifacts/15_final_resume.pdf`

**Metrics:**
- Page count: 1
- File size: 234867 bytes (229.4 KB)

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-05-02T04:46:04Z] step_14_assemble_html — starting
context: loading template cv-a4-mid-career.html; substituting header, contact, summary, per-company sections, skills, education, certifications, interests; applying theme colors
```

```text
[2026-05-02T04:46:04Z] step_14_assemble_html — acronym_expansion
context: learned 5 acronym pair(s) from source text; expanded 0 on first use: []
```

Learned dict: Team=Integrations focus, AML=Anti-Money Laundering, CDL=Common Data Layer, TCV=Total Contract Value, Award=SVP Risk Management

```text
[2026-05-02T04:46:04Z] step_14_assemble_html — eval
context: assembly pass; bullets=9; placeholders_left=0
```

**Artifact:** `artifacts/14_final_resume.html` (14582 chars)

**Metrics:**
- Total bullets in HTML: 9
- Residual `<!-- PLACEHOLDER -->` comments: 0
- Companies rendered: 4
- Skills categories: 1
- Education entries: 1

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-05-02T04:46:04Z] step_15_pdf — starting
context: launching headless Chromium via Playwright; loading HTML; rendering to A4 PDF with print_background=true; expecting 1-page output
```

```text
[2026-05-02T04:46:06Z] step_15_pdf — eval
context: pdf pass; 1 pages; 234867 bytes
```

**Artifact:** `artifacts/15_final_resume.pdf`

**Metrics:**
- Page count: 1
- File size: 234867 bytes (229.4 KB)

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-05-02T04:55:04Z] step_14_assemble_html — starting
context: loading template cv-a4-mid-career.html; substituting header, contact, summary, per-company sections, skills, education, certifications, interests; applying theme colors
```

```text
[2026-05-02T04:55:04Z] step_14_assemble_html — acronym_expansion
context: learned 5 acronym pair(s) from source text; expanded 0 on first use: []
```

Learned dict: Team=Integrations focus, AML=Anti-Money Laundering, CDL=Common Data Layer, TCV=Total Contract Value, Award=SVP Risk Management

```text
[2026-05-02T04:55:04Z] step_14_assemble_html — eval
context: assembly pass; bullets=9; placeholders_left=0
```

**Artifact:** `artifacts/14_final_resume.html` (14582 chars)

**Metrics:**
- Total bullets in HTML: 9
- Residual `<!-- PLACEHOLDER -->` comments: 0
- Companies rendered: 4
- Skills categories: 1
- Education entries: 1

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-05-02T04:55:04Z] step_15_pdf — starting
context: launching headless Chromium via Playwright; loading HTML; rendering to A4 PDF with print_background=true; expecting 1-page output
```

```text
[2026-05-02T04:55:06Z] step_15_pdf — eval
context: pdf pass; 1 pages; 234867 bytes
```

**Artifact:** `artifacts/15_final_resume.pdf`

**Metrics:**
- Page count: 1
- File size: 234867 bytes (229.4 KB)

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-05-02T04:58:13Z] step_14_assemble_html — starting
context: loading template cv-a4-mid-career.html; substituting header, contact, summary, per-company sections, skills, education, certifications, interests; applying theme colors
```

```text
[2026-05-02T04:58:13Z] step_14_assemble_html — acronym_expansion
context: learned 5 acronym pair(s) from source text; expanded 0 on first use: []
```

Learned dict: Team=Integrations focus, AML=Anti-Money Laundering, CDL=Common Data Layer, TCV=Total Contract Value, Award=SVP Risk Management

```text
[2026-05-02T04:58:13Z] step_14_assemble_html — eval
context: assembly pass; bullets=9; placeholders_left=0
```

**Artifact:** `artifacts/14_final_resume.html` (14588 chars)

**Metrics:**
- Total bullets in HTML: 9
- Residual `<!-- PLACEHOLDER -->` comments: 0
- Companies rendered: 4
- Skills categories: 1
- Education entries: 1

**Evaluation:** PASS

**Gaps:**
- none

```text
[2026-05-02T04:58:13Z] step_15_pdf — starting
context: launching headless Chromium via Playwright; loading HTML; rendering to A4 PDF with print_background=true; expecting 1-page output
```

```text
[2026-05-02T04:58:15Z] step_15_pdf — eval
context: pdf pass; 1 pages; 234877 bytes
```

**Artifact:** `artifacts/15_final_resume.pdf`

**Metrics:**
- Page count: 1
- File size: 234877 bytes (229.4 KB)

**Evaluation:** PASS

**Gaps:**
- none
