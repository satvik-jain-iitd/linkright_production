/* =========================================================================
   sections-future.jsx — where ASCII Pip lives beyond the CLI.
   Pip in: IDE status bar · git hooks · Chrome extension · web dashboard ·
   weekly digest email · Slack status · README badge · 404 page.
   Same 4-line string, every surface.
   ========================================================================= */

/* ---------- Character bible (ASCII edition) ---------- */
function AsciiCharacterBibleArtboard() {
  return (
    <div style={{
      width: "100%", height: "100%",
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
            Character bible · ASCII edition
          </div>
          <h2 style={{ fontSize: 40, fontWeight: 800, letterSpacing: "-0.025em", margin: "10px 0 0", lineHeight: 1.05 }}>
            Pip, on one page.
          </h2>
        </div>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--color-muted)", textAlign: "right", lineHeight: 1.5 }}>
          name: Pip<br />
          form: 4-line string<br />
          age: terminal-old
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "320px 1fr 1fr", gap: 18, flex: 1, minHeight: 0 }}>
        {/* Big specimen */}
        <div style={{
          background: "#0E1620",
          borderRadius: 14,
          border: "1px solid #253140",
          padding: 28,
          display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "space-between",
        }}>
          <div style={{ fontSize: 10, fontFamily: "var(--font-mono)", color: "#8E8E93", letterSpacing: "0.16em" }}>SPECIMEN</div>
          <AsciiIdle size={72} />
          <div style={{ textAlign: "center", fontFamily: "var(--font-mono)", fontSize: 11, color: "#8FA3B1", lineHeight: 1.5 }}>
            ┌───┐<br />│• •│<br />└───┘
          </div>
          <div style={{ borderTop: "1px dashed #253140", paddingTop: 12, width: "100%", textAlign: "center" }}>
            <div style={{ color: "#FF8D71", fontSize: 11, fontWeight: 600, fontFamily: "var(--font-mono)" }}>pip ›</div>
            <div style={{ color: "#EEF5F2", fontSize: 12, fontFamily: "var(--font-mono)", marginTop: 4 }}>ready when you are.</div>
          </div>
        </div>

        {/* Persona */}
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div>
            <div style={{ fontSize: 10.5, fontWeight: 600, letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--color-accent)" }}>
              Persona
            </div>
            <h3 style={{ fontSize: 22, fontWeight: 700, letterSpacing: "-0.015em", marginTop: 8 }}>The patient operator-engineer.</h3>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "100px 1fr", rowGap: 10, fontSize: 13, lineHeight: 1.55 }}>
            <div style={{ color: "var(--color-muted)" }}>Voice</div>
            <div>Terse. Evidence-led. Lowercase. Never excited about itself.</div>
            <div style={{ color: "var(--color-muted)" }}>Does</div>
            <div>blinks, reads the JD, hammers bullets, grabs coffee, hands you the PDF.</div>
            <div style={{ color: "var(--color-muted)" }}>Doesn't</div>
            <div>cheer, emoji, congratulate, apologise. Doesn't talk over the user.</div>
            <div style={{ color: "var(--color-muted)" }}>Origin</div>
            <div>a teal block in the LINKRIGHT banner that wouldn't sit still.</div>
            <div style={{ color: "var(--color-muted)" }}>Refuses</div>
            <div>red error walls, stack traces, modal dialogs, the word "amazing".</div>
          </div>

          <div style={{ marginTop: 4, padding: "12px 14px", background: "var(--color-skin-50)", borderRadius: 10, border: "1px solid var(--color-border)" }}>
            <div style={{ fontSize: 10.5, color: "var(--color-cta)", fontWeight: 600, letterSpacing: "0.12em", textTransform: "uppercase" }}>
              Tone vector
            </div>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--color-foreground)", marginTop: 6, lineHeight: 1.7 }}>
              say:   "done. 14 bullets, 0 AI words."<br />
              don't: "🎉 Your resume is ready! Great work!!"
            </div>
          </div>
        </div>

        {/* Anatomy + accent rules */}
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div>
            <div style={{ fontSize: 10.5, fontWeight: 600, letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--color-accent)" }}>Anatomy</div>
            <h3 style={{ fontSize: 22, fontWeight: 700, letterSpacing: "-0.015em", marginTop: 8 }}>Four lines. Five characters wide.</h3>
          </div>

          <div style={{ background: "#0E1620", borderRadius: 10, padding: "16px 18px", border: "1px solid #253140" }}>
            <pre style={{
              margin: 0, fontFamily: "var(--font-mono)", fontSize: 18, lineHeight: 1.25,
              color: "#26D4C2", textShadow: "0 0 14px rgba(38,212,194,0.4)",
            }}>{`   ┌───┐    ← head (box-drawing single-line)
   │• •│    ← eyes (• default · ^ happy · - blink · > focus)
   └───┘    ← jaw  (─ default · ⌣ smile · ━ flat · o ohhh)`}
            </pre>
          </div>

          <div style={{ fontSize: 10.5, fontWeight: 600, letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--color-muted)" }}>Accessory color rules</div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6, fontFamily: "var(--font-mono)", fontSize: 12 }}>
            {[
              { glyph: "★", color: "#E5B80B", note: "gold · success only" },
              { glyph: "✦", color: "#8B5CF6", note: "purple · LLM in loop" },
              { glyph: "⊙", color: "#DCE5EA", note: "silver · tools" },
              { glyph: "₹", color: "#E5B80B", note: "gold · negotiate" },
              { glyph: "≈", color: "#FF5733", note: "coral · motion / heat" },
              { glyph: "°", color: "#C5A6E6", note: "lilac · thinking" },
              { glyph: "~", color: "#FFFFFF", note: "white · steam · coffee" },
              { glyph: "z", color: "#FDF6F0", note: "cream · sleeping" },
            ].map((a) => (
              <div key={a.glyph} style={{ display: "flex", alignItems: "center", gap: 8, padding: "2px 0" }}>
                <span style={{ color: a.color, fontSize: 18, width: 22, textAlign: "center" }}>{a.glyph}</span>
                <span style={{ color: "var(--color-foreground)" }}>{a.note}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

/* ---------- Pip in places — multi-surface deployment ---------- */
function AsciiFutureFormsArtboard() {
  return (
    <div style={{
      width: "100%", height: "100%",
      background: "var(--color-background)",
      padding: "44px 56px",
      boxSizing: "border-box",
      fontFamily: "var(--font-sans)",
      color: "var(--color-foreground)",
      display: "flex", flexDirection: "column", gap: 22,
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
        <div style={{ maxWidth: 900 }}>
          <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.16em", textTransform: "uppercase", color: "var(--color-accent)" }}>
            Pip in places · 8 surfaces, one string
          </div>
          <h2 style={{ fontSize: 40, fontWeight: 800, letterSpacing: "-0.025em", margin: "10px 0 0", lineHeight: 1.05 }}>
            CLI today. Everywhere else tomorrow.
          </h2>
          <div style={{ fontSize: 14, color: "var(--color-muted)", marginTop: 8, lineHeight: 1.5, maxWidth: 760 }}>
            Same 4-line ASCII renders identically in: IDE status bar, git hook output, Chrome extension toolbar, web dashboard, weekly digest email, Slack status, README badge, even a 404. No raster fallback needed.
          </div>
        </div>
      </div>

      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(4, 1fr)",
        gridTemplateRows: "1fr 1fr",
        gap: 14,
        flex: 1,
      }}>
        {/* 1 — VS Code status bar */}
        <div style={{ background: "#1E1E1E", borderRadius: 10, padding: "16px 14px 14px", border: "1px solid #2D2D2D", display: "flex", flexDirection: "column", gap: 10 }}>
          <div style={{ fontSize: 10, color: "#858585", letterSpacing: "0.1em", textTransform: "uppercase", fontFamily: "var(--font-mono)" }}>VS Code · status bar</div>
          <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 13, color: "#CCCCCC", letterSpacing: -0.3 }}>
              <span style={{ color: "#26D4C2" }}>┌───┐ │• •│ └───┘</span>
              <span style={{ color: "#858585", marginLeft: 8 }}>linkright · idle</span>
            </div>
          </div>
          <div style={{ background: "#007ACC", padding: "4px 10px", fontFamily: "var(--font-mono)", fontSize: 11, color: "#FFFFFF", borderRadius: 3, marginTop: "auto" }}>
            ●  Pip is here — Ln 84, Col 32 — UTF-8 — main
          </div>
        </div>

        {/* 2 — Git hook (pre-commit) */}
        <div style={{ background: "#0E1620", borderRadius: 10, padding: "16px 14px 14px", border: "1px solid #253140", display: "flex", flexDirection: "column", gap: 6 }}>
          <div style={{ fontSize: 10, color: "#8FA3B1", letterSpacing: "0.1em", textTransform: "uppercase", fontFamily: "var(--font-mono)" }}>Git · pre-commit hook</div>
          <pre style={{ margin: 0, fontFamily: "var(--font-mono)", fontSize: 11, color: "#EEF5F2", lineHeight: 1.5 }}>{`$ git commit -m "tune scorer"`}</pre>
          <pre style={{ margin: 0, fontFamily: "var(--font-mono)", fontSize: 11, color: "#26D4C2", lineHeight: 1.5 }}>{`┌───┐
│• •│  linkright/pre-commit
└───┘`}</pre>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "#EEF5F2", lineHeight: 1.5 }}>
            <span style={{ color: "#34A853" }}>✓</span> 14 bullets re-scored<br />
            <span style={{ color: "#34A853" }}>✓</span> page-fit 97% · clean<br />
            <span style={{ color: "#FF5733" }}>pip ›</span> <span style={{ color: "#8FA3B1" }}>commit away.</span>
          </div>
        </div>

        {/* 3 — Chrome extension popup */}
        <div style={{ background: "var(--color-surface)", borderRadius: 10, padding: "14px", border: "1px solid var(--color-border)", display: "flex", flexDirection: "column", gap: 10 }}>
          <div style={{ fontSize: 10, color: "var(--color-muted)", letterSpacing: "0.1em", textTransform: "uppercase", fontFamily: "var(--font-mono)" }}>Chrome extension</div>
          <div style={{ display: "flex", alignItems: "center", gap: 12, paddingBottom: 10, borderBottom: "1px solid var(--color-border)" }}>
            <div style={{ background: "#0E1620", borderRadius: 6, padding: "8px 10px" }}>
              <AsciiPip pose="scout" size={14} />
            </div>
            <div>
              <div style={{ fontSize: 13, fontWeight: 700, letterSpacing: "-0.01em" }}>This JD looks promising</div>
              <div style={{ fontSize: 11, color: "var(--color-muted)" }}>linkedin.com/jobs/4471293</div>
            </div>
          </div>
          <div style={{ fontSize: 11.5, lineHeight: 1.6 }}>
            <span style={{ color: "var(--color-accent)", fontWeight: 600 }}>Fit:</span> 87%
            <span style={{ color: "var(--color-muted)" }}>  ·  </span>
            <span style={{ color: "#34A853" }}>+0.6 vs your top match</span>
          </div>
          <button style={{
            marginTop: "auto", background: "var(--color-cta)", color: "white", border: "none", padding: "8px 12px",
            borderRadius: 999, fontWeight: 700, fontSize: 12, cursor: "pointer",
          }}>Capture → linkright watch</button>
        </div>

        {/* 4 — Web dashboard tile */}
        <div style={{ background: "var(--color-background)", borderRadius: 10, padding: "14px", border: "1px solid var(--color-border)", display: "flex", flexDirection: "column", gap: 10 }}>
          <div style={{ fontSize: 10, color: "var(--color-muted)", letterSpacing: "0.1em", textTransform: "uppercase", fontFamily: "var(--font-mono)" }}>linkright.in · web dashboard</div>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div>
              <div style={{ fontSize: 11, color: "var(--color-muted)" }}>Last 7 days</div>
              <div style={{ fontSize: 28, fontWeight: 800, letterSpacing: "-0.02em", color: "var(--color-foreground)" }}>14 apps</div>
              <div style={{ fontSize: 11, color: "#34A853", fontWeight: 600 }}>↑ 3 vs last week</div>
            </div>
            <div style={{ background: "#0E1620", padding: "10px 12px", borderRadius: 8 }}>
              <AsciiPip pose="happy" size={14} />
            </div>
          </div>
          <div style={{ marginTop: 4, padding: "8px 10px", background: "var(--color-surface)", borderRadius: 6, border: "1px solid var(--color-border)", fontFamily: "var(--font-mono)", fontSize: 11 }}>
            <span style={{ color: "var(--color-cta)", fontWeight: 600 }}>pip ›</span> <span style={{ color: "var(--color-muted)" }}>3 callbacks pending. wednesday's busy.</span>
          </div>
        </div>

        {/* 5 — Weekly digest email */}
        <div style={{ background: "var(--color-surface)", borderRadius: 10, padding: 14, border: "1px solid var(--color-border)", display: "flex", flexDirection: "column", gap: 8 }}>
          <div style={{ fontSize: 10, color: "var(--color-muted)", letterSpacing: "0.1em", textTransform: "uppercase", fontFamily: "var(--font-mono)" }}>Weekly digest · email</div>
          <div style={{ paddingBottom: 8, borderBottom: "1px solid var(--color-border)" }}>
            <div style={{ fontSize: 13, fontWeight: 700 }}>Your week with Pip</div>
            <div style={{ fontSize: 10.5, color: "var(--color-muted)" }}>Friday · 5:00 AM IST · #14</div>
          </div>
          <pre style={{ margin: 0, fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--color-foreground)", lineHeight: 1.45, background: "var(--color-background)", padding: 10, borderRadius: 6 }}>{`  ★
┌───┐
│^ ^│
└─⌣─┘

This week
  14 apps · 3 callbacks · 1 offer (!)
  best-fit role: Anthropic / Claude Code`}</pre>
        </div>

        {/* 6 — Slack status */}
        <div style={{ background: "#1A1D21", borderRadius: 10, padding: 14, border: "1px solid #2D2F34", display: "flex", flexDirection: "column", gap: 8 }}>
          <div style={{ fontSize: 10, color: "#858585", letterSpacing: "0.1em", textTransform: "uppercase", fontFamily: "var(--font-mono)" }}>Slack · custom status</div>
          <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "10px 12px", background: "#222529", borderRadius: 8 }}>
            <span style={{ fontFamily: "var(--font-mono)", fontSize: 13, color: "#26D4C2", letterSpacing: -0.5 }}>┌─┐│∙∙│└─┘</span>
            <div style={{ flex: 1, color: "#D1D2D3", fontSize: 12.5 }}>
              <span style={{ fontWeight: 600 }}>Heads down — linkright tailor</span>
              <span style={{ color: "#9B9C9F", marginLeft: 6 }}>· back at 4:30</span>
            </div>
          </div>
          <div style={{ fontSize: 10.5, color: "#9B9C9F", marginTop: "auto" }}>
            auto-syncs from <code style={{ fontFamily: "var(--font-mono)" }}>~/.linkright/state.json</code>
          </div>
        </div>

        {/* 7 — README badge */}
        <div style={{ background: "var(--color-surface)", borderRadius: 10, padding: 14, border: "1px solid var(--color-border)", display: "flex", flexDirection: "column", gap: 8 }}>
          <div style={{ fontSize: 10, color: "var(--color-muted)", letterSpacing: "0.1em", textTransform: "uppercase", fontFamily: "var(--font-mono)" }}>GitHub · README.md</div>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: 11.5, padding: "8px 10px", background: "var(--color-background)", border: "1px solid var(--color-border)", borderRadius: 6 }}>
            <div style={{ color: "#57606A" }}># linkright</div>
            <div style={{ color: "#1F2328" }}>Your local-first career OS · $0 to run</div>
            <div style={{ marginTop: 6, color: "#0FBEAF" }}>┌───┐  ┌───┐  ┌───┐  ┌───┐  ┌───┐</div>
            <div style={{ color: "#0FBEAF" }}>│• •│  │• •│  │• •│  │• •│  │• •│</div>
            <div style={{ color: "#0FBEAF" }}>└───┘  └───┘  └───┘  └───┘  └───┘</div>
            <div style={{ color: "#57606A", marginTop: 6 }}>13.4k ★ · MIT · py 3.10+</div>
          </div>
          <div style={{ marginTop: "auto", fontSize: 10.5, color: "var(--color-muted)" }}>renders the same on every device, every browser.</div>
        </div>

        {/* 8 — 404 / brand moment */}
        <div style={{ background: "#0E1620", borderRadius: 10, padding: 14, border: "1px solid #253140", display: "flex", flexDirection: "column", gap: 8 }}>
          <div style={{ fontSize: 10, color: "#8FA3B1", letterSpacing: "0.1em", textTransform: "uppercase", fontFamily: "var(--font-mono)" }}>404 · brand moment</div>
          <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 10 }}>
            <AsciiPip pose="surprised" size={28} />
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 13, color: "#EEF5F2", textAlign: "center" }}>
              <span style={{ color: "#FF5733" }}>pip ›</span> <span style={{ color: "#8FA3B1" }}>nothing here.</span>
            </div>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 10.5, color: "#5A6B7C", textAlign: "center" }}>
              <code>$ linkright back</code>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ---------- Pip across the career journey (ASCII version) ---------- */
function AsciiJourneyArtboard() {
  const stops = [
    { stop: "Discover",  pose: "reading_jd", note: "scanning JDs · board by board",       color: "#0FBEAF" },
    { stop: "Position",  pose: "focus",      note: "mapping evidence → signal",            color: "#8B5CF6" },
    { stop: "Apply",     pose: "applying",    note: "momentum · sending tailored apps",     color: "#E5B80B" },
    { stop: "Interview", pose: "interview",   note: "story bank · sage practice mode",      color: "#6B8346" },
    { stop: "Negotiate", pose: "negotiating", note: "weighing comp · level · location",     color: "#F05A79" },
    { stop: "Perform",   pose: "focus",      note: "first-90 plans · weekly reviews",      color: "#0FBEAF" },
    { stop: "Promote",   pose: "with_star",  note: "promo packets · the next role",        color: "#FF5733" },
  ];

  return (
    <div style={{
      width: "100%", height: "100%",
      background: "var(--color-background-dark)",
      backgroundImage: "radial-gradient(ellipse at 50% 0%, rgba(15,190,175,0.10) 0%, transparent 65%)",
      padding: "44px 56px",
      boxSizing: "border-box",
      fontFamily: "var(--font-sans)",
      color: "#EEF5F2",
      display: "flex", flexDirection: "column", gap: 24,
    }}>
      <div>
        <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.16em", textTransform: "uppercase", color: "#26D4C2" }}>
          Pip across the career journey
        </div>
        <h2 style={{ fontSize: 36, fontWeight: 800, letterSpacing: "-0.025em", margin: "10px 0 0", lineHeight: 1.05, color: "#EEF5F2" }}>
          Discover → Position → Apply → Interview → Negotiate → Perform → Promote.
        </h2>
        <div style={{ fontSize: 14, color: "#8FA3B1", marginTop: 8 }}>
          Pip wears a different glyph at each stage. Always recognizable. Always working.
        </div>
      </div>

      <div style={{ position: "relative", display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 0", flex: 1 }}>
        <div style={{
          position: "absolute", top: "55%", left: 36, right: 36, height: 0,
          borderTop: "2px dashed rgba(143,163,177,0.25)", transform: "translateY(-50%)", zIndex: 0,
        }} />
        {stops.map((s) => (
          <div key={s.stop} style={{ position: "relative", zIndex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 10, width: 180 }}>
            <div style={{ fontSize: 10.5, fontWeight: 600, letterSpacing: "0.14em", textTransform: "uppercase", color: s.color }}>{s.stop}</div>
            <div style={{
              background: "#151F2B",
              padding: "16px 18px",
              borderRadius: 12,
              border: `1.5px solid ${s.color}`,
              lineHeight: 0,
              minHeight: 96,
              minWidth: 110,
              display: "flex", alignItems: "center", justifyContent: "center",
            }}>
              <AsciiPip pose={s.pose} size={18} accent={s.color} />
            </div>
            <div style={{ fontSize: 11.5, color: "#8FA3B1", textAlign: "center", maxWidth: 160, lineHeight: 1.4 }}>
              {s.note}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

Object.assign(window, {
  AsciiCharacterBibleArtboard,
  AsciiFutureFormsArtboard,
  AsciiJourneyArtboard,
});
