# Width synonym bank, cleanup and consolidation (W1)

## Fixed

- The width synonym bank suggested two banned words, `use -> utilize` and `own -> spearhead`. Both removed. The bank now never proposes a replacement the content gate would reject.
- The bank existed as three copies that had drifted apart (`data/`, `mcp_sync/data/`, `resume/data/`). All three are now identical.

## Changed

- Replaced aggressive, ATS-unfriendly abbreviations (`x-func`, `dev work`, `org-wide`) with readable forms.
- Expanded from 40 to 48 pairs with common resume verbs and nouns.
- All deltas are now computed from `data/roboto_weights.py`, the same table `measure_width` uses, so they stay consistent with the measurer.
