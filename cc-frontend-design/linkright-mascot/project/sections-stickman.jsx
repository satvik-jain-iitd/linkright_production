/* =========================================================================
   sections-stickman.jsx — the stickman direction.

   A new exploration: Pip as a hand-drawn line-art stickman that mirrors
   the climbing figure in the LinkRight logo.

   Three artboards:
   - Hero: pitch + big stickman
   - Pose grid: 12 states
   - Comparison: stickman vs pixel blob, same workflow moments
   - CLI form: how stickman lives in the terminal
   ========================================================================= */

/* ---------- Hero / pitch ---------- */
function StickmanHeroArtboard() {
  const W = 1480, H = 880;
  return (
    <div style={{
      width: W, height: H,
      background: "var(--color-skin-50)",
      backgroundImage:
        "radial-gradient(ellipse at 80% 10%, rgba(15,190,175,0.10) 0%, transparent 55%), radial-gradient(ellipse at 10% 100%, rgba(229,184,11,0.07) 0%, transparent 55%)",
      padding: "44px 56px",
      boxSizing: "border-box",
      fontFamily: "var(--font-sans)",
      color: "var(--color-foreground)",
      position: "relative", overflow: "hidden",
      display: "flex", flexDirection: "column",
    }}>
      {/* Eyebrow */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.16em", textTransform: "uppercase", color: "var(--color-cta)" }}>
            New direction · the stickman Pip
          </div>
          <h1 style={{ fontSize: 76, fontWeight: 800, letterSpacing: "-0.035em", margin: "16px 0 0", lineHeight: 1, maxWidth: 880 }}>
            What if Pip looked like<br />
            <span style={{ color: "var(--color-accent)" }}>the logo</span>?
          </h1>
          <div style={{ fontSize: 17, color: "var(--color-muted)", marginTop: 16, maxWidth: 720, lineHeight: 1.55 }}>
            The LinkRight logo IS a stickman climbing an arrow toward a star.
            If the mascot is also a stickman, it stops being a separate character — it
            becomes the same figure, alive, sitting beside the wordmark.
          </div>
        </div>

        {/* Big idle stickman */}
        <div style={{
          background: "var(--color-surface)",
          border: "1.5px solid var(--color-border)",
          borderRadius: 24,
          padding: "32px 28px",
          display: "flex", flexDirection: "column", alignItems: "center", gap: 18,
          minWidth: 360,
        }}>
          <Stickman pose="climb_reach" size={280} />
          <div style={{ fontSize: 13, color: "var(--color-muted)", textAlign: "center", lineHeight: 1.5 }}>
            <span style={{ color: "var(--color-foreground)", fontWeight: 600 }}>climb_reach</span> — the canonical pose.<br />
            A direct mirror of the logo.
          </div>
        </div>
      </div>

      {/* Three reasons strip */}
      <div style={{
        marginTop: 48,
        display: "grid",
        gridTemplateColumns: "repeat(3, 1fr)",
        gap: 28,
      }}>
        {[
          {
            num: "01",
            title: "It IS the logo.",
            body: "Same single-weight teal stroke, same climbing posture, same striving energy. The mascot extends the brand mark rather than competing with it.",
          },
          {
            num: "02",
            title: "Body language > face shifts.",
            body: "A stickman running, sitting, holding a paper, reaching upward conveys action instantly. No more guessing what a tiny eye-pixel means.",
          },
          {
            num: "03",
            title: "Three fidelities, one character.",
            body: "Hi-fi SVG for the dashboard. Chunky pixel form for truecolor terminals. Plain ASCII for everywhere else. Same Pip, three skins.",
          },
        ].map((p) => (
          <div key={p.num} style={{
            borderTop: "2px solid var(--color-foreground)",
            paddingTop: 14,
          }}>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--color-cta)", fontWeight: 600, letterSpacing: "0.08em" }}>
              {p.num}
            </div>
            <div style={{ fontSize: 19, fontWeight: 700, marginTop: 6, letterSpacing: "-0.01em" }}>
              {p.title}
            </div>
            <div style={{ fontSize: 14, color: "var(--color-muted)", marginTop: 8, lineHeight: 1.55 }}>
              {p.body}
            </div>
          </div>
        ))}
      </div>

      {/* Bottom note */}
      <div style={{
        marginTop: "auto",
        padding: "20px 24px",
        background: "var(--color-surface)",
        borderRadius: 14,
        border: "1px dashed var(--color-border)",
        display: "flex", alignItems: "center", gap: 18, fontSize: 14, color: "var(--color-muted)",
      }}>
        <Stickman pose="idle" size={60} />
        <div>
          <strong style={{ color: "var(--color-foreground)" }}>The voice doesn't change.</strong>{" "}
          Same lowercase, evidence-led builder voice. Same dialogue lines (<em>"ready when you are."</em>,
          <em> "filling 97% width. tight."</em>). Just a more human silhouette delivering them.
        </div>
      </div>
    </div>
  );
}

