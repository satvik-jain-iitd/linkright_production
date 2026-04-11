// Next.js middleware — Supabase session refresh on every request.
// Without this file, proxy.ts is never loaded and sessions are never refreshed server-side.
export { proxy as middleware, config } from "./proxy";
