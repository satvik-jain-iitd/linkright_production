import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { AppNav } from "@/components/AppNav";
import { BroadcastScheduleTracker } from "@/components/broadcast/BroadcastScheduleTracker";

// Wave 2 / S18 — Schedule + tracker.

export const metadata = {
  title: "Schedule — LinkRight",
};

export default async function BroadcastSchedulePage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) redirect("/auth");

  return (
    <div className="min-h-screen">
      <AppNav user={user} />
      <main className="mx-auto max-w-[1200px] px-6 py-10">
        <BroadcastScheduleTracker />
      </main>
    </div>
  );
}
