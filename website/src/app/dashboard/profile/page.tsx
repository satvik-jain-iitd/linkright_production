import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { ProfileView } from "./ProfileView";

export default async function ProfilePage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/auth");
  }

  const fullName = (user.user_metadata?.full_name as string) ?? undefined;
  return <ProfileView email={user.email ?? ""} fullName={fullName} />;
}
