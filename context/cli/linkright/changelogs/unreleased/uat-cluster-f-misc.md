# UAT Cluster F — Flag-hint polish + long-doc warning (#3, #12)

## Bug #3 — Flag-based command suggestions removed from runtime output

Runtime messages (click.echo, print to stderr) no longer suggest raw CLI flags
to non-technical users. Affected locations:

- `linkright doctor`: failure summary no longer suggests `--auto-fix`; uses
  "with the auto-fix option" plain-English phrasing instead.
- `linkright profile show/status/edit-contact/delete-nugget/enrich/graph`:
  "No profile found" errors simplified from
  `Run linkright profile create -r resume.pdf --yes` to
  `Run linkright profile create` (flags belong in --help, not error messages).
- `linkright profile refresh`: staged-resume-missing error simplified similarly.
- `linkright profile graph`: rebuild hint uses plain English instead of `--force`.

Non-TTY / CI paths retain `--force` hint (scripted automation legitimately needs
this; removing it would break power-user workflows without TTY).

## Bug #12 — Long document safety-net warning in `profile create`

`parse_and_extract` (the PDF ingestion entry point for `linkright profile create`)
now emits a stderr warning when raw extracted text exceeds 15,000 characters
(≈3,750 tokens — a conservative LLM context-limit safety margin):

```
⚠ Document is long (N chars). If extraction is incomplete, consider shortening
your resume or using a trimmed plain-text version.
```

This is a **user safety net only** — the pipeline does NOT truncate or refuse
to process the document. The warning lets users self-remediate if they notice
extraction quality issues. Full chunking / partitioning is deferred.

Also includes `regex_extract.py` (from pending PR cluster B-truth-engine #13)
as a dependency fix — `pipeline.py` imported it but the file was absent from
main, causing `ModuleNotFoundError` on `profile create` invocations.
