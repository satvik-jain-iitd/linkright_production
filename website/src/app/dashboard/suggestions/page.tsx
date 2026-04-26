import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { AppNav } from "@/components/AppNav";
import { SuggestionsInbox } from "./SuggestionsInbox";

// SMA_v2 — LinkedIn post suggestions inbox.
// Diary likhne ke 30s baad yahan 3 ranked concepts dikhte hain.

export const metadata = {
  title: "Suggestions — LinkRight",
};

export default async function SuggestionsPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) redirect("/auth");

  return (
    <div className="min-h-screen">
      <AppNav user={user} />
      <main className="mx-auto max-w-[1100px] px-6 py-10">
        <SuggestionsInbox />
      </main>
    </div>
  );
}
