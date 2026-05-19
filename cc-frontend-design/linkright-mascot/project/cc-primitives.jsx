/* =========================================================================
   cc-primitives.jsx — Claude-Code-true visual primitives.

   Every value here is sourced from cc-frontend-design/* docs:
     palette: 02-rendering.md (frequency-ranked ANSI hits)
     glyphs:  CHEATSHEET.md, 09-tool-render.md
     hint:    02-rendering.md (dim+cyan+dim signature)
     shell:   01-stack.md (Ink+Bun, alt-screen, bordered input)

   Goal: build LinkRight's CLI so it visually & structurally feels like CC.
   The LR house palette (teal/coral/gold) stays for the LINKRIGHT banner
   only — every other surface follows CC conventions verbatim.
   ========================================================================= */

/* ---------- The real CC palette (dark theme) ---------- */
const CC = {
  // Terminal paper. CC enters alt-screen, so we paint a clean canvas.
  bg:       "#0E1118",    // terminal default (slightly blue-black)
  fg:       "#E5E5E5",    // \x1b[0m default foreground
  dim:      "rgba(229,229,229,0.55)",  // \x1b[2m — workhorse
  dimSolid: "#8E8E93",    // dim flattened for places that can't alpha
  // Semantic 8-bit colours (terminal-rendered)
  red:      "#E55353",    // \x1b[31m
  green:    "#62C264",    // \x1b[32m
  yellow:   "#D6BA5B",    // \x1b[33m
  blue:     "#5C9DD9",    // \x1b[34m
  magenta:  "#B870C5",    // \x1b[35m — plan mode
  cyan:     "#5BC0D0",    // \x1b[36m — keys, slash, links
  white:    "#FFFFFF",    // \x1b[37m (rare)
  // Bright variants
  brYellow: "#F5C842",    // \x1b[93m — diff hunk headers
  // Borders
  border:   "rgba(229,229,229,0.20)",   // input box / panels
  borderD:  "rgba(229,229,229,0.10)",
  // Selected (inverse \x1b[7m): swap fg/bg
  invFg:    "#0E1118",
  invBg:    "#E5E5E5",
};

/* ---------- 1. Shell — alt-screen terminal frame ----------
   01-stack.md: 198 MB Bun-compiled Ink. 02-rendering.md: enters
   alt-screen (\x1b[?1049h). We render that as a mac-chrome-less
   full-bleed pane so the design canvas reads as "what the user
   actually sees once CC takes over the terminal".
*/
function CCShell({ title = "linkright", size = "120×36", children, style }) {
  return (
    <div style={{
      background: CC.bg,
      borderRadius: 10,
      overflow: "hidden",
      border: `1px solid ${CC.borderD}`,
      fontFamily: "ui-monospace, 'SF Mono', Menlo, Consolas, monospace",
      color: CC.fg,
      fontSize: 12.5,
      lineHeight: 1.55,
      display: "flex", flexDirection: "column",
      ...style,
    }}>
      {/* tab strip — extremely minimal mac chrome, faded */}
      <div style={{
        height: 24, display: "flex", alignItems: "center", padding: "0 12px", gap: 6,
        background: "rgba(255,255,255,0.025)", borderBottom: `1px solid ${CC.borderD}`,
        flex: "0 0 auto",
      }}>
        <span style={{ width: 9, height: 9, borderRadius: "50%", background: "#3A3A3F" }} />
        <span style={{ width: 9, height: 9, borderRadius: "50%", background: "#3A3A3F" }} />
        <span style={{ width: 9, height: 9, borderRadius: "50%", background: "#3A3A3F" }} />
        <span style={{ marginLeft: 12, fontSize: 10.5, color: CC.dim, letterSpacing: 0.2 }}>
          {title} — {size}
        </span>
      </div>
      <div style={{ padding: "12px 16px 0", flex: 1, overflow: "hidden", display: "flex", flexDirection: "column", minHeight: 0 }}>
        {children}
      </div>
    </div>
  );
}

