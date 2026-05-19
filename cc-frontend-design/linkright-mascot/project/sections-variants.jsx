/* =========================================================================
   sections-variants.jsx — design exploration.
   Three creative directions for Pip + an ASCII fallback so Pip works
   even in plain terminals with no color support.
   ========================================================================= */

/* ----- Alternate sprites used by the variant explorations ----- */

// Pip-the-Climber — a more humanoid pixel figure reaching toward a star.
// Direct callback to the LinkRight logo (the climbing arrow + star).
// 16 wide × 18 tall.
const CLIMBER_SPRITE = [
  ".......GG.......",
  "......GGGG......",
  ".......GG.......",
  "................",
  ".....nnnnnn.....",
  "....ncccccccn...",
  "....nccKccKcn...",
  "....ncccccccn...",
  "....nccccccn....",
  ".....nccccn.....",
  "....ccccccccc...",
  "...nccTTTTTccn..",
  "...ccTTTTTTccc..",
  ".cccTTTTTTTTccc.",
  "..ncTTTTTTTTcn..",
  "....cccccccc....",
  "....cc....cc....",
  "...ncc....ccn...",
];

// Pip-the-Operator — sitting at a tiny pixel workstation.
// 22 wide × 14 tall.
const OPERATOR_SPRITE = [
  "......................",
  "....CCCCCCCCCCCC......",
  "...CCCCCCCCCCCCCC.....",
  "...CCCKKCCCCKKCCC.....",
  "...CCCKKCCCCKKCCC.....",
  "...CCCCCCCCCCCCCC.....",
  "...CCCCCCCCCCCCCC.....",
  "...CCCCCCCCCCCCCC.....",
  ".XXXXXXXXXXXXXXXXXX...",
  ".XKKKKKKKKKKKKKKKKX...",
  ".XKTTTTTTTTTTTTTTKX...",
  ".XKTKTKTKTKTKTKTTKX...",
  ".XKKKKKKKKKKKKKKKKX...",
  ".XXXXXXXXXXXXXXXXXX...",
];

/* ----- A direct-render sprite helper for the inline variant grids ----- */
function RawSprite({ grid, pixel = 6, palette }) {
  const cols = grid[0].length;
  const rows = grid.length;
  const w = cols * pixel;
  const h = rows * pixel;
  const pal = palette ? { ...PIP_PALETTE, ...palette } : PIP_PALETTE;
  const rects = [];
  for (let y = 0; y < rows; y++) {
    for (let x = 0; x < cols; x++) {
      const fill = pal[grid[y][x]];
      if (!fill) continue;
      rects.push(
        <rect key={y * cols + x} x={x * pixel} y={y * pixel} width={pixel} height={pixel} fill={fill} />
      );
    }
  }
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width={w} height={h} viewBox={`0 0 ${w} ${h}`} shapeRendering="crispEdges">
      {rects}
    </svg>
  );
}

