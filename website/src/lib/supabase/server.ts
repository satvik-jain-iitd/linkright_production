import { createServerClient } from "@supabase/ssr";
import { createClient as createSupabaseClient } from "@supabase/supabase-js";
import { cookies } from "next/headers";

const DEV_USER = {
  id: "c2305b3f-f934-4955-8c71-1875d7e45c64",
  email: "klickbae8yt@gmail.com",
  aud: "authenticated",
  role: "authenticated",
  user_metadata: { full_name: "Klickbae8 YT" },
  app_metadata: { provider: "google", providers: ["google"] },
} as any;

export async function createClient() {
  if (process.env.SKIP_AUTH === "true" && process.env.SUPABASE_SERVICE_ROLE_KEY) {
    const client = createSupabaseClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.SUPABASE_SERVICE_ROLE_KEY!
    );
    const originalGetUser = client.auth.getUser.bind(client.auth);
    (client.auth as any).getUser = async () => ({
      data: { user: DEV_USER },
      error: null,
    });
    return client as any;
  }

  const cookieStore = await cookies();

  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
        setAll(cookiesToSet) {
          try {
            cookiesToSet.forEach(({ name, value, options }) =>
              cookieStore.set(name, value, options)
            );
          } catch {
            // The `setAll` method was called from a Server Component.
            // This can be ignored if you have middleware refreshing sessions.
          }
        },
      },
    }
  );
}
