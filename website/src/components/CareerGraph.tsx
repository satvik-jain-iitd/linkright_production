"use client";

import dynamic from "next/dynamic";
import type { ComponentType } from "react";

// Re-export types so existing imports of `{ CytoElement, CytoElementData }` still work.
export type { CytoElement, CytoElementData } from "./CareerGraphImpl";

interface CareerGraphProps {
  elements: import("./CareerGraphImpl").CytoElement[];
}

// Lazy-load the Cytoscape-heavy implementation (cytoscape + fcose ≈ 2.5MB).
// SSR is disabled because Cytoscape touches `window` on init.
const CareerGraphImpl = dynamic(
  () => import("./CareerGraphImpl"),
  {
    ssr: false,
    loading: () => (
      <div className="w-full h-[480px] rounded-lg border border-neutral-200 bg-neutral-50 animate-pulse" />
    ),
  },
) as ComponentType<CareerGraphProps>;

export function CareerGraph(props: CareerGraphProps) {
  return <CareerGraphImpl {...props} />;
}
