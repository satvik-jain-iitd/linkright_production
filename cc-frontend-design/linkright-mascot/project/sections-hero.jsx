/* =========================================================================
   sections-hero.jsx — the headline artboard.
   A live CLI window with LINKRIGHT banner + animated Pip beside it,
   plus a designer-style manifesto strip.
   ========================================================================= */

function HeroArtboard() {
  const ARTBOARD_W = 1480;
  const ARTBOARD_H = 880;

  return (
    <div
      style={{
        width: ARTBOARD_W,
        height: ARTBOARD_H,
        background: "var(--color-skin-50)",
        backgroundImage:
          "radial-gradient(ellipse at 25% 110%, rgba(255,87,51,0.07) 0%, transparent 55%), radial-gradient(ellipse at 80% -10%, rgba(15,190,175,0.06) 0%, transparent 55%)",
        position: "relative",
        overflow: "hidden",
        fontFamily: "var(--font-sans)",
        color: "var(--color-foreground)",
      }}
    >
      {/* Top eyebrow strip */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "32px 56px 0",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <PipSprite name="idle" pixel={3} />
          <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
            <span
              style={{
                fontSize: 12,
                fontWeight: 500,
                letterSpacing: "0.18em",
                textTransform: "uppercase",
                color: "var(--color-accent)",
              }}
            >
              LinkRight · Mascot Concept
            </span>
            <span style={{ fontSize: 14, color: "var(--color-muted)", letterSpacing: "-0.005em" }}>
              For the CLI today. The dashboard tomorrow. The extension after that.
            </span>
          </div>
        </div>
        <div
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: 12,
            color: "var(--color-muted)",
            display: "flex",
            gap: 18,
          }}
        >
          <span>v0.1 · concept</span>
          <span style={{ color: "#E5B80B" }}>◆</span>
          <span>14×10 sprite · single-color CLI friendly</span>
        </div>
      </div>

      {/* Manifesto headline */}
      <div style={{ padding: "44px 56px 0", maxWidth: 1100 }}>
        <h1
          style={{
            fontSize: 72,
            fontWeight: 800,
            letterSpacing: "-0.035em",
            lineHeight: 1.02,
            margin: 0,
            color: "var(--color-foreground)",
          }}
        >
          Meet <span style={{ color: "var(--color-cta)" }}>Pip</span>.
          <span style={{ display: "block", color: "var(--color-muted)", fontWeight: 600, fontSize: 36, marginTop: 14, letterSpacing: "-0.015em" }}>
            The small operator who lives beside LINKRIGHT.
          </span>
        </h1>
      </div>

      {/* The terminal */}
      <div style={{ padding: "32px 56px 0" }}>
        <TerminalChrome>
          <Prompt>
            <span style={{ marginLeft: 4 }}>linkright</span>
          </Prompt>

          {/* The banner row — LINKRIGHT pixel art + Pip animated beside */}
          <div
            style={{
              display: "flex",
              alignItems: "flex-end",
              justifyContent: "space-between",
              gap: 32,
              padding: "28px 0 6px 8px",
            }}
          >
            <LinkrightBanner pixel={11} gap={6} outline={false} />
            <div style={{ display: "flex", alignItems: "flex-end", paddingBottom: 4 }}>
              <PipIdle pixel={10} />
            </div>
          </div>

          {/* Tagline */}
          <div style={{ marginTop: 8, marginLeft: 8 }}>
            <Line icon="◆">
              <strong style={{ color: "#EEF5F2" }}>Your local-first career OS</strong>
              <Dim>{" · "}</Dim>
              <Gold>$0 to run</Gold>
            </Line>
            <div style={{ marginLeft: 16, color: "#E5B80B", fontSize: 12, marginTop: 2 }}>
              v0.9.2
            </div>
          </div>

          {/* A Pip first-line greeting */}
          <div style={{ marginTop: 18, marginLeft: 8, fontSize: 13, color: "#8FA3B1" }}>
            <span style={{ color: "#FF8D71", fontWeight: 600 }}>pip</span>
            <span style={{ color: "#5A6B7C" }}>{" › "}</span>
            <span style={{ color: "#EEF5F2" }}>ready when you are. </span>
            <Dim>JD, resume, or a fresh opportunity — your call.</Dim>
          </div>
          <div style={{ marginTop: 14 }}>
            <Prompt>
              <Cursor />
            </Prompt>
          </div>
        </TerminalChrome>
      </div>

      {/* Bottom — designer's three-point note */}
      <div
        style={{
          position: "absolute",
          bottom: 36,
          left: 56,
          right: 56,
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: 28,
        }}
      >
        {[
          {
            num: "01",
            title: "Pixel-native.",
            body: "14×10 grid, single-color fallback, renders crisp at 16px or 256px. ASCII fallback for plain terminals.",
          },
          {
            num: "02",
            title: "Behaviour over decoration.",
            body: "Pip changes with the workflow — scanning JDs, hammering bullets, sweating retries. Never just sitting pretty.",
          },
          {
            num: "03",
            title: "Same voice as the product.",
            body: "Builder-confident, evidence-led, quietly witty. Pip refuses to invent metrics. He just ships.",
          },
        ].map((p) => (
          <div
            key={p.num}
            style={{
              borderTop: "2px solid var(--color-foreground)",
              paddingTop: 14,
            }}
          >
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--color-cta)", fontWeight: 600, letterSpacing: "0.08em" }}>
              {p.num}
            </div>
            <div style={{ fontSize: 17, fontWeight: 700, marginTop: 6, letterSpacing: "-0.01em" }}>
              {p.title}
            </div>
            <div style={{ fontSize: 13, color: "var(--color-muted)", marginTop: 6, lineHeight: 1.55 }}>
              {p.body}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

Object.assign(window, { HeroArtboard });
