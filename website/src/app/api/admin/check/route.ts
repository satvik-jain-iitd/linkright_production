import { checkAdmin } from "@/lib/admin-auth";

export async function GET() {
  const admin = await checkAdmin();
  return Response.json({ is_admin: admin.ok, role: admin.ok ? admin.role : null });
}
