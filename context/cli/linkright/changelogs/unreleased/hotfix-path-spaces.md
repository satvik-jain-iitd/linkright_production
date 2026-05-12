## [type: Fixed]
<!-- pr: TBD -->
- **Hotfix (path prompt spaces):** `_sanitize_path_input` no longer truncates unquoted paths containing spaces (e.g. `Ruch_ Dubey_Resume.pdf`). shlex decoding is now applied only when the input uses shell quoting or backslash escapes; bare unquoted paths are passed through verbatim.
