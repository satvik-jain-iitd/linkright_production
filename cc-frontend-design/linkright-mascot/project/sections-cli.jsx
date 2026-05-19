/* =========================================================================
   sections-cli.jsx — Pip's behavioural atlas.
   Six mini-terminals showing Pip in real LinkRight workflow states,
   plus a full sprite sheet of every state and accessory.
   ========================================================================= */

/* ------------ A single behaviour card (mini terminal + caption) ------------ */
function BehaviourCard({ tag, title, caption, command, children, pip, pipName, animated, dialogue }) {
  return (
    <div style={{
      background: "#0E1620",
      borderRadius: 12,
      overflow: "hidden",
      border: "1px solid #253140",
      fontFamily: "var(--font-mono)",
      display: "flex",
      flexDirection: "column",
    }}>
      {/* Mini title bar */}
      <div style={{
        height: 28,
        background: "#151F2B",
        borderBottom: "1px solid #253140",
        display: "flex", alignItems: "center", gap: 6,
        padding: "0 12px",
      }}>
        <span style={{ width: 8, height: 8, borderRadius: "50%", background: "#FF5F57" }} />
        <span style={{ width: 8, height: 8, borderRadius: "50%", background: "#FEBC2E" }} />
        <span style={{ width: 8, height: 8, borderRadius: "50%", background: "#28C840" }} />
        <span style={{ marginLeft: 8, fontSize: 10.5, color: "#8FA3B1" }}>{tag}</span>
      </div>

      {/* Body */}
      <div style={{ padding: "14px 16px", color: "#EEF5F2", flex: 1, display: "flex", flexDirection: "column" }}>
        {/* command */}
        <div style={{ fontSize: 12.5, display: "flex", gap: 6, alignItems: "baseline", marginBottom: 10 }}>
          <span style={{ color: "#5A6B7C" }}>●</span>
          <span style={{ color: "#8FA3B1" }}>(base)</span>
          <span style={{ color: "#E5B80B" }}>%</span>
          <span style={{ color: "#EEF5F2" }}>{command}</span>
        </div>

        {/* output */}
        <div style={{ flex: 1, display: "flex", gap: 12, alignItems: "flex-start" }}>
          <div style={{ flex: 1, fontSize: 11.5, lineHeight: 1.65, color: "#8FA3B1" }}>
            {children}
          </div>
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 6, paddingTop: 4, minWidth: 150 }}>
            {animated ? (
              <PipAnimated states={animated.states} durations={animated.durations} pixel={6} />
            ) : (
              <PipSprite name={pipName || "idle"} pixel={6} />
            )}
          </div>
        </div>

        {/* pip dialogue line */}
        {dialogue && (
          <div style={{ marginTop: 10, paddingTop: 10, borderTop: "1px dashed #253140", fontSize: 11.5 }}>
            <span style={{ color: "#FF8D71", fontWeight: 600 }}>pip</span>
            <span style={{ color: "#3B475A" }}>{" › "}</span>
            <span style={{ color: "#EEF5F2" }}>{dialogue}</span>
          </div>
        )}
      </div>

      {/* Caption strip */}
      <div style={{
        background: "var(--color-surface)",
        borderTop: "1px solid var(--color-border)",
        padding: "12px 16px",
        fontFamily: "var(--font-sans)",
      }}>
        <div style={{ fontSize: 10.5, fontWeight: 600, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--color-cta)" }}>
          {title}
        </div>
        <div style={{ fontSize: 12, color: "var(--color-muted)", marginTop: 4, lineHeight: 1.4 }}>
          {caption}
        </div>
      </div>
    </div>
  );
}

