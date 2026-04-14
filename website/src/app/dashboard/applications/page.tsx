import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { AppNav } from "@/components/AppNav";
import { KanbanBoard } from "@/components/kanban/KanbanBoard";

export default async function ApplicationsPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/auth");
  }

  return (
    <div className="min-h-screen bg-background">
      <AppNav user={user} variant="app" />
      <main className="mx-auto max-w-7xl px-6 py-6">
        <KanbanBoard />
      </main>
    </div>
  );
}
