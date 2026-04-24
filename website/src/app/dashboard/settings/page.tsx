import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { AppNav } from "@/components/AppNav";
import { ProfileView } from "../profile/ProfileView";

export default async function SettingsPage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect("/auth");

  const fullName = (user.user_metadata?.full_name as string) ?? undefined;
  return (
    <div className="min-h-screen">
      <AppNav user={user} />
      <ProfileView email={user.email ?? ""} fullName={fullName} />
    </div>
  );
}
