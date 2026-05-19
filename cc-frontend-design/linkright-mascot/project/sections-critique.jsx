/* =========================================================================
   sections-critique.jsx — designer's self-evaluation, before → after.

   Shows the v1 problems honestly: low contrast accessories, ambiguous
   expressions, undersized props. Then the v2 fix beside each one.
   ========================================================================= */

/* ---------- v1 (old) sprite grids embedded inline so we can show
   them as "before" alongside the new ones. These match what shipped
   in the first round; they no longer live in the main sprite file. ---------- */
const V1_SPRITES = {
  idle: [
    ".CCCCCCCCCCCC.",
    "CCCCCCCCCCCCCC",
    "CCCKKCCCCKKCCC",
    "CCCKKCCCCKKCCC",
    "CCCCCCCCCCCCCC",
    "CCCCCCCCCCCCCC",
    "CCCCCCCCCCCCCC",
    "CCCCCCCCCCCCCC",
    ".CCCCCCCCCCCC.",
    "..CCCCCCCCCC..",
  ],
  happy_v1: [
    "..CCCCCCCCCC..",
    ".CCCCCCCCCCCC.",
    "CCCCCCCCCCCCCC",
    "CCCKCCCCCCKCCC",
    "CCKCKCCCCKCKCC",
    "CCCCCCCCCCCCCC",
    "CCCCCCCCCCCCCC",
    "CCCCCCCCCCCCCC",
    ".CCCCCCCCCCCC.",
    "..CCCCCCCCCC..",
  ],
  hammer_v1: [
    "..........XXX.........",
    "..........XXX.........",
    "..........XXX.........",
    "...XXX....XXX.........",
    "...XXXXXXXXXX.........",
    "...XXX....XXX....c....",
    "....CCCCCCCCCCCC.c.c..",
    "...CCCCCCCCCCCCCC..c..",
    "...CCCKKCCCCKKCCC.....",
    "...CCCKKCCCCKKCCC.....",
    "...CCCCCCCCCCCCCC.....",
    "...CCCCCCCCCCCCCC.....",
    "....CCCCCCCCCCCC......",
    ".....CCCCCCCCCC.......",
  ],
  coffee_v1: [
    "......................",
    "......................",
    "......................",
    "..............LLL.....",
    "....CCCCCCCCCCXXX.....",
    "...CCCCCCCCCCCXXXX....",
    "...CCCKKCCCCKKXXX.....",
    "...CCCKKCCCCKKXXX.....",
    "...CCCCCCCCCCCXXX.....",
    "...CCCCCCCCCCCCCC.....",
    "...CCCCCCCCCCCCCC.....",
    "....CCCCCCCCCCCC......",
    ".....CCCCCCCCCC.......",
    "......................",
  ],
  magnifier_v1: [
    "......................",
    ".....CCCCCCCCCCCC.....",
    "....CCCCCCCCCCCCCC....",
    "....CCCCCCCCCCCCCC....",
    "....CCCKKCCCCKKKKK....",
    "....CCCKKCCCCKKWKK....",
    "....CCCCCCCCCCKKKKK...",
    "....CCCCCCCCCCCKK.K...",
    "....CCCCCCCCCCCC.K....",
    "....CCCCCCCCCCCC......",
    ".....CCCCCCCCCCCC.....",
    "......CCCCCCCCCC......",
    "......................",
    "......................",
  ],
  page_v1: [
    "......................",
    "......LLLLLLLLL.......",
    "......LXXXLLLLL.......",
    "......LLLLLLLLL.......",
    "......LXXXXXXLL.......",
    "....CCCLXXXXXXLLC.....",
    "...CCCCLXXXXXXLLCC....",
    "...CCCKKLLLLLLLLCC....",
    "...CCCKKCCCCKKCCC.....",
    "...CCCCCCCCCCCCCC.....",
    "...CCCCCCCCCCCCCC.....",
    "....CCCCCCCCCCCC......",
    ".....CCCCCCCCCC.......",
    "......................",
  ],
};

// v1 palette (coral body, dark X for "tools")
const V1_PALETTE = {
  ".": null,
  "C": "#FF5733",
  "c": "#FF8D71",
  "K": "#0E1620",
  "W": "#FFFFFF",
  "G": "#E5B80B",
  "X": "#3B475A",   // <-- the offender: dark gray "tools" on dark bg
  "L": "#FDF6F0",
  "T": "#0FBEAF",
};

