# Modular Update Guide
# How to update each component of the LifeOS Career Coach without breaking others.
# This is the maintenance reference — read this before touching anything.

---

## COMPONENT MAP

```
┌─────────────────────────────────────────────────────────┐
│                   CUSTOM GPT BUILDER                    │
│                                                         │
│  [System Prompt]          [Knowledge Files]             │
│  system_prompt.md         01_atom_schema.json           │
│  (paste verbatim)         02_interview_questions.md     │
│                           03_achievement_guide.md       │
│  [OpenAPI Schema]         04_conflict_handling.md       │
│  openapi_schema.yaml      05_example_atoms.json         │
│  (paste in Actions)       06_update_guide.md (this)     │
│                                                         │
│  [Action Auth]                                          │
│  Bearer: CUSTOM_GPT_SECRET                              │
│  (stored in GPT Action config)                          │
└────────────────────┬────────────────────────────────────┘
                     │ HTTPS to linkright.in
┌────────────────────▼────────────────────────────────────┐
│              NEXT.JS PROXY ROUTES                       │
│              website/src/app/api/oracle/                │
│                                                         │
│  verify-token/route.ts    → validates token + atom count│
│  ingest-atom/route.ts     → forwards to Oracle          │
│  session-close/route.ts   → forwards to Oracle          │
│                                                         │
│  Auth in: Bearer CUSTOM_GPT_SECRET                      │
│  Auth out: Bearer ORACLE_BACKEND_SECRET                 │
└────────────────────┬────────────────────────────────────┘
                     │ HTTP to Oracle ARM server
┌────────────────────▼────────────────────────────────────┐
│              ORACLE ARM FASTAPI BACKEND                 │
│              oracle-backend/ (on server)                │
│                                                         │
│  main.py                  → endpoints + auth            │
│  lifeos/ingest.py         → embed + Neo4j MERGE         │
│  lifeos/neo4j_client.py   → Cypher queries              │
│  lifeos/embeddings.py     → Ollama nomic-embed-text     │
│                                                         │
│  Running: systemd lifeos.service on 80.225.198.184:8000 │
└─────────────────────────────────────────────────────────┘
```

---

## UPDATE PROCEDURES

### Change the interview conversation flow or persona
→ Edit `system_prompt.md`, paste new text into GPT builder Instructions field.
→ No code changes needed.

### Add or modify interview questions
→ Edit `knowledge/02_interview_questions.md`.
→ Delete old file in GPT builder, re-upload updated file.
→ No code changes needed.

### Change how achievements are extracted / atom quality rules
→ Edit `knowledge/03_achievement_guide.md`.
→ Re-upload in GPT builder.
→ No code changes needed.

### Add a new atom field
1. Add field to `knowledge/01_atom_schema.json`
2. Add field to `openapi_schema.yaml` under `CareerAtom` schema
3. Add field handling to `oracle-backend/lifeos/ingest.py` (`ingest_atom` function)
4. Add field to `oracle-backend/lifeos/neo4j_client.py` (`merge_achievement` props)
5. Re-upload 01_atom_schema.json to GPT builder
6. Paste updated openapi_schema.yaml into GPT Actions
7. Deploy updated oracle-backend to server

### Add a new API action (new endpoint)
1. Create new Next.js route in `website/src/app/api/oracle/`
2. Add new Oracle endpoint in `oracle-backend/main.py` if needed
3. Add new path to `openapi_schema.yaml`
4. Paste updated schema into GPT Actions

### Change conflict detection threshold
→ Edit `oracle-backend/lifeos/ingest.py`, line with `threshold=0.85`
→ Redeploy oracle-backend (`sudo systemctl restart lifeos`)
→ Update `knowledge/04_conflict_handling.md` similarity table if changing threshold

### Change the session token format or expiry
→ Edit `website/src/app/api/profile/token/route.ts` (generation)
→ Expiry is set in `website/db/migrations/010_profile_tokens.sql`
→ If changing format, also update system_prompt.md example format

### Rotate secrets
→ CUSTOM_GPT_SECRET: generate new → add to Vercel env → update GPT Action auth config
→ ORACLE_BACKEND_SECRET: generate new → update oracle-backend/.env + Vercel env
→ After rotating ORACLE_BACKEND_SECRET, restart oracle-backend: `sudo systemctl restart lifeos`

### Update the Oracle ARM server
```bash
# SSH to server
ssh -i ~/Desktop/oracle_new opc@80.225.198.184

# Pull latest code (if using git) OR rsync from local:
rsync -av -e "ssh -i ~/Desktop/oracle_new" \
  oracle-backend/ opc@80.225.198.184:/home/opc/lifeos-backend/

# Restart service
sudo systemctl restart lifeos
sudo systemctl status lifeos
```

### Add a new knowledge file
→ Create file in `knowledge/` directory
→ Upload to GPT builder (knowledge section)
→ Reference it by filename in system_prompt.md if needed
→ Max 20 files total in GPT knowledge.

---

## ENV VARS REFERENCE

| Variable | Location | Used by |
|---|---|---|
| `CUSTOM_GPT_SECRET` | Vercel + GPT Action auth | Next.js proxy routes (inbound auth) |
| `ORACLE_BACKEND_URL` | Vercel | Next.js proxy routes (outbound URL) |
| `ORACLE_BACKEND_SECRET` | Vercel + oracle .env | Next.js (outbound) + Oracle (inbound) |
| `SUPABASE_SERVICE_ROLE_KEY` | Vercel + oracle .env | Supabase writes |
| `NEXT_PUBLIC_SUPABASE_URL` | Vercel | Supabase client init |

---

## FILE COUNT (GPT knowledge limit: 20 files)
Currently used: 6 / 20
```
01_atom_schema.json          (schema reference)
02_interview_questions.md    (question bank)
03_achievement_guide.md      (extraction methodology)
04_conflict_handling.md      (conflict resolution)
05_example_atoms.json        (good examples)
06_update_guide.md           (this file)
```

Remaining slots: 14 — available for role-specific guides, industry templates, etc.
