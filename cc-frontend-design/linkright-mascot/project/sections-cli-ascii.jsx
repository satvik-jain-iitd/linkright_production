/* =========================================================================
   sections-cli-ascii.jsx — LinkRight CLI surfaces, all rendered using the
   Claude-Code-aligned primitive set (linkright.ui.*) with ASCII Pip as
   the mascot. One artboard per high-value command surface.
   ========================================================================= */

/* ---------- Common building blocks ---------- */
function BoardShell({ title, eyebrow, blurb, tone = "dark", children, footnote }) {
  const dark = tone === "dark";
  return (
    <div style={{
      width: "100%", height: "100%",
      background: dark ? "var(--color-skin-50)" : "var(--color-surface)",
      padding: "44px 56px",
      boxSizing: "border-box",
      fontFamily: "var(--font-sans)",
      color: "var(--color-foreground)",
      display: "flex", flexDirection: "column", gap: 18,
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", gap: 32 }}>
        <div style={{ maxWidth: 920 }}>
          <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.16em", textTransform: "uppercase", color: "var(--color-accent)" }}>
            {eyebrow}
          </div>
          <h2 style={{ fontSize: 36, fontWeight: 800, letterSpacing: "-0.025em", margin: "10px 0 0", lineHeight: 1.05 }}>
            {title}
          </h2>
          {blurb && (
            <div style={{ fontSize: 14, color: "var(--color-muted)", marginTop: 8, lineHeight: 1.55, maxWidth: 820 }}>
              {blurb}
            </div>
          )}
        </div>
        {footnote && (
          <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--color-muted)", textAlign: "right", lineHeight: 1.5 }}>
            {footnote}
          </div>
        )}
      </div>
      {children}
    </div>
  );
}

function PipNote({ pose = "idle", line, sub }) {
  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 18,
      padding: "14px 18px",
      background: "rgba(15,190,175,0.04)",
      border: "1px solid rgba(15,190,175,0.18)",
      borderRadius: 12,
    }}>
      <AsciiPip pose={pose} size={20} glow />
      <div style={{ fontFamily: "var(--font-mono)", fontSize: 13, color: "var(--color-foreground)", lineHeight: 1.5 }}>
        <div>
          <span style={{ color: "#FF5733", fontWeight: 600 }}>pip ›</span>{" "}
          <span>{line}</span>
        </div>
        {sub && <div style={{ color: "var(--color-muted)", marginTop: 2 }}>{sub}</div>}
      </div>
    </div>
  );
}

/* =========================================================================
   01 · BOOT — `linkright` (no args) — banner + tldr + sticky footer
   ========================================================================= */
function CliBootArtboard() {
  return (
    <BoardShell
      eyebrow="01 · linkright (boot)"
      title="The banner. The cheat sheet. Pip standing by."
      blurb="No args. We show the gradient banner, the curated cheat sheet (industry convention: git, kubectl, docker), a one-line subtitle, and a sticky footer. ASCII Pip blinks beside the banner — first impression in 6 characters."
      footnote={<>entry: <code>linkright/__main__</code><br />primitives used: banner · tldr · sticky_footer</>}
    >
      <ShellWindow size="120×36" style={{ flex: 1 }}>
        <ShPrompt cwd="~/linkright_production">linkright</ShPrompt>

        <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", gap: 24, padding: "16px 0 8px 4px" }}>
          <LinkrightBanner pixel={10} gap={5} />
          <div style={{ paddingBottom: 2 }}><AsciiIdle size={32} /></div>
        </div>

        <div style={{ marginLeft: 4, marginTop: 4 }}>
          <div style={{ fontSize: 13, display: "flex", gap: 8, alignItems: "baseline" }}>
            <span style={{ color: "#F4B400" }}>◆</span>
            <span style={{ color: "#EEF5F2", fontWeight: 600 }}>Your local-first career OS</span>
            <span style={{ color: "#8E8E93" }}>·</span>
            <span style={{ color: "#F4B400", fontWeight: 600 }}>$0 to run</span>
          </div>
          <div style={{ marginLeft: 18, color: "#F4B400", fontSize: 11.5 }}>v0.9.2</div>
        </div>

        <div style={{ borderTop: "1px solid #253140", margin: "14px 0 10px" }} />

        <div style={{ marginLeft: 4 }}>
          <div style={{ fontSize: 11.5, fontWeight: 600, color: "#8E8E93", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 6 }}>Common workflow</div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", columnGap: 36, rowGap: 4, fontSize: 12.5 }}>
            <div><span style={{ color: "#0FBEAF" }}>linkright tailor</span>  <span style={{ color: "#8E8E93" }}>-j jd.md</span>   <span style={{ color: "#5A6B7C" }}># tailored resume</span></div>
            <div><span style={{ color: "#0FBEAF" }}>linkright cl</span>      <span style={{ color: "#8E8E93" }}>-j jd.md</span>   <span style={{ color: "#5A6B7C" }}># cover letter</span></div>
            <div><span style={{ color: "#0FBEAF" }}>linkright critique</span><span style={{ color: "#5A6B7C" }}>                # LLM review</span></div>
            <div><span style={{ color: "#0FBEAF" }}>linkright fill</span>    <span style={{ color: "#5A6B7C" }}>                  # gap analysis</span></div>
            <div><span style={{ color: "#0FBEAF" }}>linkright practice</span><span style={{ color: "#5A6B7C" }}>                # interview prep</span></div>
            <div><span style={{ color: "#0FBEAF" }}>linkright jobs scout</span><span style={{ color: "#5A6B7C" }}>              # scan 12 boards</span></div>
          </div>

          <div style={{ fontSize: 11.5, fontWeight: 600, color: "#8E8E93", letterSpacing: "0.08em", textTransform: "uppercase", marginTop: 14, marginBottom: 6 }}>Quick reference</div>
          <div style={{ fontSize: 12, color: "#8E8E93", lineHeight: 1.7 }}>
            <span style={{ color: "#0FBEAF" }}>linkright tldr</span>     full cheat sheet<br />
            <span style={{ color: "#0FBEAF" }}>linkright doctor</span>   health check
          </div>
        </div>

        <div style={{ marginTop: 14 }}>
          <ShPrompt cwd="~/linkright_production">
            <span style={{
              display: "inline-block", width: 7, height: 13, background: "#EEF5F2",
              verticalAlign: "middle", animation: "pipBlink 1s steps(1) infinite", marginLeft: 2,
            }} />
          </ShPrompt>
        </div>
      </ShellWindow>

      <ShFooter tier="v0.9.2" mode="resume" status="linkright --help  ·  linkright doctor" />
    </BoardShell>
  );
}

