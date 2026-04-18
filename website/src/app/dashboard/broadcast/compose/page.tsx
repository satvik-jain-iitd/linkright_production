import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { AppNav } from "@/components/AppNav";
import { BroadcastCompose } from "@/components/broadcast/BroadcastCompose";

// Wave 2 / S17 — Compose + edit.

export const metadata = {
  title: "Compose broadcast — LinkRight",
};

export default async function BroadcastComposePage({
  searchParams,
}: {
  searchParams: Promise<{ insight_id?: string; kind?: string; post_id?: string }>;
}) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) redirect("/auth");

  const params = await searchParams;
  const fullName = (user.user_metadata?.full_name as string) ?? "";

  return (
    <div className="min-h-screen">
      <AppNav user={user} />
      <main className="mx-auto max-w-[1200px] px-6 py-8">
        <BroadcastCompose
          insightId={params.insight_id ?? null}
          insightKind={(params.kind as "nugget" | "diary" | undefined) ?? null}
          existingPostId={params.post_id ?? null}
          authorName={fullName || user.email || "You"}
          authorEmail={user.email ?? ""}
        />
      </main>
    </div>
  );
}
