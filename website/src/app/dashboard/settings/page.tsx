import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
// [PSA5-382.1.1.1] Settings page eliminated — redirect to dashboard
// import { SettingsContent } from "./SettingsContent"; // commented out

export default async function SettingsPage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  redirect(user ? "/dashboard" : "/auth");
}