/* =========================================================================
   02 · TAILOR — the 16-step pipeline. The flagship surface.
   ========================================================================= */
function CliTailorArtboard() {
  return (
    <BoardShell
      eyebrow="02 · linkright tailor -j jd.md"
      title="The 16-step pipeline. Pip changes pose with the work."
      blurb="The flagship command. Steps stream as `* working…` then settle to `● done`. Pip rotates through reading → focus → ai_thinking → building → with_star as the pipeline progresses. Telemetry is muted; results lead with the arrow."
      footnote={<>entry: <code>linkright.resume.cli</code><br />uses: progress_verb · tree_branch · status · result · insight</>}
    >
      <div style={{ display: "grid", gridTemplateColumns: "1fr 360px", gap: 18, flex: 1, minHeight: 0 }}>
        <ShellWindow size="120×40" style={{ height: "100%" }}>
          <ShPrompt cwd="~/linkright">linkright tailor -j google-pm.md</ShPrompt>

          <div style={{ margin: "10px 0 4px", display: "flex", alignItems: "baseline", gap: 8 }}>
            <span style={{ color: "#F4B400" }}>◆</span>
            <span style={{ color: "#EEF5F2", fontWeight: 700, fontSize: 13 }}>Tailor pipeline</span>
            <span style={{ color: "#8E8E93", fontSize: 11 }}>· google-pm.md · 16 steps</span>
          </div>

          {/* Phase 1 — parse */}
          <ShTip connector="├" label="phase">Parse</ShTip>
          <div style={{ paddingLeft: 14 }}>
            <div style={{ display: "flex", gap: 8, alignItems: "baseline", fontSize: 12.5 }}>
              <span style={{ color: "#0FBEAF", fontWeight: 700 }}>●</span><span>parsed JD</span><span style={{ color: "#8E8E93" }}>0.4s · 7 signals</span>
            </div>
            <div style={{ display: "flex", gap: 8, alignItems: "baseline", fontSize: 12.5 }}>
              <span style={{ color: "#0FBEAF", fontWeight: 700 }}>●</span><span>mapped JD → strategy</span><span style={{ color: "#8E8E93" }}>0.8s · "operator + AI infra"</span>
            </div>
          </div>

          {/* Phase 2 — retrieve */}
          <ShTip connector="├" label="phase">Retrieve</ShTip>
          <div style={{ paddingLeft: 14 }}>
            <div style={{ display: "flex", gap: 8, alignItems: "baseline", fontSize: 12.5 }}>
              <span style={{ color: "#0FBEAF", fontWeight: 700 }}>●</span><span>evidence nuggets</span><span style={{ color: "#8E8E93" }}>1.2s · 23 hits</span>
            </div>
            <div style={{ display: "flex", gap: 8, alignItems: "baseline", fontSize: 12.5 }}>
              <span style={{ color: "#0FBEAF", fontWeight: 700 }}>●</span><span>career signals</span><span style={{ color: "#8E8E93" }}>0.3s · 14 verbs</span>
            </div>
          </div>

          {/* Phase 3 — generate (in flight, coral *) */}
          <ShTip connector="├" label="phase">Generate</ShTip>
          <div style={{ paddingLeft: 14 }}>
            <ShWork verb="Drafting bullet 06/14…" telemetry="(2.4s · gemma3:1b)" icon="*" />
            <ShWork verb="Thinking…" telemetry="(0.9s · 480 toks)" icon="+" />
            <div style={{ display: "flex", gap: 8, alignItems: "baseline", fontSize: 12.5 }}>
              <span style={{ color: "#0FBEAF", fontWeight: 700 }}>●</span><span>scored bullets</span><span style={{ color: "#8E8E93" }}>3.1s · 14 keepers / 18 candidates</span>
            </div>
          </div>

          {/* Phase 4 — render */}
          <ShTip connector="└" label="phase">Render</ShTip>
          <div style={{ paddingLeft: 14 }}>
            <div style={{ display: "flex", gap: 8, alignItems: "baseline", fontSize: 12.5 }}>
              <span style={{ color: "#0FBEAF", fontWeight: 700 }}>●</span><span>rendered PDF</span><span style={{ color: "#8E8E93" }}>0.7s · 97% width fill</span>
            </div>
          </div>

          <ShInsight title="Insight">
            <div>Width fill 97% — one notch from overflow.</div>
            <div style={{ color: "#8E8E93", marginTop: 2 }}>— if Citi adds a longer title, drop the "infra" qualifier in bullet 03.</div>
          </ShInsight>

          <ShResult>14 bullets · 0 AI words · GPTZero 87/100 human</ShResult>
          <ShResult>~/.linkright/outputs/run-a3f2/resume_google_pm.pdf</ShResult>

          <div style={{ color: "#8E8E93", fontSize: 11, padding: "6px 0", fontFamily: "ui-monospace" }}>
            · Run: 2026-05-13-a3f2  ·  Model: gemma3:1b  ·  Tokens: 1.2k  ·  Cost: $0.00
          </div>

          <div style={{ marginTop: 8 }}>
            <ShPrompt cwd="~/linkright">
              <span style={{ display: "inline-block", width: 7, height: 13, background: "#EEF5F2", verticalAlign: "middle", animation: "pipBlink 1s steps(1) infinite", marginLeft: 2 }} />
            </ShPrompt>
          </div>
        </ShellWindow>

        {/* Pip side panel — pose-by-phase */}
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {[
            { phase: "Parse", pose: "reading_jd", note: "scanning the JD" },
            { phase: "Retrieve", pose: "focus", note: "matching to evidence" },
            { phase: "Generate", pose: "ai_thinking", note: "LLM in the loop" },
            { phase: "Score", pose: "building", note: "shaping the bullets" },
            { phase: "Render", pose: "with_star", note: "shipped" },
          ].map((p) => (
            <div key={p.phase} style={{
              background: "#0E1620",
              border: "1px solid #253140",
              borderRadius: 10,
              padding: "12px 14px",
              display: "flex", alignItems: "center", gap: 14,
              flex: 1,
            }}>
              <div style={{ minWidth: 90, lineHeight: 0 }}>
                <AsciiPip pose={p.pose} size={16} />
              </div>
              <div style={{ flex: 1, fontFamily: "var(--font-mono)", fontSize: 11.5, color: "#EEF5F2" }}>
                <div style={{ color: "#F4B400", fontSize: 10, letterSpacing: "0.1em", textTransform: "uppercase" }}>{p.phase}</div>
                <div style={{ color: "#8FA3B1", marginTop: 2 }}>{p.note}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </BoardShell>
  );
}

/* =========================================================================
   03 · ONBOARD / INIT — interactive picker + ◇ inputs + echo
   ========================================================================= */
function CliOnboardArtboard() {
  return (
    <BoardShell
      eyebrow="03 · linkright init  ·  linkright onboard"
      title="The first run. Inputs, pickers, and Pip waving hello."
      blurb="The interactive setup flow. ◇ marks text inputs, ◆ marks pickers. Already-answered questions echo back with the high-contrast ● bullet. Pip waves on entry and reads the welcome line."
      footnote={<>entry: <code>linkright.setup_wizard</code> · <code>onboard.cli</code><br />uses: lr_text · lr_select · lr_multi_select · user_input_echo</>}
    >
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 18, flex: 1, minHeight: 0 }}>
        {/* Left — init (config) */}
        <ShellWindow size="100×34" title="linkright init">
          <ShPrompt cwd="~/linkright">linkright init</ShPrompt>

          <div style={{ padding: "12px 0 8px", display: "flex", alignItems: "center", gap: 14 }}>
            <AsciiPip pose="wave" size={18} />
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 12.5 }}>
              <span style={{ color: "#FF5733", fontWeight: 600 }}>pip ›</span>{" "}
              <span style={{ color: "#EEF5F2" }}>welcome — 6 questions, 90 seconds.</span>
            </div>
          </div>

          <div style={{ borderTop: "1px solid #253140", margin: "8px 0" }} />

          <ShEcho label="Name" value="Satvik Jain" />
          <ShEcho label="Email" value="satvik@linkright.in" />
          <ShEcho label="Target role" value="Senior PM, AI infra" />
          <ShEcho label="Location" value="Bangalore · remote-friendly" />

          <div style={{ borderTop: "1px solid #253140", margin: "10px 0" }} />

          <ShInput label="Years of PM experience" focused value="4" hint="we'll calibrate signal weighting" accent="#06B6D4" />

          <ShPicker
            title="Which LLM provider?"
            items={["Ollama (local · free · slower)", "Anthropic Claude (paid · fast)", "OpenAI GPT-4o (paid · fast)", "Google Gemini (paid · fast)"]}
            selected={0}
          />
          <div style={{ marginLeft: 22, fontSize: 10.5, color: "#8E8E93" }}>↑↓ navigate  ·  Enter to select  ·  Esc cancel</div>
        </ShellWindow>

        {/* Right — onboard (multi-select boards) */}
        <ShellWindow size="100×34" title="linkright onboard">
          <ShPrompt cwd="~/linkright">linkright onboard</ShPrompt>

          <div style={{ padding: "8px 0", display: "flex", alignItems: "center", gap: 14 }}>
            <AsciiPip pose="pointing" size={16} />
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 12 }}>
              <span style={{ color: "#FF5733", fontWeight: 600 }}>pip ›</span>{" "}
              <span style={{ color: "#EEF5F2" }}>tell me where you want to be seen.</span>
            </div>
          </div>

          <ShRule label="step 3 of 6" />

          <div style={{ display: "flex", gap: 8, alignItems: "baseline", fontSize: 12.5, marginBottom: 6 }}>
            <span style={{ color: "#F4B400" }}>◆</span>
            <span style={{ color: "#EEF5F2", fontWeight: 600 }}>Job boards to scan</span>
          </div>
          {[
            { on: true, board: "LinkedIn", note: "personal connections + Easy Apply" },
            { on: true, board: "Greenhouse", note: "ATS · most YC + late-stage" },
            { on: false, board: "Lever", note: "ATS · early-stage SaaS" },
            { on: true, board: "Ashby", note: "ATS · AI-native co's (Anthropic, Mistral)" },
            { on: false, board: "Wellfound (AngelList)", note: "early-stage / startup-only" },
            { on: true, board: "Workable", note: "ATS · enterprise + EU" },
          ].map((b) => (
            <div key={b.board} style={{ fontSize: 12, padding: "1px 0", display: "flex", gap: 8, alignItems: "baseline" }}>
              <span style={{ color: b.on ? "#E5B80B" : "#5A6B7C", fontWeight: 700 }}>{b.on ? "[v]" : "[ ]"}</span>
              <span style={{ color: b.on ? "#EEF5F2" : "#8FA3B1", fontWeight: b.on ? 500 : 400 }}>{b.board}</span>
              <span style={{ color: "#8E8E93", marginLeft: "auto" }}>{b.note}</span>
            </div>
          ))}
          <div style={{ marginTop: 4, fontSize: 10.5, color: "#8E8E93" }}>Space to toggle  ·  Enter to confirm  ·  Esc cancel</div>

          <div style={{ borderTop: "1px solid #253140", margin: "10px 0 8px" }} />

          <div style={{ display: "flex", gap: 8, alignItems: "baseline", fontSize: 12.5 }}>
            <span style={{ color: "#F4B400" }}>◆</span>
            <span style={{ color: "#EEF5F2", fontWeight: 600 }}>What kind of role narrative?</span>
          </div>
          <ShPicker
            items={[
              "AI-native operator (the bet you're making)",
              "Senior PM with AI as a tool",
              "PM-to-Founder (build-in-public lean)",
              "Type something…",
            ]}
            selected={0}
          />
        </ShellWindow>
      </div>
    </BoardShell>
  );
}

