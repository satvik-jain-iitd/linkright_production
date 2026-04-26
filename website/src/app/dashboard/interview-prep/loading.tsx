export default function Loading() {
  return (
    <div className="p-6 space-y-6">
      <div className="h-8 w-64 rounded bg-neutral-200 animate-pulse" />
      <div className="h-4 w-96 rounded bg-neutral-200 animate-pulse" />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[0, 1, 2, 3, 4, 5, 6, 7].map((i) => (
          <div key={i} className="h-24 rounded-lg border border-neutral-200 bg-neutral-50 animate-pulse" />
        ))}
      </div>
      <div className="rounded-lg border border-neutral-200 p-4 h-48 animate-pulse" />
    </div>
  );
}
