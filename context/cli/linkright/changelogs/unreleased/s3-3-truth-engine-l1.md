## [type: Fixed]
<!-- pr: TBD -->
- **S3.3 (Truth Engine Layer 1):** Personal-details verification prompt at pipeline start; checks professional email format + LinkedIn slug quality; user can edit/skip each field; --no-pause / LR_NO_PAUSE=1 bypasses for CI/scripted use.
- **S3.3 Blocker 1:** step_01b_verify_contact_details now silently skips on non-TTY stdin (MCP/pipe mode) and catches EOFError from questionary — no more crash in MCP subprocesses.
- **S3.3 Blocker 2:** save_contact() now calls mkdir(parents=True, exist_ok=True) before writing contact.yaml — edits no longer silently lost when ~/.linkright/profile/ doesn't exist.
- **S3.3 Blocker 3:** _UNPROFESSIONAL_WORDS regex now uses \b word boundaries — hotel.manager, catherine.james, radical.ideas no longer false-positive; hotgirl99 still correctly warned.