function BehavioursArtboard() {
  const W = 1480, H = 980;
  return (
    <div style={{
      width: W, height: H,
      background: "var(--color-background)",
      padding: "48px 56px",
      boxSizing: "border-box",
      fontFamily: "var(--font-sans)",
      color: "var(--color-foreground)",
      display: "flex", flexDirection: "column", gap: 28,
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
        <div>
          <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.16em", textTransform: "uppercase", color: "var(--color-accent)" }}>
            Behaviour atlas · live in the CLI
          </div>
          <h2 style={{ fontSize: 44, fontWeight: 800, letterSpacing: "-0.025em", margin: "10px 0 0", lineHeight: 1.05 }}>
            Pip changes with the workflow.
          </h2>
          <div style={{ fontSize: 15, color: "var(--color-muted)", marginTop: 8, maxWidth: 760, lineHeight: 1.55 }}>
            Each state has a sprite, a dialogue line, and a meaning. Pip never just stares — when you run a
            command, he picks up a tool and gets to work.
          </div>
        </div>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--color-muted)", textAlign: "right", lineHeight: 1.5 }}>
          6 of 14 workflow states shown<br />
          full set ships in <code>~/.linkright/mascot/</code>
        </div>
      </div>

      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(3, 1fr)",
        gridTemplateRows: "1fr 1fr",
        gap: 20,
        flex: 1,
      }}>
        {/* 1. Boot / idle */}
        <BehaviourCard
          tag="linkright · boot"
          title="01 · Idle"
          caption="No active task. Pip blinks every ~4s, looks around between commands. Never just sits still."
          command="linkright"
          animated={{
            states: ["idle", "idle", "blink_mid", "blink_closed", "blink_mid", "idle", "look_left", "idle", "look_right", "idle"],
            durations: [2400, 1600, 80, 140, 80, 2400, 900, 1800, 900, 2000],
          }}
          dialogue="ready when you are."
        >
          <div><span style={{ color: "#E5B80B" }}>◆</span> Your local-first career OS</div>
          <div style={{ marginLeft: 14, color: "#5A6B7C" }}>v0.9.2</div>
        </BehaviourCard>

        {/* 2. Analyzing JD */}
        <BehaviourCard
          tag="linkright · apply"
          title="02 · Reading the JD"
          caption="JD parsing. Pip holds a magnifier and his eyes scan side-to-side, mimicking how the parser walks the text."
          command="linkright apply google-pm.txt"
          animated={{
            states: ["with_magnifier", "look_right", "with_magnifier", "look_left", "with_magnifier"],
            durations: [1200, 600, 1200, 600, 1200],
          }}
          dialogue="reading the JD. one sec."
        >
          <div><Spinner /> parsing <span style={{ color: "#C5A6E6" }}>google-pm.txt</span></div>
          <div style={{ paddingLeft: 18, color: "#5A6B7C" }}>found 7 strategic signals<Dots /></div>
          <div style={{ paddingLeft: 18, color: "#5A6B7C" }}>mapping to evidence graph</div>
        </BehaviourCard>

        {/* 3. AI mode — generating */}
        <BehaviourCard
          tag="linkright · ai"
          title="03 · AI generating"
          caption="When the LLM is in the loop, Pip wears a soft purple aura. It's the design system's purple = AI rule, made tactile."
          command="linkright bullets --rewrite"
          animated={{
            states: ["ai_aura", "ai_aura", "ai_aura"],
            durations: [800, 800, 800],
          }}
          dialogue="three rewrites. best one wins."
        >
          <div><span style={{ color: "#C5A6E6" }}>◐</span> drafting variant 1 of 3</div>
          <div><span style={{ color: "#C5A6E6" }}>◑</span> drafting variant 2 of 3</div>
          <div><span style={{ color: "#C5A6E6" }}>◒</span> drafting variant 3 of 3</div>
        </BehaviourCard>

        {/* 4. Shipped */}
        <BehaviourCard
          tag="linkright · ship"
          title="04 · Shipped"
          caption="Success. Pip jumps with a tiny gold star. Used sparingly — only for real wins (resume exported, offer received)."
          command="linkright resume export"
          animated={{
            states: ["happy", "jump_up", "with_star", "happy"],
            durations: [400, 360, 700, 600],
          }}
          dialogue="done. 14 bullets, 0 AI words."
        >
          <div><span style={{ color: "#0FBEAF" }}>✓</span> resume_google_pm.pdf</div>
          <div style={{ paddingLeft: 16, color: "#5A6B7C" }}>1 page · 97% width fill</div>
          <div style={{ paddingLeft: 16, color: "#5A6B7C" }}>0 AI words · GPTZero clean</div>
        </BehaviourCard>

        {/* 5. Retry / error */}
        <BehaviourCard
          tag="linkright · err"
          title="05 · Blocked"
          caption="Pip never panics. Eyes go flat, a single teal sweat drop appears, and he asks for what he needs. No red walls."
          command="linkright apply"
          animated={{
            states: ["flat", "sweat", "flat", "look_up"],
            durations: [800, 1400, 800, 700],
          }}
          dialogue="JD's empty. paste it again?"
        >
          <div style={{ color: "#FF8D71" }}>! no JD found at stdin</div>
          <div style={{ color: "#5A6B7C", paddingLeft: 14 }}>I need the text, not the link.</div>
        </BehaviourCard>

        {/* 6. Long task — coffee */}
        <BehaviourCard
          tag="linkright · scout"
          title="06 · Long task"
          caption="When a job will run more than ~30s, Pip grabs coffee. Subtle joke for users staring at a long output."
          command="linkright scout watch --boards 12"
          animated={{
            states: ["with_coffee", "with_coffee", "blink_mid", "blink_closed", "with_coffee"],
            durations: [2200, 1800, 80, 140, 2400],
          }}
          dialogue="this one's deep. fetching from 12 boards."
        >
          <div><Spinner /> scanning 12 boards · est 90s</div>
          <div style={{ paddingLeft: 18, color: "#5A6B7C" }}>linkedin · greenhouse · ashby<Dots /></div>
          <div style={{ paddingLeft: 18, color: "#5A6B7C" }}>17 matches so far</div>
        </BehaviourCard>
      </div>
    </div>
  );
}

