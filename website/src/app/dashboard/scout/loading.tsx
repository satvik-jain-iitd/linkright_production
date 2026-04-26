export default function Loading() {
  return (
    <div className="p-6 space-y-4">
      <div className="h-8 w-48 rounded bg-neutral-200 animate-pulse" />
      <div className="flex gap-2">
        <div className="h-10 w-32 rounded bg-neutral-200 animate-pulse" />
        <div className="h-10 w-32 rounded bg-neutral-200 animate-pulse" />
      </div>
      <div className="space-y-3">
        {[0, 1, 2, 3, 4].map((i) => (
          <div key={i} className="rounded-lg border border-neutral-200 p-4 flex justify-between items-center">
            <div className="space-y-2 flex-1">
              <div className="h-5 w-2/3 rounded bg-neutral-200 animate-pulse" />
              <div className="h-4 w-1/3 rounded bg-neutral-200 animate-pulse" />
            </div>
            <div className="h-10 w-24 rounded bg-neutral-200 animate-pulse" />
          </div>
        ))}
      </div>
    </div>
  );
}
