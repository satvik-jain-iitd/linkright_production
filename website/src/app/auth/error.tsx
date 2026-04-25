"use client";

export default function AuthError({
  error,
  reset,
}: {
  error: Error;
  reset: () => void;
}) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="w-full max-w-sm rounded-2xl border border-border bg-white p-8 text-center shadow-sm">
        <div className="mb-3 text-3xl">⚠️</div>
        <h2 className="text-base font-semibold text-foreground">Something went wrong</h2>
        <p className="mt-1.5 text-sm text-muted">
          {error?.message || "An unexpected error occurred during sign in."}
        </p>
        <button
          onClick={reset}
          className="mt-5 w-full rounded-lg bg-accent py-2.5 text-sm font-semibold text-white hover:bg-accent/90"
        >
          Try again
        </button>
      </div>
    </div>
  );
}
