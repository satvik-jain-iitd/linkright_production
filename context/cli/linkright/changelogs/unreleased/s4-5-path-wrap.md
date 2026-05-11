## [type: Fixed]
<!-- pr: -->

- **S4.5 (Success box path wrap):** Fixed `linkright resume tailor` success card
  showing the PDF path mid-word wrapped across lines. `_render_success_card` in
  `resume/cli.py` now passes the filename and full path as two separate lines
  (`filename\nfull_path`). `success_card()` in `ui/__init__.py` was updated to
  handle multi-line field values: the first line renders on the key row in accent
  colour, and continuation lines are indented to the value column and rendered
  dimmed. Rich `Text(overflow="fold")` is used for the panel body so that even
  on 80-col terminals the filename component is never broken mid-word (fold only
  occurs at path-separator boundaries). 15 new tests in
  `tests/test_success_box_render.py` verify no mid-word wraps at 80, 100, and
  120 col widths via both the helper primitives and the `success_card()` module
  function.