/* =========================================================================
   04 · DOCTOR / AUTH — status events + masked input + ✓/✗
   ========================================================================= */
function CliDoctorArtboard() {
  return (
    <BoardShell
      eyebrow="04 · linkright doctor  ·  linkright auth login"
      title="Health check. Auth login. Status events end-to-end."
      blurb="The diagnostic surface. Every line is a status_event (✓ green · ✗ red · muted detail). Login uses a ◇ masked input. Pip listens patiently; he doesn't celebrate until every check is green."
      footnote={<>entry: <code>linkright.cli:doctor</code> · <code>auth.cli</code><br />uses: status_event · lr_password · insight_block</>}
    >
      <div style={{ display: "grid", gridTemplateColumns: "1.3fr 1fr", gap: 18, flex: 1, minHeight: 0 }}>
        {/* doctor */}
        <ShellWindow size="120×34" title="linkright doctor">
          <ShPrompt cwd="~/linkright">linkright doctor</ShPrompt>

          <div style={{ padding: "8px 0", display: "flex", alignItems: "center", gap: 14 }}>
            <AsciiPip pose="scout" size={16} />
            <div style={{ fontFamily: "ui-monospace", fontSize: 12 }}>
              <span style={{ color: "#FF5733", fontWeight: 600 }}>pip ›</span>{" "}
              <span style={{ color: "#EEF5F2" }}>let me look around.</span>
            </div>
          </div>

          <ShSection>Environment</ShSection>
          <ShStatus ok={true} label="Python 3.11.9" detail="≥ 3.10 required" />
          <ShStatus ok={true} label="MongoDB" detail="localhost:27017 · 12 collections" />
          <ShStatus ok={true} label="~/.linkright/" detail="initialized · 4 evidence files" />

          <ShSection>API keys (3 live, 1 missing)</ShSection>
          <ShStatus ok={true} label="ANTHROPIC_API_KEY" detail="sk-ant-…ef9c · valid · 200 OK" />
          <ShStatus ok={true} label="OPENAI_API_KEY" detail="sk-…7a31 · valid · 200 OK" />
          <ShStatus ok={true} label="OLLAMA local" detail="gemma3:1b · phi3:mini available" />
          <ShStatus ok={false} label="GEMINI_API_KEY" detail="not set · run `linkright keys add gemini`" />

          <ShSection>Optional</ShSection>
          <ShStatus ok={false} label="Chrome CDP (for `watch`)" detail="port 9222 closed · open Chrome with --remote-debugging-port=9222" />

          <ShInsight title="Suggestion">
            <div>You can skip Gemini — Claude + Ollama covers every command.</div>
            <div style={{ color: "#8E8E93", marginTop: 2 }}>— `watch` only matters if you want passive job-page capture.</div>
          </ShInsight>

          <ShResult>11 of 13 checks passed. You're ready to tailor.</ShResult>
        </ShellWindow>

        {/* auth login */}
        <ShellWindow size="100×34" title="linkright auth login">
          <ShPrompt cwd="~/linkright">linkright auth login</ShPrompt>

          <div style={{ padding: "8px 0", display: "flex", alignItems: "center", gap: 14 }}>
            <AsciiPip pose="listening" size={16} />
            <div style={{ fontFamily: "ui-monospace", fontSize: 12 }}>
              <span style={{ color: "#FF5733", fontWeight: 600 }}>pip ›</span>{" "}
              <span style={{ color: "#EEF5F2" }}>one-time code · 60 seconds.</span>
            </div>
          </div>

          <ShInput label="Email" focused={false} value="satvik@linkright.in" hint="account we'll send the code to" accent="#06B6D4" />

          <div style={{ display: "flex", gap: 8, alignItems: "baseline", fontSize: 12.5, padding: "1px 0" }}>
            <span style={{ color: "#34A853", fontWeight: 700 }}>✓</span>
            <span>Code sent</span>
            <span style={{ color: "#8E8E93" }}>check inbox for "LinkRight: your code"</span>
          </div>

          <ShInput label="One-time code" focused value="•••••" hint="6 digits · expires in 0:54" accent="#06B6D4" />

          <ShWork verb="Verifying with sync.linkright.in…" telemetry="(0.4s)" icon="*" />
          <ShStatus ok={true} label="Authenticated" detail="session · ~/.linkright/auth.json (mode 600)" />

          <div style={{ borderTop: "1px solid #253140", margin: "10px 0" }} />

          <ShResult>You can now run `linkright jobs scout` and `linkright jobs apply`.</ShResult>
          <div style={{ fontSize: 11, color: "#8E8E93", padding: "2px 0" }}>· Session: 2026-05-13-2a1f  ·  Plan: BASE  ·  Expires: 30d</div>
        </ShellWindow>
      </div>
    </BoardShell>
  );
}

