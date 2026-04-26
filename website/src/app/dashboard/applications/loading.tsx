export default function Loading() {
  return (
    <div className="p-6">
      <div className="h-8 w-48 mb-6 rounded bg-neutral-200 animate-pulse" />
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {["Applied", "Interview", "Offer", "Closed"].map((col) => (
          <div key={col} className="rounded-lg border border-neutral-200 p-3">
            <div className="h-5 w-24 mb-3 rounded bg-neutral-200 animate-pulse" />
            <div className="space-y-2">
              {[0, 1, 2].map((i) => (
                <div key={i} className="h-20 rounded bg-neutral-100 animate-pulse" />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
