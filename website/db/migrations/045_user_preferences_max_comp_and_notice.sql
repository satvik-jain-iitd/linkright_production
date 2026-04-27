-- 045_user_preferences_max_comp_and_notice.sql
-- Adds two columns the UI already collected but the API silently dropped:
--   max_comp_usd        — upper bound on annual comp (lakhs ₹ in current UI; rename if needed)
--   notice_period_days  — joining flexibility (0/15/30/60/90)
-- Without these the matching cannot honour the user's comp ceiling or notice flexibility.

ALTER TABLE user_preferences
  ADD COLUMN IF NOT EXISTS max_comp_usd        int,
  ADD COLUMN IF NOT EXISTS notice_period_days  int CHECK (
    notice_period_days IS NULL OR notice_period_days BETWEEN 0 AND 365
  );
