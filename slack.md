# LinkRight CLI — Slack (Romanized Hindi, short @mentions)

[2026-06-07 22:00 IST] @sonu → @aman @sanika @satvik — naya sprint: linkright CLI ko 100k-user production-grade banana (sync-resume-engine NAHI, sirf CLI). Step 1 Analysis plan.md mein likh diya. Padho aur critique karo.

[2026-06-07 22:00 IST] @sonu → @aman — tera scope: plan.md dimensions C (Mongo centrality — onboard/tailor ko Mongo chahiye ya optional?), E (auth/ + keys/ secret handling), F (modularity/pillar coupling). Plan.md ke open-Q1 ka jawab code se confirm karo.

[2026-06-07 22:00 IST] @sonu → @sanika — tera scope: dimension B (llm/direct.py 1659 LOC — provider dispatch, retry, rate-limit, cost guards) aur D (telemetry.py 694 — $0 model, koi phone-home?). 1M context hai tera, bade files tu hi padh.

[2026-06-07 22:00 IST] @sonu → @satvik — ek product call chahiye (plan.md open-Q2): end-users ko shared oracle.linkright.in creds milte hain, ya hamesha bring-your-own/local-only? G4 risk isi pe depend karta hai.

[2026-06-07 22:15 IST] @aman → team — deep-dive done (C/E/F). Bada news: Mongo core path ke liye REQUIRED NAHI (lazy, graceful) → G2 closed. Par [BLOCK] mila: koi encryption-at-rest nahi, session.json+.env plaintext. Details plan.md synthesis table.

[2026-06-07 22:15 IST] @sanika → team — deep-dive done (B/D). 2 [BLOCK]: API key stacktrace mein leak (direct.py:332), thundering-herd in-memory cooldowns (direct.py:53). Plus $0 model scale pe tootta hai (paid OpenRouter fallback). Telemetry local-only, no phone-home.

[2026-06-07 22:16 IST] @sonu → team — Step 1 synthesis plan.md mein. Verdict: arch 100k ke liye sound, par 3 BLOCKER (B1 key-leak, B2 no-encryption, B3 thundering-herd) + cost-at-scale. Aman+Sanika ✅. @satvik open-Q ka jawab do → Step 2 (Planning, Aman leads, B1-B3 prioritize) shuru.

[2026-06-07 22:45 IST] @sonu → team — SHIPPED to PR #190. B1+B3+W1+B2 implement+test (14 tests pass, 0 regression). Sanika adversarial review ne 5 real bugs pakde (jitter<Retry-After, budget model-bypass, race, unlink crash, stale-plaintext) → sab fix. Satvik decision: local-only/BYO. Oracle capacity ~1-2k DAU max (NUM_PARALLEL=1). @satvik #190 review+merge karo.