/* =========================================================================
   05 · CRITIQUE / FILL — insight blocks + gap analysis + apply-fix picker
   ========================================================================= */
function CliCritiqueArtboard() {
  return (
    <BoardShell
      eyebrow="05 · linkright critique  ·  linkright fill"
      title="LLM review → insights → resolve. The honest mirror."
      blurb="Critique surfaces issues as `★ Insight` blocks (coral rule above + below). `fill` then walks each gap with a picker — accept the suggestion, edit it, type your own, or skip. Pip is in flat mode (no celebration; this is feedback)."
      footnote={<>entry: <code>resume.cli:critique</code> · <code>enrich.cli</code><br />uses: insight_block · lr_select_with_custom · TYPE_SOMETHING</>}
    >
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 18, flex: 1, minHeight: 0 }}>
        <ShellWindow size="100×38" title="linkright critique">
          <ShPrompt cwd="~/linkright">linkright critique</ShPrompt>

          <div style={{ padding: "8px 0", display: "flex", alignItems: "center", gap: 14 }}>
            <AsciiPip pose="flat" size={16} />
            <div style={{ fontFamily: "ui-monospace", fontSize: 12 }}>
              <span style={{ color: "#FF5733", fontWeight: 600 }}>pip ›</span>{" "}
              <span style={{ color: "#EEF5F2" }}>4 issues. nothing fatal.</span>
            </div>
          </div>

          <ShInsight title="Insight · 01 / Lead bullet buries the metric">
            <div style={{ color: "#8E8E93" }}>Current:</div>
            <div>"Led activation experiments across the consumer app"</div>
            <div style={{ color: "#8E8E93", marginTop: 6 }}>— rewrite as evidence-first:</div>
            <div style={{ color: "#0FBEAF" }}>"Lifted 30-day activation 31% (5.4M users) via 9-arm onboarding test"</div>
          </ShInsight>

          <ShInsight title="Insight · 02 / 'AI' appears 7 times — none with evidence">
            <div>Bullets 02, 05, 09 say "AI-powered" without naming the model, the task, or the lift.</div>
            <div style={{ color: "#8E8E93", marginTop: 4 }}>— either cite the model + lift, or remove the word.</div>
          </ShInsight>

          <ShInsight title="Insight · 03 / One sentence runs 38 words">
            <div>Bullet 11 is unreadable. Cut to 18-22 words.</div>
          </ShInsight>

          <div style={{ borderTop: "1px solid #253140", margin: "8px 0" }} />

          <ShResult>Run `linkright fill` to resolve interactively, or `linkright tailor --apply-critique` to auto-apply 2 of 4.</ShResult>
        </ShellWindow>

        <ShellWindow size="100×38" title="linkright fill">
          <ShPrompt cwd="~/linkright">linkright fill</ShPrompt>

          <div style={{ padding: "8px 0", display: "flex", alignItems: "center", gap: 14 }}>
            <AsciiPip pose="thinking" size={16} />
            <div style={{ fontFamily: "ui-monospace", fontSize: 12 }}>
              <span style={{ color: "#FF5733", fontWeight: 600 }}>pip ›</span>{" "}
              <span style={{ color: "#EEF5F2" }}>gap 01 of 03. your call.</span>
            </div>
          </div>

          <ShRule label="missing metric · bullet 03" />

          <div style={{ fontSize: 12, color: "#8FA3B1", lineHeight: 1.7 }}>
            <span style={{ color: "#8E8E93" }}>Current bullet:</span><br />
            <span style={{ color: "#EEF5F2" }}>"Shipped pricing experiments that helped revenue"</span>
          </div>

          <div style={{ borderTop: "1px solid #253140", margin: "10px 0" }} />

          <div style={{ display: "flex", gap: 8, alignItems: "baseline", fontSize: 12.5, marginBottom: 4 }}>
            <span style={{ color: "#F4B400" }}>◆</span>
            <span style={{ color: "#EEF5F2", fontWeight: 600 }}>How much revenue lift?</span>
          </div>
          <ShPicker
            items={[
              "+18% MRR (Q4 2024)",
              "+$2.4M ARR (annualized)",
              "+30bp gross margin",
              "Type something…",
            ]}
            selected={1}
          />
          <div style={{ marginLeft: 22, fontSize: 10.5, color: "#8E8E93" }}>↑↓ navigate  ·  Enter to select  ·  Esc to skip</div>

          <div style={{ borderTop: "1px solid #253140", margin: "10px 0" }} />

          <ShEcho value="Selected: +$2.4M ARR (annualized)" />
          <ShResult>Rewriting bullet 03…</ShResult>
          <div style={{ fontSize: 12, color: "#5EB3A8", paddingLeft: 18 }}>"Drove +$2.4M ARR via 6-week pricing test (3 cohorts, 4 price points)"</div>

          <div style={{ borderTop: "1px solid #253140", margin: "10px 0 6px" }} />

          <ShStatus ok={true} label="Gap 01 resolved" detail="2 to go" />
        </ShellWindow>
      </div>
    </BoardShell>
  );
}

