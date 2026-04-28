/**
 * Polyfill for AbortSignal.any([...signals]).
 *
 * AbortSignal.any is available in Node 20+ (and modern browsers).
 * This polyfill works on Node 18+ and avoids a runtime TypeError when
 * Vercel uses an older Node runtime.
 *
 * Behaviour matches the spec:
 * - If any input signal is already aborted, the returned signal is
 *   already aborted (synchronously) with the same reason.
 * - Otherwise, the first signal to abort wins.
 */
export function abortSignalAny(signals: AbortSignal[]): AbortSignal {
  // Use native implementation when available (Node 20+, modern browsers).
  if (typeof AbortSignal.any === "function") {
    return AbortSignal.any(signals);
  }

  const controller = new AbortController();

  for (const signal of signals) {
    // Already aborted — propagate synchronously.
    if (signal.aborted) {
      controller.abort(signal.reason);
      return controller.signal;
    }
  }

  for (const signal of signals) {
    signal.addEventListener(
      "abort",
      () => {
        if (!controller.signal.aborted) {
          controller.abort(signal.reason);
        }
      },
      { once: true }
    );
  }

  return controller.signal;
}
