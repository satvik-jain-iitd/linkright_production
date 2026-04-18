import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { AppNav } from "@/components/AppNav";
import { BroadcastInsightsBrowser } from "@/components/broadcast/BroadcastInsightsBrowser";

// Wave 2 / S16 — Broadcast · Insights browser (default broadcast surface).

export const metadata = {
  title: "Broadcast — LinkRight",
};

export default async function BroadcastPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) redirect("/auth");

  return (
    <div className="min-h-screen">
      <AppNav user={user} />
      <main className="mx-auto max-w-[1200px] px-6 py-10">
        <BroadcastInsightsBrowser />
      </main>
    </div>
  );
}
