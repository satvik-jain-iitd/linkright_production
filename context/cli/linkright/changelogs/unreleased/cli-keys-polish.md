## [type: Fixed]
<!-- pr: TBD -->
- **CLI keys polish:** Replace `key(s)`/`provider(s)`/`slot(s)` with correct singular/plural throughout `keys add` output. Add duplicate key-value warning — if the same API key is entered twice across slots, user sees `⚠ This key value is already saved as <slot>` instead of silent overwrite.
