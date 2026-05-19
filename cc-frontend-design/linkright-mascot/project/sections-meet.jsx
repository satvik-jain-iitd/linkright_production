/* =========================================================================
   sections-meet.jsx — character bible.
   Persona card, anatomy / sprite card, and voice / dialogue catalog.
   ========================================================================= */

/* ----- Persona card ----- */
function PersonaArtboard() {
  const W = 720, H = 880;
  const facts = [
    ["Name",        <>Pip<span style={{ color: "var(--color-muted)", fontWeight: 400 }}> · /pɪp/</span></>],
    ["Born",        "in a terminal, beside LINKRIGHT v0.9"],
    ["Lives in",    "~/.linkright/, between your prompts"],
    ["Job",         "small operator. ships beside you."],
    ["Carries",     "a hammer, a magnifier, a tiny gold star"],
  ];
  return (
    <div
      style={{
        width: W, height: H,
        background: "var(--color-surface)",
        fontFamily: "var(--font-sans)",
        color: "var(--color-foreground)",
        padding: "44px 48px",
        boxSizing: "border-box",
        display: "flex", flexDirection: "column", gap: 24,
        position: "relative", overflow: "hidden",
      }}
    >
      <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.16em", textTransform: "uppercase", color: "var(--color-accent)" }}>
        Character · 01
      </div>
      <div style={{ display: "flex", alignItems: "flex-end", gap: 28 }}>
        <div style={{ background: "#0E1620", padding: 20, borderRadius: 12, lineHeight: 0 }}>
          <PipIdle pixel={14} />
        </div>
        <div>
          <h2 style={{ fontSize: 56, fontWeight: 800, letterSpacing: "-0.03em", margin: 0, lineHeight: 1 }}>
            Pip.
          </h2>
          <div style={{ fontSize: 18, color: "var(--color-muted)", marginTop: 8, fontWeight: 500 }}>
            Career-build copilot.<br />
            <span style={{ color: "var(--color-cta)" }}>14×10</span> pixels of intent.
          </div>
        </div>
      </div>

      {/* Quick facts list */}
      <div style={{ marginTop: 4 }}>
        {facts.map(([k, v]) => (
          <div key={k} style={{ display: "grid", gridTemplateColumns: "120px 1fr", borderTop: "1px solid var(--color-border)", padding: "12px 0", fontSize: 14 }}>
            <span style={{ color: "var(--color-muted)", fontFamily: "var(--font-mono)", fontSize: 12, paddingTop: 2 }}>{k}</span>
            <span style={{ color: "var(--color-foreground)", fontWeight: 500 }}>{v}</span>
          </div>
        ))}
      </div>

      {/* Believes / Refuses */}
      <div style={{ marginTop: 8, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 18 }}>
        <div style={{ padding: 18, background: "rgba(15,190,175,0.06)", border: "1px solid rgba(15,190,175,0.18)", borderRadius: 14 }}>
          <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--color-accent)", marginBottom: 8 }}>
            Believes
          </div>
          <ul style={{ margin: 0, padding: "0 0 0 16px", color: "var(--color-foreground)", fontSize: 13.5, lineHeight: 1.6 }}>
            <li>Evidence over claims.</li>
            <li>Width over poetry.</li>
            <li>One page, every time.</li>
            <li>Ship, then iterate.</li>
          </ul>
        </div>
        <div style={{ padding: 18, background: "rgba(255,87,51,0.05)", border: "1px solid rgba(255,87,51,0.18)", borderRadius: 14 }}>
          <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--color-cta)", marginBottom: 8 }}>
            Won't do
          </div>
          <ul style={{ margin: 0, padding: "0 0 0 16px", color: "var(--color-foreground)", fontSize: 13.5, lineHeight: 1.6 }}>
            <li>Invent your metrics.</li>
            <li>Use "leveraged."</li>
            <li>Pretend to be human.</li>
            <li>Auto-submit anything.</li>
          </ul>
        </div>
      </div>

      {/* The reach-quote at bottom */}
      <div style={{ marginTop: "auto", paddingTop: 18, borderTop: "1px solid var(--color-border)", display: "flex", alignItems: "center", gap: 16 }}>
        <PipSprite name="reaching" pixel={6} />
        <div style={{ fontSize: 14, color: "var(--color-muted)", fontStyle: "italic", lineHeight: 1.45 }}>
          "I'm small. I climb anyway."<br />
          <span style={{ fontSize: 11, fontStyle: "normal", letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--color-cta)" }}>— Pip, on the logo</span>
        </div>
      </div>
    </div>
  );
}

