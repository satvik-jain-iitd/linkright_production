-- Enable Adzuna (keys already configured) and switch wellfound→themuse in sources_enabled.
-- TheMuse is a free API that replaced the blocked Wellfound endpoint.
-- iimjobs API is dead (404) — removed.

UPDATE scanner_settings
SET sources_enabled = (
  sources_enabled
  - 'wellfound'
  - 'iimjobs'
  || '{"themuse": true, "adzuna": true}'::jsonb
)
WHERE id = 1;
