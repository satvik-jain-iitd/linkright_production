"""Profile management — one-time creation, persistent reuse across runs.

Storage at ``~/.linkright/profile/`` (single profile per machine for now).

Submodules:
  - pipeline: thin shim that re-points orchestrator paths and calls step_01-03
  - cli: Click subcommand group `profile_group` (create / show / delete-nugget / enrich / refresh / rebuild)
  - render: rich-based outline renderer
  - enrich: deep-enrichment (3 follow-up Qs per nugget)

Public entry points are exposed via cli.profile_group; everything else is
internal helpers.
"""
