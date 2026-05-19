/* =========================================================================
   sections-cc-true.jsx — LinkRight CLI v2, rendered to Claude-Code TUI
   conventions verbatim. Every artboard is one phase from
   cc-frontend-design/BUILD-INSTRUCTIONS.md §5.

   Pip stays as the LinkRight mascot but recedes — he lives in the banner
   row and the welcome line, never on the tool cards or in the chrome.
   The TUI itself is pure CC.
   ========================================================================= */

/* ----- Shared header for each board ----- */
function CCBoard({ phase, title, blurb, sources, children }) {
  return (
    <div style={{
      width: "100%", height: "100%",
      background: "var(--color-surface)",
      padding: "40px 48px",
      boxSizing: "border-box",
      fontFamily: "var(--font-sans)",
      color: "var(--color-foreground)",
      display: "flex", flexDirection: "column", gap: 18,
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", gap: 32 }}>
        <div style={{ maxWidth: 980 }}>
          <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.16em", textTransform: "uppercase", color: "var(--color-accent)" }}>
            {phase}
          </div>
          <h2 style={{ fontSize: 32, fontWeight: 800, letterSpacing: "-0.025em", margin: "10px 0 0", lineHeight: 1.05 }}>
            {title}
          </h2>
          {blurb && (
            <div style={{ fontSize: 13.5, color: "var(--color-muted)", marginTop: 8, lineHeight: 1.55, maxWidth: 880 }}>
              {blurb}
            </div>
          )}
        </div>
        {sources && (
          <div style={{ fontFamily: "var(--font-mono)", fontSize: 10.5, color: "var(--color-muted)", textAlign: "right", lineHeight: 1.55 }}>
            sources<br />
            {sources.map((s, i) => <div key={i}>{s}</div>)}
          </div>
        )}
      </div>
      {children}
    </div>
  );
}

/* =========================================================================
   00 · The Primitive Crosswalk — LR house style ↔ CC verbatim
   ========================================================================= */
function CCCrosswalkArtboard() {
  const rows = [
    { lr: "◆ section header",       lrColor: "#F4B400", cc: "(no glyph)",       ccDesc: "bold + dim suffix · \\x1b[1m \\x1b[2m" },
    { lr: "◇ input marker (cyan)",  lrColor: "#06B6D4", cc: "bordered box",     ccDesc: "input is a <Box borderStyle=\"round\">, not a glyph" },
    { lr: "●  step done (teal)",    lrColor: "#0FBEAF", cc: "● done (green)",   ccDesc: "tool card status — green ●" },
    { lr: "★  insight (coral)",     lrColor: "#FF8B6E", cc: "(no insight)",     ccDesc: "CC has no \"insight block\"; uses tip/hint line" },
    { lr: "*  working (coral)",     lrColor: "#EE6F4F", cc: "⠋⠙⠹⠸… (braille)", ccDesc: "10-frame braille spinner @ 80ms · 191 verbs" },
    { lr: "+  thinking (green)",    lrColor: "#34A853", cc: "⠋ Thinking…",      ccDesc: "same spinner; verb = Thinking when no tool yet" },
    { lr: "✓ success (green)",      lrColor: "#34A853", cc: "✓ success",        ccDesc: "kept · same convention" },
    { lr: "✗ fail (red)",           lrColor: "#EA4335", cc: "✗ fail",           ccDesc: "kept · same convention" },
    { lr: "→ result arrow",         lrColor: "#5EB3A8", cc: "⎿ output",         ccDesc: "tool output uses ⎿ (U+23BF) connector, not →" },
    { lr: "└ tip / branch",         lrColor: "#8E8E93", cc: "(rare in CC)",     ccDesc: "CC uses inline dim text · 'Tip:' prefix" },
    { lr: "⊗ active tab",           lrColor: "#0FBEAF", cc: "(no tabs)",        ccDesc: "CC has no tab bar — slash palette + focus mgmt instead" },
    { lr: "[v0.9.2] sticky footer", lrColor: "#F4B400", cc: "statusLine",       ccDesc: "subprocess output, ANSI-styled by the user's script" },
    { lr: "TUI house copy",         lrColor: "#EE6F4F", cc: "dim is voice",     ccDesc: "\\x1b[2m runs 2961× — the dominant aesthetic" },
    { lr: "Sectioned tree (├ └)",   lrColor: "#0FBEAF", cc: "<Static> log",     ccDesc: "committed messages mounted once; live tail re-renders" },
  ];

  return (
    <CCBoard
      phase="00 · Crosswalk · LR house style → CC verbatim"
      title="Where the design system diverges from Claude Code."
      blurb="The current LinkRight TUI uses a richer iconography (◆ section, ◇ input, ★ insight) and a horizontal divider/tab/footer system. CC is leaner: dim is the voice, one bordered input, one spinner, one ⎿-connector. This crosswalk is the rulebook for v2 surfaces."
      sources={["02-rendering.md · 05-color-theme.md", "09-tool-render.md · CHEATSHEET.md"]}
    >
      <div style={{ display: "grid", gridTemplateColumns: "0.9fr 0.9fr 1.4fr", gap: 0, flex: 1, border: "1px solid var(--color-border)", borderRadius: 10, overflow: "hidden" }}>
        {/* header */}
        <div style={{ padding: "12px 16px", background: "var(--color-skin-50)", fontSize: 11, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--color-muted)", borderBottom: "1px solid var(--color-border)" }}>LinkRight house</div>
        <div style={{ padding: "12px 16px", background: "#0E1118", fontSize: 11, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#E5E5E5", borderBottom: "1px solid var(--color-border)" }}>Claude Code v2.1.143</div>
        <div style={{ padding: "12px 16px", background: "var(--color-skin-50)", fontSize: 11, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--color-muted)", borderBottom: "1px solid var(--color-border)" }}>Notes / source</div>

        {rows.map((r, i) => (
          <React.Fragment key={i}>
            <div style={{ padding: "10px 16px", borderBottom: i === rows.length - 1 ? "none" : "1px solid var(--color-border)", fontFamily: "var(--font-mono)", fontSize: 12.5, color: "var(--color-foreground)", display: "flex", alignItems: "baseline", gap: 8 }}>
              <span style={{ color: r.lrColor, fontSize: 14, fontWeight: 700, fontFamily: "ui-monospace" }}>{r.lr.charAt(0)}</span>
              <span>{r.lr.slice(2)}</span>
            </div>
            <div style={{ padding: "10px 16px", borderBottom: i === rows.length - 1 ? "none" : "1px solid #1B202B", fontFamily: "var(--font-mono)", fontSize: 12.5, color: "#E5E5E5", background: "#0E1118" }}>
              {r.cc}
            </div>
            <div style={{ padding: "10px 16px", borderBottom: i === rows.length - 1 ? "none" : "1px solid var(--color-border)", fontFamily: "var(--font-mono)", fontSize: 11.5, color: "var(--color-muted)" }}>
              {r.ccDesc}
            </div>
          </React.Fragment>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: 8, paddingTop: 4 }}>
        {[
          { hex: "#E55353", role: "red · errors · removed lines",     ansi: "\\x1b[31m" },
          { hex: "#62C264", role: "green · success · added · ●",      ansi: "\\x1b[32m" },
          { hex: "#D6BA5B", role: "yellow · warnings · running",      ansi: "\\x1b[33m" },
          { hex: "#5C9DD9", role: "blue · info",                      ansi: "\\x1b[34m" },
          { hex: "#B870C5", role: "magenta · plan mode",              ansi: "\\x1b[35m" },
          { hex: "#5BC0D0", role: "cyan · keys · slash · links",      ansi: "\\x1b[36m" },
          { hex: "#F5C842", role: "bright yellow · diff hunks",       ansi: "\\x1b[93m" },
        ].map((c) => (
          <div key={c.hex} style={{ fontFamily: "var(--font-mono)", fontSize: 10.5, lineHeight: 1.4 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <span style={{ width: 14, height: 14, borderRadius: 3, background: c.hex }} />
              <span style={{ color: "var(--color-foreground)", fontWeight: 700 }}>{c.hex}</span>
            </div>
            <div style={{ color: "var(--color-muted)", marginTop: 2 }}>{c.role}</div>
            <div style={{ color: "var(--color-accent)", marginTop: 2 }}>{c.ansi}</div>
          </div>
        ))}
      </div>

      <ImplNote
        files={["linkright/ui/theme.py", "linkright/ui/icons.py", "linkright/ui/patterns.py"]}
        summary="Start here — 3 files to update before anything else."
        steps={[
          "In `theme.py`: add `\"tui.cyan_bold\": \"#5BC0D0 bold\"` and verify `tui.green` is `#62C264` (not `#34A853`). The green token is used for ALL success ● glyphs.",
          "In `theme.py`: `step.accent` (teal ●) is the old 'done' colour — change to `tui.green` so step_done() renders green not teal.",
          "In `icons.py`: `ICON.working = \"*\"` → remove from active use once spinner is added. `ICON.prompt = \"›\"` → stays, but ensure `ICON.prompt_bold = \"❯\"` is used in pickers.",
          "In `patterns.py`: `insight_block()` outputs `★` in coral — this LR-house pattern has NO CC equivalent. Replace every `insight_block()` call with a plain dim `Tip:` line instead.",
          "In `patterns.py`: `sticky_footer()` / `tab_bar()` → remove from all surfaces. StatusLine subprocess replaces them (see artboard H).",
          "Verify `NO_COLOR=1` renders cleanly: run `NO_COLOR=1 linkright tldr` and ensure all text is readable without ANSI codes.",
        ]}
        warn="Do NOT break backward-compat on `step.gold`, `tui.coral`, `step.accent` until every call site is updated. Add new aliases first, migrate callsites, then remove old aliases."
      />
    </CCBoard>
  );
}

/* =========================================================================
   B · The skeleton — Static log + live tail + bordered input + status
   ========================================================================= */
function CCSkeletonArtboard() {
  return (
    <CCBoard
      phase="B · Skeleton · Static log + live tail + input + status"
      title="The whole shell, in one Ink scaffold."
      blurb="Committed turns mount inside <Static> (never re-rendered). The streaming turn lives in a normal <Box> beneath it — re-renders every chunk. Bordered round input below, statusLine subprocess at the very bottom. This skeleton is the load-bearing pattern; every other surface composes from here."
      sources={["02-rendering.md (Static trick)", "11-repro-ink-clone.md (App shell)"]}
    >
      <CCShell title="linkright · session 7a2f" size="120×36" style={{ flex: 1 }}>
        {/* welcome */}
        <CCWelcomeBanner subtitle="Local-first career OS · v2.0 · pip ready">
          Welcome to LinkRight for Satvik Jain
        </CCWelcomeBanner>

        {/* === <Static> committed log === */}
        <div style={{ flex: 1, overflow: "hidden" }}>
          <CCUserTurn>tailor this for the Anthropic PM, Claude Code role</CCUserTurn>

          <CCToolCard tool="Read" args="jd/anthropic-claude-code-pm.md" status="done">
            Returns: 142 lines
          </CCToolCard>

          <CCToolCard tool="Grep" args='"operator", "infra"' status="done">
            7 matches in 3 files
          </CCToolCard>

          <CCAssistant>
            <span>I'll tailor against 14 evidence nuggets — top cluster: </span>
            <span style={{ color: CC.cyan }}>operator-PM with AI infra</span>
            <span>. Let me draft the bullets, then we'll review.</span>
          </CCAssistant>

          <CCToolCard tool="Edit" args="resume/master.md" status="done">
            Updated 12 lines (5 added, 4 removed, 3 modified)
          </CCToolCard>

          {/* === live tail (streaming turn) === */}
          <div style={{ borderTop: `1px dashed ${CC.borderD}`, paddingTop: 8, marginTop: 6 }}>
            <div style={{ fontSize: 10, color: CC.dim, letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 4 }}>↓ live tail (re-renders on every token)</div>
            <CCSpinner verb="Scoring" tip="run /critique after this to surface anything I missed." elapsed="4.2s" />
            <div style={{ color: CC.fg, paddingLeft: 18, marginTop: 4 }}>
              <span style={{ color: CC.dim }}>scored 8 / 14 bullets · </span>
              <span>top so far: </span>
              <span style={{ color: CC.cyan }}>"Lifted 30-day activation 31% (5.4M users)"</span>
            </div>
          </div>
        </div>

        {/* input */}
        <CCInputBox />

        <div style={{ display: "flex", justifyContent: "space-between", marginTop: 2 }}>
          <CCHint>
            Press <CCKey>?</CCKey> for shortcuts · <CCKey>Shift+Tab</CCKey> to cycle modes · <CCKey>esc</CCKey> to interrupt
          </CCHint>
        </div>

        <CCStatusLine>
          claude-haiku-4.5 · 12,345 / 1M tokens · 78% cache · mode: default · plan: BASE
        </CCStatusLine>
      </CCShell>

      <ImplNote
        files={["linkright/ui/__init__.py", "linkright/cli.py"]}
        summary="The shell skeleton: welcome banner → committed log → live tail → input → statusLine."
        steps={[
          "**Banner:** `lr_banner(version=__version__)` already renders the gradient LINKRIGHT header — keep as-is. Add `pip_welcome()` below it using `AsciiIdle(size=24)` in the banner row.",
          "**Committed log:** Rich has no `<Static>`. Approximate it: maintain `committed: list[str]` and only ever `console.print()` completed turns. Never re-print the committed list.",
          "**Live tail:** Wrap LLM calls in `with console.status('[yellow]⠋[/] {verb}…')` from Rich. The status context replaces the current `step_progress()` coral-verb lines.",
          "**Input box:** `lr_text()` / `lr_select()` already render InquirerPy boxes with the correct gray border. Key change: ensure `qmark='◆'` pointer is `'❯'` in `_lr_style()` — update `'pointer': f'{accent} bold'` to use `❯`.",
          "**StatusLine:** After every command, spawn `subprocess.run(settings.status_line_cmd, shell=True, ...)` and print stdout as the bottom row. See artboard H for the full schema.",
          "**Alt-screen (optional):** Add `console.control(Control(ESC + '[?1049h'))` at startup and `Control(ESC + '[?1049l')` on exit for a clean terminal take-over.",
        ]}
        before={`# current: lr_banner() + step_start/done scattered
from linkright.ui import lr_banner, step_start, step_done
lr_banner(version=__version__)
step_start("Parsing JD…", accent=TEAL)
# ... work ...
step_done("done", detail="7 signals")`}
        after={`# target: banner + Rich status spinner + ⎿ output
from linkright.ui import lr_banner, tool_card, tool_output
from rich.status import Status
lr_banner(version=__version__)
with console.status(f"[yellow]⠋[/] {pick_verb()}…"):
    result = parse_jd(jd_path)
tool_card("Read", jd_path, status="done")
tool_output(f"Returns: {result.line_count} lines")`}
      />
    </CCBoard>
  );
}

/* =========================================================================
   C · Input — / palette + @ picker + ! bash + multi-line tricks
   ========================================================================= */
function CCInputArtboard() {
  return (
    <CCBoard
      phase="C · Input · / palette · @ picker · ! bash · multi-line"
      title="One input box. Three column-1 triggers. Two ways to newline."
      blurb="Slash, at-sign, and bang are mutually exclusive at column 1. Inside the palette, ↑↓ navigate, Tab fills the longest common prefix, Enter selects. Backslash+Return always inserts a newline; Shift+Enter is native on supported terminals (iTerm2, WezTerm, Ghostty, Kitty, Warp, Windows Terminal)."
      sources={["03-input.md · 06-slash-commands.md"]}
    >
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 18, flex: 1, minHeight: 0 }}>
        {/* Left — slash palette open */}
        <CCShell title="linkright · / palette" size="100×30">
          <div style={{ flex: 1 }}>
            <CCUserTurn>tailor for Anthropic and then …</CCUserTurn>
            <CCAssistant>Here's the resume with 14 bullets. Let me know what to refine.</CCAssistant>
            <div style={{ marginTop: 8 }} />
          </div>
          <CCInputBox value="/" />
          <CCSlashPalette
            focused={2}
            matches={[
              { cmd: "/help",     desc: "  show keyboard shortcuts" },
              { cmd: "/clear",    desc: "  reset conversation (in-place)" },
              { cmd: "/tailor",   desc: "  re-tailor against a JD" },
              { cmd: "/critique", desc: "  LLM review of current resume" },
              { cmd: "/fill",     desc: "  resolve gaps interactively" },
              { cmd: "/practice", desc: "  interview prep · question bank" },
              { cmd: "/cost",     desc: "  show session token + cost" },
            ]}
          />
          <div style={{ paddingTop: 8 }}>
            <CCHint>
              <CCKey>↑↓</CCKey> navigate · <CCKey>tab</CCKey> longest prefix · <CCKey>enter</CCKey> select · <CCKey>esc</CCKey> cancel
            </CCHint>
          </div>
          <CCStatusLine>↑ palette open · 7 of 47 commands match "/"</CCStatusLine>
        </CCShell>

        {/* Right — @ file picker open */}
        <CCShell title="linkright · @ file picker" size="100×30">
          <div style={{ flex: 1 }}>
            <CCUserTurn>compare against my previous resume</CCUserTurn>
            <CCAssistant>Sure — drop the file with <span style={{ color: CC.cyan }}>@</span>.</CCAssistant>
          </div>
          <CCInputBox value="@jd/" />
          <div style={{ paddingLeft: 14, fontFamily: "ui-monospace, monospace", fontSize: 12, marginTop: 2 }}>
            {[
              { name: "jd/anthropic-claude-code-pm.md", size: "4.2KB", focused: true },
              { name: "jd/vercel-ai-pm.md",             size: "3.1KB" },
              { name: "jd/notion-workspace-ai.md",      size: "2.8KB" },
              { name: "jd/cursor-editor.md",            size: "5.0KB" },
            ].map((f) => (
              <div key={f.name} style={{ display: "flex", gap: 8, padding: "1px 0" }}>
                <span style={{ color: f.focused ? CC.cyan : "transparent" }}>❯</span>
                <span style={{ color: f.focused ? CC.cyan : CC.fg }}>{f.name}</span>
                <span style={{ color: CC.dim, marginLeft: "auto" }}>{f.size}</span>
              </div>
            ))}
          </div>
          <div style={{ paddingTop: 8 }}>
            <CCHint>
              fuzzy match against cwd · <CCKey>tab</CCKey> insert path · resolves files inline
            </CCHint>
          </div>
          <div style={{ borderTop: `1px dashed ${CC.borderD}`, marginTop: 6, paddingTop: 6 }}>
            <div style={{ color: CC.dim, fontSize: 11 }}>multi-line tricks (also work in this input):</div>
            <div style={{ color: CC.fg, fontSize: 11.5, marginTop: 2 }}>
              <span style={{ color: CC.cyan }}>\</span>
              <span style={{ color: CC.dim }}> + Enter</span>
              <span> → newline (universal fallback)</span>
            </div>
            <div style={{ color: CC.fg, fontSize: 11.5 }}>
              <CCKey>Shift+Enter</CCKey>
              <span style={{ color: CC.dim }}> → newline (iTerm2/WezTerm/Ghostty/Kitty/Warp/Win Terminal)</span>
            </div>
          </div>
          <CCStatusLine>! at col 1 → bash passthrough · ! &gt; ls returns to assistant</CCStatusLine>
        </CCShell>
      </div>

      <ImplNote
        files={["linkright/ui/__init__.py", "linkright/cli_aliases.py"]}
        summary="Add three column-1 triggers to the main input loop, and multiline via backslash."
        steps={[
          "**Slash palette `/`:** In `lr_select()` add a `fuzzy=True` path: if the user types `/`, show a fuzzy InquirerPy `inquirer.fuzzy(message='/', choices=_all_commands())`. `_all_commands()` returns built-ins + skills + custom commands discovered at startup.",
          "**File picker `@`:** If input starts with `@`, call `fd --type f` via `subprocess` and pipe results to an InquirerPy fuzzy select. Chosen file path is injected inline into the prompt.",
          "**Bash passthrough `!`:** If input starts with `!`, strip the `!`, run `subprocess.run(cmd, shell=True, capture_output=True)` and prepend the stdout to the next user turn context.",
          "**Backslash-newline:** In `lr_text()`, pass `multiline=True` to InquirerPy. The `\\` + Enter combo is handled automatically.",
          "**Exclusive triggers:** Add a guard: `/`, `@`, `!` only activate when they're the first character AND no other mode is active.",
        ]}
        before={`# current: all input goes directly to LLM
user_input = lr_text("You:")
send_to_model(user_input)`}
        after={`# target: column-1 trigger dispatch
raw = lr_text("You:")
if raw and raw[0] == '/':
    cmd = slash_palette(raw[1:])   # fuzzy over all_commands()
    raw = execute_slash(cmd) or ""
elif raw and raw[0] == '@':
    path = file_picker(raw[1:])    # fd + InquirerPy fuzzy
    raw = f"@{path} {raw[1+len(path):]}"
elif raw and raw[0] == '!':
    out = bash_passthrough(raw[1:])  # subprocess.run
    raw = f"[shell output]\n{out}"
send_to_model(raw)`}
      />
    </CCBoard>
  );
}

/* =========================================================================
   D · Streaming + Spinner — braille + 191 verbs + tip
   ========================================================================= */
function CCStreamingArtboard() {
  const verbRotation = [
    { frame: "⠋", verb: "Marinating",       elapsed: "0.3s", tip: "Tip: press Esc to cancel and keep what we have so far." },
    { frame: "⠙", verb: "Cogitating",       elapsed: "1.1s", tip: "Tip: /effort high lets the model think 3× longer per turn." },
    { frame: "⠹", verb: "Crafting",         elapsed: "2.4s", tip: "Tip: @-mention a JD file to anchor the rewrite to evidence." },
    { frame: "⠸", verb: "Forging",          elapsed: "3.8s" },
    { frame: "⠼", verb: "Synthesizing",     elapsed: "5.1s" },
    { frame: "⠴", verb: "Pondering",        elapsed: "6.7s" },
    { frame: "⠦", verb: "Brewing",          elapsed: "8.2s" },
    { frame: "⠧", verb: "Discombobulating", elapsed: "9.4s", tip: "Tip: spinner verbs come from a canonical 191-verb pool." },
    { frame: "⠇", verb: "Whisking",         elapsed: "10.8s" },
    { frame: "⠏", verb: "Calculating",      elapsed: "11.5s" },
  ];

  return (
    <CCBoard
      phase="D · Streaming + Spinner · 191-verb rotation + tip line"
      title="The signature CC heartbeat — braille, verb, tip."
      blurb="Ten braille frames at 80ms each (⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏), a verb that rotates every 3–5s from a 191-strong dictionary, and a dim 'Tip:' line below. Interrupt via Esc (mild) or Ctrl+C (double-tap to exit)."
      sources={["04-feedback.md · spinner-verbs/", "02-rendering.md (sync output)"]}
    >
      <div style={{ display: "grid", gridTemplateColumns: "1.3fr 1fr", gap: 18, flex: 1, minHeight: 0 }}>
        {/* live tail with rotating verb */}
        <CCShell title="linkright · /tailor (streaming)" size="100×32" style={{ height: "100%" }}>
          <CCUserTurn>tailor for the Anthropic PM, Claude Code role</CCUserTurn>

          <CCToolCard tool="Read" args="jd/anthropic-claude-code-pm.md" status="done">Returns: 142 lines</CCToolCard>
          <CCToolCard tool="Grep" args='"operator-PM", "infra"' status="done">7 matches in 3 files</CCToolCard>

          <div style={{ marginTop: 4 }}>
            <CCSpinner
              frame="⠹"
              verb="Crafting"
              elapsed="2.4s"
              tip="@-mention a JD file to anchor the rewrite to evidence."
            />
          </div>

          <div style={{ paddingLeft: 18, color: CC.fg, marginTop: 4 }}>
            <div style={{ color: CC.dim }}>Drafting 14 bullets, scored against 23 evidence nuggets:</div>
            <div style={{ color: CC.green }}>+ "Lifted 30-day activation 31% (5.4M users) via 9-arm onboarding test"</div>
            <div style={{ color: CC.green }}>+ "Drove +$2.4M ARR via 6-week pricing test (3 cohorts, 4 price points)"</div>
            <div style={{ color: CC.dim }}>(8 more streaming…)</div>
          </div>

          <div style={{ flex: 1 }} />
          <CCInputBox />
          <div>
            <CCHint>
              <CCKey>esc</CCKey> interrupt (keeps work) · <CCKey>ctrl+c</CCKey> ×1 hint · <CCKey>ctrl+c</CCKey> ×2 exit
            </CCHint>
          </div>
          <CCStatusLine>haiku-4.5 · streaming · 12.4k / 1M · 78% cache · est 18s remaining</CCStatusLine>
        </CCShell>

        {/* verb-frame matrix */}
        <div style={{ background: "#0E1118", borderRadius: 10, border: `1px solid ${CC.borderD}`, padding: "16px 18px", fontFamily: "ui-monospace, monospace", color: CC.fg, fontSize: 12 }}>
          <div style={{ fontSize: 10.5, color: CC.dim, letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 10 }}>
            ↻ verb rotation · 80ms / frame · ~4s / verb
          </div>
          {verbRotation.map((r, i) => (
            <div key={i} style={{ display: "grid", gridTemplateColumns: "30px 1fr 60px", gap: 8, padding: "5px 0", borderBottom: i === verbRotation.length - 1 ? "none" : `1px dashed ${CC.borderD}` }}>
              <span style={{ color: CC.yellow, fontSize: 14 }}>{r.frame}</span>
              <span style={{ color: CC.fg }}>{r.verb}…</span>
              <span style={{ color: CC.dim, textAlign: "right" }}>{r.elapsed}</span>
              {r.tip && (
                <div style={{ gridColumn: "1 / -1", color: CC.dim, paddingLeft: 38, fontSize: 11, marginTop: 1 }}>
                  Tip: {r.tip.replace(/^Tip: /, "")}
                </div>
              )}
            </div>
          ))}
          <div style={{ marginTop: 10, paddingTop: 10, borderTop: `1px solid ${CC.borderD}`, fontSize: 10.5, color: CC.dim, lineHeight: 1.6 }}>
            mood pools (9 in verbs.json):<br />
            <span style={{ color: CC.cyan }}>culinary · kinetic · cerebral · whimsical · scientific · musical · existential · construction · computational</span>
          </div>
        </div>
      </div>

      <ImplNote
        files={["linkright/ui/__init__.py", "linkright/ui/patterns.py"]}
        summary="Replace coral working-verb lines with a braille spinner + rotating verb from the 191-pool."
        steps={[
          "Add `VERB_POOL` list at top of `ui/__init__.py` — copy 32-verb subset from `cc-frontend-design/CHEATSHEET.md` or load full `spinner-verbs/verbs.json` if bundled.",
          "Add `pick_verb() → str` that returns a random entry. For mood-weighted selection: `pick_verb_by_mood('culinary')`, etc.",
          "Replace every `step_progress(verb, icon='*')` callsite with `with console.status(f'[yellow]⠋[/] {pick_verb()}…')`. The status context auto-clears when the `with` block exits.",
          "Rotate the verb every 3–5s during long calls using `threading.Timer(4.0, lambda: status.update(f'[yellow]⠋[/] {pick_verb()}…')).start()`.",
          "Tip line below spinner: `console.print(f'  [dim]Tip: {random.choice(TIPS)}[/]')`. Keep `TIPS` list in `ui/__init__.py`.",
          "Interrupt via `Esc` should call `status.stop()`. Ctrl+C should set a flag → print `[red]Interrupted[/]` + hint, second Ctrl+C calls `sys.exit(130)`.",
        ]}
        before={`# current: coral working verb (LR house)
from linkright.ui.patterns import progress_verb
progress_verb("Drafting bullet 06/14…",
    telemetry="(2.4s · gemma3:1b)",
    icon="*")`}
        after={`# target: braille spinner + rotating verb
import random, threading
from linkright.ui import console, pick_verb, TIPS
with console.status(f"[yellow]⠋[/] {pick_verb()}…") as status:
    t = threading.Timer(4, lambda: status.update(
        f"[yellow]⠙[/] {pick_verb()}…"))
    t.start()
    result = draft_bullet(evidence)
    t.cancel()
console.print(f"  [dim]Tip: {random.choice(TIPS)}[/]")`}
      />
    </CCBoard>
  );
}

/* =========================================================================
   E · Tool calls — Read, Edit/diff, Bash, subagent, AskUserQuestion
   ========================================================================= */
function CCToolCardsArtboard() {
  return (
    <CCBoard
      phase="E · Tool cards · ● · ⎿ · diff · subagent · AskUserQuestion"
      title="Every tool renders as a card. Diffs are foreground-only."
      blurb="● (green/red/yellow) for status, ⎿ (U+23BF) for output, indented dim text. Diffs use red - / green + / bright-yellow @@ hunks — never background fills. Subagent transcripts nest with a │ connector. AskUserQuestion paints a side-by-side options + preview UI."
      sources={["09-tool-render.md · 02-rendering.md (diff render)"]}
    >
      <div style={{ display: "grid", gridTemplateColumns: "1.1fr 1fr", gap: 18, flex: 1, minHeight: 0 }}>
        <CCShell title="linkright · tool atlas" size="120×40" style={{ height: "100%" }}>
          {/* Read */}
          <CCToolCard tool="Read" args="resume/master.md" status="done">Returns: 487 lines · last edit 3m ago</CCToolCard>

          {/* Edit + diff */}
          <CCToolCard tool="Edit" args="resume/bullets/experience.md" status="done">
            Updated 12 lines (5 added, 4 removed, 3 modified)
          </CCToolCard>
          <div style={{ paddingLeft: 22 }}>
            <CCDiff
              path="resume/bullets/experience.md"
              hunks={[{
                header: "-3,4 +3,4",
                lines: [
                  "- Shipped pricing experiments that helped revenue",
                  "- Worked closely with eng to ship features quickly",
                  "+ Drove +$2.4M ARR via 6-week pricing test (3 cohorts, 4 price points)",
                  "+ Cut feature ship time 38% by replacing PRD review with code-first spec",
                ],
              }]}
            />
          </div>

          {/* Bash */}
          <CCToolCard tool="Bash" args="git status" status="done">
            <div style={{ whiteSpace: "pre", lineHeight: 1.5 }}>{`On branch main
Changes not staged for commit:
  modified:   resume/bullets/experience.md
  modified:   resume/master.md`}</div>
          </CCToolCard>

          {/* Bash error */}
          <CCToolCard tool="Bash" args="git push origin main" status="error">
            <span style={{ color: CC.red }}>fatal: Authentication failed for 'https://github.com/satvik-jain-iitd/linkright_production.git'</span>
          </CCToolCard>

          {/* Permission-denied */}
          <CCToolCard tool="Bash" args="rm -rf ~/Documents" status="denied">
            <span style={{ color: CC.yellow }}>(denied) </span> destructive pattern matched · `Bash(rm -rf *)` not in allow list
          </CCToolCard>

          {/* Collapsed */}
          <CCToolCard tool="Bash" args="npm install" status="done" collapsed={47}>
            <div>added 1248 packages in 38s</div>
            <div>147 packages are looking for funding</div>
          </CCToolCard>
        </CCShell>

        <CCShell title="linkright · subagent · AskUserQuestion" size="100×40" style={{ height: "100%" }}>
          {/* Subagent */}
          <CCToolCard tool="Agent" args="Explore: find best-fit JD cluster" status="done">
            Subagent started · model: haiku-4.5
          </CCToolCard>
          <CCSubagent>
            <CCToolCard tool="Grep" args='"AI infra", "operator-PM"' status="done">14 matches in 6 nuggets</CCToolCard>
            <CCToolCard tool="Read" args="nuggets/activation-30pct.md" status="done">Returns: 87 lines</CCToolCard>
            <CCToolCard tool="Read" args="nuggets/pricing-2.4M.md" status="done">Returns: 41 lines</CCToolCard>
            <div style={{ padding: "2px 0", color: CC.dim }}>
              Returned: "Top cluster: operator-PM + AI infra; lead with activation 31% (5.4M)"
            </div>
          </CCSubagent>
          <CCToolCard tool="Agent" args="Explore" status="done">Done · 12.3s · 4521 tokens</CCToolCard>

          {/* AskUserQuestion */}
          <div style={{ marginTop: 14 }}>
            <CCAskUser
              question="Which lead bullet do you want?"
              focused={0}
              options={[
                "+31% activation (5.4M users)",
                "+$2.4M ARR (pricing test)",
                "−38% ship time (PRD → code-first)",
              ]}
              preview={`Lifted 30-day activation 31% (5.4M users)
via 9-arm onboarding test; promoted variant
to default + saved $1.2M / yr in re-engagement
spend.

(strongest of the three for "AI infra"
narrative — JD names operator-PM explicitly)`}
            />
          </div>

          <div style={{ marginTop: "auto", paddingTop: 8 }}>
            <CCHint>
              <CCKey>↑↓</CCKey> nav · <CCKey>enter</CCKey> select · subagent transcripts nest with <CCKey>│</CCKey>
            </CCHint>
          </div>
        </CCShell>
      </div>

      <ImplNote
        files={["linkright/ui/__init__.py", "linkright/ui/patterns.py"]}
        summary="Add tool_card() and tool_output() helpers; change step_done() bullet from teal to green."
        steps={[
          "**New `tool_card(tool, args, status)`:** `console.print(f'[{color}]●[/] [bold]{tool}[/][dim]({args})[/]')` where color = `green` (done), `red` (error), `yellow` (running/denied).",
          "**New `tool_output(text)`:** `console.print(f'  [dim]⎿  {text}[/]')` — the ⎿ connector (U+23BF). Use after every `tool_card()` call.",
          "**Change `step_done()`:** In `ui/__init__.py`, change `[{accent}]●[/]` (teal) to `[tui.green]●[/]` (green). Done is green in CC, not teal.",
          "**Diff rendering:** For Edit/Write tools, use Rich `Syntax` with `+` lines wrapped in `[green]`, `-` lines in `[red]`, `@@` headers in `[yellow]`. No background fill — foreground only.",
          "**Subagent nesting:** Add `with console.indent(2):` around subagent output blocks. Prepend `[dim]│[/]` to each line of nested output.",
          "**Collapsed output:** If tool output > 20 lines, show first 10 then `[dim]… ({n} more lines)[/]`. Add `--verbose` flag to expand.",
        ]}
        before={`# current: teal ● step primitives
step_done("parsed JD", detail="7 signals")
step_detail("mapped strategy: operator-PM")`}
        after={`# target: CC-true tool_card + ⎿ output connector
tool_card("Read", "jd/anthropic.md", status="done")
tool_output("Returns: 142 lines · 7 signals")
tool_card("Edit", "resume/bullets.md", status="done")
tool_output("Updated 12 lines (5 added, 4 removed)")
# diff preview below the card:
console.print("  [yellow]@@ -3,4 +3,4 @@[/]")
console.print("  [red]- Shipped pricing experiments...[/]")
console.print("  [green]+ Drove +$2.4M ARR via 6-week test[/]")`}
      />
    </CCBoard>
  );
}

/* =========================================================================
   F · Permission prompts — bordered radio, ❯ focus, Esc=Deny
   ========================================================================= */
function CCPermissionArtboard() {
  return (
    <CCBoard
      phase="F · Permissions · 6 modes · the radio prompt · hook veto"
      title="Every mutation goes through a typed enum."
      blurb="default · acceptEdits · auto · bypassPermissions · dontAsk · plan. Prompts are bordered round-boxes with arrow nav, ❯ marks focus, Enter selects, Esc denies. 'Allow always' tiers are generated per-call — never auto-suggest Bash(*) for rm/curl/ssh."
      sources={["07-permission-modes.md · 10-settings-hooks.md (PreToolUse veto)"]}
    >
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 18, flex: 1, minHeight: 0 }}>
        <CCShell title="linkright · permission prompt" size="100×30">
          <CCUserTurn>commit the resume and push to my fork</CCUserTurn>
          <CCAssistant>I'll stage, commit, push, and open a PR. The first step needs approval.</CCAssistant>

          <CCPermissionPrompt
            title="LinkRight wants to run a command:"
            command="git push origin satvik/anthropic-tailor"
            focused={1}
            options={[
              { label: "Allow once" },
              { label: "Allow always",   note: "Bash(git push *)" },
              { label: "Allow always",   note: "Bash(git *)" },
              { label: "Deny",           note: "esc" },
            ]}
          />

          <div style={{ marginTop: "auto" }}>
            <CCInputBox />
            <CCHint>
              <CCKey>↑↓</CCKey> nav · <CCKey>enter</CCKey> select · <CCKey>esc</CCKey> Deny · Allow-always tiers generated per command
            </CCHint>
          </div>
          <CCStatusLine>haiku-4.5 · mode: default · permission_prompt fired hook → osascript Glass.aiff</CCStatusLine>
        </CCShell>

        <CCShell title="linkright · permissions · settings + modes" size="100×30">
          <div style={{ color: CC.dim, fontSize: 11, marginBottom: 6 }}># ~/.linkright/settings.json</div>
          <pre style={{ margin: 0, fontSize: 11.5, color: CC.fg, lineHeight: 1.6, whiteSpace: "pre-wrap" }}>{`{
  "permissions": {
    "defaultMode": "default",
    "allow": [
      "Read(*)",
      "Bash(git *)",
      "Edit(~/linkright/resume/**)",
      "WebFetch(domain:linkedin.com)"
    ],
    "deny": [
      "Bash(rm -rf *)",
      "Edit(**/.env*)",
      "Edit(**/secrets/**)"
    ],
    "additionalDirectories": ["/tmp"]
  },
  "hooks": {
    "PreToolUse": [{
      "matcher": "Bash",
      "hooks": [{
        "type": "command",
        "command": "node ~/.linkright/hooks/safety.cjs",
        "timeout": 10
      }]
    }]
  }
}`}</pre>

          <div style={{ marginTop: 12, borderTop: `1px solid ${CC.borderD}`, paddingTop: 10 }}>
            <div style={{ color: CC.dim, fontSize: 11, letterSpacing: "0.08em", textTransform: "uppercase" }}>modes · Shift+Tab cycles</div>
            {[
              { name: "default",           hits: 8015, color: CC.fg,    desc: "prompt per new tool/scope" },
              { name: "acceptEdits",       hits: 92,   color: CC.green, desc: "auto-approve Edit/Write" },
              { name: "auto",              hits: 1555, color: CC.fg,    desc: "auto-approve non-destructive" },
              { name: "bypassPermissions", hits: 127,  color: CC.red,   desc: "sandboxes only" },
              { name: "dontAsk",           hits: 50,   color: CC.dim,   desc: "silent deny" },
              { name: "plan",              hits: 1030, color: CC.magenta, desc: "read-only · system-prompt level" },
            ].map((m) => (
              <div key={m.name} style={{ display: "grid", gridTemplateColumns: "150px 1fr 60px", gap: 8, fontSize: 11.5, padding: "2px 0" }}>
                <span style={{ color: m.color, fontWeight: 600 }}>{m.name}</span>
                <span style={{ color: CC.dim }}>{m.desc}</span>
                <span style={{ color: CC.dim, textAlign: "right" }}>{m.hits}×</span>
              </div>
            ))}
          </div>
        </CCShell>
      </div>

      <ImplNote
        files={["linkright/config.py", "linkright/ui/__init__.py"]}
        summary="Add PermissionMode enum and a permission_prompt() helper wrapping InquirerPy."
        steps={[
          "**In `config.py`:** Add `permission_mode: str = 'default'` to the `Config` dataclass. Valid values: `default | acceptEdits | auto | bypassPermissions | dontAsk | plan`.",
          "**New `permission_prompt(tool, command)`:** Show a Rich `Panel` with `border_style='rounded'` containing a `lr_select()` with 4 choices: Allow once / Allow always (scoped glob) / Allow always (wide) / Deny.",
          "**Scoped glob auto-generation:** For `Bash(git push origin main)` → suggest `Bash(git push *)` and `Bash(git *)` as the two 'Allow always' tiers. Never auto-suggest `Bash(*)`.",
          "**Call site:** Before any tool that mutates filesystem/network/shell, check `if config.permission_mode == 'default': result = permission_prompt(tool, command)`. Skip check if mode is `auto` or `bypassPermissions`.",
          "**Persist allow rules:** When user picks 'Allow always', append `{\"tool\": \"Bash\", \"pattern\": \"git *\"}` to `~/.linkright/permissions.json` and reload at next startup.",
          "**Fire Notification hook:** After showing the prompt, call `hooks_fire('Notification', matcher='permission_prompt')` (see artboard H).",
        ]}
        before={`# current: no permission layer — tools run directly
result = subprocess.run(cmd, shell=True)`}
        after={`# target: permission gate before every mutating tool
from linkright.ui.permissions import permission_prompt
from linkright.config import Config
cfg = Config.load()
if requires_permission(tool, cmd) and not is_allowed(cfg, tool, cmd):
    decision = permission_prompt(tool, cmd)
    if decision == "deny":
        return tool_card(tool, cmd, status="denied")
    if decision.startswith("always"):
        persist_allow_rule(cfg, tool, decision)
result = subprocess.run(cmd, shell=True)`}
      />
    </CCBoard>
  );
}

/* =========================================================================
   G · Plan mode — magenta banner + ExitPlanMode card
   ========================================================================= */
function CCPlanModeArtboard() {
  return (
    <CCBoard
      phase="G · Plan mode · magenta banner · ExitPlanMode approval"
      title="Read-only by system prompt, not just by flag."
      blurb="Plan mode is three coordinated layers: system-prompt constraint (no mutations), permission constraint (read-only tools), and UI (magenta banner sticky on top). ExitPlanMode is a tool — model writes a plan file, requests approval; user approves to leave read-only mode."
      sources={["08-plan-mode.md · 07-permission-modes.md"]}
    >
      <CCShell title="linkright · /plan · session 7a2f" size="120×36" style={{ flex: 1 }}>
        <CCPlanBanner>
          Read-only · all tools constrained to Read/Grep/Glob · Use ExitPlanMode when ready.
        </CCPlanBanner>

        <CCUserTurn>I want to add a coverletter pillar — figure out what it touches before we build it.</CCUserTurn>

        <CCToolCard tool="Glob" args='"coverletter/**"' status="done">3 files: cli.py, pipeline.py, __init__.py</CCToolCard>
        <CCToolCard tool="Read" args="coverletter/cli.py" status="done">Returns: 218 lines</CCToolCard>
        <CCToolCard tool="Read" args="coverletter/pipeline.py" status="done">Returns: 412 lines</CCToolCard>
        <CCToolCard tool="Grep" args='"coverletter" in src/linkright' status="done">23 matches in 8 files</CCToolCard>

        <CCAssistant>
          The pipeline already exists — it's a thin orchestrator over <span style={{ color: CC.cyan }}>coverletter/pipeline.py</span> that
          calls the same evidence retriever as <span style={{ color: CC.cyan }}>tailor</span>. The new pillar mostly needs a CLI surface,
          a template directory, and one new prompt. I'm ready to surface the plan.
        </CCAssistant>

        <CCToolCard tool="ExitPlanMode" status="running" args="awaiting approval">
          plan written to ~/.linkright/plans/coverletter-v1.md
        </CCToolCard>

        {/* Approval card */}
        <div style={{
          border: `1px solid ${CC.magenta}`, borderRadius: 6, padding: "12px 16px",
          margin: "6px 0", display: "flex", flexDirection: "column", gap: 8,
        }}>
          <div style={{ color: CC.magenta, fontWeight: 700, letterSpacing: "0.06em" }}>┌─ PLAN READY ──────────────────────────────────────────────────────────────</div>
          <div style={{ color: CC.fg, fontFamily: "ui-monospace, monospace" }}>
            <span style={{ color: CC.dim }}>summary:</span>{" "}
            Add coverletter pillar. ~310 LoC new (cli.py, prompts/, 4 templates).
            Reuses tailor's evidence retriever. Adds <span style={{ color: CC.cyan }}>/cl</span>{" "}
            top-level alias. No schema migration.
          </div>
          <div style={{ marginTop: 4 }}>
            {[
              { label: "Approve and exit plan mode", focused: true },
              { label: "Stay in plan mode (iterate on the plan)" },
              { label: "Reject (back to plan mode with feedback)" },
            ].map((o, i) => (
              <div key={o.label} style={{ display: "flex", gap: 6, padding: "1px 0" }}>
                <span style={{ color: o.focused ? CC.magenta : "transparent" }}>❯</span>
                <span style={{ color: o.focused ? CC.magenta : CC.fg }}>{o.label}</span>
              </div>
            ))}
          </div>
          <div style={{ color: CC.magenta }}>└──────────────────────────────────────────────────────────────────────────</div>
        </div>

        <div style={{ flex: 1 }} />
        <CCInputBox />
        <CCHint>
          <CCKey>Shift+Tab</CCKey> exits plan mode without approval · 51 plan files in ~/.linkright/plans/
        </CCHint>
        <CCStatusLine>mode: plan · magenta = system-prompt level constraint · model can ask via AskUserQuestion</CCStatusLine>
      </CCShell>

      <ImplNote
        files={["linkright/cli.py", "linkright/config.py"]}
        summary="Plan mode = three coordinated layers: system prompt constraint + permission gate + magenta UI."
        steps={[
          "**In `config.py`:** When `permission_mode == 'plan'`, set a flag `plan_active = True`. All Edit/Write/Bash commands check this flag and abort with a magenta message if true.",
          "**Magenta banner:** At the start of any interactive session in plan mode, call: `console.print(Panel('[magenta bold]PLAN MODE[/] — Read-only. Use exit-plan when ready.', border_style='magenta'))`.",
          "**Read-only gate:** In each mutating command (resume/tailor, enrich, etc.), add: `if cfg.plan_active: console.print('[magenta]![/] Blocked — plan mode active.'); return`.",
          "**New `@main.command('exit-plan')`:** Show the ExitPlanMode approval card (a `lr_select()` inside a magenta `Panel`). On approve: write `~/.linkright/plans/<session_id>.md`, set `cfg.plan_active = False`.",
          "**Plan file location:** `LINKRIGHT_HOME / 'plans' / f'{session_id}.md'`. Include timestamp, command history summary, and the plan body.",
          "**Entry point:** Add `--plan` / `--permission-mode plan` flag to `main()` in `cli.py`. Also add `Shift+Tab` as a mode-cycle shortcut in interactive sessions.",
        ]}
        before={`# current: no plan mode — all commands run freely
@main.command()
def tailor():
    run_pipeline()`}
        after={`# target: plan mode gate on all mutating commands
@main.command()
@click.pass_context
def tailor(ctx):
    cfg = Config.load()
    if cfg.plan_active:
        console.print("[magenta bold]PLAN MODE[/] — tailor is blocked.")
        console.print("[dim]Call[/] [magenta]linkright exit-plan[/] [dim]when ready.[/]")
        return
    run_pipeline()`}
      />
    </CCBoard>
  );
}

/* =========================================================================
   H · Settings + Hooks + StatusLine
   ========================================================================= */
function CCSettingsArtboard() {
  return (
    <CCBoard
      phase="H · Settings + Hooks + statusLine subprocess"
      title="Settings cascade. Hooks fire on every lifecycle moment."
      blurb="Resolution: CLI flag > project-local > project shared > user > defaults. Hooks fire at SessionStart, UserPromptSubmit, PreToolUse, PostToolUse, PreCompact, Stop, SubagentStop, Notification — each gets a JSON blob on stdin, returns optional additionalContext on stdout. statusLine spawns a subprocess per render tick (debounced) and renders stdout at the bottom."
      sources={["10-settings-hooks.md · CHEATSHEET.md"]}
    >
      <div style={{ display: "grid", gridTemplateColumns: "1.1fr 1fr", gap: 18, flex: 1, minHeight: 0 }}>
        <CCShell title="~/.linkright/settings.json" size="100×40" style={{ height: "100%" }}>
          <div style={{ color: CC.dim, fontSize: 11, marginBottom: 6 }}># resolution: cli > project-local > project > user > defaults</div>
          <pre style={{ margin: 0, fontSize: 11.5, color: CC.fg, lineHeight: 1.55, whiteSpace: "pre-wrap" }}>{`{
  "theme": "dark",
  "editorMode": "normal",
  "permissions": { … },

  "hooks": {
    "SessionStart": [{
      "matcher": "",
      "hooks": [{ "type": "command",
                  "command": "linkright doctor --quiet" }]
    }],
    "UserPromptSubmit": [{
      "matcher": "",
      "hooks": [{ "type": "command",
                  "command": "node ~/.linkright/hooks/jd-detect.cjs",
                  "statusMessage": "Detecting attached JD…" }]
    }],
    "PreToolUse": [{
      "matcher": "Edit|Write",
      "hooks": [{ "type": "command",
                  "command": "node ~/.linkright/hooks/page-fit.cjs" }]
    }],
    "PostToolUse": [{ "matcher": "Edit", "hooks": [...] }],
    "PreCompact":  [{ "matcher": "",     "hooks": [...] }],
    "Stop":        [{ "matcher": "",     "hooks": [
                       { "type":"command","command":"afplay /System/Library/Sounds/Glass.aiff" }
                     ]}],
    "Notification": [{ "matcher": "permission_prompt", "hooks": [...] }]
  },

  "statusLine": {
    "type": "command",
    "command": "bash ~/.linkright/statusline.sh"
  },

  "mcpServers": {
    "linkright-watch": { "command": "linkright", "args": ["watch", "mcp"] }
  },

  "inputNeededNotifEnabled": true,
  "agentPushNotifEnabled": true
}`}</pre>
        </CCShell>

        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {/* Hook event timeline */}
          <div style={{ background: "#0E1118", borderRadius: 10, border: `1px solid ${CC.borderD}`, padding: "14px 18px", flex: 1, fontFamily: "ui-monospace, monospace", color: CC.fg }}>
            <div style={{ fontSize: 10.5, color: CC.dim, letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 10 }}>
              hook event timeline · one turn
            </div>
            {[
              { evt: "SessionStart",     when: "launch",                fires: "linkright doctor --quiet → injects context" },
              { evt: "UserPromptSubmit", when: "after user hits Enter", fires: "jd-detect.cjs → adds 'detected JD: anthropic.md'" },
              { evt: "PreToolUse",       when: "before each tool",      fires: "page-fit.cjs · can VETO non-zero" },
              { evt: "PostToolUse",      when: "after each tool",       fires: "page-fit.cjs → reports new width %" },
              { evt: "Stop",             when: "turn ends, awaiting",   fires: "afplay Glass.aiff" },
              { evt: "SubagentStop",     when: "subagent finishes",     fires: "(unused — leave blank)" },
              { evt: "PreCompact",       when: "before auto-compact",   fires: "bd prime · save state" },
              { evt: "Notification",     when: "permission_prompt",     fires: "afplay Pop.aiff" },
            ].map((h, i) => (
              <div key={i} style={{ padding: "3px 0", display: "grid", gridTemplateColumns: "140px 1fr", gap: 8, fontSize: 11.5 }}>
                <span style={{ color: CC.cyan }}>{h.evt}</span>
                <span style={{ color: CC.dim }}>{h.when} · <span style={{ color: CC.fg }}>{h.fires}</span></span>
              </div>
            ))}
          </div>

          {/* StatusLine subprocess */}
          <div style={{ background: "#0E1118", borderRadius: 10, border: `1px solid ${CC.borderD}`, padding: "14px 18px", fontFamily: "ui-monospace, monospace", color: CC.fg }}>
            <div style={{ fontSize: 10.5, color: CC.dim, letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 8 }}>
              statusLine subprocess · stdin → stdout
            </div>
            <div style={{ fontSize: 11.5, color: CC.dim, marginBottom: 4 }}>stdin (json piped each render tick):</div>
            <pre style={{ margin: "0 0 8px", color: CC.fg, fontSize: 11, lineHeight: 1.5 }}>{`{ "model":  {"id":"haiku-4.5"},
  "tokens": {"used":12345,"limit":1000000},
  "cwd":    "/Users/satvik/linkright",
  "branch": "satvik/anthropic-tailor",
  "permission_mode": "default" }`}</pre>
            <div style={{ fontSize: 11.5, color: CC.dim, marginBottom: 4 }}>stdout (rendered at bottom):</div>
            <div style={{ padding: "6px 10px", border: `1px solid ${CC.borderD}`, borderRadius: 4 }}>
              <span style={{ color: CC.cyan }}>🦴 pip</span>
              <span style={{ color: CC.dim }}>{" · "}haiku-4.5{" · "}12k/1M{" · "}78% cache{" · "}</span>
              <span style={{ color: CC.green }}>satvik/anthropic-tailor</span>
              <span style={{ color: CC.dim }}>{" · default"}</span>
            </div>
          </div>
        </div>
      </div>

      <ImplNote
        files={["linkright/config.py", "linkright/ui/__init__.py"]}
        summary="Extend Config with hooks + statusLine; add hooks_fire() and spawn statusLine subprocess."
        steps={[
          "**Extend `Config` dataclass:** Add `hooks: dict = field(default_factory=dict)` and `status_line_cmd: str = ''`. Load from `~/.linkright/config.yaml` (already YAML-based).",
          "**New `hooks_fire(event, **kwargs)`** in `ui/__init__.py`: iterate `cfg.hooks.get(event, [])`, check `matcher` against tool name, call `subprocess.run(command, input=json.dumps(kwargs))`. Return `stdout` as `additionalContext`.",
          "**`PreToolUse` veto:** If hook exits non-zero, treat as deny. Print `[red]✗[/] Hook blocked {tool}` + hook stderr.",
          "**StatusLine subprocess:** After each command output, run `subprocess.run(cfg.status_line_cmd, shell=True, input=json.dumps(session_state), capture_output=True)` and `console.print(f'[dim]{stdout.strip()}[/]')` on one line.",
          "**Session state JSON shape:** Pass `{model, tokens_used, tokens_limit, cwd, branch, permission_mode}` to the status script stdin.",
          "**Settings cascade order:** CLI `--settings` flag > `.claude/settings.local.json` > `.claude/settings.json` > `~/.linkright/config.yaml` > defaults. Use `Config.load()` chain with `Config.merge()` helper.",
        ]}
        before={`# current: no hook system — direct function calls
def tailor_pipeline():
    parse_jd()
    retrieve_evidence()
    draft_bullets()`}
        after={`# target: hooks around each operation
def tailor_pipeline():
    hooks_fire("UserPromptSubmit", command="tailor")
    ctx = hooks_fire("PreToolUse", tool="Read", args=jd_path)
    parse_jd(extra_context=ctx.get("additionalContext"))
    hooks_fire("PostToolUse", tool="Read", result=result)
    # ... other steps ...
    hooks_fire("Stop", tokens_used=total_tokens)
    statusline_render(session_state)`}
      />
    </CCBoard>
  );
}

/* =========================================================================
   I · Slash palette + skills + custom commands
   ========================================================================= */
function CCSlashArtboard() {
  return (
    <CCBoard
      phase="I · Slash palette · 4 sources of commands"
      title="Built-in + settings + skills + custom — one fuzzy list."
      blurb="The slash palette unifies four sources: compiled-in CLI commands, settings mutators (/config /model /permissions), discovered skills (~/.linkright/skills/*/SKILL.md), and user commands (~/.linkright/commands/*.md). Tab fills the longest common prefix; selected item is inverse-painted."
      sources={["06-slash-commands.md · 10-settings-hooks.md (skills)"]}
    >
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 18, flex: 1, minHeight: 0 }}>
        <CCShell title="linkright · /palette" size="100×34" style={{ height: "100%" }}>
          <div style={{ flex: 1 }}>
            <CCAssistant>The 14 bullets are ready. Tell me what's next.</CCAssistant>
          </div>
          <CCInputBox value="/" />
          <div style={{ paddingLeft: 14, marginTop: 4 }}>
            <div style={{ color: CC.dim, fontSize: 10.5, letterSpacing: "0.1em", textTransform: "uppercase", padding: "4px 0" }}>built-in</div>
            {[
              { cmd: "/tailor",   desc: "  re-tailor against a JD",        focus: true },
              { cmd: "/critique", desc: "  LLM review of current resume" },
              { cmd: "/fill",     desc: "  resolve missing-metric gaps" },
              { cmd: "/practice", desc: "  interview prep · question bank" },
              { cmd: "/cl",       desc: "  cover letter (alias: cover-letter)" },
            ].map((m, i) => (
              <div key={m.cmd} style={{ display: "flex", gap: 8, padding: "1px 0", alignItems: "baseline",
                background: m.focus ? CC.invBg : "transparent" }}>
                <span style={{ color: m.focus ? CC.invFg : "transparent", paddingLeft: 4, paddingRight: 4 }}>❯</span>
                <span style={{ color: m.focus ? CC.invFg : CC.cyan }}>{m.cmd}</span>
                <span style={{ color: m.focus ? CC.invFg : CC.dim }}>{m.desc}</span>
              </div>
            ))}

            <div style={{ color: CC.dim, fontSize: 10.5, letterSpacing: "0.1em", textTransform: "uppercase", padding: "8px 0 4px" }}>settings · config</div>
            <div style={{ display: "flex", gap: 8, padding: "1px 0" }}><span /><span style={{ color: CC.cyan }}>/model</span><span style={{ color: CC.dim }}>  switch model · haiku-4.5 / sonnet / opus</span></div>
            <div style={{ display: "flex", gap: 8, padding: "1px 0" }}><span /><span style={{ color: CC.cyan }}>/permissions</span><span style={{ color: CC.dim }}>  edit allow/deny rules</span></div>
            <div style={{ display: "flex", gap: 8, padding: "1px 0" }}><span /><span style={{ color: CC.cyan }}>/cost</span><span style={{ color: CC.dim }}>  session token + USD</span></div>

            <div style={{ color: CC.dim, fontSize: 10.5, letterSpacing: "0.1em", textTransform: "uppercase", padding: "8px 0 4px" }}>skills (3 discovered)</div>
            <div style={{ display: "flex", gap: 8, padding: "1px 0" }}><span /><span style={{ color: CC.cyan }}>/scout</span><span style={{ color: CC.dim }}>  scan 12 boards · voice: "scout jobs"</span></div>
            <div style={{ display: "flex", gap: 8, padding: "1px 0" }}><span /><span style={{ color: CC.cyan }}>/watch</span><span style={{ color: CC.dim }}>  passive JD capture · MCP server</span></div>
            <div style={{ display: "flex", gap: 8, padding: "1px 0" }}><span /><span style={{ color: CC.cyan }}>/coach</span><span style={{ color: CC.dim }}>  interview coach · session mode</span></div>

            <div style={{ color: CC.dim, fontSize: 10.5, letterSpacing: "0.1em", textTransform: "uppercase", padding: "8px 0 4px" }}>custom (you wrote these)</div>
            <div style={{ display: "flex", gap: 8, padding: "1px 0" }}><span /><span style={{ color: CC.cyan }}>/digest</span><span style={{ color: CC.dim }}>  weekly summary email · ~/.linkright/commands/digest.md</span></div>
            <div style={{ display: "flex", gap: 8, padding: "1px 0" }}><span /><span style={{ color: CC.cyan }}>/pipsay</span><span style={{ color: CC.dim }}>  print pip in any pose · 5 lines</span></div>
          </div>
          <div style={{ paddingTop: 8 }}>
            <CCHint>
              <CCKey>↑↓</CCKey> nav · <CCKey>tab</CCKey> fill prefix · selected item is inverse (\x1b[7m)
            </CCHint>
          </div>
        </CCShell>

        <CCShell title="custom command file" size="100×34" style={{ height: "100%" }}>
          <div style={{ color: CC.dim, fontSize: 11, marginBottom: 6 }}># ~/.linkright/commands/digest.md</div>
          <pre style={{ margin: 0, fontSize: 11.5, color: CC.fg, lineHeight: 1.6, whiteSpace: "pre-wrap" }}>{`---
description: weekly applications digest as markdown email
allowed-tools: [Read, Grep, WebFetch]
---

Summarise this week's job-search activity from
~/.linkright/state.json. Group by:

  1. Applications sent (with fit score)
  2. Callbacks pending
  3. Best new JDs since last Friday
  4. One concrete suggestion for next week

Format: markdown, ready to paste into email.
Tone: pip · terse, evidence-led, no celebration.

End with the pip ASCII signature:

    ┌───┐
    │^ ^│
    └─⌣─┘`}</pre>

          <div style={{ marginTop: 12, borderTop: `1px solid ${CC.borderD}`, paddingTop: 10 }}>
            <div style={{ color: CC.dim, fontSize: 11, letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 6 }}>skill manifest (SKILL.md)</div>
            <pre style={{ margin: 0, fontSize: 11, color: CC.fg, lineHeight: 1.55 }}>{`---
name: scout
description: scan job boards for fits ≥ 78%
tools: [Read, WebFetch, Grep]
voice_triggers: ["scout jobs", "find roles"]
---`}</pre>
          </div>

          <div style={{ marginTop: "auto", paddingTop: 8 }}>
            <CCHint>
              Tab fills the longest common prefix · empty palette → falls back to literal /text as message
            </CCHint>
          </div>
        </CCShell>
      </div>

      <ImplNote
        files={["linkright/cli.py", "linkright/cli_aliases.py"]}
        summary="Unify built-in commands + skills + custom commands into one fuzzy-match slash palette."
        steps={[
          "**`_all_commands()`:** Returns a merged list from: (1) `[cmd.name for cmd in main.commands.values()]`, (2) skills discovered via `glob('~/.linkright/skills/*/SKILL.md')`, (3) custom from `glob('~/.linkright/commands/*.md')`.",
          "**Skills discovery:** In a new `linkright/skills.py`, parse each `SKILL.md` YAML frontmatter for `name`, `description`, `voice_triggers`. Cache at startup.",
          "**Custom commands discovery:** Parse filename (without `.md`) as command name, first YAML frontmatter `description` line as label.",
          "**Palette UI:** `inquirer.fuzzy(message='/', choices=_all_commands(), max_height='60%')` — InquirerPy's fuzzy preset handles ↑↓ nav, Tab prefix-fill, inverse on selected.",
          "**Execution routing:** Built-in commands → `main.invoke(ctx, name)`. Skill commands → inject the SKILL.md body as a system message then call the LLM. Custom commands → same as skill.",
          "**`AliasedGroup` compatibility:** `cli_aliases.py` already provides aliases. Keep it — the palette just adds fuzzy discovery on top.",
        ]}
        before={`# current: AliasedGroup only — user must know exact names
# linkright tailor, linkright t, linkright critique…
# No fuzzy discovery, no skill/custom surfacing`}
        after={`# target: / opens fuzzy palette over all sources
# In the main input loop, if raw == '/' or raw.startswith('/'):
from linkright.skills import discover_skills, discover_custom
all_cmds = list(main.commands.keys()) + discover_skills() + discover_custom()
chosen = inquirer.fuzzy(
    message="/",
    choices=all_cmds,
    max_height="60%",
).execute()
main.invoke(ctx, chosen)  # built-in
# or: skill_run(chosen)   # skill / custom`}
      />
    </CCBoard>
  );
}

/* =========================================================================
   J · Polish — NO_COLOR · daltonized · interrupt double-tap · context warn
   ========================================================================= */
function CCPolishArtboard() {
  return (
    <CCBoard
      phase="J · Polish · NO_COLOR · daltonized · interrupt · context warn"
      title="The corners that make CC feel finished."
      blurb="NO_COLOR=1 must remain readable. Daltonized themes remap red/green to colorblind-safer hues. Interrupt is double-tap — first Ctrl+C shows the hint, second exits. Context warning fires at ~80% of token budget."
      sources={["05-color-theme.md (NO_COLOR · daltonized)", "03-input.md (interrupt) · 04-feedback.md (compact)"]}
    >
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gridTemplateRows: "1fr 1fr", gap: 14, flex: 1, minHeight: 0 }}>
        {/* NO_COLOR fallback */}
        <CCShell title="NO_COLOR=1 · accessible fallback" size="80×16">
          <CCUserTurn>/tailor jd/anthropic.md</CCUserTurn>
          <div style={{ color: CC.fg }}>
            <div>● Read(jd/anthropic.md)</div>
            <div style={{ paddingLeft: 14 }}>⎿  Returns: 142 lines</div>
            <div>● Edit(resume/master.md)</div>
            <div style={{ paddingLeft: 14 }}>⎿  Updated 12 lines (5 added, 4 removed, 3 modified)</div>
            <div style={{ paddingLeft: 22, whiteSpace: "pre" }}>{`@@ -3,4 +3,4 @@
- Shipped pricing experiments that helped revenue
+ Drove +$2.4M ARR via 6-week pricing test`}</div>
          </div>
          <div style={{ marginTop: "auto", color: CC.fg, fontSize: 10.5 }}>
            no ANSI codes · structure conveys meaning · symbols not colour-only (✓ / ✗ / +/-)
          </div>
        </CCShell>

        {/* Daltonized */}
        <CCShell title="theme: dark-daltonized" size="80×16">
          <CCToolCard tool="Edit" args="resume/bullets.md" status="done">Updated 12 lines</CCToolCard>
          <div style={{ paddingLeft: 22 }}>
            <CCDiff
              path="resume/bullets.md"
              hunks={[{
                header: "-3 +3",
                lines: [
                  "- Shipped pricing experiments that helped revenue",
                  "+ Drove +$2.4M ARR via 6-week pricing test",
                ],
              }]}
            />
          </div>
          <div style={{ marginTop: "auto", color: CC.dim, fontSize: 10.5 }}>
            red/green remapped to <span style={{ color: "#F5C842" }}>amber</span> and <span style={{ color: "#5BC0D0" }}>cyan</span> — distinguishable for deuteranopia
          </div>
        </CCShell>

        {/* Interrupt double-tap */}
        <CCShell title="interrupt · ctrl+c × 2" size="80×16">
          <CCSpinner verb="Brewing" elapsed="14.2s" frame="⠧" />
          <div style={{ color: CC.red, fontWeight: 700, marginTop: 6 }}>Interrupted</div>
          <div style={{ color: CC.dim }}>(press <CCKey>Ctrl+C</CCKey> again to exit, or <CCKey>Ctrl+D</CCKey>)</div>
          <div style={{ marginTop: "auto", paddingTop: 8, color: CC.dim, fontSize: 10.5 }}>
            first ctrl+c: cancels the in-flight stream, keeps progress<br />
            second ctrl+c (within ~2s): exits the session
          </div>
        </CCShell>

        {/* Context warning + compaction */}
        <CCShell title="context approaching limit" size="80×16">
          <div style={{ color: CC.yellow }}>⚠  Context approaching limit (820k / 1M tokens used)</div>
          <div style={{ color: CC.dim, fontSize: 11, marginTop: 4 }}>auto-compaction will run at ~95%, or run <CCKey>/compact</CCKey> now.</div>
          <div style={{ marginTop: 8 }}>
            <CCSpinner verb="Compacting" elapsed="0.4s" frame="⠹" tip="summarising prior turns to free up tokens" />
          </div>
          <div style={{ marginTop: "auto", paddingTop: 8 }}>
            <CCToolCard tool="PreCompact hook" status="done">linkright watch sync → state saved to ~/.linkright/snapshots/</CCToolCard>
          </div>
        </CCShell>
      </div>

      <ImplNote
        files={["linkright/ui/__init__.py", "linkright/ui/theme.py"]}
        summary="NO_COLOR, daltonized theme, interrupt double-tap, and context budget warning."
        steps={[
          "**`NO_COLOR=1`:** At module load in `ui/__init__.py`: `_no_color = bool(os.getenv('NO_COLOR'))`. Then `console = Console(no_color=_no_color, force_terminal=not _no_color)`. All Rich markup strips automatically when `no_color=True`.",
          "**Daltonized theme:** In `theme.py`, add a `LR_THEME_DALTONIZED` variant that remaps `[red]` → `[#F5C842]` (amber) and `[green]` → `[#5BC0D0]` (cyan). Detect via `settings.theme == 'dark-daltonized'`.",
          "**Interrupt double-tap:** Use `signal.signal(signal.SIGINT, _sigint_handler)`. Handler: on first call, set `_interrupted = True`, print `[red]Interrupted[/]` + `[dim](press Ctrl+C again to exit)[/]`. On second call within 2s: `sys.exit(130)`.",
          "**Context budget warning:** Before each LLM call, check `tokens_used / model_max_tokens > 0.80`. If so: `console.print('[yellow]⚠[/] Context approaching limit ({tokens_used:,} / {model_max_tokens:,} used)')`. Suggest `/compact` or `--compact` flag.",
          "**Verification checklist (run before shipping each phase):** `NO_COLOR=1 linkright tldr` renders cleanly · Ctrl+C during streaming shows hint · second Ctrl+C exits · `--permission-mode plan linkright tailor` shows magenta banner.",
        ]}
        warn="Test NO_COLOR=1 on every new surface — it's easy to accidentally leak ANSI through f-strings that bypass Rich markup."
      />
    </CCBoard>
  );
}

/* =========================================================================
   A · Stack choice card — the one Phase A artifact
   ========================================================================= */
function CCStackArtboard() {
  return (
    <CCBoard
      phase="A · Stack · single binary · one runtime question"
      title="Bun + Ink + React. Compiled to one file. Match CC distribution."
      blurb="LinkRight today is Python + Rich + InquirerPy. The CC-true target is Bun-compiled Ink — single Mach-O / ELF / EXE per platform, identical UX everywhere. This is the only Phase A decision; everything else (B–J) compiles from the same scaffold."
      sources={["01-stack.md · 11-repro-ink-clone.md"]}
    >
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 18, flex: 1, minHeight: 0 }}>
        <div style={{ background: "var(--color-skin-50)", borderRadius: 12, padding: "20px 24px", border: "1px solid var(--color-border)", display: "flex", flexDirection: "column", gap: 16 }}>
          <div style={{ fontSize: 12, color: "var(--color-muted)", letterSpacing: "0.12em", textTransform: "uppercase", fontWeight: 600 }}>LinkRight today (v0.9.2)</div>
          <div style={{ display: "grid", gridTemplateColumns: "120px 1fr", rowGap: 8, fontSize: 13, fontFamily: "var(--font-mono)" }}>
            <div style={{ color: "var(--color-muted)" }}>Runtime</div><div>Python 3.10+</div>
            <div style={{ color: "var(--color-muted)" }}>TUI lib</div><div>Rich + InquirerPy</div>
            <div style={{ color: "var(--color-muted)" }}>Layout</div><div>Rich console (single column)</div>
            <div style={{ color: "var(--color-muted)" }}>Dist</div><div>pip install linkright</div>
            <div style={{ color: "var(--color-muted)" }}>Size</div><div>~12 MB site-packages</div>
            <div style={{ color: "var(--color-muted)" }}>Streaming</div><div>print() · Rich progress</div>
            <div style={{ color: "var(--color-muted)" }}>State</div><div>Click context + JSON files</div>
          </div>
          <div style={{ marginTop: "auto", fontSize: 12, color: "var(--color-foreground)", lineHeight: 1.6 }}>
            <strong>Strengths:</strong> fast iteration, ML libs nearby, low binary size.<br />
            <strong>Costs:</strong> no <code>{"<Static>"}</code> primitive, no alt-screen by default, hard to do live tail without flicker.
          </div>
        </div>

        <div style={{ background: "#0E1118", borderRadius: 12, padding: "20px 24px", border: `1.5px solid ${CC.cyan}`, color: CC.fg, fontFamily: "ui-monospace, monospace", display: "flex", flexDirection: "column", gap: 16 }}>
          <div style={{ fontSize: 12, color: CC.cyan, letterSpacing: "0.12em", textTransform: "uppercase", fontWeight: 700 }}>CC-true target (v2.0)</div>
          <div style={{ display: "grid", gridTemplateColumns: "120px 1fr", rowGap: 8, fontSize: 13 }}>
            <div style={{ color: CC.dim }}>Runtime</div><div>Bun 1.3.14+</div>
            <div style={{ color: CC.dim }}>TUI lib</div><div>Ink (React reconciler)</div>
            <div style={{ color: CC.dim }}>Layout</div><div>Yoga (flexbox)</div>
            <div style={{ color: CC.dim }}>Dist</div><div>npm wrapper → platform binary</div>
            <div style={{ color: CC.dim }}>Size</div><div>~120–180 MB (single file)</div>
            <div style={{ color: CC.dim }}>Streaming</div><div>{"<Static>"} log + live {"<Box>"} tail</div>
            <div style={{ color: CC.dim }}>State</div><div>useState / useRef / useEffect</div>
          </div>
          <div style={{ marginTop: "auto", fontSize: 12, color: CC.fg, lineHeight: 1.6 }}>
            <span style={{ color: CC.green }}>+ </span>identical UX on macOS / Linux / Windows / WSL<br />
            <span style={{ color: CC.green }}>+ </span><code>bun build --compile</code> = one binary per platform<br />
            <span style={{ color: CC.green }}>+ </span>Static trick scales to 1000-turn sessions trivially<br />
            <span style={{ color: CC.red }}>− </span>Python pipeline (resume, scoring) runs as subprocess
          </div>
        </div>
      </div>

      <div style={{ background: "#0E1118", borderRadius: 10, border: `1px solid ${CC.borderD}`, padding: "16px 20px", fontFamily: "ui-monospace, monospace", color: CC.fg, fontSize: 12 }}>
        <div style={{ color: CC.dim, fontSize: 10.5, letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 6 }}>
          phase A · the one command to start
        </div>
        <div><span style={{ color: CC.dim }}>$ </span>mkdir linkright-tui && cd linkright-tui</div>
        <div><span style={{ color: CC.dim }}>$ </span>bun init -y</div>
        <div><span style={{ color: CC.dim }}>$ </span>bun add ink react ink-spinner</div>
        <div><span style={{ color: CC.dim }}>$ </span>cp ../cc-frontend-design/spinner-verbs/verbs.json ./spinner-verbs/</div>
        <div><span style={{ color: CC.dim }}>$ </span>{"# paste the scaffold from 11-repro-ink-clone.md → app.jsx"}</div>
        <div><span style={{ color: CC.dim }}>$ </span>bun run app.jsx <span style={{ color: CC.dim }}># dev loop</span></div>
        <div><span style={{ color: CC.dim }}>$ </span>bun build app.jsx --compile --outfile linkright <span style={{ color: CC.dim }}># ship</span></div>
      </div>

      <ImplNote
        files={["pyproject.toml", "linkright/config.py"]}
        summary="Near-term: stay on Python+Rich and apply all CC visual tokens. Long-term: Bun+Ink for full parity."
        steps={[
          "**Near-term (applies now):** Phases B–J are all doable in Python+Rich. Apply them in order. The visual output will match CC even without Ink.",
          "**Long-term (v2.0 migration):** `bun init` → `bun add ink react ink-spinner` → scaffold from `cc-frontend-design/11-repro-ink-clone.md`. The Python pipeline (resume scoring, LLM calls) runs as a subprocess spawned by the Ink shell.",
          "**Add to `config.py`:** `permission_mode: str = 'default'` — required before phases F and G.",
          "**`pyproject.toml`:** Keep entry point `linkright.cli:main` for near-term. When Bun shell is ready, add a second entry `linkright-ui` pointing to the compiled binary.",
          "**Single binary (Bun):** `bun build app.jsx --compile --outfile dist/linkright` produces a ~150 MB self-contained executable identical to CC's distribution model.",
        ]}
        warn="Do NOT start the Bun migration until all Python near-term changes (phases B–J) are shipped and approved. They are independent improvements that deliver value immediately."
      />
    </CCBoard>
  );
}

Object.assign(window, {
  CCCrosswalkArtboard,
  CCStackArtboard,
  CCSkeletonArtboard,
  CCInputArtboard,
  CCStreamingArtboard,
  CCToolCardsArtboard,
  CCPermissionArtboard,
  CCPlanModeArtboard,
  CCSettingsArtboard,
  CCSlashArtboard,
  CCPolishArtboard,
});
