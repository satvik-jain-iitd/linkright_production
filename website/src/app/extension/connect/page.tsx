import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { ConnectExtension } from "./ConnectExtension";

// /extension/connect?return=<chrome-extension://.../popup/connected.html>&ext_id=<id>
//
// The extension's popup opens this page. We require an active Supabase
// session, then hand the user a "Connect" button. On click, the client
// component fetches /api/extension/connect to get a 30-day JWT and
// window.location-redirects to the return URL with ?token=...&ttl_ms=...
// so popup/connected.html can stash it via chrome.storage.local.

type SearchParams = Record<string, string | string[] | undefined>;

export default async function ExtensionConnectPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const params = await searchParams;
  const returnUrl = typeof params.return === "string" ? params.return : "";
  const extId = typeof params.ext_id === "string" ? params.ext_id : "";

  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();

  if (!user) {
    // Preserve the extension redirect across signin.
    const nextUrl = `/extension/connect?return=${encodeURIComponent(returnUrl)}&ext_id=${encodeURIComponent(extId)}`;
    redirect(`/auth?mode=signin&next=${encodeURIComponent(nextUrl)}`);
  }

  return <ConnectExtension email={user.email ?? ""} returnUrl={returnUrl} extId={extId} />;
}
