// Wave 2 / S20 — Template download for bulk career-file upload.
// Returns a richly commented example JSON that the user fills in + re-uploads.
// No auth required (it's a static-ish response) but we check anyway so the
// button doesn't leak sample to random crawlers.

import { createClient } from "@/lib/supabase/server";

const TEMPLATE = {
  _description:
    "LinkRight career file template. Fill the sections you care about, save as .json, and upload from Profile → Bulk upload. Anything you omit just stays empty. You can always run the upload multiple times; we merge, we don't overwrite.",
  profile: {
    full_name: "Your Name",
    headline: "Senior Product Manager",
    location: "Bangalore, IN",
    linkedin_url: "https://linkedin.com/in/example",
  },
  experience: [
    {
      company: "Example Co",
      role: "Senior Product Manager",
      start_date: "2023-08",
      end_date: "present",
      highlights: [
        {
          title: "Rebuilt the returns flow",
          one_liner:
            "Led a 12-person team redesigning returns for Indian merchants.",
          impact:
            "18% lift in completion, 22% drop in support tickets, shipped in 6 weeks.",
          tags: ["product-design", "user-research", "launch"],
        },
      ],
    },
  ],
  education: [
    {
      institution: "IIT Delhi",
      degree: "B.Tech, Computer Science",
      year: "2019",
    },
  ],
  projects: [
    {
      title: "Open-source Chrome extension",
      one_liner: "LinkedIn filter for applied roles — 2k active users.",
      tags: ["side-project"],
    },
  ],
  skills: ["Product strategy", "SQL", "A/B testing"],
  certifications: ["Pragmatic Marketing PMC-III"],
  takes: [
    "The hardest product decision is usually: what do we remove?",
  ],
};

export async function GET() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  return new Response(JSON.stringify(TEMPLATE, null, 2), {
    status: 200,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Content-Disposition":
        'attachment; filename="linkright-career-template.json"',
    },
  });
}
