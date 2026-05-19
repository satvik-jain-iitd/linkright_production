/* =========================================================================
   sections-primitives.jsx — the Claude-Code-aligned TUI primitive atlas.

   Every symbol in this file is sourced from linkright/ui/icons.py +
   theme.py + patterns.py + layout.py. This artboard is the reference
   spec: hand it to engineering and every CLI surface follows.
   ========================================================================= */

function PrimitivesAtlasArtboard() {
  const W = 1480, H = 1180;

  const Cell = ({ title, kind, children, span = 1 }) => (
    <div style={{
      gridColumn: `span ${span}`,
      background: "#0E1620",
      border: "1px solid #253140",
      borderRadius: 12,
      padding: "16px 18px 14px",
      display: "flex", flexDirection: "column", gap: 8,
      fontFamily: "ui-monospace, 'SF Mono', Menlo, Consolas, monospace",
      color: "#EEF5F2",
      minHeight: 0,
    }}>
      <div style={{ display: "flex", alignItems: "baseline", gap: 10, paddingBottom: 8, borderBottom: "1px dashed #253140" }}>
        <span style={{ fontSize: 10, color: "#8E8E93", fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase" }}>{kind}</span>
        <span style={{ fontSize: 13, color: "#EEF5F2", fontWeight: 600, fontFamily: "Inter, sans-serif" }}>{title}</span>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>{children}</div>
    </div>
  );

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
        <div style={{ maxWidth: 880 }}>
          <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.16em", textTransform: "uppercase", color: "var(--color-accent)" }}>
            CLI primitive atlas · Claude-Code aligned
          </div>
          <h2 style={{ fontSize: 40, fontWeight: 800, letterSpacing: "-0.025em", margin: "10px 0 0", lineHeight: 1.05 }}>
            The whole CLI, made of fifteen primitives.
          </h2>
          <div style={{ fontSize: 14, color: "var(--color-muted)", marginTop: 8, lineHeight: 1.55 }}>
            Every LinkRight surface composes from this set. Symbols sourced from <code style={{ fontFamily: "var(--font-mono)" }}>linkright/ui/icons.py</code>;
            colors from <code style={{ fontFamily: "var(--font-mono)" }}>theme.py</code> (cluster E1+). Pip narrates between cells.
          </div>
        </div>

        <div style={{
          background: "#0E1620",
          padding: "16px 22px",
          borderRadius: 12,
          border: "1px solid #253140",
          display: "flex", alignItems: "center", gap: 18,
        }}>
          <AsciiPip pose="pointing" size={22} glow />
          <div style={{ color: "#8FA3B1", fontSize: 12, fontFamily: "var(--font-mono)", lineHeight: 1.5 }}>
            <span style={{ color: "#FF8D71", fontWeight: 600 }}>pip ›</span> here's the toolbox.<br />
            <span style={{ color: "#5A6B7C" }}># every surface uses these and only these.</span>
          </div>
        </div>
      </div>

      <div style={{
        flex: 1,
        display: "grid",
        gridTemplateColumns: "repeat(4, 1fr)",
        gap: 14,
      }}>
        {/* row 1 — STATUS family */}
        <Cell kind="01 · status" title="status_event">
          <ShStatus ok={true} label="MongoDB" detail="localhost:27017" />
          <ShStatus ok={true} label="API keys" detail="3 of 3 live" />
          <ShStatus ok={false} label="ChromeCDP" detail="port 9222 closed" />
        </Cell>

        <Cell kind="02 · progress" title="progress_verb">
          <ShWork verb="Smooshing nuggets…" telemetry="(0.3s · 12 toks)" icon="*" />
          <ShWork verb="Thinking…" telemetry="(1.1s · 480 toks)" icon="+" />
          <ShWork verb="Drafting bullet 03/14…" telemetry="(2.4s)" icon="*" />
        </Cell>

        <Cell kind="03 · progress (done)" title="progress_indicator">
          <div style={{ display: "flex", gap: 8, alignItems: "baseline", fontSize: 12.5 }}>
            <span style={{ color: "#0FBEAF", fontWeight: 700 }}>●</span>
            <span>Parsed JD</span>
            <span style={{ color: "#8E8E93" }}>0.4s</span>
          </div>
          <div style={{ display: "flex", gap: 8, alignItems: "baseline", fontSize: 12.5 }}>
            <span style={{ color: "#0FBEAF", fontWeight: 700 }}>●</span>
            <span>Retrieved evidence</span>
            <span style={{ color: "#8E8E93" }}>1.2s</span>
          </div>
          <div style={{ display: "flex", gap: 8, alignItems: "baseline", fontSize: 12.5 }}>
            <span style={{ color: "#0FBEAF", fontWeight: 700 }}>●</span>
            <span>Scored bullets</span>
            <span style={{ color: "#8E8E93" }}>3.1s</span>
          </div>
        </Cell>

        <Cell kind="04 · echo" title="user_input_echo">
          <ShEcho label="Name" value="Satvik Jain" />
          <ShEcho label="Target role" value="Senior PM, AI infra" />
          <ShEcho value="Increased activation 30% in Q4 (5.4M users)" />
        </Cell>

        {/* row 2 — INTERACTIVE */}
        <Cell kind="05 · picker (single)" title="lr_select / picker">
          <div style={{ display: "flex", gap: 8, alignItems: "baseline", fontSize: 12.5, marginBottom: 4 }}>
            <span style={{ color: "#F4B400" }}>◆</span>
            <span style={{ fontWeight: 600 }}>Which template?</span>
          </div>
          <ShPicker items={["Standard 1-page", "Two-column", "FAANG dense"]} selected={1} />
          <div style={{ fontSize: 10.5, color: "#8E8E93", marginTop: 2 }}>↑↓ navigate · Enter to select · Esc cancel</div>
        </Cell>

        <Cell kind="06 · picker (multi)" title="lr_multi_select">
          <div style={{ display: "flex", gap: 8, alignItems: "baseline", fontSize: 12.5, marginBottom: 4 }}>
            <span style={{ color: "#F4B400" }}>◆</span>
            <span style={{ fontWeight: 600 }}>Boards to scan</span>
          </div>
          <div style={{ fontSize: 12, color: "#EEF5F2" }}><span style={{ color: "#E5B80B" }}>[v]</span> LinkedIn</div>
          <div style={{ fontSize: 12, color: "#EEF5F2" }}><span style={{ color: "#E5B80B" }}>[v]</span> Greenhouse</div>
          <div style={{ fontSize: 12, color: "#8FA3B1" }}><span style={{ color: "#8E8E93" }}>[ ]</span> Lever</div>
          <div style={{ fontSize: 12, color: "#EEF5F2" }}><span style={{ color: "#E5B80B" }}>[v]</span> Ashby</div>
          <div style={{ fontSize: 10.5, color: "#8E8E93", marginTop: 2 }}>Space toggle · Enter confirm</div>
        </Cell>

        <Cell kind="07 · text input" title="lr_text · ◇ marker">
          <ShInput label="Email" focused value="satvik@linkright.in" hint="we'll send a one-time code" accent="#06B6D4" />
        </Cell>

        <Cell kind="08 · password" title="lr_password · ◇ masked">
          <ShInput label="API key" focused value="•••••••••••••••••" hint="Anthropic / OpenAI / Gemini" accent="#06B6D4" />
        </Cell>

        {/* row 3 — STRUCTURAL */}
        <Cell kind="09 · insight" title="insight_block">
          <ShInsight title="Insight">
            <div>Your top-of-resume line buries the 30% activation lift.</div>
            <div style={{ color: "#8E8E93", marginTop: 4 }}>— lead with the metric, not the role title.</div>
          </ShInsight>
        </Cell>

        <Cell kind="10 · tree_branch" title="tree_branch + l_branch_tip">
          <div style={{ display: "flex", gap: 8, alignItems: "baseline", fontSize: 12.5 }}>
            <span style={{ color: "#0FBEAF" }}>◆</span>
            <span style={{ fontWeight: 600 }}>Tailor pipeline</span>
          </div>
          <ShTip connector="├" label="01">parse_jd → 7 signals</ShTip>
          <ShTip connector="├" label="02">retrieve_evidence → 23 nuggets</ShTip>
          <ShTip connector="├" label="03">score_bullets → 14 keepers</ShTip>
          <ShTip connector="└" label="04">render_pdf → 97% fill</ShTip>
        </Cell>

        <Cell kind="11 · result arrow" title="arrow_right · muted teal">
          <ShResult>14 bullets · 0 AI words</ShResult>
          <ShResult>1 page · 97% width fill</ShResult>
          <ShResult>GPTZero clean (87 / 100 human)</ShResult>
        </Cell>

        <Cell kind="12 · metadata" title="muted_detail · claude_metadata">
          <div style={{ fontSize: 11, color: "#8E8E93" }}>· Run: 2026-05-13-a3f2</div>
          <div style={{ fontSize: 11, color: "#8E8E93" }}>· Model: gemma3:1b  ·  Tokens: 1.2k  ·  Cost: $0.00</div>
          <div style={{ fontSize: 11, color: "#8E8E93" }}>· ~/.linkright/outputs/run-a3f2/resume.pdf</div>
        </Cell>

        {/* row 4 — LAYOUT */}
        <Cell kind="13 · horizontal_divider" title="turn_divider">
          <div style={{ fontSize: 12, color: "#EEF5F2" }}>What's the role?</div>
          <div style={{ borderTop: "1px solid #8E8E93", margin: "8px 0", opacity: 0.6 }} />
          <div style={{ fontSize: 11, color: "#8E8E93", fontStyle: "italic" }}>· user ·</div>
          <div style={{ fontSize: 12, color: "#EEF5F2", marginTop: 6 }}>Senior PM, AI infra</div>
          <div style={{ borderTop: "1px solid #8E8E93", margin: "8px 0", opacity: 0.6 }} />
          <div style={{ fontSize: 11, color: "#8E8E93", fontStyle: "italic" }}>· assistant ·</div>
        </Cell>

        <Cell kind="14 · tab_bar" title="tab_navigate">
          <ShTabs items={["JD", "Evidence", "Bullets", "PDF"]} current={2} />
        </Cell>

        <Cell kind="15 · sticky_footer" title="tier · status · mode">
          <div style={{ flex: 1 }} />
          <div style={{
            display: "flex", alignItems: "center", padding: "8px 10px",
            borderTop: "1px solid #253140", background: "#151F2B",
            fontSize: 10.5, marginTop: 8,
          }}>
            <span style={{ color: "#F4B400", fontWeight: 700 }}>[v0.9.2]</span>
            <span style={{ flex: 1, textAlign: "center", color: "#8E8E93" }}>linkright --help · doctor</span>
            <span style={{ color: "#34A853" }}>/resume</span>
          </div>
        </Cell>

        <Cell kind="bonus" title="Pip narrates · the connective tissue">
          <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", padding: "8px 0" }}>
            <AsciiPip pose="happy" size={20} />
          </div>
          <div style={{ fontSize: 11, color: "#8E8E93", textAlign: "center", lineHeight: 1.5 }}>
            <span style={{ color: "#FF8D71", fontWeight: 600 }}>pip ›</span> sits beside the banner.<br />
            shows up beside long tasks.<br />
            never blocks user input.
          </div>
        </Cell>
      </div>

      {/* Color legend strip */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(9, 1fr)",
        gap: 8,
        paddingTop: 12,
        borderTop: "1px solid var(--color-border)",
      }}>
        {[
          { hex: "#0FBEAF", token: "step.accent", use: "step done · ●" },
          { hex: "#EE6F4F", token: "tui.coral", use: "working · *" },
          { hex: "#34A853", token: "tui.green", use: "thinking · + · ✓" },
          { hex: "#F4B400", token: "tui.gold", use: "section · ◆" },
          { hex: "#06B6D4", token: "tui.cyan", use: "input · ◇ · ›" },
          { hex: "#8E8E93", token: "tui.muted", use: "tip · branch · ·" },
          { hex: "#5EB3A8", token: "tui.muted_teal", use: "result · →" },
          { hex: "#FF8B6E", token: "tui.salmon", use: "insight · ★" },
          { hex: "#EA4335", token: "error", use: "fail · ✗" },
        ].map((c) => (
          <div key={c.token} style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 10.5, fontFamily: "var(--font-mono)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <span style={{ width: 14, height: 14, borderRadius: 3, background: c.hex }} />
              <span style={{ color: "var(--color-foreground)", fontWeight: 600 }}>{c.hex}</span>
            </div>
            <div style={{ color: "var(--color-accent)" }}>{c.token}</div>
            <div style={{ color: "var(--color-muted)" }}>{c.use}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

Object.assign(window, { PrimitivesAtlasArtboard });
