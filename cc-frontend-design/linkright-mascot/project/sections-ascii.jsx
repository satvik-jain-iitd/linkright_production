/* =========================================================================
   sections-ascii.jsx — the ASCII direction.

   Pitch: Pip is a string. A pose is 4 lines of characters. Maintainable
   forever; renders in any terminal, any editor, any code review.

   Five artboards:
   - Hero: pitch + big ASCII Pip + the maintenance argument
   - Pose grid: all 18 ASCII poses
   - Terminal scene: ASCII Pip beside LINKRIGHT
   - Maintenance: blob code vs ASCII code, side by side
   - Three-way compare: ASCII vs blob vs stickman at same workflow states
   ========================================================================= */

/* ---------- Hero / pitch ---------- */
function AsciiHeroArtboard() {
  const W = 1480, H = 880;
  return (
    <div style={{
      width: W, height: H,
      background: "#0E1620",
      backgroundImage: "radial-gradient(ellipse at 75% 20%, rgba(15,190,175,0.12) 0%, transparent 55%)",
      padding: "44px 56px",
      boxSizing: "border-box",
      fontFamily: "var(--font-sans)",
      color: "#EEF5F2",
      position: "relative", overflow: "hidden",
      display: "flex", flexDirection: "column",
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 48 }}>
        <div style={{ maxWidth: 760 }}>
          <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.16em", textTransform: "uppercase", color: "#26D4C2" }}>
            New direction · pip as a string
          </div>
          <h1 style={{ fontSize: 80, fontWeight: 800, letterSpacing: "-0.035em", margin: "16px 0 0", lineHeight: 0.98, color: "#EEF5F2" }}>
            Pip is <span style={{ color: "#26D4C2" }}>11 characters</span>.
          </h1>
          <div style={{ fontSize: 17, color: "#8FA3B1", marginTop: 18, lineHeight: 1.55, maxWidth: 640 }}>
            No SVG. No sprite sheet. No palette system. Pip is a four-line monospace string. To add a new behaviour,
            a developer types four lines of characters and commits. Forever maintainable.
          </div>

          {/* Code-as-mascot evidence */}
          <div style={{
            marginTop: 28, padding: "20px 22px",
            background: "#151F2B", borderRadius: 12,
            border: "1px solid #253140",
            fontFamily: "var(--font-mono)", fontSize: 14,
          }}>
            <div style={{ color: "#5A6B7C", fontSize: 11 }}># pip/ascii.py</div>
            <div style={{ color: "#26D4C2", marginTop: 6 }}>
              <span style={{ color: "#8FA3B1" }}>idle = </span>
              <span style={{ color: "#FF8D71" }}>"""</span>
            </div>
            <div style={{ color: "#26D4C2", whiteSpace: "pre", marginLeft: 0 }}>┌───┐
│• •│
└───┘</div>
            <div style={{ color: "#FF8D71" }}>"""</div>
            <div style={{ color: "#5A6B7C", marginTop: 10, fontSize: 11 }}># that's the whole mascot file.</div>
          </div>
        </div>

        {/* Big animated ASCII Pip */}
        <div style={{
          flex: 1,
          background: "linear-gradient(135deg, rgba(15,190,175,0.08), rgba(139,92,246,0.05))",
          borderRadius: 24,
          border: "1px solid #253140",
          display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
          padding: "40px 20px",
          gap: 24, minHeight: 540,
        }}>
          <AsciiIdle size={96} />
          <div style={{
            fontFamily: "var(--font-mono)", fontSize: 13, color: "#8FA3B1",
            paddingTop: 16, borderTop: "1px dashed #253140", textAlign: "center",
            width: "100%",
          }}>
            <span style={{ color: "#FF8D71", fontWeight: 600 }}>pip ›</span> ready when you are.
          </div>
        </div>
      </div>

      {/* Three reasons strip */}
      <div style={{
        marginTop: "auto",
        display: "grid",
        gridTemplateColumns: "repeat(3, 1fr)",
        gap: 28,
        paddingTop: 36,
      }}>
        {[
          {
            num: "01",
            title: "Maintainable forever.",
            body: "A new behaviour is 4 lines of string in source code. Anyone on the team can add one in under 30 seconds. No design tools needed.",
          },
          {
            num: "02",
            title: "Terminal-native.",
            body: "ASCII renders at full fidelity in every terminal ever made. SSH, CI logs, tmux, your friend's vintage Linux box — Pip shows up the same everywhere.",
          },
          {
            num: "03",
            title: "Builder-honest.",
            body: "ASCII is the most LinkRight-voice form possible: terse, evidence-led, anti-fluff, anti-AI-slop. The product, made of itself.",
          },
        ].map((p) => (
          <div key={p.num} style={{
            borderTop: "2px solid #26D4C2",
            paddingTop: 14,
          }}>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "#FF8D71", fontWeight: 600, letterSpacing: "0.08em" }}>
              {p.num}
            </div>
            <div style={{ fontSize: 19, fontWeight: 700, marginTop: 6, letterSpacing: "-0.01em", color: "#EEF5F2" }}>
              {p.title}
            </div>
            <div style={{ fontSize: 13, color: "#8FA3B1", marginTop: 8, lineHeight: 1.55 }}>
              {p.body}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ---------- Pose grid ---------- */
function AsciiPosesArtboard() {
  const W = 1480, H = 880;

  const poses = [
    { name: "idle",         caption: "boot / standing by" },
    { name: "blink",        caption: "every ~4s" },
    { name: "happy",        caption: "after a successful ship" },
    { name: "surprised",    caption: "unexpected match found" },
    { name: "flat",         caption: "blocked, no judgement" },
    { name: "focus",        caption: "deep work mode" },
    { name: "wave",         caption: "welcome back" },
    { name: "with_star",    caption: "resume shipped" },
    { name: "reaching",     caption: "climb · logo callback" },
    { name: "reading_jd",   caption: "parsing JD" },
    { name: "building",     caption: "tailoring resume" },
    { name: "ai_thinking",  caption: "LLM in the loop" },
    { name: "coffee",       caption: "scanning 12 boards" },
    { name: "sleep",        caption: "no activity" },
    { name: "retry",        caption: "asking for input" },
    { name: "interview",    caption: "story bank · prep" },
    { name: "negotiating",  caption: "weighing tradeoffs" },
    { name: "applying",     caption: "sending apps · momentum" },
  ];

  return (
    <div style={{
      width: W, height: H,
      background: "var(--color-surface)",
      padding: "44px 56px",
      boxSizing: "border-box",
      fontFamily: "var(--font-sans)",
      color: "var(--color-foreground)",
      display: "flex", flexDirection: "column", gap: 24,
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
        <div>
          <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.16em", textTransform: "uppercase", color: "var(--color-accent)" }}>
            Pose grid · 18 states · all strings
          </div>
          <h2 style={{ fontSize: 40, fontWeight: 800, letterSpacing: "-0.025em", margin: "10px 0 0", lineHeight: 1.05 }}>
            Eighteen behaviours, all in characters.
          </h2>
          <div style={{ fontSize: 14, color: "var(--color-muted)", marginTop: 8, maxWidth: 760, lineHeight: 1.5 }}>
            Color accents per character (gold ★ for success, silver ⊙ for tools, purple ✦ for AI) — same color system as the blob, just applied to glyphs.
          </div>
        </div>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--color-muted)", textAlign: "right", lineHeight: 1.5 }}>
          chars used: ┌ ─ ┐ │ └ ┘ ╨ ╔ ═ ╗ ╲ ╱<br />
          ★ ✦ ⊙ ₹ ~ ≈ • ^ ⌣ &lt; &gt; - O o
        </div>
      </div>

      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(6, 1fr)",
        gap: 14,
        flex: 1,
      }}>
        {poses.map((p) => (
          <div key={p.name} style={{
            background: "#0E1620",
            borderRadius: 12,
            padding: "16px 12px 14px",
            display: "flex", flexDirection: "column", alignItems: "center", gap: 10,
            border: "1px solid #253140",
            minHeight: 0,
          }}>
            <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", width: "100%", minHeight: 80 }}>
              <AsciiPip pose={p.name} size={22} weight={700} />
            </div>
            <div style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "#26D4C2", fontWeight: 600 }}>
              {p.name}
            </div>
            <div style={{ fontSize: 10, color: "#8FA3B1", textAlign: "center", lineHeight: 1.3 }}>
              {p.caption}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ---------- Terminal scene — ASCII Pip beside LINKRIGHT ---------- */
function AsciiTerminalArtboard() {
  const W = 1480, H = 640;
  return (
    <div style={{
      width: W, height: H,
      background: "var(--color-skin-50)",
      padding: "44px 56px",
      boxSizing: "border-box",
      fontFamily: "var(--font-sans)",
      color: "var(--color-foreground)",
      display: "flex", flexDirection: "column", gap: 22,
    }}>
      <div>
        <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.16em", textTransform: "uppercase", color: "var(--color-accent)" }}>
          ASCII Pip · in the CLI banner
        </div>
        <h2 style={{ fontSize: 38, fontWeight: 800, letterSpacing: "-0.025em", margin: "10px 0 0", lineHeight: 1.05 }}>
          Same banner. Same line. Six characters of personality.
        </h2>
      </div>

      <TerminalChrome>
        <Prompt><span style={{ marginLeft: 4 }}>linkright</span></Prompt>

        <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", gap: 28, padding: "30px 0 10px 8px" }}>
          <LinkrightBanner pixel={11} gap={6} />
          <div style={{ paddingBottom: 4 }}>
            <AsciiIdle size={36} />
          </div>
        </div>

        <div style={{ marginTop: 6, marginLeft: 8 }}>
          <Line icon="◆">
            <strong style={{ color: "#EEF5F2" }}>Your local-first career OS</strong>
            <Dim>{" · "}</Dim>
            <Gold>$0 to run</Gold>
          </Line>
          <div style={{ marginLeft: 16, color: "#E5B80B", fontSize: 12, marginTop: 2 }}>v0.9.2</div>
        </div>

        <div style={{ marginTop: 16, marginLeft: 8, fontSize: 13, color: "#8FA3B1" }}>
          <span style={{ color: "#FF8D71", fontWeight: 600 }}>pip</span>
          <span style={{ color: "#5A6B7C" }}>{" › "}</span>
          <span style={{ color: "#EEF5F2" }}>ready when you are. </span>
          <Dim>JD, resume, or a fresh opportunity — your call.</Dim>
        </div>
        <div style={{ marginTop: 14 }}>
          <Prompt><Cursor /></Prompt>
        </div>
      </TerminalChrome>
    </div>
  );
}

/* ---------- Maintainability comparison — blob code vs ASCII code ---------- */
function AsciiMaintenanceArtboard() {
  const W = 1480, H = 880;

  return (
    <div style={{
      width: W, height: H,
      background: "var(--color-background)",
      padding: "44px 56px",
      boxSizing: "border-box",
      fontFamily: "var(--font-sans)",
      color: "var(--color-foreground)",
      display: "flex", flexDirection: "column", gap: 22,
    }}>
      <div>
        <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.16em", textTransform: "uppercase", color: "var(--color-cta)" }}>
          Maintenance · the cost of adding ONE new state
        </div>
        <h2 style={{ fontSize: 40, fontWeight: 800, letterSpacing: "-0.025em", margin: "10px 0 0", lineHeight: 1.05 }}>
          Want a new behaviour? Here's what you write.
        </h2>
        <div style={{ fontSize: 14, color: "var(--color-muted)", marginTop: 8, maxWidth: 880, lineHeight: 1.5 }}>
          Same imagined state: <strong>Pip making coffee on a long-running task</strong>. Compare what each direction asks of the developer.
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 22, flex: 1 }}>

        {/* BLOB SIDE */}
        <div style={{
          background: "var(--color-surface)",
          border: "1px solid var(--color-border)",
          borderRadius: 16,
          padding: "22px 24px",
          display: "flex", flexDirection: "column", gap: 16,
          overflow: "hidden",
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
            <div style={{ fontSize: 14, fontWeight: 700, letterSpacing: "-0.01em" }}>Blob direction</div>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--color-cta)" }}>
              ~24 lines · 24×16 grid · palette system
            </div>
          </div>
          <pre style={{
            margin: 0, flex: 1, overflow: "auto",
            background: "#0E1620", color: "#EEF5F2",
            fontFamily: "var(--font-mono)", fontSize: 11.5, lineHeight: 1.55,
            padding: "16px 18px", borderRadius: 10,
            border: "1px solid #253140",
          }}>{`with_coffee: [
  "...............W........",
  "..............W.W.......",
  "...............W........",
  "..............WW........",
  "..............LLLLM.....",
  ".............LBBBBLM....",
  ".............LBBBBLM....",
  ".............LLLLLLM....",
  "......TTTTTTTTLLLL......",
  "......TtTTTTTTTTTT......",
  "......TTKKTTTTKKTTT.....",
  "......TTKKTTTTKKTTT.....",
  "......TTTTTTTTTTTTT.....",
  "......TTTTTTTTTTTT......",
  ".......TTTTTTTTTT.......",
  "........TTTTTTTT........",
],
// + understand the palette legend (T, t, K, W, L, B, M…)
// + render via SVG <rect> grid
// + design feedback loop
`}</pre>
          <div style={{ display: "flex", alignItems: "center", gap: 16, padding: "12px 14px", background: "rgba(255,87,51,0.06)", borderRadius: 10, border: "1px solid rgba(255,87,51,0.18)" }}>
            <PipSprite name="with_coffee" pixel={4} />
            <div style={{ fontSize: 12.5, color: "var(--color-foreground)" }}>
              <strong style={{ color: "var(--color-cta)" }}>Cost:</strong> 384 pixel slots to position, 8 colors to coordinate, ~20 minutes of pixel-pushing per new state.
            </div>
          </div>
        </div>

        {/* ASCII SIDE */}
        <div style={{
          background: "var(--color-surface)",
          border: "1.5px solid var(--color-accent)",
          borderRadius: 16,
          padding: "22px 24px",
          display: "flex", flexDirection: "column", gap: 16,
          overflow: "hidden",
          boxShadow: "0 12px 32px rgba(15,190,175,0.10)",
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
            <div style={{ fontSize: 14, fontWeight: 700, letterSpacing: "-0.01em" }}>ASCII direction</div>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--color-accent)" }}>
              5 lines · zero deps · plain string
            </div>
          </div>
          <pre style={{
            margin: 0, flex: 1, overflow: "auto",
            background: "#0E1620", color: "#EEF5F2",
            fontFamily: "var(--font-mono)", fontSize: 13, lineHeight: 1.7,
            padding: "16px 18px", borderRadius: 10,
            border: "1px solid #253140",
          }}>{`coffee = """
     ~
     ~
┌───┐ ┌─┐
│• •│ │═│
└───┘ └─┘
"""
# done. ship it.`}</pre>
          <div style={{ display: "flex", alignItems: "center", gap: 16, padding: "12px 14px", background: "rgba(15,190,175,0.08)", borderRadius: 10, border: "1px solid rgba(15,190,175,0.25)" }}>
            <AsciiPip pose="coffee" size={18} glow={false} />
            <div style={{ fontSize: 12.5, color: "var(--color-foreground)" }}>
              <strong style={{ color: "var(--color-accent)" }}>Cost:</strong> 30 seconds. A junior dev can add states. New PMs can suggest them. Reviewable in any chat tool.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ---------- Three-way comparison — ASCII vs blob vs stickman ---------- */
function AsciiComparisonArtboard() {
  const W = 1480, H = 980;

  const states = [
    { label: "Idle",           ascii: "idle",       blob: "idle",          stick: "idle" },
    { label: "Reading the JD", ascii: "reading_jd", blob: "with_magnifier",stick: "reading_jd" },
    { label: "Building",       ascii: "building",   blob: "with_hammer",   stick: "building" },
    { label: "AI generating",  ascii: "ai_thinking",blob: "ai_aura",       stick: "ai_thinking" },
    { label: "Shipped",        ascii: "with_star",  blob: "with_star",     stick: "success" },
    { label: "Long task",      ascii: "coffee",     blob: "with_coffee",   stick: "coffee" },
  ];

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
      <div>
        <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.16em", textTransform: "uppercase", color: "var(--color-accent)" }}>
          Three directions · same six moments
        </div>
        <h2 style={{ fontSize: 40, fontWeight: 800, letterSpacing: "-0.025em", margin: "10px 0 0", lineHeight: 1.05 }}>
          Pick a winner.
        </h2>
        <div style={{ fontSize: 14, color: "var(--color-muted)", marginTop: 8, maxWidth: 760, lineHeight: 1.5 }}>
          Each row is the same workflow moment rendered in all three directions. Look at first-glance clarity, maintainability, and brand fit.
        </div>
      </div>

      {/* Header */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "180px repeat(3, 1fr)",
        gap: 14,
        padding: "10px 0",
        borderBottom: "1px solid var(--color-border)",
      }}>
        <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--color-muted)" }}>State</div>
        <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--color-accent)", textAlign: "center" }}>ASCII (new)</div>
        <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--color-muted)", textAlign: "center" }}>Pixel blob (v2)</div>
        <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--color-muted)", textAlign: "center" }}>Stickman</div>
      </div>

      {/* Rows */}
      <div style={{ flex: 1, display: "grid", gridTemplateRows: "repeat(6, 1fr)", gap: 0 }}>
        {states.map((s, i) => (
          <div key={s.label} style={{
            display: "grid",
            gridTemplateColumns: "180px repeat(3, 1fr)",
            gap: 14,
            alignItems: "center",
            borderBottom: i < states.length - 1 ? "1px solid var(--color-border)" : "none",
            padding: "8px 0",
          }}>
            <div style={{ fontSize: 13, fontWeight: 600 }}>{s.label}</div>

            <div style={{ background: "#0E1620", borderRadius: 10, border: "1.5px solid rgba(15,190,175,0.4)", padding: "14px 8px", display: "flex", alignItems: "center", justifyContent: "center", minHeight: 88 }}>
              <AsciiPip pose={s.ascii} size={16} />
            </div>

            <div style={{ background: "#0E1620", borderRadius: 10, border: "1px solid #253140", padding: "14px 8px", display: "flex", alignItems: "center", justifyContent: "center", minHeight: 88 }}>
              <PipSprite name={s.blob} pixel={4} />
            </div>

            <div style={{ background: "var(--color-skin-50)", borderRadius: 10, border: "1px solid var(--color-border)", padding: "14px 8px", display: "flex", alignItems: "center", justifyContent: "center", minHeight: 88 }}>
              <Stickman pose={s.stick} size={80} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

Object.assign(window, {
  AsciiHeroArtboard,
  AsciiPosesArtboard,
  AsciiTerminalArtboard,
  AsciiMaintenanceArtboard,
  AsciiComparisonArtboard,
});