/* ---------- 2. Hint — the signature dim → dim+cyan → dim pattern ----------
   02-rendering.md: \x1b[2mPress \x1b[2;36mh + Enter\x1b[39;2m to show shortcuts\x1b[0m
*/
function CCHint({ children }) {
  return <span style={{ color: CC.dim }}>{children}</span>;
}
function CCKey({ children }) {
  return <span style={{ color: CC.cyan, opacity: 0.85 }}>{children}</span>;
}

/* ---------- 3. Static / Streaming / committed turn helpers ---------- */
function CCUserTurn({ children }) {
  return (
    <div style={{ padding: "4px 0" }}>
      <span style={{ color: CC.green, fontWeight: 600 }}>{"› "}</span>
      <span style={{ color: CC.fg }}>{children}</span>
    </div>
  );
}

function CCAssistant({ children }) {
  return (
    <div style={{ padding: "4px 0", color: CC.fg }}>{children}</div>
  );
}

/* ---------- 4. Tool card — ● glyph + ⎿ connector ----------
   09-tool-render.md: status glyph coloured by state, ⎿ (U+23BF) connector,
   indented dim output, optional collapse.
*/
function CCToolCard({ status = "done", tool, args, children, collapsed }) {
  const glyphColor =
    status === "running" ? CC.yellow :
    status === "error"   ? CC.red    :
    status === "denied"  ? CC.yellow :
                           CC.green;
  const glyph = status === "running" ? "○" : "●";
  return (
    <div style={{ margin: "6px 0" }}>
      <div style={{ display: "flex", alignItems: "baseline", gap: 0 }}>
        <span style={{ color: glyphColor }}>{glyph}{" "}</span>
        <span style={{ color: CC.fg, fontWeight: 600 }}>{tool}</span>
        {args && <span style={{ color: CC.dim }}>{"("}{args}{")"}</span>}
      </div>
      {children && (
        <div style={{ paddingLeft: 2, marginTop: 2, display: "flex", gap: 4 }}>
          <span style={{ color: CC.dim }}>⎿{"  "}</span>
          <div style={{ color: CC.dim, flex: 1 }}>{children}</div>
        </div>
      )}
      {collapsed && (
        <div style={{ paddingLeft: 22, color: CC.dim, fontStyle: "italic", marginTop: 2 }}>
          … ({collapsed} more lines, press <CCKey>↓</CCKey> to expand)
        </div>
      )}
    </div>
  );
}

/* ---------- 5. Diff renderer — red - / green + / bright-yellow @@ ---------- */
function CCDiff({ path, hunks }) {
  return (
    <div style={{ margin: "2px 0 4px", fontFamily: "ui-monospace, monospace", fontSize: 11.5 }}>
      <div style={{ color: CC.dim, fontWeight: 700 }}>{path}</div>
      {hunks.map((h, hi) => (
        <div key={hi}>
          <div style={{ color: CC.brYellow }}>@@ {h.header} @@</div>
          {h.lines.map((line, li) => {
            const isAdd = line.startsWith("+");
            const isDel = line.startsWith("-");
            return (
              <div key={li} style={{
                color: isAdd ? CC.green : isDel ? CC.red : CC.fg,
                whiteSpace: "pre",
              }}>{line}</div>
            );
          })}
        </div>
      ))}
    </div>
  );
}

/* ---------- 6. Spinner — braille dots + rotating verb + tip ----------
   04-feedback.md: 32-verb initial pool, ~80ms/frame, tip line below.
*/
function CCSpinner({ verb = "Crafting", tip, frame = "⠋", elapsed }) {
  return (
    <div style={{ padding: "6px 0" }}>
      <div style={{ display: "flex", alignItems: "baseline", gap: 6 }}>
        <span style={{ color: CC.yellow }}>{frame}</span>
        <span style={{ color: CC.fg }}>{verb}…</span>
        {elapsed && <span style={{ color: CC.dim }}>({elapsed})</span>}
        <span style={{ color: CC.dim }}>(</span>
        <CCKey>esc</CCKey>
        <span style={{ color: CC.dim }}>to interrupt)</span>
      </div>
      {tip && (
        <div style={{ paddingLeft: 18, color: CC.dim, marginTop: 2 }}>
          <span style={{ color: CC.dim }}>Tip: </span>{tip}
        </div>
      )}
    </div>
  );
}