/* =========================================================================
   06 · PRACTICE — interview prep, tab bar, ASCII pip with book
   ========================================================================= */
function CliPracticeArtboard() {
  return (
    <BoardShell
      eyebrow="06 · linkright practice"
      title="Interview prep. Tab-bar across question types. Pip with the book."
      blurb="Practice mode opens a tabbed session: Behavioural · Product · Strategy · Technical · Negotiation. Tab toggles via Tab key. Pip switches to `interview` pose (book in front). Live answer scoring uses status events; the insight block surfaces what to do better."
      footnote={<>entry: <code>interview.cli</code> · <code>coach.session</code><br />uses: tab_bar · insight_block · progress_verb · status_event</>}
    >
      <ShellWindow size="120×40" style={{ flex: 1 }}>
        <ShPrompt cwd="~/linkright">linkright practice --role "Senior PM, AI infra"</ShPrompt>

        <div style={{ padding: "8px 0 4px", display: "flex", alignItems: "center", gap: 16 }}>
          <AsciiPip pose="interview" size={20} />
          <div style={{ fontFamily: "ui-monospace", fontSize: 12.5 }}>
            <span style={{ color: "#FF5733", fontWeight: 600 }}>pip ›</span>{" "}
            <span style={{ color: "#EEF5F2" }}>5 question types. say "skip" to move on. say "again" to retry.</span>
          </div>
        </div>

        <ShTabs items={["Behavioural", "Product", "Strategy", "Technical", "Negotiation"]} current={1} />

        <div style={{ borderTop: "1px solid #253140", margin: "10px 0 8px" }} />

        <div style={{ display: "flex", gap: 8, alignItems: "baseline", fontSize: 12.5 }}>
          <span style={{ color: "#F4B400" }}>◆</span>
          <span style={{ color: "#EEF5F2", fontWeight: 700 }}>Q3 / 8</span>
          <span style={{ color: "#8E8E93" }}>· product · medium · est 4 min</span>
        </div>
        <div style={{ fontSize: 13, color: "#EEF5F2", padding: "6px 0 12px 18px", lineHeight: 1.55 }}>
          "Anthropic ships Claude Code. Day 1 you're the PM. Pick the metric you'll defend in front of Dario, and how you'll move it 20% in 90 days."
        </div>

        <ShRule label="your answer (voice or type)" />

        <ShWork verb="Listening…" telemetry="(0:18 · 1.2k words est)" icon="*" />
        <ShWork verb="Scoring against rubric…" telemetry="(0.6s · 4 dimensions)" icon="+" />

        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10, padding: "10px 0" }}>
          {[
            { dim: "Metric clarity", score: "8 / 10", color: "#34A853" },
            { dim: "Tradeoff depth", score: "6 / 10", color: "#F4B400" },
            { dim: "Operational specificity", score: "9 / 10", color: "#34A853" },
            { dim: "Executive framing", score: "5 / 10", color: "#EE6F4F" },
          ].map((s) => (
            <div key={s.dim} style={{ background: "#151F2B", border: `1px solid ${s.color}40`, borderRadius: 8, padding: "8px 10px" }}>
              <div style={{ fontSize: 10.5, color: "#8E8E93", letterSpacing: "0.08em", textTransform: "uppercase" }}>{s.dim}</div>
              <div style={{ fontSize: 16, color: s.color, fontWeight: 700, fontFamily: "ui-monospace" }}>{s.score}</div>
            </div>
          ))}
        </div>

        <ShInsight title="Insight · executive framing (5/10)">
          <div>You named the metric (daily active code-edit sessions) but you didn't tie it to revenue, retention, or the strategic bet. Dario will ask "why this and not retention?" within 30 seconds.</div>
          <div style={{ color: "#8E8E93", marginTop: 4 }}>— add one sentence: "This is the leading indicator for seat expansion; retention follows at 60-day lag."</div>
        </ShInsight>

        <div style={{ display: "flex", gap: 14, marginTop: 6 }}>
          <ShResult>Score saved · ~/.linkright/coach/session-2a1f.json</ShResult>
        </div>
        <ShMeta pairs={[["Session", "2a1f"], ["Model", "claude-3-5-sonnet"], ["Tokens", "4.2k"], ["Cost", "$0.04"]]} />
      </ShellWindow>
    </BoardShell>
  );
}