/* ----- Anatomy card — sprite breakdown ----- */
function AnatomyArtboard() {
  const W = 720, H = 880;

  // a 1-pixel-wide-bigger reference rendering with overlay annotations
  const SPRITE_PX = 22;
  const COLS = 14, ROWS = 10;

  // axis labels — we draw a thin guide rule around the sprite
  return (
    <div
      style={{
        width: W, height: H,
        background: "var(--color-skin-50)",
        fontFamily: "var(--font-sans)",
        color: "var(--color-foreground)",
        padding: "44px 48px",
        boxSizing: "border-box",
        display: "flex", flexDirection: "column", gap: 18,
        position: "relative", overflow: "hidden",
      }}
    >
      <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.16em", textTransform: "uppercase", color: "var(--color-accent)" }}>
        Character · 02
      </div>

      <h2 style={{ fontSize: 38, fontWeight: 800, letterSpacing: "-0.025em", margin: 0, lineHeight: 1.05 }}>
        Anatomy of a small operator.
      </h2>
      <div style={{ fontSize: 14, color: "var(--color-muted)", marginTop: -8 }}>
        One sprite, twenty-two states, four colors. Single source of truth.
      </div>

      {/* Big sprite with measurement overlay */}
      <div style={{ display: "flex", justifyContent: "center", padding: "20px 0 8px", position: "relative" }}>
        <div style={{ position: "relative" }}>
          {/* Top measurement: 14 px */}
          <div style={{
            position: "absolute", top: -22, left: 0, right: 0,
            display: "flex", justifyContent: "space-between", alignItems: "center",
            color: "var(--color-cta)", fontFamily: "var(--font-mono)", fontSize: 11,
          }}>
            <span>├</span>
            <span style={{ fontWeight: 600 }}>14 px</span>
            <span>┤</span>
          </div>
          {/* Right measurement */}
          <div style={{
            position: "absolute", right: -38, top: 0, bottom: 0,
            display: "flex", flexDirection: "column", justifyContent: "space-between", alignItems: "center",
            color: "var(--color-cta)", fontFamily: "var(--font-mono)", fontSize: 11,
          }}>
            <span>┬</span>
            <span style={{ fontWeight: 600, writingMode: "vertical-rl" }}>10 px</span>
            <span>┴</span>
          </div>
          <div style={{
            background: "#0E1620", padding: 4, borderRadius: 6,
            outline: "1px dashed rgba(255,87,51,0.4)", outlineOffset: 8,
          }}>
            <PipSprite name="idle" pixel={SPRITE_PX} />
          </div>
        </div>
      </div>

      {/* Palette swatches */}
      <div style={{ marginTop: 12 }}>
        <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--color-muted)", marginBottom: 10 }}>
          Palette · 8 inks (4 functional + 4 materials)
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8 }}>
          {[
            { name: "Teal 500",   hex: "#0FBEAF", token: "primary-500",   role: "body"   },
            { name: "Pip black",  hex: "#000000", token: "true-black",    role: "eyes"   },
            { name: "Gold 500",   hex: "#E5B80B", token: "gold-500",      role: "star · success" },
            { name: "Coral 500",  hex: "#FF5733", token: "secondary-500", role: "alert · sparks" },
            { name: "Silver",     hex: "#DCE5EA", token: "silver",        role: "tools" },
            { name: "Cream",      hex: "#FDF6F0", token: "skin-50",       role: "paper · coffee" },
            { name: "Purple 500", hex: "#8B5CF6", token: "tertiary-500",  role: "AI aura"},
            { name: "Pink 500",   hex: "#F05A79", token: "pink-500",      role: "scout · human" },
          ].map((c) => (
            <div key={c.hex} style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: 10, padding: 10 }}>
              <div style={{ width: "100%", height: 24, background: c.hex, borderRadius: 5, marginBottom: 8, border: c.hex === "#FDF6F0" || c.hex === "#DCE5EA" ? "1px solid var(--color-border)" : "none" }} />
              <div style={{ fontSize: 11, fontWeight: 600 }}>{c.name}</div>
              <div style={{ fontSize: 9.5, fontFamily: "var(--font-mono)", color: "var(--color-muted)" }}>{c.hex}</div>
              <div style={{ fontSize: 9.5, color: "var(--color-cta)", marginTop: 2, fontWeight: 500 }}>· {c.role}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Render targets — scale ladder */}
      <div style={{ marginTop: 18 }}>
        <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--color-muted)", marginBottom: 10 }}>
          Scales · 6 px → 96 px (CLI to hero)
        </div>
        <div style={{
          display: "flex", alignItems: "flex-end", gap: 18, padding: "16px 14px",
          background: "#0E1620", borderRadius: 12,
        }}>
          {[1, 2, 3, 5, 8].map((p, i) => (
            <div key={i} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 8 }}>
              <PipSprite name="idle" pixel={p} />
              <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "#8FA3B1" }}>{p * 14}px</span>
            </div>
          ))}
          <div style={{ flex: 1, textAlign: "right", color: "#5A6B7C", fontSize: 11, fontFamily: "var(--font-mono)", lineHeight: 1.5 }}>
            stays crisp on<br />
            any monitor or<br />
            terminal cell.
          </div>
        </div>
      </div>
    </div>
  );
}