/* ---------- 7. Input box — round border, > prompt, cursor ----------
   03-input.md: borderStyle="round" borderColor="gray" paddingX={1}.
*/
function CCInputBox({ value, mode, focused = true }) {
  return (
    <div style={{
      border: `1px solid ${CC.border}`,
      borderRadius: 6,
      padding: "6px 12px",
      margin: "8px 0 4px",
    }}>
      <div style={{ display: "flex", alignItems: "baseline", gap: 6 }}>
        <span style={{ color: CC.cyan }}>{"> "}</span>
        <span style={{ color: value ? CC.fg : CC.dim }}>
          {value || "Type a message, / for commands, @ for files, ! for bash"}
        </span>
        {focused && (
          <span style={{
            display: "inline-block", width: 6, height: 13,
            background: CC.fg, marginLeft: 2, verticalAlign: "middle",
            animation: "pipBlink 1s steps(1) infinite",
          }} />
        )}
      </div>
    </div>
  );
}

/* ---------- 8. Status line — bottom row, dim, subprocess output ---------- */
function CCStatusLine({ children }) {
  return (
    <div style={{
      color: CC.dim, padding: "4px 0 8px", flex: "0 0 auto",
    }}>
      {children}
    </div>
  );
}

/* ---------- 9. Permission prompt — bordered radio list ----------
   07-permission-modes.md: bordered round, ❯ focus, Esc=Deny.
*/
function CCPermissionPrompt({ title = "Claude wants to run a command:", command, options, focused = 0 }) {
  return (
    <div style={{
      border: `1px solid ${CC.border}`,
      borderRadius: 6,
      padding: "10px 14px",
      margin: "6px 0",
      maxWidth: 640,
    }}>
      <div style={{ color: CC.fg }}>{title}</div>
      <div style={{ margin: "10px 0", paddingLeft: 2 }}>
        <span style={{ color: CC.cyan }}>{command}</span>
      </div>
      {options.map((opt, i) => (
        <div key={i} style={{ display: "flex", alignItems: "baseline", gap: 2, padding: "1px 0" }}>
          <span style={{ color: i === focused ? CC.cyan : "transparent", width: 14 }}>
            {i === focused ? "❯ " : "  "}
          </span>
          <span style={{ color: i === focused ? CC.cyan : CC.fg }}>{opt.label}</span>
          {opt.note && <span style={{ color: CC.dim, marginLeft: 6 }}>{opt.note}</span>}
        </div>
      ))}
    </div>
  );
}

/* ---------- 10. Plan-mode banner — magenta bordered ----------
   08-plan-mode.md: \x1b[35m magenta is reserved for plan mode.
*/
function CCPlanBanner({ children = "Read-only. Use ExitPlanMode when ready." }) {
  return (
    <div style={{
      border: `1px solid ${CC.magenta}`,
      borderRadius: 6,
      padding: "6px 12px",
      margin: "6px 0",
      display: "flex", gap: 12, alignItems: "baseline",
    }}>
      <span style={{ color: CC.magenta, fontWeight: 700, letterSpacing: "0.06em" }}>PLAN MODE</span>
      <span style={{ color: CC.dim }}>{children}</span>
    </div>
  );
}

/* ---------- 11. Slash palette — drop-down beneath input ----------
   06-slash-commands.md: fuzzy match, ↑↓ nav, Tab fills prefix, ❯ focus.
*/
function CCSlashPalette({ matches, focused = 0 }) {
  return (
    <div style={{ paddingLeft: 14, marginTop: 2 }}>
      {matches.map((m, i) => (
        <div key={m.cmd} style={{ display: "flex", gap: 8, padding: "1px 0", alignItems: "baseline" }}>
          <span style={{ color: i === focused ? CC.cyan : "transparent" }}>❯</span>
          <span style={{ color: i === focused ? CC.cyan : CC.fg, fontWeight: i === focused ? 600 : 400 }}>{m.cmd}</span>
          <span style={{ color: CC.dim }}>{m.desc}</span>
        </div>
      ))}
    </div>
  );
}

