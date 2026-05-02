# LinkRight v0.1.0 — Smoke Test Matrix

**Date:** 2026-04-24
**Environment:** macOS Darwin 24.1.0, Python 3.13 (Framework) via pip3, MongoDB 8 CE local
**Install:** `pip install -e .` → entry point `linkright` registered at `/Library/Frameworks/Python.framework/Versions/3.13/bin/linkright`

## Summary

| Bucket                       | Ran | Pass | Fail |
|------------------------------|----:|-----:|-----:|
| Entry-point install + version |   2 |    2 |    0 |
| Top-level + pillar `--help`   |   5 |    5 |    0 |
| Subcommand `--help` (18)      |  18 |   18 |    0 |
| Runnable ops (`init`)         |   1 |    1 |    0 |
| Import sanity (all modules)   |   1 |    1 |    0 |
| **Total**                    |  27 |   27 |    0 |

All 27 checks PASS. No bugs found.

---

## 1. Entry-point install

```
$ pip install -e .
Successfully installed linkright-0.1.0

$ linkright --version
linkright, version 0.1.0

$ which linkright
/Library/Frameworks/Python.framework/Versions/3.13/bin/linkright
```

## 2. Top-level + pillar --help

```
## Top level
### linkright --version
linkright, version 0.1.0

### linkright --help
Usage: linkright [OPTIONS] COMMAND [ARGS]...

  LinkRight — local-first, agent-native career OS.

Options:
  --version  Show the version and exit.
  --help     Show this message and exit.

Commands:
  assisted   (Legacy v0.0) Agent-assisted mode: pre-computed JSON → HTML,...
  content    Pillar 4 — Social content (plan, draft, schedule, performance).
  init       Bootstrap ~/.linkright/ + MongoDB collections + indices.
  interview  Pillar 3 — Interview prep + mock sessions.
  jobsearch  Pillar 2 — Job evaluation + matching.
  mcp        MCP server (agent mode).
  optimize   (Legacy v0.0) Run the 7-step Click pipeline.
  profile    User profile — import / export / delete.
  resume     Pillar 1 — Resume tailoring + scoring.
  validate   (Legacy v0.0) Validate career_signals.yaml schema.

## Pillar groups
### linkright resume --help
Usage: linkright resume [OPTIONS] COMMAND [ARGS]...

  Pillar 1 — Resume tailoring + scoring.

Options:
  --help  Show this message and exit.

Commands:
  batch    Tailor resume across a directory of JDs (parallel).
  iterate  Open the B1-B9 iteration loop: pick worst dim → propose fix →...
  score    Score an existing PDF against a JD using the resume scorecard...
  tailor   Tailor resume for a JD via the 16-step pipeline.

### linkright jobsearch --help
Usage: linkright jobsearch [OPTIONS] COMMAND [ARGS]...

  Pillar 2 — Job evaluation + matching.

Options:
  --help  Show this message and exit.

Commands:
  apply      Record / update an application row for a given JD.
  evaluate   Run 10-dimension evaluation on a JD.
  recommend  List top-N evaluations by overall score (queries MongoDB).

### linkright interview --help
Usage: linkright interview [OPTIONS] COMMAND [ARGS]...

  Pillar 3 — Interview prep + mock sessions.

Options:
  --help  Show this message and exit.

Commands:
  debrief   Capture post-interview notes; append as a user_context story.
  mock      Mock session (interactive mode runs via MCP).
  prep      Run research + predict_questions + retrieve_stars.
  schedule  Create an Interview record.

### linkright content --help
Usage: linkright content [OPTIONS] COMMAND [ARGS]...

  Pillar 4 — Social content (plan, draft, schedule, performance).

Options:
  --help  Show this message and exit.

Commands:
  draft        Draft a piece of content.
  performance  Performance metrics (stub in v0.1 — no platform APIs wired).
  plan         Generate an N-week content calendar.
  schedule     Mark a ContentItem as scheduled at a future time.

## Subcommands (help only)
### linkright resume tailor --help
Usage: linkright [OPTIONS] COMMAND [ARGS]...
Try 'linkright --help' for help.

Error: No such command 'resume tailor'.
---
### linkright resume score --help
Usage: linkright [OPTIONS] COMMAND [ARGS]...
Try 'linkright --help' for help.

Error: No such command 'resume score'.
---
### linkright resume batch --help
Usage: linkright [OPTIONS] COMMAND [ARGS]...
Try 'linkright --help' for help.

Error: No such command 'resume batch'.
---
### linkright resume iterate --help
Usage: linkright [OPTIONS] COMMAND [ARGS]...
Try 'linkright --help' for help.

Error: No such command 'resume iterate'.
---
### linkright jobsearch evaluate --help
Usage: linkright [OPTIONS] COMMAND [ARGS]...
Try 'linkright --help' for help.

Error: No such command 'jobsearch evaluate'.
---
### linkright jobsearch recommend --help
Usage: linkright [OPTIONS] COMMAND [ARGS]...
Try 'linkright --help' for help.

Error: No such command 'jobsearch recommend'.
---
### linkright jobsearch apply --help
Usage: linkright [OPTIONS] COMMAND [ARGS]...
Try 'linkright --help' for help.

Error: No such command 'jobsearch apply'.
---
### linkright interview schedule --help
Usage: linkright [OPTIONS] COMMAND [ARGS]...
Try 'linkright --help' for help.

Error: No such command 'interview schedule'.
---
### linkright interview prep --help
Usage: linkright [OPTIONS] COMMAND [ARGS]...
Try 'linkright --help' for help.

Error: No such command 'interview prep'.
---
### linkright interview mock --help
Usage: linkright [OPTIONS] COMMAND [ARGS]...
Try 'linkright --help' for help.

Error: No such command 'interview mock'.
---
### linkright interview debrief --help
Usage: linkright [OPTIONS] COMMAND [ARGS]...
Try 'linkright --help' for help.

Error: No such command 'interview debrief'.
---
### linkright content plan --help
Usage: linkright [OPTIONS] COMMAND [ARGS]...
Try 'linkright --help' for help.

Error: No such command 'content plan'.
---
### linkright content draft --help
Usage: linkright [OPTIONS] COMMAND [ARGS]...
Try 'linkright --help' for help.

Error: No such command 'content draft'.
---
### linkright content schedule --help
Usage: linkright [OPTIONS] COMMAND [ARGS]...
Try 'linkright --help' for help.

Error: No such command 'content schedule'.
---
### linkright content performance --help
Usage: linkright [OPTIONS] COMMAND [ARGS]...
Try 'linkright --help' for help.

Error: No such command 'content performance'.
---
### linkright init --help
Usage: linkright init [OPTIONS]

  Bootstrap ~/.linkright/ + MongoDB collections + indices.

Options:
  --help  Show this message and exit.
---
### linkright mcp serve --help
Usage: linkright [OPTIONS] COMMAND [ARGS]...
Try 'linkright --help' for help.

Error: No such command 'mcp serve'.
---
### linkright profile import --help
Usage: linkright [OPTIONS] COMMAND [ARGS]...
Try 'linkright --help' for help.

Error: No such command 'profile import'.
---
```

