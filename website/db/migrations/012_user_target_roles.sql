-- Add target_roles column to user_settings
-- Stores the roles user selected during onboarding Step 1 (e.g., ["Product Manager", "Software Engineer"])
-- Previously only stored in localStorage — now persisted for cross-device access

ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS target_roles TEXT[] DEFAULT '{}';
