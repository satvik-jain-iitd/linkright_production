import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { AppNav } from "@/components/AppNav";
import { CoverLettersView } from "@/components/cover-letters/CoverLettersView";

export const metadata = {
  title: "Cover letters — LinkRight",
};

export default async function CoverLettersPage({
  searchParams,
}: {
  searchParams: Promise<{ resume_job?: string; application_id?: string }>;
}) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) redirect("/auth");

  const params = await searchParams;

  return (
    <div className="min-h-screen">
      <AppNav user={user} />
      <main className="mx-auto max-w-[1100px] px-6 py-10">
        <CoverLettersView
          autoResumeJobId={params.resume_job ?? null}
          preselectApplicationId={params.application_id ?? null}
        />
      </main>
    </div>
  );
}