/* =========================================================================
   07 · JOBS SCOUT — long-running task + coffee Pip + multi-board scan
   ========================================================================= */
function CliJobsScoutArtboard() {
  return (
    <BoardShell
      eyebrow="07 · linkright jobs scout"
      title="The long task. 12 boards. Pip grabs coffee."
      blurb="A scan that runs ~90 seconds. Pip switches to `coffee` pose — subtle joke for users staring at output. Progress streams per board with the coral working verb. Matches collect into a results table; the insight block surfaces the best one."
      footnote={<>entry: <code>jobsearch.cli:scout</code><br />uses: progress_verb · status_event · result_arrow · sticky_footer</>}
    >
      <ShellWindow size="140×40" style={{ flex: 1 }}>
        <ShPrompt cwd="~/linkright">linkright jobs scout --boards 12 --since 7d</ShPrompt>

        <div style={{ padding: "8px 0 4px", display: "flex", alignItems: "center", gap: 16 }}>
          <AsciiPip pose="coffee" size={22} />
          <div style={{ fontFamily: "ui-monospace", fontSize: 12.5 }}>
            <span style={{ color: "#FF5733", fontWeight: 600 }}>pip ›</span>{" "}
            <span style={{ color: "#EEF5F2" }}>this one's deep. fetching 12 boards. ~90s.</span>
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginTop: 8 }}>
          {/* Live work column */}
          <div>
            <ShSection>Live scan</ShSection>
            <ShWork verb="LinkedIn · Easy Apply · pm/AI…" telemetry="(2.1s · 47 hits)" icon="*" />
            <ShWork verb="Greenhouse · senior pm/AI infra…" telemetry="(3.4s · 23 hits)" icon="*" />
            <div style={{ display: "flex", gap: 8, alignItems: "baseline", fontSize: 12.5 }}>
              <span style={{ color: "#0FBEAF", fontWeight: 700 }}>●</span><span>Ashby · ai-native co's</span><span style={{ color: "#8E8E93" }}>1.2s · 11 hits</span>
            </div>
            <div style={{ display: "flex", gap: 8, alignItems: "baseline", fontSize: 12.5 }}>
              <span style={{ color: "#0FBEAF", fontWeight: 700 }}>●</span><span>Workable · EU + enterprise</span><span style={{ color: "#8E8E93" }}>0.8s · 6 hits</span>
            </div>
            <ShWork verb="Lever · early-stage SaaS…" telemetry="(0:14)" icon="*" />
            <ShWork verb="Wellfound · founder-style…" telemetry="(0:18)" icon="+" />

            <div style={{ borderTop: "1px solid #253140", margin: "10px 0" }} />
            <div style={{ fontSize: 11.5, color: "#8E8E93", fontFamily: "ui-monospace" }}>
              progress: 5 of 12 boards · 87 raw hits · 23 after JD-fit filter (≥ 78% match)
            </div>
            <div style={{ fontFamily: "ui-monospace", marginTop: 6, display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ color: "#0FBEAF" }}>{"█".repeat(10)}</span>
              <span style={{ color: "#5A6B7C" }}>{"░".repeat(14)}</span>
              <span style={{ color: "#EEF5F2", fontSize: 11 }}>42%</span>
            </div>
          </div>

          {/* Results column */}
          <div>
            <ShSection>Top matches so far</ShSection>
            {[
              { co: "Anthropic", role: "PM, Claude Code", loc: "SF · remote", fit: "94%", color: "#0FBEAF" },
              { co: "Vercel", role: "PM, AI Apps", loc: "remote · global", fit: "89%", color: "#0FBEAF" },
              { co: "Notion AI", role: "PM, Workspace AI", loc: "SF · NYC", fit: "85%", color: "#34A853" },
              { co: "Cursor", role: "PM, Editor", loc: "SF", fit: "82%", color: "#34A853" },
              { co: "Linear", role: "Senior PM", loc: "remote · EU", fit: "78%", color: "#F4B400" },
            ].map((j) => (
              <div key={j.co} style={{ display: "grid", gridTemplateColumns: "120px 1fr 130px 60px", gap: 8, fontSize: 12, padding: "4px 0", borderBottom: "1px dashed #253140" }}>
                <span style={{ color: "#EEF5F2", fontWeight: 600 }}>{j.co}</span>
                <span style={{ color: "#8FA3B1" }}>{j.role}</span>
                <span style={{ color: "#8E8E93" }}>{j.loc}</span>
                <span style={{ color: j.color, fontFamily: "ui-monospace", textAlign: "right", fontWeight: 700 }}>{j.fit}</span>
              </div>
            ))}
            <ShInsight title="Pip suggests">
              <div>Anthropic · PM, Claude Code · 94% fit. JD names "operator-PM with AI infra" — your top-3 evidence cluster.</div>
              <div style={{ color: "#8E8E93", marginTop: 2 }}>— `linkright apply anthropic-claude-code`</div>
            </ShInsight>
          </div>
        </div>

        <div style={{ borderTop: "1px solid #253140", margin: "10px 0 0" }} />
        <ShMeta pairs={[["Boards", "5/12"], ["ETA", "0:54"], ["Cache", "stale 14m"], ["Model", "haiku-3.5"]]} />
      </ShellWindow>
    </BoardShell>
  );
}

