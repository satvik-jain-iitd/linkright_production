"use client";

import { useEffect, useRef, useState } from "react";

interface CytoElementData {
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

interface CytoElement {
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
  const cyRef = useRef<unknown>(null);
  const [selected, setSelected] = useState<SelectedNode | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!containerRef.current || elements.length === 0) return;

    let cy: {
      destroy: () => void;
      on: (event: string, selector: string, handler: (evt: { target: { data: (key: string) => unknown } }) => void) => void;
    };

    // Dynamically import to avoid SSR issues with DOM manipulation
    Promise.all([
      import("cytoscape"),
      import("cytoscape-fcose"),
      import("react-cytoscapejs"),
    ])
      .then(([cytoscapeModule, fcoseModule]) => {
        const cytoscape = cytoscapeModule.default;
        const fcose = fcoseModule.default;

        // Register fcose layout (safe to call multiple times)
        try { cytoscape.use(fcose); } catch { /* already registered */ }

        const stylesheet = [
          {
            selector: 'node[type="achievement"]',
            style: {
              "background-color": NODE_COLORS.achievement,
              label: "data(label)",
              "font-size": 9,
              width: "data(size)",
              height: "data(size)",
              color: "#ffffff",
              "text-valign": "center",
              "text-halign": "center",
              "text-wrap": "wrap",
              "text-max-width": 70,
              "text-overflow-wrap": "anywhere",
            },
          },
          {
            selector: 'node[type="experience"]',
            style: {
              "background-color": NODE_COLORS.experience,
              label: "data(label)",
              "font-size": 11,
              "font-weight": "bold",
              width: "data(size)",
              height: "data(size)",
              color: "#ffffff",
              "text-valign": "center",
              "text-halign": "center",
              "text-wrap": "wrap",
              "text-max-width": 80,
              shape: "roundrectangle",
            },
          },
          {
            selector: 'node[type="skill"]',
            style: {
              "background-color": NODE_COLORS.skill,
              label: "data(label)",
              "font-size": 8,
              width: "data(size)",
              height: "data(size)",
              color: "#ffffff",
              "text-valign": "center",
              "text-halign": "center",
              "text-wrap": "wrap",
              "text-max-width": 60,
            },
          },
          {
            selector: 'edge[edgeType="AT"]',
            style: {
              width: 2,
              "line-color": "#8B5CF6",
              "target-arrow-color": "#8B5CF6",
              "target-arrow-shape": "triangle",
              "curve-style": "bezier",
              opacity: 0.6,
            },
          },
          {
            selector: 'edge[edgeType="DEMONSTRATES"]',
            style: {
              width: 1,
              "line-color": "#10B981",
              "target-arrow-color": "#10B981",
              "target-arrow-shape": "triangle",
              "curve-style": "bezier",
              opacity: 0.35,
              "line-style": "dashed",
            },
          },
          {
            selector: "node:selected",
            style: {
              "border-width": 3,
              "border-color": "#F59E0B",
            },
          },
        ];

        cy = cytoscape({
          container: containerRef.current!,
          elements,
          style: stylesheet,
          layout: {
            name: "fcose",
            // @ts-expect-error fcose types
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
          const nodeType = node.data("type") as "achievement" | "experience" | "skill";
          if (!nodeType) return;
          setSelected({
            id: node.data("id"),
            type: nodeType,
            label: node.data("label") ?? "",
            company: node.data("company"),
            role: node.data("role"),
            date: node.data("date"),
            importance: node.data("importance"),
            answer: node.data("answer"),
            count: node.data("count"),
          });
        });

        setReady(true);
      })
      .catch(console.error);

    return () => {
      if (cyRef.current) {
        (cyRef.current as { destroy: () => void }).destroy();
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
            <span className="text-xs text-muted">Rendering graph…</span>
          </div>
        )}
        {/* Legend */}
        <div className="absolute bottom-3 left-3 flex gap-3 bg-gray-950/80 backdrop-blur-sm rounded-lg px-3 py-1.5">
          {(["achievement", "experience", "skill"] as const).map((type) => (
            <span key={type} className="flex items-center gap-1.5 text-xs text-gray-300">
              <span
                className="inline-block w-2.5 h-2.5 rounded-full"
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
              <p className="text-xs text-foreground">{selected.count} achievement{selected.count !== 1 ? "s" : ""}</p>
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