/* ----- Variant card primitive ----- */
function VariantCard({ tag, name, mood, voice, bg, surface, body, footer }) {
  return (
    <div style={{
      background: bg, borderRadius: 18, padding: 26,
      display: "flex", flexDirection: "column", gap: 14,
      height: "100%", boxSizing: "border-box", overflow: "hidden",
      fontFamily: "var(--font-sans)",
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
        <div style={{ fontSize: 10.5, fontWeight: 600, letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--color-accent)" }}>
          {tag}
        </div>
        <div style={{ fontSize: 10.5, color: "var(--color-muted)", fontFamily: "var(--font-mono)" }}>{mood}</div>
      </div>
      <div style={{
        background: surface, borderRadius: 14, padding: "32px 16px",
        display: "flex", alignItems: "center", justifyContent: "center",
        minHeight: 230,
      }}>
        {body}
      </div>
      <div>
        <h3 style={{ fontSize: 24, fontWeight: 700, margin: 0, letterSpacing: "-0.015em" }}>{name}</h3>
        <div style={{ fontSize: 13.5, color: "var(--color-muted)", marginTop: 6, lineHeight: 1.5 }}>
          {footer}
        </div>
      </div>
      {voice && (
        <div style={{
          marginTop: "auto", paddingTop: 12, borderTop: "1px dashed var(--color-border)",
          fontFamily: "var(--font-mono)", fontSize: 11.5, color: "var(--color-foreground)",
        }}>
          <span style={{ color: "var(--color-cta)", fontWeight: 600 }}>pip</span>
          <span style={{ color: "var(--color-muted)" }}>{" › "}</span>
          <span>{voice}</span>
        </div>
      )}
    </div>
  );
}

function VariantsArtboard() {
  const W = 1480, H = 720;
  return (
    <div style={{
      width: W, height: H,
      background: "var(--color-surface)",
      padding: "44px 56px",
      boxSizing: "border-box",
      fontFamily: "var(--font-sans)",
      color: "var(--color-foreground)",
      display: "flex", flexDirection: "column", gap: 22,
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
        <div>
          <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.16em", textTransform: "uppercase", color: "var(--color-accent)" }}>
            Direction options · pick a Pip
          </div>
          <h2 style={{ fontSize: 40, fontWeight: 800, letterSpacing: "-0.025em", margin: "10px 0 0", lineHeight: 1.05 }}>
            Same energy. Four expressions.
          </h2>
          <div style={{ fontSize: 14, color: "var(--color-muted)", marginTop: 8, maxWidth: 720, lineHeight: 1.5 }}>
            All four ship from the same source pixel grid — just different palettes, accessories, or fidelity.
            Pick one as canonical; keep the rest for context-specific moments (interview mode, no-color terminals, dark mode).
          </div>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 18, flex: 1 }}>

        {/* V1 — Pip Teal (canonical, brand primary) */}
        <VariantCard
          tag="V1 · Canonical"
          name="Pip · Teal"
          mood="brand-primary · trust"
          bg="var(--color-skin-50)"
          surface="#0E1620"
          voice="ready when you are."
          footer="The default. Brand teal on dark terminal. Use everywhere unless context demands otherwise."
          body={<PipIdle pixel={10} />}
        />

        {/* V2 — Sage Pip (interview prep mode) */}
        <VariantCard
          tag="V2 · Quiet room"
          name="Pip · Sage"
          mood="reflective · interview mode"
          bg="var(--color-sage-50)"
          surface="#2E3B1E"
          voice="practice run. one story at a time."
          footer="For interview prep & negotiation. Same Pip, repainted in sage — the design system's 'quiet room' palette."
          body={
            <PipSprite
              name="focus"
              pixel={10}
              palette={{ T: "#AABA85", t: "#C9D4A8", n: "#6B8346" }}
            />
          }
        />

        {/* V3 — Coral Pip (alert / urgent CTA mode) */}
        <VariantCard
          tag="V3 · Alert"
          name="Pip · Coral"
          mood="urgent · attention"
          bg="rgba(255,87,51,0.06)"
          surface="#0E1620"
          voice="deadline tomorrow. let's move."
          footer="For high-attention moments: streak alerts, application deadlines, errors needing user action. Used sparingly."
          body={
            <PipSprite
              name="surprised"
              pixel={10}
              palette={{ T: "#FF5733", t: "#FF8D71", n: "#B3341C" }}
            />
          }
        />

        {/* V4 — ASCII Pip */}
        <VariantCard
          tag="V4 · No-color fallback"
          name="Pip · ASCII"
          mood="terminals without truecolor"
          bg="#0E1620"
          surface="#151F2B"
          voice="(rendering in 16-color mode)"
          footer={<span style={{ color: "#8FA3B1" }}>
            For SSH sessions, embedded shells, CI logs. Built from box-drawing chars — ships with the CLI as a hard fallback.
          </span>}
          body={
            <pre style={{
              margin: 0,
              fontFamily: "ui-monospace, monospace",
              fontSize: 28,
              lineHeight: 1.05,
              color: "#26D4C2",
              letterSpacing: 0,
              fontWeight: 700,
              textShadow: "0 0 10px rgba(38,212,194,0.25)",
            }}>{` _________ 
|  ●   ●  |
|         |
|_________|`}</pre>
          }
        />
      </div>
    </div>
  );
}

/* ============================================================
   Future forms — beyond the CLI.
   ============================================================ */
function FutureFormsArtboard() {
  const W = 1480, H = 880;
  return (
    <div style={{
      width: W, height: H,
      background: "var(--color-background)",
      padding: "44px 56px",
      boxSizing: "border-box",
      fontFamily: "var(--font-sans)",
      color: "var(--color-foreground)",
      display: "flex", flexDirection: "column", gap: 24,
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
        <div>
          <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.16em", textTransform: "uppercase", color: "var(--color-accent)" }}>
            Future forms · phase 2 + 3
          </div>
          <h2 style={{ fontSize: 40, fontWeight: 800, letterSpacing: "-0.025em", margin: "10px 0 0", lineHeight: 1.05 }}>
            Pip travels well.
          </h2>
          <div style={{ fontSize: 14, color: "var(--color-muted)", marginTop: 8, maxWidth: 760, lineHeight: 1.5 }}>
            The same 14×10 grid scales up to a glossy dashboard companion and down to a 32×32 extension favicon.
            Personality stays intact. Pixels just get a little more polish.
          </div>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr", gap: 22, flex: 1 }}>
        <DashboardMock />
        <ExtensionMock />
      </div>
    </div>
  );
}

/* --- Dashboard-corner Pip --- */
function DashboardMock() {
  return (
    <div style={{
      background: "var(--color-surface)",
      border: "1px solid var(--color-border)",
      borderRadius: 18,
      overflow: "hidden",
      display: "flex", flexDirection: "column",
    }}>
      {/* Browser chrome */}
      <div style={{
        height: 36, background: "#F7FAFC", borderBottom: "1px solid var(--color-border)",
        display: "flex", alignItems: "center", gap: 6, padding: "0 14px",
      }}>
        <span style={{ width: 10, height: 10, borderRadius: "50%", background: "#FF5F57" }} />
        <span style={{ width: 10, height: 10, borderRadius: "50%", background: "#FEBC2E" }} />
        <span style={{ width: 10, height: 10, borderRadius: "50%", background: "#28C840" }} />
        <div style={{
          marginLeft: 14, flex: 1,
          background: "var(--color-surface)",
          border: "1px solid var(--color-border)",
          borderRadius: 6, padding: "3px 10px", fontSize: 11,
          color: "var(--color-muted)", fontFamily: "var(--font-mono)",
        }}>linkright.app/dashboard</div>
      </div>

      {/* App body */}
      <div style={{ flex: 1, padding: "26px 30px", position: "relative", background: "var(--color-background)" }}>
        {/* Top nav */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 28 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 20, fontWeight: 700, letterSpacing: "-0.01em" }}>
            <PipSprite name="idle" pixel={3} />
            <span>Link<span style={{ color: "var(--color-accent)" }}>Right</span></span>
          </div>
          <div style={{ display: "flex", gap: 18, fontSize: 13, color: "var(--color-muted)" }}>
            <span>Resumes</span><span>Scout</span><span>Interview</span>
            <span style={{ color: "var(--color-foreground)", fontWeight: 600 }}>Dashboard</span>
          </div>
        </div>

        {/* Welcome panel */}
        <div style={{
          background: "rgba(15,190,175,0.05)",
          border: "1px solid rgba(15,190,175,0.18)",
          borderRadius: 16, padding: "20px 22px",
          display: "flex", alignItems: "center", gap: 18,
        }}>
          <PipIdle pixel={5} />
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 17, fontWeight: 600, letterSpacing: "-0.01em" }}>
              Welcome back, Satvik.
            </div>
            <div style={{ fontSize: 13, color: "var(--color-muted)", marginTop: 4 }}>
              You have <strong style={{ color: "var(--color-foreground)" }}>3 JDs</strong> waiting and a resume draft from yesterday.
            </div>
          </div>
          <button style={{
            background: "var(--color-cta)", color: "white",
            border: "none", borderRadius: 9999, padding: "10px 20px",
            fontFamily: "var(--font-sans)", fontSize: 13, fontWeight: 600,
            boxShadow: "var(--shadow-cta)",
          }}>Resume yesterday</button>
        </div>

        {/* Grid of cards */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginTop: 22 }}>
          {[
            { t: "Resume builder", b: "Sync · last edited 12m ago", pip: "with_hammer" },
            { t: "Scout", b: "3 new roles match your graph", pip: "scout" },
            { t: "Interview prep", b: "Negotiation pack 70% ready", pip: "with_rupee" },
          ].map((c, i) => (
            <div key={i} style={{
              background: "var(--color-surface)",
              border: "1px solid var(--color-border)",
              borderRadius: 14, padding: 14,
            }}>
              <PipSprite name={c.pip} pixel={3} />
              <div style={{ fontSize: 14, fontWeight: 600, marginTop: 8 }}>{c.t}</div>
              <div style={{ fontSize: 11.5, color: "var(--color-muted)", marginTop: 2 }}>{c.b}</div>
            </div>
          ))}
        </div>

        {/* Floating Pip companion in bottom-right */}
        <div style={{
          position: "absolute", bottom: 22, right: 26,
          background: "var(--color-surface)",
          border: "1px solid var(--color-border)",
          borderRadius: 9999,
          boxShadow: "var(--shadow-md)",
          padding: "10px 16px 10px 12px",
          display: "flex", alignItems: "center", gap: 10,
        }}>
          <PipIdle pixel={4} />
          <div style={{ fontSize: 12, color: "var(--color-foreground)" }}>
            <span style={{ fontWeight: 600, color: "var(--color-cta)" }}>pip › </span>
            paste a JD?
          </div>
        </div>
      </div>

      <div style={{ padding: "12px 18px", background: "var(--color-skin-50)", borderTop: "1px solid var(--color-border)", fontSize: 12, color: "var(--color-muted)" }}>
        <strong style={{ color: "var(--color-foreground)" }}>Phase 2 · Dashboard.</strong> Pip lives in the nav and the welcome banner. Same idle blink. Same dialogue voice.
      </div>
    </div>
  );
}

/* --- Chrome extension Pip --- */
function ExtensionMock() {
  return (
    <div style={{
      display: "flex", flexDirection: "column", gap: 18, height: "100%",
    }}>
      {/* JD page mock with extension popup */}
      <div style={{
        flex: 1,
        background: "var(--color-surface)",
        border: "1px solid var(--color-border)",
        borderRadius: 18,
        position: "relative",
        overflow: "hidden",
      }}>
        {/* fake page content */}
        <div style={{ padding: "20px 24px" }}>
          <div style={{ fontSize: 11, color: "var(--color-muted)", marginBottom: 8 }}>linkedin.com/jobs/3892...</div>
          <div style={{ fontSize: 17, fontWeight: 700, letterSpacing: "-0.01em" }}>Senior Product Manager · AI</div>
          <div style={{ fontSize: 12, color: "var(--color-muted)", marginTop: 4 }}>Google · Bengaluru</div>
          <div style={{ marginTop: 16, display: "flex", flexDirection: "column", gap: 6 }}>
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} style={{
                height: i === 0 ? 8 : 6,
                background: "var(--color-border)",
                borderRadius: 3,
                width: `${85 - (i % 4) * 8}%`,
              }} />
            ))}
          </div>
        </div>

        {/* extension popup */}
        <div style={{
          position: "absolute", top: 16, right: 16,
          width: 240,
          background: "#0E1620",
          color: "#EEF5F2",
          borderRadius: 14,
          padding: "14px 16px",
          boxShadow: "0 20px 40px rgba(15,23,42,0.25)",
          border: "1px solid #253140",
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
            <PipSprite name="with_magnifier" pixel={4} />
            <div style={{ fontSize: 11, color: "#8FA3B1" }}>pip in your browser</div>
          </div>
          <div style={{ fontSize: 12.5, lineHeight: 1.5 }}>
            <span style={{ color: "#FF8D71", fontWeight: 600 }}>pip › </span>
            I've parsed this JD. <span style={{ color: "#26D4C2" }}>78% match</span> with your strongest resume.
          </div>
          <div style={{ display: "flex", gap: 6, marginTop: 12 }}>
            <button style={{
              background: "#FF5733", color: "white", border: "none",
              borderRadius: 9999, padding: "6px 12px", fontSize: 11, fontWeight: 600,
            }}>Tailor →</button>
            <button style={{
              background: "transparent", color: "#8FA3B1", border: "1px solid #253140",
              borderRadius: 9999, padding: "6px 12px", fontSize: 11,
            }}>Save</button>
          </div>
        </div>
      </div>

      {/* Favicon strip */}
      <div style={{
        background: "var(--color-surface)",
        border: "1px solid var(--color-border)",
        borderRadius: 18, padding: 18,
      }}>
        <div style={{ fontSize: 10.5, fontWeight: 600, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--color-muted)", marginBottom: 12 }}>
          Tiny Pips — favicon scales
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
          {[1, 2, 3, 4].map((p) => (
            <div key={p} style={{
              width: 44, height: 44, borderRadius: 10,
              background: "#0E1620",
              display: "flex", alignItems: "center", justifyContent: "center",
            }}>
              <PipSprite name="idle" pixel={p} />
            </div>
          ))}
          <div style={{ flex: 1, fontSize: 11.5, color: "var(--color-muted)", marginLeft: 8, lineHeight: 1.5 }}>
            16, 32, 48, 64 px favicons. Same sprite, no asset variants needed.
          </div>
        </div>
      </div>

      <div style={{ padding: "12px 18px", background: "var(--color-skin-50)", borderTop: "1px solid var(--color-border)", fontSize: 12, color: "var(--color-muted)", borderRadius: 12 }}>
        <strong style={{ color: "var(--color-foreground)" }}>Phase 4 · Browser ambient.</strong> Pip parses the JD in-page, suggests the matching resume, and disappears.
      </div>
    </div>
  );
}

Object.assign(window, { VariantsArtboard, FutureFormsArtboard });