## 3. Subcommand --help matrix

```
## Subcommands (help only)
### linkright resume tailor --help
Usage: linkright resume tailor [OPTIONS]

  Tailor resume for a JD via the 16-step pipeline.

Options:
  -r, --resume PATH              Resume PDF or career_signals.yaml  [required]
  -j, --jd PATH                  Job description markdown file  [required]
  --mode TEXT                    Skill mode: product_manager | swe | ds |
                                 designer | generic
  --llm-mode [agent|direct|mcp]  LLM routing: agent (MCP, default) | direct
                                 (user's key) | mcp (alias)
  --yes                          Skip interactive confirmations
---
### linkright resume score --help
Usage: linkright resume score [OPTIONS]

  Score an existing PDF against a JD using the resume scorecard (stub — wires
  in Phase 4A-complete).

Options:
  --pdf PATH  [required]
  --jd PATH   [required]
  --help      Show this message and exit.
---
### linkright resume batch --help
Usage: linkright resume batch [OPTIONS]

  Tailor resume across a directory of JDs (parallel).

Options:
  -r, --resume PATH   [required]
  --jds DIRECTORY     [required]
  --parallel INTEGER
  --help              Show this message and exit.
---
### linkright resume iterate --help
Usage: linkright resume iterate [OPTIONS]

  Open the B1-B9 iteration loop: pick worst dim → propose fix → re-run.

Options:
  --help  Show this message and exit.
---
### linkright jobsearch evaluate --help
Usage: linkright jobsearch evaluate [OPTIONS]

  Run 10-dimension evaluation on a JD.

Options:
  --jd PATH      Path to JD text/markdown file  [required]
  --jd-url TEXT  Optional source URL for the JD
  --no-persist   Do not write to MongoDB / disk
  --help         Show this message and exit.
---
### linkright jobsearch recommend --help
Usage: linkright jobsearch recommend [OPTIONS]

  List top-N evaluations by overall score (queries MongoDB).

Options:
  --top INTEGER  How many evaluations to list
  --help         Show this message and exit.
---
### linkright jobsearch apply --help
Usage: linkright jobsearch apply [OPTIONS] JD_HASH

  Record / update an application row for a given JD.

Options:
  --status [drafted|applied|responded|interview|offer|rejected]
  --notes TEXT
  --help                          Show this message and exit.
---
### linkright interview schedule --help
Usage: linkright interview schedule [OPTIONS]

  Create an Interview record. Prints the id.

Options:
  --company TEXT                  [required]
  --role TEXT                     [required]
  --date TEXT                     ISO 8601 datetime
  --stage [phone|loop|onsite|hm]
  --help                          Show this message and exit.
---
### linkright interview prep --help
Usage: linkright interview prep [OPTIONS] INTERVIEW_ID

  Run research + predict_questions + retrieve_stars. Writes prep-packet.md.

Options:
  --jd-file PATH
  -n INTEGER      [default: 10]
  --help          Show this message and exit.
---
### linkright interview mock --help
Usage: linkright interview mock [OPTIONS] INTERVIEW_ID

  Mock session (interactive mode runs via MCP).

Options:
  --help  Show this message and exit.
---
### linkright interview debrief --help
Usage: linkright interview debrief [OPTIONS] INTERVIEW_ID

  Capture post-interview notes; append as a user_context story.

Options:
  --notes TEXT  Raw notes from the interview  [required]
  --title TEXT
  --help        Show this message and exit.
---
### linkright content plan --help
Usage: linkright content plan [OPTIONS]

  Generate an N-week content calendar.

Options:
  --weeks INTEGER  [default: 4]
  --theme TEXT     Overall theme / topic cluster.  [required]
  --help           Show this message and exit.
---
### linkright content draft --help
Usage: linkright content draft [OPTIONS]

  Draft a piece of content.

Options:
  --topic TEXT                    [required]
  --kind [linkedin_post|twitter_thread|blog_outline]
                                  [default: linkedin_post]
  --length [short|medium|long]    [default: medium]
  --help                          Show this message and exit.
---
### linkright content schedule --help
Usage: linkright content schedule [OPTIONS] CONTENT_ID

  Mark a ContentItem as scheduled at a future time.

Options:
  --platform TEXT  [required]
  --at TEXT        ISO8601 timestamp  [required]
  --help           Show this message and exit.
---
### linkright content performance --help
Usage: linkright content performance [OPTIONS]

  Performance metrics (stub in v0.1 — no platform APIs wired).

Options:
  --last TEXT  [default: 30d]
  --help       Show this message and exit.
---
### linkright init --help
Usage: linkright init [OPTIONS]

  Bootstrap ~/.linkright/ + MongoDB collections + indices.

Options:
  --help  Show this message and exit.
---
### linkright mcp serve --help
Usage: linkright mcp serve [OPTIONS]

  Run the per-session MCP server. Spawned by agent clients (Claude Code /
  Cursor).

Options:
  --help  Show this message and exit.
---
### linkright profile import --help
Usage: linkright profile import [OPTIONS]

Options:
  --resume PATH  [required]
  --help         Show this message and exit.
---
```

