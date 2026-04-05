import { createClient } from "@/lib/supabase/server";
import { redirect } from "next/navigation";
import { WizardShell } from "./WizardShell";

export default async function NewResumePage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) redirect("/auth");

  return (
    <div className="min-h-screen bg-background">
      <WizardShell userId={user.id} />
    </div>
  );
}
