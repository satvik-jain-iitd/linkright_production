import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { CareerContent } from "./CareerContent";

export default async function CareerPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/auth");
  }

  const [{ count: chunkCount }, { count: nuggetCount }] = await Promise.all([
    supabase
      .from("career_chunks")
      .select("*", { count: "exact", head: true })
      .eq("user_id", user.id),
    supabase
      .from("career_nuggets")
      .select("*", { count: "exact", head: true })
      .eq("user_id", user.id),
  ]);

  return (
    <CareerContent
      user={user}
      chunkCount={chunkCount ?? 0}
      nuggetCount={nuggetCount ?? 0}
    />
  );
}
