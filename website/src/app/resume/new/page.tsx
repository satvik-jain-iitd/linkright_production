import { createClient } from "@/lib/supabase/server";
import { redirect } from "next/navigation";
import { WizardShell } from "./WizardShell";

export default async function NewResumePage({
  searchParams,
}: {
  searchParams: Promise<{ job?: string }>;
}) {
  const { job } = await searchParams;
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) redirect("/auth");

  // Onboarding gate: redirect if user hasn't completed setup
  const [{ count: keyCount }, { count: chunkCount }] = await Promise.all([
    supabase
      .from("user_api_keys")
      .select("*", { count: "exact", head: true })
      .eq("user_id", user.id)
      .eq("is_active", true),
    supabase
      .from("career_chunks")
      .select("*", { count: "exact", head: true })
      .eq("user_id", user.id),
  ]);

  if ((keyCount ?? 0) === 0 || (chunkCount ?? 0) === 0) {
    redirect("/onboarding");
  }

  return (
    <div className="min-h-screen bg-background">
      <WizardShell userId={user.id} jobId={job} />
    </div>
  );
}
