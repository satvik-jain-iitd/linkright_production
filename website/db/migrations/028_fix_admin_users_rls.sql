-- Fix: admin_users RLS was recursive — users couldn't read their own admin row
-- because the read policy itself required being IN admin_users (which required
-- reading admin_users). Classic chicken-and-egg.
--
-- Replacement: a user can SELECT only rows where user_id = auth.uid(). That's
-- enough for checkAdmin() to verify their own status. Service role still has
-- full access via the existing service_writes_admins policy.

DROP POLICY IF EXISTS "admins_read_allowlist" ON admin_users;

CREATE POLICY "users_check_own_admin_row" ON admin_users
  FOR SELECT USING (auth.uid() = user_id);
