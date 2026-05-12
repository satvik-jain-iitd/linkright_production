## [type: Fixed]
<!-- pr: TBD -->
- **S5.0 (Pre-flight guards):** Commands now check for required artifacts before dispatching any pipeline logic. `resume tailor` and `cover-letter` guard profile + LLM key; harness commands (`improve`, `fill-metrics`, `practice`, `strategy-review`, `critique`) guard profile + prior tailor run; `profile create` guards PDF readability. Users see a clear "run X first" message instead of a Python traceback.
