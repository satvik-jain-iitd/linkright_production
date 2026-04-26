# Sample Fixtures

Real-world sample data for E2E tests. Use these in any spec that needs a believable
candidate profile / JD / nuggets payload — instead of generating mocks inline.

| File | Purpose |
|---|---|
| `ruchi_resume.pdf` | Junior PM-track resume (good for "fresher / entry" pipeline coverage) |
| `satvik_aml_pm_resume.pdf` | Senior PM resume with AML / FinCrime domain (good for "mid / senior" + domain-keyword coverage) |
| `sample_jd.md` | Mid-seniority PM JD with ~20 keyword density |
| `sample_career_nuggets.json` | Pre-parsed career nuggets with embeddings — skip parse step in tests that only need downstream data |

Source of truth lives here. Do NOT add new sample files to `/testing/` (legacy diagnostic dir).