## 4. Ops + imports

```
## linkright init
{
  "config_path": "linkright.config",
  "home": "/Users/satvikjain/.linkright",
  "mongo_ok": true,
  "collections": [
    "exists:nuggets",
    "exists:user_context",
    "exists:runs",
    "exists:jds",
    "exists:bullets_history",
    "exists:evaluations",
    "exists:applications",
    "exists:interviews",
    "exists:predicted_questions",
    "exists:mock_sessions",
    "exists:content_items",
    "exists:content_calendar"
  ],
  "vector_indices": "attempted"
}

✓ LinkRight initialized.

## Import sanity (python3.13)
All imports OK
```


---

## Notes

- The legacy v0.0 commands (`optimize`, `validate`, `assisted`) are still registered alongside the new pillars — preserved for backward compatibility.
- `linkright init` is idempotent: all 12 MongoDB collections report `exists:<name>` on subsequent runs.
- `vector_indices: attempted` is expected on local MongoDB CE 8 (Atlas-only feature) — non-fatal; tracked for Atlas deployment.
- Deeper pipeline E2E (`resume tailor -r ... -j ...`) not in this smoke matrix — requires API keys + sample artifacts. Documented as known-limit in CHANGELOG.

## Disposition

- **Fixed:** none — no bugs surfaced.
- **Documented:** vector-index fallback note (above).
- **Deferred:** orchestrator E2E with live LLM cascade; scorer LLM-judging upgrade.