/* ============================================================
   Sprite sheet — every state on display.
   ============================================================ */
function SpriteSheetArtboard() {
  const W = 1480, H = 720;

  const FACE_STATES = [
    { name: "idle",         label: "idle" },
    { name: "blink_closed", label: "blink" },
    { name: "happy",        label: "happy" },
    { name: "look_up",      label: "look up" },
    { name: "look_left",    label: "look L" },
    { name: "look_right",   label: "look R" },
    { name: "surprised",    label: "surprised" },
    { name: "flat",         label: "flat" },
    { name: "sleep",        label: "sleeping" },
    { name: "focus",        label: "focus" },
    { name: "confused",     label: "confused" },
  ];

  const ACCESSORY_STATES = [
    { name: "with_star",       label: "with star" },
    { name: "jump_up",         label: "jumping" },
    { name: "with_magnifier",  label: "scanning JD" },
    { name: "with_hammer",     label: "building" },
    { name: "with_coffee",     label: "brewing" },
    { name: "with_page",       label: "carrying resume" },
    { name: "with_book",       label: "interview prep" },
    { name: "reaching",        label: "reaching" },
    { name: "sweat",           label: "sweat / retry" },
    { name: "sleep_z",         label: "sleeping Zs" },
    { name: "ai_aura",         label: "AI aura" },
    { name: "with_rupee",      label: "negotiating" },
    { name: "scout",           label: "scouting" },
  ];

  return (
    <div style={{
      width: W, height: H,
      background: "#0E1620",
      backgroundImage: "radial-gradient(ellipse at center, rgba(15,190,175,0.04) 0%, transparent 60%)",
      padding: "44px 56px",
      boxSizing: "border-box",
      fontFamily: "var(--font-sans)",
      color: "#EEF5F2",
      display: "flex", flexDirection: "column", gap: 24,
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
        <div>
          <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.16em", textTransform: "uppercase", color: "#26D4C2" }}>
            Sprite sheet · 23 states
          </div>
          <h2 style={{ fontSize: 40, fontWeight: 800, letterSpacing: "-0.025em", margin: "10px 0 0", lineHeight: 1.05, color: "#EEF5F2" }}>
            Pip, fully posed.
          </h2>
        </div>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "#8FA3B1", textAlign: "right", lineHeight: 1.5 }}>
          drag a sprite into your script.<br />
          all states render at 14×10 px base.
        </div>
      </div>

      {/* Face states */}
      <div>
        <div style={{ fontSize: 10.5, fontWeight: 600, letterSpacing: "0.14em", textTransform: "uppercase", color: "#8FA3B1", marginBottom: 14 }}>
          Faces — 11 expressions
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(11, 1fr)", gap: 10 }}>
          {FACE_STATES.map((s) => (
            <div key={s.name} style={{
              background: "#151F2B",
              border: "1px solid #253140",
              borderRadius: 10,
              padding: "14px 8px 10px",
              display: "flex", flexDirection: "column", alignItems: "center", gap: 8,
            }}>
              <PipSprite name={s.name} pixel={6} />
              <div style={{ fontSize: 10.5, color: "#8FA3B1", fontFamily: "var(--font-mono)" }}>{s.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Accessory / composite states */}
      <div>
        <div style={{ fontSize: 10.5, fontWeight: 600, letterSpacing: "0.14em", textTransform: "uppercase", color: "#8FA3B1", marginBottom: 14 }}>
          With tools — 13 accessories
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 12 }}>
          {ACCESSORY_STATES.map((s) => (
            <div key={s.name} style={{
              background: "#151F2B",
              border: "1px solid #253140",
              borderRadius: 10,
              padding: "16px 10px 12px",
              display: "flex", flexDirection: "column", alignItems: "center", gap: 8,
            }}>
              <PipSprite name={s.name} pixel={5} />
              <div style={{ fontSize: 10.5, color: "#8FA3B1", fontFamily: "var(--font-mono)" }}>{s.label}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { BehavioursArtboard, SpriteSheetArtboard, BehaviourCard });