/* ----- Voice / dialogue catalog ----- */
function VoiceArtboard() {
  const W = 1480, H = 720;

  const groups = [
    {
      label: "Boot · idle",
      tint: "var(--color-accent)",
      lines: [
        "ready when you are.",
        "JD, resume, or a fresh opportunity — your call.",
        "no AI fluff today. just the work.",
      ],
    },
    {
      label: "Reading the JD",
      tint: "var(--color-tertiary-500)",
      lines: [
        "reading the JD. one sec.",
        "found 7 signals. mapping to your evidence.",
        "this one wants 'shipped,' not 'led.'",
      ],
    },
    {
      label: "Building the resume",
      tint: "var(--color-gold-500)",
      lines: [
        "filling 97% width. tight.",
        "swapping in 'shipped' for 'leveraged.'",
        "three rewrites — best one wins.",
        "0 AI words. checked twice.",
      ],
    },
    {
      label: "Shipping",
      tint: "var(--color-primary-500)",
      lines: [
        "done. 14 bullets, single page.",
        "looks defensible. ship it.",
        "first resume's on the house.",
      ],
    },
    {
      label: "Blocked · retry",
      tint: "var(--color-cta)",
      lines: [
        "JD's empty. paste it again?",
        "ran out of evidence for that bullet. add a story?",
        "tried, didn't beat the baseline. keeping the old one.",
      ],
    },
    {
      label: "Refusal · anti-slop",
      tint: "var(--color-pink-500)",
      lines: [
        "I won't make up that metric. give me the number.",
        "can't say 'Staff' — not in your history yet.",
        "this bullet's good. it's just yours, not mine.",
      ],
    },
  ];

  return (
    <div
      style={{
        width: W, height: H,
        background: "var(--color-surface)",
        fontFamily: "var(--font-sans)",
        color: "var(--color-foreground)",
        padding: "44px 56px",
        boxSizing: "border-box",
        position: "relative", overflow: "hidden",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24 }}>
        <div>
          <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.16em", textTransform: "uppercase", color: "var(--color-accent)" }}>
            Voice · How Pip talks
          </div>
          <h2 style={{ fontSize: 44, fontWeight: 800, letterSpacing: "-0.025em", margin: "12px 0 0", lineHeight: 1.05 }}>
            Short sentences. Specific numbers. <span style={{ color: "var(--color-muted)" }}>No fluff.</span>
          </h2>
        </div>
        <div style={{ display: "flex", alignItems: "flex-end", gap: 16, fontSize: 12, color: "var(--color-muted)", fontFamily: "var(--font-mono)" }}>
          <div style={{ textAlign: "right" }}>
            never: "leveraged" · "empowered" · "unleashed"<br />
            never: emoji as decoration · ALL CAPS · 3+ commas
          </div>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 22 }}>
        {groups.map((g) => (
          <div key={g.label} style={{ padding: 22, background: "var(--color-skin-50)", border: "1px solid var(--color-border)", borderRadius: 16 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 14 }}>
              <span style={{ width: 8, height: 8, borderRadius: "50%", background: g.tint }} />
              <span style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.12em", textTransform: "uppercase", color: g.tint }}>
                {g.label}
              </span>
            </div>
            <ul style={{ margin: 0, padding: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: 10 }}>
              {g.lines.map((l, i) => (
                <li key={i} style={{ display: "flex", gap: 8, fontSize: 13.5, lineHeight: 1.5 }}>
                  <span style={{ color: g.tint, fontFamily: "var(--font-mono)", fontWeight: 600, flexShrink: 0 }}>{">"}</span>
                  <span>{l}</span>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}

Object.assign(window, { PersonaArtboard, AnatomyArtboard, VoiceArtboard });
