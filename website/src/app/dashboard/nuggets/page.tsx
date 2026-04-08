import { createClient } from "@/lib/supabase/server";
import NuggetsDashboard from "./NuggetsDashboard";

export default async function NuggetsPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  return <NuggetsDashboard user={user} />;
}