/* ---------- 12. Subagent connector — '│ ' indent ---------- */
function CCSubagent({ children }) {
  return (
    <div style={{ paddingLeft: 20, borderLeft: `1px solid ${CC.borderD}`, marginLeft: 8, margin: "4px 0 4px 8px" }}>
      {React.Children.map(children, (child, i) => (
        <div key={i} style={{ display: "flex", gap: 8 }}>
          <span style={{ color: CC.dim, paddingTop: 4 }}>│</span>
          <div style={{ flex: 1 }}>{child}</div>
        </div>
      ))}
    </div>
  );
}

/* ---------- 13. Welcome banner — CC's "Welcome to ..." ---------- */
function CCWelcomeBanner({ children = "Welcome to LinkRight for Satvik Jain", subtitle }) {
  return (
    <div style={{ padding: "4px 0 8px" }}>
      <div style={{ color: CC.green, fontWeight: 700 }}>{children}</div>
      {subtitle && <div style={{ color: CC.dim, marginTop: 2 }}>{subtitle}</div>}
    </div>
  );
}

/* ---------- 14. AskUserQuestion form (side-by-side preview) ---------- */
function CCAskUser({ question, options, focused = 0, preview }) {
  return (
    <div style={{ margin: "8px 0" }}>
      <div style={{ color: CC.fg, marginBottom: 6 }}>
        <span style={{ color: CC.green }}>● </span>
        <span style={{ fontWeight: 600 }}>AskUserQuestion: </span>
        <span>{question}</span>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        <div style={{ border: `1px solid ${CC.border}`, borderRadius: 6, padding: "8px 10px" }}>
          <div style={{ color: CC.dim, fontSize: 10.5, letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 4 }}>options</div>
          {options.map((opt, i) => (
            <div key={opt} style={{ padding: "1px 0", display: "flex", gap: 4 }}>
              <span style={{ color: i === focused ? CC.cyan : "transparent" }}>❯</span>
              <span style={{ color: i === focused ? CC.cyan : CC.fg }}>{opt}</span>
            </div>
          ))}
        </div>
        <div style={{ border: `1px solid ${CC.border}`, borderRadius: 6, padding: "8px 10px" }}>
          <div style={{ color: CC.dim, fontSize: 10.5, letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 4 }}>preview</div>
          <pre style={{ margin: 0, color: CC.fg, fontSize: 11, fontFamily: "ui-monospace, monospace", whiteSpace: "pre-wrap" }}>{preview}</pre>
        </div>
      </div>
    </div>
  );
}

/* ---------- 15. Todo card — [ ] [⏵] [✓] ---------- */
function CCTodo({ items }) {
  return (
    <div>
      {items.map((it, i) => {
        const mark = it.state === "done" ? "[✓]" : it.state === "doing" ? "[⏵]" : "[ ]";
        const color = it.state === "done" ? CC.green : it.state === "doing" ? CC.yellow : CC.dim;
        return (
          <div key={i} style={{ display: "flex", gap: 8 }}>
            <span style={{ color }}>{mark}</span>
            <span style={{ color: it.state === "done" ? CC.dim : CC.fg, textDecoration: it.state === "done" ? "line-through" : "none" }}>{it.label}</span>
          </div>
        );
      })}
    </div>
  );
}

/* =========================================================================
   ImplNote — annotates an artboard with concrete Python implementation
   guidance. Visually separated from the CC terminal mock above it.

   Props:
     files    — array of "path/to/file.py" strings shown as badges
     summary  — one-line description of what to change
     steps    — array of step strings (numbered checklist)
     before   — current LR-house code snippet (optional)
     after    — CC-true code snippet (optional)
     warn     — yellow warning callout (optional)
   ========================================================================= */