function V1Sprite({ name, pixel = 6 }) {
  const grid = V1_SPRITES[name];
  if (!grid) return null;
  const cols = grid[0].length;
  const rows = grid.length;
  const w = cols * pixel;
  const h = rows * pixel;
  const rects = [];
  for (let y = 0; y < rows; y++) {
    for (let x = 0; x < cols; x++) {
      const fill = V1_PALETTE[grid[y][x]];
      if (!fill) continue;
      rects.push(<rect key={y * cols + x} x={x * pixel} y={y * pixel} width={pixel} height={pixel} fill={fill} />);
    }
  }
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width={w} height={h} viewBox={`0 0 ${w} ${h}`} shapeRendering="crispEdges">
      {rects}
    </svg>
  );
}

/* ---------- The critique artboard ---------- */
function CritiqueArtboard() {
  const W = 1480, H = 1100;

  const rows = [
    {
      label: "01 · Body color",
      problem: "Coral on dark navy is warm but mid-luminance — Pip reads as muddy when small.",
      score: "3/5",
      fix: "Switch to brand-primary TEAL. Higher luminance on dark, brand-aligned, instantly readable.",
      v1: { kind: "sprite", name: "idle" },
      v2: { kind: "sprite", name: "idle" },
    },
    {
      label: "02 · Hammer (building)",
      problem: "Hammer drawn in #3B475A — a dark gray ON dark navy. Invisible. The action 'building' didn't read at all.",
      score: "1/5",
      fix: "Silver hammer head with light handle. Coral sparks fly off on impact. Clear T-shape, clearly above Pip's head.",
      v1: { kind: "sprite", name: "hammer_v1" },
      v2: { kind: "sprite", name: "with_hammer" },
    },
    {
      label: "03 · Coffee (long task)",
      problem: "Mug rendered in same dark gray. Merged with Pip's silhouette. No steam, no readable cup.",
      score: "1/5",
      fix: "Cream mug with brown coffee inside + visible white steam curls. Reads as 'Pip is brewing' at first glance.",
      v1: { kind: "sprite", name: "coffee_v1" },
      v2: { kind: "sprite", name: "with_coffee" },
    },
    {
      label: "04 · Magnifier (reading JD)",
      problem: "Magnifier squeezed into Pip's face with no clear ring shape. Looked like 'Pip has weird eyes'.",
      score: "1/5",
      fix: "Big silver ring with white glass, clear handle, placed BESIDE Pip's head. Reads instantly as 'inspecting'.",
      v1: { kind: "sprite", name: "magnifier_v1" },
      v2: { kind: "sprite", name: "with_magnifier" },
    },
    {
      label: "05 · Happy face",
      problem: "Squint achieved by shifting eyes 1 pixel. At small render sizes, the change is invisible — felt indistinguishable from idle.",
      score: "2/5",
      fix: "Squint + an actual SMILE MOUTH. Emotion no longer depends on sub-pixel detail.",
      v1: { kind: "sprite", name: "happy_v1" },
      v2: { kind: "sprite", name: "happy" },
    },
    {
      label: "06 · Carrying resume page",
      problem: "Page and Pip overlapped in the same warm palette. Hard to see where Pip ended and the page began.",
      score: "2/5",
      fix: "Cream document silhouette held in front, with header line + body text lines. Document is unambiguously a document.",
      v1: { kind: "sprite", name: "page_v1" },
      v2: { kind: "sprite", name: "with_page" },
    },
  ];

  return (
    <div style={{
      width: W, height: H,
      background: "#F2EAE0",
      backgroundImage: "radial-gradient(ellipse at 20% 0%, rgba(15,190,175,0.08) 0%, transparent 50%)",
      padding: "44px 56px",
      boxSizing: "border-box",
      fontFamily: "var(--font-sans)",
      color: "var(--color-foreground)",
      display: "flex", flexDirection: "column", gap: 22,
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
        <div>
          <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.16em", textTransform: "uppercase", color: "var(--color-cta)" }}>
            00 · Designer's critique · v1 → v2
          </div>
          <h2 style={{ fontSize: 44, fontWeight: 800, letterSpacing: "-0.025em", margin: "10px 0 0", lineHeight: 1.05 }}>
            I rebuilt Pip. Here's what was wrong.
          </h2>
          <div style={{ fontSize: 14, color: "var(--color-muted)", marginTop: 8, maxWidth: 880, lineHeight: 1.55 }}>
            The v1 mascot looked fine in isolation but failed the first-glance test in real terminal contexts.
            The pattern was consistent: <strong style={{ color: "var(--color-foreground)" }}>dark-on-dark accessories and sub-pixel emotional cues.</strong> v2 fixes both.
          </div>
        </div>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--color-muted)", textAlign: "right", lineHeight: 1.5 }}>
          tested against<br />
          terminal bg #0E1620
        </div>
      </div>

      {/* The before/after table */}
      <div style={{
        background: "var(--color-surface)",
        borderRadius: 16,
        border: "1px solid var(--color-border)",
        overflow: "hidden",
        flex: 1,
        display: "flex", flexDirection: "column",
      }}>
        {/* Header row */}
        <div style={{
          display: "grid",
          gridTemplateColumns: "180px 240px 1fr 240px 1fr",
          gap: 0,
          background: "#FAFBFC",
          borderBottom: "1px solid var(--color-border)",
          fontSize: 11, fontWeight: 600, letterSpacing: "0.12em",
          textTransform: "uppercase", color: "var(--color-muted)",
        }}>
          <div style={{ padding: "14px 18px" }}>State</div>
          <div style={{ padding: "14px 14px" }}>v1 (coral) · before</div>
          <div style={{ padding: "14px 14px" }}>Problem</div>
          <div style={{ padding: "14px 14px", color: "var(--color-accent)" }}>v2 (teal) · after</div>
          <div style={{ padding: "14px 14px", color: "var(--color-accent)" }}>Fix</div>
        </div>

        {/* Data rows */}
        {rows.map((r, i) => (
          <div key={r.label} style={{
            display: "grid",
            gridTemplateColumns: "180px 240px 1fr 240px 1fr",
            gap: 0,
            borderBottom: i < rows.length - 1 ? "1px solid var(--color-border)" : "none",
            alignItems: "center",
            minHeight: 110,
          }}>
            <div style={{ padding: "16px 18px" }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: "var(--color-cta)", fontFamily: "var(--font-mono)", letterSpacing: "0.08em" }}>
                {r.label.split(" · ")[0]}
              </div>
              <div style={{ fontSize: 14, fontWeight: 600, marginTop: 4, letterSpacing: "-0.005em" }}>
                {r.label.split(" · ")[1]}
              </div>
              <div style={{
                fontSize: 11, color: "var(--color-cta)",
                fontFamily: "var(--font-mono)", fontWeight: 600,
                marginTop: 6,
              }}>
                clarity {r.score}
              </div>
            </div>

            {/* v1 sprite, dark bg */}
            <div style={{ padding: "12px 14px" }}>
              <div style={{
                background: "#0E1620",
                borderRadius: 10,
                padding: 12,
                display: "flex", alignItems: "center", justifyContent: "center",
                minHeight: 86,
                border: "1px solid #253140",
              }}>
                <V1Sprite name={r.v1.name} pixel={5} />
              </div>
            </div>

            <div style={{ padding: "12px 14px", fontSize: 13, color: "var(--color-foreground)", lineHeight: 1.5 }}>
              {r.problem}
            </div>

            {/* v2 sprite, dark bg */}
            <div style={{ padding: "12px 14px" }}>
              <div style={{
                background: "#0E1620",
                borderRadius: 10,
                padding: 12,
                display: "flex", alignItems: "center", justifyContent: "center",
                minHeight: 86,
                border: "1.5px solid rgba(15,190,175,0.5)",
              }}>
                <PipSprite name={r.v2.name} pixel={5} />
              </div>
            </div>

            <div style={{ padding: "12px 14px", fontSize: 13, color: "var(--color-foreground)", lineHeight: 1.5 }}>
              {r.fix}
            </div>
          </div>
        ))}
      </div>

      {/* Summary strip */}
      <div style={{
        display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 18,
      }}>
        {[
          { tag: "Palette law", body: "Body in TEAL. Eyes in BLACK. Accessories only in SILVER · CREAM · GOLD · PURPLE · CORAL. Nothing dark on dark, ever." },
          { tag: "Expression law", body: "If a face change is < 2px, add a MOUTH. Emotion must read at the smallest display size (~28px tall)." },
          { tag: "Composite law", body: "Tools go OUTSIDE the body silhouette, in their own clear shape. Sparks + motion lines clarify action." },
        ].map((p) => (
          <div key={p.tag} style={{
            padding: 18,
            background: "rgba(15,190,175,0.06)",
            border: "1px solid rgba(15,190,175,0.25)",
            borderRadius: 14,
          }}>
            <div style={{ fontSize: 10.5, fontWeight: 600, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--color-accent)" }}>
              {p.tag}
            </div>
            <div style={{ fontSize: 13, color: "var(--color-foreground)", marginTop: 6, lineHeight: 1.5 }}>
              {p.body}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

Object.assign(window, { CritiqueArtboard, V1Sprite });
