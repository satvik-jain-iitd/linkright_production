"use client";

import { useEffect, useRef, useState } from "react";
import type cytoscape from "cytoscape";

export interface CytoElementData {
  id: string;
  label?: string;
  type?: "achievement" | "experience" | "skill";
  size?: number;
  source?: string;
  target?: string;
  edgeType?: string;
  company?: string;
  role?: string;
  date?: string;
  importance?: string;
  answer?: string;
  count?: number;
}

export interface CytoElement {
  data: CytoElementData;
}

interface SelectedNode {
  id: string;
  type: "achievement" | "experience" | "skill";
  label: string;
  company?: string;
  role?: string;
  date?: string;
  importance?: string;
  answer?: string;
  count?: number;
}

interface CareerGraphProps {
  elements: CytoElement[];
}

const NODE_COLORS = {
  achievement: "#3B82F6",
  experience: "#8B5CF6",
  skill: "#10B981",
} as const;

export function CareerGraph({ elements }: CareerGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);
  const [selected, setSelected] = useState<SelectedNode | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!containerRef.current || elements.length === 0) return;

    let destroyed = false;

    Promise.all([import("cytoscape"), import("cytoscape-fcose")])
      .then(([cytoscapeModule, fcoseModule]) => {
        if (destroyed) return;
        const cytoscape = cytoscapeModule.default;
        const fcose = fcoseModule.default;

        try { cytoscape.use(fcose); } catch { /* already registered */ }

        // Stylesheet cast: cytoscape's type for StylesheetJson is complex;
        // runtime behavior is correct, so we cast to avoid string-literal mismatch.
        const stylesheet = [
          {
            selector: 'node[type="achievement"]',
            style: {
              "background-color": "#3B82F6",
              label: "data(label)",
              "font-size": 9,
              width: "data(size)",
              height: "data(size)",
              color: "#ffffff",
              "text-valign": "center" as const,
              "text-halign": "center" as const,
              "text-wrap": "wrap" as const,
              "text-max-width": "70",
            },
          },
          {
            selector: 'node[type="experience"]',
            style: {
              "background-color": "#8B5CF6",
              label: "data(label)",
              "font-size": 11,
              "font-weight": "bold",
              width: "data(size)",
              height: "data(size)",
              color: "#ffffff",
              "text-valign": "center" as const,
              "text-halign": "center" as const,
              "text-wrap": "wrap" as const,
              "text-max-width": "80",
              shape: "roundrectangle" as const,
            },
          },
          {
            selector: 'node[type="skill"]',
            style: {
              "background-color": "#10B981",
              label: "data(label)",
              "font-size": 8,
              width: "data(size)",
              height: "data(size)",
              color: "#ffffff",
              "text-valign": "center" as const,
              "text-halign": "center" as const,
              "text-wrap": "wrap" as const,
              "text-max-width": "60",
            },
          },
          {
            selector: 'edge[edgeType="AT"]',
            style: {
              width: 2,
              "line-color": "#8B5CF6",
              "target-arrow-color": "#8B5CF6",
              "target-arrow-shape": "triangle" as const,
              "curve-style": "bezier" as const,
              opacity: 0.6,
            },
          },
          {
            selector: 'edge[edgeType="DEMONSTRATES"]',
            style: {
              width: 1,
              "line-color": "#10B981",
              "target-arrow-color": "#10B981",
              "target-arrow-shape": "triangle" as const,
              "curve-style": "bezier" as const,
              opacity: 0.35,
              "line-style": "dashed" as const,
            },
          },
          {
            selector: "node:selected",
            style: {
              "border-width": 3,
              "border-color": "#F59E0B",
            },
          },
        ] as unknown as cytoscape.StylesheetJson;

        const cy = cytoscape({
          container: containerRef.current!,
          elements: elements as cytoscape.ElementDefinition[],
          style: stylesheet,
          layout: {
            name: "fcose",
            // @ts-expect-error fcose-specific options not in base layout type
            nodeRepulsion: 9000,
            idealEdgeLength: 90,
            edgeElasticity: 0.45,
            gravity: 0.25,
            gravityRange: 3.8,
            animate: true,
            animationDuration: 800,
            randomize: false,
          },
          minZoom: 0.2,
          maxZoom: 3,
        });

        cyRef.current = cy;

        cy.on("tap", "node", (evt) => {
          const node = evt.target;
          const nodeType = node.data("type") as "achievement" | "experience" | "skill" | undefined;
          if (!nodeType) return;
          setSelected({
            id: node.data("id") as string,
            type: nodeType,
            label: (node.data("label") as string | undefined) ?? "",
            company: node.data("company") as string | undefined,
            role: node.data("role") as string | undefined,
            date: node.data("date") as string | undefined,
            importance: node.data("importance") as string | undefined,
            answer: node.data("answer") as string | undefined,
            count: node.data("count") as number | undefined,
          });
        });

        setReady(true);
      })
      .catch(console.error);

    return () => {
      destroyed = true;
      if (cyRef.current) {
        cyRef.current.destroy();
        cyRef.current = null;
      }
    };
  }, [elements]);

  if (elements.length === 0) return null;

  return (
    <div className="flex gap-3 h-[420px]">
      {/* Graph canvas */}
      <div className="relative flex-1 rounded-xl border border-border bg-gray-950 overflow-hidden">
        <div ref={containerRef} className="w-full h-full" />
        {!ready && (
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-xs text-gray-400">Rendering graph…</span>
          </div>
        )}
        {/* Legend */}
        <div className="absolute bottom-3 left-3 flex gap-3 bg-gray-950/80 backdrop-blur-sm rounded-lg px-3 py-1.5">
          {(["achievement", "experience", "skill"] as const).map((type) => (
            <span key={type} className="flex items-center gap-1.5 text-xs text-gray-300">
              <span
                className="inline-block w-2.5 h-2.5 rounded-full shrink-0"
                style={{ backgroundColor: NODE_COLORS[type] }}
              />
              {type.charAt(0).toUpperCase() + type.slice(1)}
            </span>
          ))}
        </div>
      </div>

      {/* Node detail panel */}
      {selected && (
        <div className="w-52 shrink-0 rounded-xl border border-border bg-surface p-4 space-y-2 overflow-y-auto">
          <div className="flex items-start justify-between gap-2">
            <span
              className="shrink-0 inline-block w-2.5 h-2.5 rounded-full mt-1"
              style={{ backgroundColor: NODE_COLORS[selected.type] }}
            />
            <p className="flex-1 text-xs font-semibold text-foreground leading-snug">
              {selected.label}
            </p>
            <button
              onClick={() => setSelected(null)}
              className="shrink-0 text-muted hover:text-foreground text-xs"
            >
              ✕
            </button>
          </div>
          <span className="inline-block text-[10px] uppercase tracking-wide text-muted border border-border rounded px-1.5 py-0.5">
            {selected.type}
          </span>
          {selected.company && (
            <div>
              <p className="text-[10px] text-muted uppercase tracking-wide">Company</p>
              <p className="text-xs text-foreground">{selected.company}</p>
            </div>
          )}
          {selected.role && (
            <div>
              <p className="text-[10px] text-muted uppercase tracking-wide">Role</p>
              <p className="text-xs text-foreground">{selected.role}</p>
            </div>
          )}
          {selected.date && (
            <div>
              <p className="text-[10px] text-muted uppercase tracking-wide">Date</p>
              <p className="text-xs text-foreground">{selected.date}</p>
            </div>
          )}
          {selected.importance && (
            <div>
              <p className="text-[10px] text-muted uppercase tracking-wide">Importance</p>
              <p className="text-xs text-foreground">{selected.importance}</p>
            </div>
          )}
          {selected.count !== undefined && (
            <div>
              <p className="text-[10px] text-muted uppercase tracking-wide">Used in</p>
              <p className="text-xs text-foreground">
                {selected.count} achievement{selected.count !== 1 ? "s" : ""}
              </p>
            </div>
          )}
          {selected.answer && (
            <div>
              <p className="text-[10px] text-muted uppercase tracking-wide">Result</p>
              <p className="text-xs text-muted leading-relaxed">{selected.answer}…</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
