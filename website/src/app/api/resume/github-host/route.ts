import { createClient } from "@/lib/supabase/server";

const GITHUB_API = "https://api.github.com";

async function githubFetch(path: string, pat: string, options?: RequestInit) {
  return fetch(`${GITHUB_API}${path}`, {
    ...options,
    headers: {
      Accept: "application/vnd.github+json",
      Authorization: `Bearer ${pat}`,
      "X-GitHub-Api-Version": "2022-11-28",
      "Content-Type": "application/json",
      ...(options?.headers ?? {}),
    },
  });
}

export async function POST(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  const body = await request.json();
  const { html, pat, repo_name } = body as {
    html: string;
    pat: string;
    repo_name?: string;
  };

  if (!html || !pat) {
    return Response.json({ error: "Missing html or pat" }, { status: 400 });
  }

  // 1. Get GitHub username
  const userRes = await githubFetch("/user", pat);
  if (!userRes.ok) {
    return Response.json(
      { error: "Invalid GitHub token — check scopes (needs repo + pages)" },
      { status: 400 }
    );
  }
  const ghUser = await userRes.json();
  const owner = ghUser.login as string;

  // 2. Choose repo name
  const slug = repo_name?.trim() || `resume-${Date.now().toString(36)}`;
  const finalRepo = slug.replace(/[^a-zA-Z0-9-_.]/g, "-").slice(0, 100);

  // 3. Create public repo
  const createRes = await githubFetch("/user/repos", pat, {
    method: "POST",
    body: JSON.stringify({
      name: finalRepo,
      description: "Resume hosted via LinkRight",
      private: false,
      auto_init: false,
    }),
  });

  if (!createRes.ok) {
    const err = await createRes.json();
    const msg = Array.isArray(err.errors) && err.errors[0]?.message
      ? err.errors[0].message
      : err.message || "Failed to create repository";
    return Response.json({ error: msg }, { status: 422 });
  }

  // 4. Push index.html (base64 encoded)
  const content = Buffer.from(html).toString("base64");
  const pushRes = await githubFetch(
    `/repos/${owner}/${finalRepo}/contents/index.html`,
    pat,
    {
      method: "PUT",
      body: JSON.stringify({
        message: "Add resume via LinkRight",
        content,
        branch: "main",
      }),
    }
  );

  if (!pushRes.ok) {
    const err = await pushRes.json();
    return Response.json(
      { error: err.message || "Failed to push file" },
      { status: 500 }
    );
  }

  // 5. Enable GitHub Pages
  const pagesRes = await githubFetch(`/repos/${owner}/${finalRepo}/pages`, pat, {
    method: "POST",
    body: JSON.stringify({ source: { branch: "main", path: "/" } }),
  });

  // Pages might already be enabled or take a moment — non-fatal if 409
  const pagesOk = pagesRes.ok || pagesRes.status === 409;
  if (!pagesOk) {
    // Repo and file created — return partial success with repo URL
    return Response.json({
      repo_url: `https://github.com/${owner}/${finalRepo}`,
      page_url: null,
      warning: "Could not enable GitHub Pages automatically. Enable it manually in the repo Settings → Pages.",
    });
  }

  return Response.json({
    repo_url: `https://github.com/${owner}/${finalRepo}`,
    page_url: `https://${owner}.github.io/${finalRepo}/`,
  });
}