/* ---------- Pose grid ---------- */
function StickmanPosesArtboard() {
  const W = 1480, H = 720;

  const poses = [
    { name: "idle",         label: "idle",           caption: "boot / standing by" },
    { name: "wave",         label: "wave",           caption: "greeting, returning user" },
    { name: "reading_jd",   label: "reading JD",     caption: "parsing job description" },
    { name: "building",     label: "building",       caption: "tailoring resume / typing" },
    { name: "ai_thinking",  label: "AI thinking",    caption: "LLM in the loop" },
    { name: "success",      label: "success",        caption: "resume shipped · star earned" },
    { name: "retry",        label: "retry",          caption: "blocked, asking for input" },
    { name: "coffee",       label: "long task",      caption: "scanning 12 job boards" },
    { name: "interview",    label: "interview prep", caption: "story bank · clipboard" },
    { name: "negotiate",    label: "negotiate",      caption: "comp · level tradeoffs" },
    { name: "climb_reach",  label: "climb · reach",  caption: "canonical · logo callback" },
    { name: "run",          label: "running",        caption: "applying, momentum" },
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
            Pose grid · 12 states
          </div>
          <h2 style={{ fontSize: 40, fontWeight: 800, letterSpacing: "-0.025em", margin: "10px 0 0", lineHeight: 1.05 }}>
            Pip, with a body.
          </h2>
          <div style={{ fontSize: 14, color: "var(--color-muted)", marginTop: 8, maxWidth: 720, lineHeight: 1.5 }}>
            Each pose tells you what Pip is doing without reading the label. That's the whole point.
          </div>
        </div>
      </div>

      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(6, 1fr)",
        gridAutoRows: "1fr",
        gap: 14,
        flex: 1,
      }}>
        {poses.map((p) => (
          <div key={p.name} style={{
            background: "var(--color-skin-50)",
            border: "1px solid var(--color-border)",
            borderRadius: 14,
            padding: "16px 12px 12px",
            display: "flex", flexDirection: "column", alignItems: "center", gap: 8,
          }}>
            <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", width: "100%" }}>
              <Stickman pose={p.name} size={140} />
            </div>
            <div style={{ fontSize: 12, fontWeight: 600, fontFamily: "var(--font-mono)", color: "var(--color-foreground)" }}>
              {p.label}
            </div>
            <div style={{ fontSize: 10.5, color: "var(--color-muted)", textAlign: "center", lineHeight: 1.35 }}>
              {p.caption}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ---------- Stickman vs blob comparison ---------- */
function StickmanComparisonArtboard() {
  const W = 1480, H = 880;

  const states = [
    { stick: "reading_jd",  blob: "with_magnifier", label: "Reading the JD",       desc: "Stickman: holding paper, focused gaze. Blob: magnifier accessory beside head." },
    { stick: "building",    blob: "with_hammer",    label: "Building the resume",  desc: "Stickman: leaning over desk + laptop + sparks. Blob: hammer above head." },
    { stick: "success",     blob: "with_star",      label: "Shipped",              desc: "Stickman: arms raised, full body celebration. Blob: star icon above." },
    { stick: "retry",       blob: "sweat",          label: "Blocked",              desc: "Stickman: hand on forehead, sweat. Blob: flat face + drop." },
    { stick: "ai_thinking", blob: "ai_aura",        label: "AI generating",        desc: "Stickman: gaze + thought bubble with sparkle. Blob: purple aura ring." },
    { stick: "coffee",      blob: "with_coffee",    label: "Long task",            desc: "Stickman: sitting, mug in hand. Blob: mug beside head." },
  ];

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
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
        <div>
          <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.16em", textTransform: "uppercase", color: "var(--color-accent)" }}>
            Stickman vs blob · same six moments
          </div>
          <h2 style={{ fontSize: 40, fontWeight: 800, letterSpacing: "-0.025em", margin: "10px 0 0", lineHeight: 1.05 }}>
            Two directions, side by side.
          </h2>
          <div style={{ fontSize: 14, color: "var(--color-muted)", marginTop: 8, maxWidth: 760, lineHeight: 1.5 }}>
            Both work. The stickman conveys action through posture (more legible at a glance, less novelty). The blob conveys it through accessories (more iconic, more playful).
          </div>
        </div>
      </div>

      {/* Comparison grid */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(3, 1fr)",
        gridTemplateRows: "1fr 1fr",
        gap: 16,
        flex: 1,
      }}>
        {states.map((s) => (
          <div key={s.label} style={{
            background: "var(--color-surface)",
            border: "1px solid var(--color-border)",
            borderRadius: 14,
            display: "grid",
            gridTemplateRows: "auto 1fr auto",
            overflow: "hidden",
          }}>
            <div style={{
              fontSize: 10.5, fontWeight: 600, letterSpacing: "0.12em",
              textTransform: "uppercase", color: "var(--color-cta)",
              padding: "12px 16px 0",
            }}>
              {s.label}
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 0 }}>
              {/* Stickman side */}
              <div style={{
                background: "var(--color-skin-50)",
                display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
                padding: "16px 8px", gap: 8,
                borderRight: "1px solid var(--color-border)",
              }}>
                <Stickman pose={s.stick} size={120} />
                <div style={{ fontSize: 10, fontFamily: "var(--font-mono)", color: "var(--color-muted)" }}>
                  stickman
                </div>
              </div>

              {/* Blob side — on dark navy to test in CLI context */}
              <div style={{
                background: "#0E1620",
                display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
                padding: "16px 8px", gap: 8,
              }}>
                <PipSprite name={s.blob} pixel={5} />
                <div style={{ fontSize: 10, fontFamily: "var(--font-mono)", color: "#8FA3B1" }}>
                  pixel blob
                </div>
              </div>
            </div>

            <div style={{ padding: "10px 16px 12px", fontSize: 11.5, color: "var(--color-muted)", lineHeight: 1.5 }}>
              {s.desc}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ---------- CLI form — how stickman lives in the terminal ---------- */
function StickmanCLIArtboard() {
  const W = 1480, H = 720;

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
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
        <div>
          <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.16em", textTransform: "uppercase", color: "var(--color-accent)" }}>
            CLI fallbacks · stickman at terminal fidelity
          </div>
          <h2 style={{ fontSize: 38, fontWeight: 800, letterSpacing: "-0.025em", margin: "10px 0 0", lineHeight: 1.05 }}>
            Three fidelities. Same Pip.
          </h2>
          <div style={{ fontSize: 14, color: "var(--color-muted)", marginTop: 8, maxWidth: 760, lineHeight: 1.5 }}>
            CLI tools must work across terminals. Pip renders at whatever fidelity the terminal supports.
          </div>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 22, flex: 1 }}>
        {/* Truecolor — SVG/line-art rendered as inline image */}
        <div style={{
          background: "#0E1620",
          borderRadius: 14,
          padding: 22,
          display: "flex", flexDirection: "column", gap: 12,
          border: "1px solid #253140",
        }}>
          <div style={{ fontSize: 10.5, fontWeight: 600, letterSpacing: "0.12em", textTransform: "uppercase", color: "#26D4C2" }}>
            Hi-fi · iTerm 3 + sixel
          </div>
          <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", background: "transparent" }}>
            <Stickman pose="climb_reach" size={170} />
          </div>
          <div style={{
            fontFamily: "ui-monospace, monospace", fontSize: 12, color: "#EEF5F2",
            padding: "10px 12px", background: "rgba(15,190,175,0.06)", borderRadius: 8,
            borderLeft: "2px solid #26D4C2",
          }}>
            <span style={{ color: "#FF8D71", fontWeight: 600 }}>pip ›</span> climbing today.
          </div>
          <div style={{ fontSize: 11, color: "#8FA3B1", fontFamily: "var(--font-mono)" }}>
            Sixel-capable terminals render the SVG directly.
          </div>
        </div>

        {/* Chunky pixel — for truecolor terminals without sixel */}
        <div style={{
          background: "#0E1620",
          borderRadius: 14,
          padding: 22,
          display: "flex", flexDirection: "column", gap: 12,
          border: "1px solid #253140",
        }}>
          <div style={{ fontSize: 10.5, fontWeight: 600, letterSpacing: "0.12em", textTransform: "uppercase", color: "#26D4C2" }}>
            Mid-fi · truecolor
          </div>
          <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <PixelStickman pixel={9} />
          </div>
          <div style={{
            fontFamily: "ui-monospace, monospace", fontSize: 12, color: "#EEF5F2",
            padding: "10px 12px", background: "rgba(15,190,175,0.06)", borderRadius: 8,
            borderLeft: "2px solid #26D4C2",
          }}>
            <span style={{ color: "#FF8D71", fontWeight: 600 }}>pip ›</span> rendered with █ blocks.
          </div>
          <div style={{ fontSize: 11, color: "#8FA3B1", fontFamily: "var(--font-mono)" }}>
            Unicode block characters. Works in Terminal.app, kitty, alacritty.
          </div>
        </div>

        {/* ASCII — universal */}
        <div style={{
          background: "#0E1620",
          borderRadius: 14,
          padding: 22,
          display: "flex", flexDirection: "column", gap: 12,
          border: "1px solid #253140",
        }}>
          <div style={{ fontSize: 10.5, fontWeight: 600, letterSpacing: "0.12em", textTransform: "uppercase", color: "#26D4C2" }}>
            Lo-fi · plain ASCII
          </div>
          <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <pre style={{
              fontFamily: "ui-monospace, monospace",
              fontSize: 36,
              lineHeight: 1.1,
              color: "#26D4C2",
              margin: 0,
              fontWeight: 700,
              textAlign: "center",
              letterSpacing: 0,
            }}>{ASCII_STICK}</pre>
          </div>
          <div style={{
            fontFamily: "ui-monospace, monospace", fontSize: 12, color: "#EEF5F2",
            padding: "10px 12px", background: "rgba(15,190,175,0.06)", borderRadius: 8,
            borderLeft: "2px solid #26D4C2",
          }}>
            <span style={{ color: "#FF8D71", fontWeight: 600 }}>pip ›</span> 6 chars. zero deps.
          </div>
          <div style={{ fontSize: 11, color: "#8FA3B1", fontFamily: "var(--font-mono)" }}>
            SSH sessions, CI logs, dumb terminals. Renders anywhere.
          </div>
        </div>
      </div>
    </div>
  );
}

/* ---------- Terminal scene — stickman beside LINKRIGHT banner ---------- */
function StickmanTerminalArtboard() {
  const W = 1480, H = 720;
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
          Stickman · in the CLI banner
        </div>
        <h2 style={{ fontSize: 38, fontWeight: 800, letterSpacing: "-0.025em", margin: "10px 0 0", lineHeight: 1.05 }}>
          Beside the wordmark, same scale, same DNA.
        </h2>
      </div>

      <TerminalChrome>
        <Prompt><span style={{ marginLeft: 4 }}>linkright</span></Prompt>

        <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", gap: 28, padding: "30px 0 10px 8px" }}>
          <LinkrightBanner pixel={11} gap={6} />
          <div style={{ paddingBottom: 0 }}>
            <PixelStickman pixel={7} />
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

Object.assign(window, {
  StickmanHeroArtboard,
  StickmanPosesArtboard,
  StickmanComparisonArtboard,
  StickmanCLIArtboard,
  StickmanTerminalArtboard,
});