function ImplNote({ files = [], summary, steps = [], before, after, warn, children }) {
  return (
    <div style={{
      background: "var(--color-background)",
      borderLeft: "3px solid var(--color-accent)",
      borderRadius: "0 8px 8px 0",
      padding: "14px 20px",
      fontFamily: "var(--font-sans)",
      fontSize: 12.5,
      lineHeight: 1.6,
      display: "flex",
      flexDirection: "column",
      gap: 10,
    }}>
      {/* file badges */}
      {files.length > 0 && (
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          <span style={{ fontSize: 10.5, color: "var(--color-muted)", fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase", alignSelf: "center", marginRight: 4 }}>files</span>
          {files.map(f => (
            <code key={f} style={{
              fontFamily: "var(--font-mono)", fontSize: 11,
              background: "rgba(15,190,175,0.08)", color: "var(--color-accent)",
              padding: "1px 7px", borderRadius: 4, border: "1px solid rgba(15,190,175,0.2)",
            }}>{f}</code>
          ))}
        </div>
      )}

      {/* summary */}
      {summary && (
        <div style={{ color: "var(--color-foreground)", fontWeight: 600, fontSize: 13 }}>{summary}</div>
      )}

      {/* warn */}
      {warn && (
        <div style={{
          display: "flex", gap: 8, alignItems: "flex-start",
          background: "rgba(255,87,51,0.06)", border: "1px solid rgba(255,87,51,0.18)",
          borderRadius: 6, padding: "8px 10px", fontSize: 12,
        }}>
          <span style={{ color: "var(--color-cta)", fontWeight: 700 }}>⚠</span>
          <span style={{ color: "var(--color-foreground)" }}>{warn}</span>
        </div>
      )}

      {/* numbered steps */}
      {steps.length > 0 && (
        <ol style={{ margin: 0, paddingLeft: 20, display: "flex", flexDirection: "column", gap: 4 }}>
          {steps.map((s, i) => (
            <li key={i} style={{ color: "var(--color-foreground)", fontSize: 12.5 }}>
              <span dangerouslySetInnerHTML={{ __html: s
                .replace(/`([^`]+)`/g, '<code style="font-family:var(--font-mono);font-size:11px;background:rgba(0,0,0,0.07);padding:1px 5px;border-radius:3px">$1</code>')
                .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
              }} />
            </li>
          ))}
        </ol>
      )}

      {/* freeform children */}
      {children}

      {/* before / after code */}
      {(before || after) && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          {before && (
            <div>
              <div style={{ fontSize: 10, color: "var(--color-cta)", letterSpacing: "0.1em", textTransform: "uppercase", fontWeight: 600, marginBottom: 4 }}>current (LR house)</div>
              <pre style={{
                margin: 0, background: "#1A1F2E", color: "#EEF5F2",
                padding: "10px 12px", borderRadius: 6, fontSize: 11,
                fontFamily: "var(--font-mono)", lineHeight: 1.55, whiteSpace: "pre-wrap",
                borderLeft: "3px solid var(--color-cta)",
              }}>{before}</pre>
            </div>
          )}
          {after && (
            <div>
              <div style={{ fontSize: 10, color: "var(--color-accent)", letterSpacing: "0.1em", textTransform: "uppercase", fontWeight: 600, marginBottom: 4 }}>target (CC-true)</div>
              <pre style={{
                margin: 0, background: "#1A1F2E", color: "#EEF5F2",
                padding: "10px 12px", borderRadius: 6, fontSize: 11,
                fontFamily: "var(--font-mono)", lineHeight: 1.55, whiteSpace: "pre-wrap",
                borderLeft: "3px solid var(--color-accent)",
              }}>{after}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

Object.assign(window, {
  CC,
  CCShell, CCHint, CCKey, CCUserTurn, CCAssistant,
  CCToolCard, CCDiff, CCSpinner, CCInputBox, CCStatusLine,
  CCPermissionPrompt, CCPlanBanner, CCSlashPalette, CCSubagent,
  CCWelcomeBanner, CCAskUser, CCTodo, ImplNote,
});
