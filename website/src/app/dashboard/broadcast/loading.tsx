export default function Loading() {
  return (
    <div className="p-6 space-y-4">
      <div className="h-8 w-56 rounded bg-neutral-200 animate-pulse" />
      <div className="h-4 w-96 rounded bg-neutral-200 animate-pulse" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-6">
        {[0, 1, 2].map((i) => (
          <div key={i} className="rounded-lg border border-neutral-200 p-4 space-y-3">
            <div className="h-5 w-32 rounded bg-neutral-200 animate-pulse" />
            <div className="h-32 rounded bg-neutral-100 animate-pulse" />
            <div className="h-4 w-3/4 rounded bg-neutral-200 animate-pulse" />
          </div>
        ))}
      </div>
    </div>
  );
}
