# Resume, content gate on bullets

## Added

- **`tools/bullet_quality.py`**: a deterministic per-bullet content gate. Flags a passive opener, house filler words, and a missing `<b>` emphasis. Lenient by design, it never forces a number where the history is qualitative.

## Changed

- **`agents/bullet_writer.py`**: the per-bullet revision loop now gates on content as well as width. A bullet ships only when it both fits the width and clears the content gate. When the width is fine but the content is weak, a targeted content-revise pass fixes the named issue. This brings resume bullets to the same ground-then-gate-then-revise discipline the content and interview pillars use, on top of the existing width loop.