/* =========================================================================
   08 · ERROR / BLOCKED — Pip flat, single sweat drop, recovery path
   ========================================================================= */
function CliErrorArtboard() {
  return (
    <BoardShell
      eyebrow="08 · errors · blocked · recovery"
      title="Pip never panics. He asks for what he needs."
      blurb="No red walls. No traceback dumps. Failures render as a single coral exclamation, a one-line muted reason, and a recovery picker. Pip's eyes go flat with a single sweat drop. The user is always offered a path forward."
      footnote={<>uses: status (fail) · muted_detail · lr_select · TYPE_SOMETHING</>}
    >
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 14, flex: 1, minHeight: 0 }}>
        {/* Empty JD */}
        <ShellWindow size="80×24" title="apply · empty JD" dense>
          <ShPrompt cwd="~/linkright">linkright apply</ShPrompt>
          <div style={{ padding: "6px 0", display: "flex", alignItems: "center", gap: 10 }}>
            <AsciiPip pose="retry" size={14} />
            <div style={{ fontFamily: "ui-monospace", fontSize: 11.5 }}>
              <span style={{ color: "#FF5733", fontWeight: 600 }}>pip ›</span>{" "}
              <span style={{ color: "#EEF5F2" }}>JD's empty. paste it again?</span>
            </div>
          </div>
          <div style={{ display: "flex", gap: 8, alignItems: "baseline", fontSize: 12, marginTop: 2 }}>
            <span style={{ color: "#EE6F4F", fontWeight: 700 }}>!</span>
            <span style={{ color: "#EEF5F2" }}>no JD found at stdin</span>
          </div>
          <div style={{ fontSize: 11, color: "#8E8E93", paddingLeft: 14, marginTop: 2 }}>· tried: stdin · -j flag · ~/.linkright/last_jd</div>
          <ShRule />
          <ShPicker
            title="What now?"
            items={["Paste JD now", "Re-run with -j path/to/jd.md", "Pull last JD from clipboard"]}
            selected={0}
          />
        </ShellWindow>

        {/* API key missing */}
        <ShellWindow size="80×24" title="bullets · key missing" dense>
          <ShPrompt cwd="~/linkright">linkright bullets --rewrite</ShPrompt>
          <div style={{ padding: "6px 0", display: "flex", alignItems: "center", gap: 10 }}>
            <AsciiPip pose="thinking" size={14} />
            <div style={{ fontFamily: "ui-monospace", fontSize: 11.5 }}>
              <span style={{ color: "#FF5733", fontWeight: 600 }}>pip ›</span>{" "}
              <span style={{ color: "#EEF5F2" }}>no anthropic key. ollama works too.</span>
            </div>
          </div>
          <ShStatus ok={false} label="ANTHROPIC_API_KEY" detail="not set" />
          <div style={{ fontSize: 11, color: "#8E8E93", paddingLeft: 14 }}>· checked: env · ~/.linkright/keys.json · macOS keychain</div>
          <ShRule />
          <ShPicker
            title="Use which model?"
            items={["Switch to local Ollama (free)", "Paste an Anthropic key", "Use OpenAI (key is set)", "Abort"]}
            selected={0}
          />
        </ShellWindow>

        {/* Width overflow */}
        <ShellWindow size="80×24" title="tailor · pdf overflow" dense>
          <ShPrompt cwd="~/linkright">linkright tailor -j jd.md</ShPrompt>
          <div style={{ padding: "6px 0", display: "flex", alignItems: "center", gap: 10 }}>
            <AsciiPip pose="flat" size={14} />
            <div style={{ fontFamily: "ui-monospace", fontSize: 11.5 }}>
              <span style={{ color: "#FF5733", fontWeight: 600 }}>pip ›</span>{" "}
              <span style={{ color: "#EEF5F2" }}>bullet 03 spills. tight call.</span>
            </div>
          </div>
          <div style={{ fontSize: 12, color: "#EEF5F2" }}>
            <span style={{ color: "#EE6F4F", fontWeight: 700 }}>! </span>
            page-fit · bullet 03 overflows by 4 px
          </div>
          <div style={{ fontSize: 11, color: "#8E8E93", paddingLeft: 14 }}>· 102.1% width fill · target ≤ 99%</div>
          <ShRule />
          <ShPicker
            title="Pip suggests"
            items={[
              "Auto-shrink: drop 'AI infra' qualifier",
              "Swap to template B (looser kerning)",
              "Manual edit (opens $EDITOR)",
              "Ship anyway (1pt overflow)",
            ]}
            selected={0}
          />
        </ShellWindow>
      </div>

      <PipNote
        pose="happy"
        line="rule of thumb · never show a stack trace at the top level."
        sub="if you must, hide it behind `linkright --verbose` or `~/.linkright/logs/last_run.log`."
      />
    </BoardShell>
  );
}

Object.assign(window, {
  CliBootArtboard,
  CliTailorArtboard,
  CliOnboardArtboard,
  CliDoctorArtboard,
  CliCritiqueArtboard,
  CliPracticeArtboard,
  CliJobsScoutArtboard,
  CliErrorArtboard,
});
