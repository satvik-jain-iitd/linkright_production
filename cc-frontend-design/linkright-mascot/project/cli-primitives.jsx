/* =========================================================================
   cli-primitives.jsx — shared building blocks for LinkRight CLI mockups.

   Implements the exact iconography + theme aliases defined in
   linkright/ui/icons.py + theme.py + patterns.py + layout.py.

   Symbol set (from icons.py):
     ◇ input    ●  info    🌟 highlight   ✓ success   ✗ fail   ★ insight
     *  working  +  thinking  └/├/│ branch   →/← arrow   ⊗/□ tab
     ◆  section  ›/❯ prompt    ·  dot       — em-dash    ─ rule
   ========================================================================= */

const LR = {
  // brand palette aliases from theme.py
  primary:  "#4285F4",
  err:      "#EA4335",
  good:     "#34A853",
  muted:    "#8E8E93",
  divider:  "#DADCE0",
  // banner gradient family
  teal:     "#0FBEAF",
  cyan:     "#06B6D4",
  cyanBold: "#0891B2",
  gold:     "#F4B400",
  coral:    "#EE6F4F",   // tui.coral — working *
  salmon:   "#FF8B6E",
  mutedTeal:"#5EB3A8",
  // shell paper
  bg:       "#0E1620",
  panel:    "#151F2B",
  border:   "#253140",
  fg:       "#EEF5F2",
  faint:    "#5A6B7C",
};

/* ---------- ShellWindow — tiny mac-style window, no host strip
   so multiple mockups fit on one artboard. ---------- */
function ShellWindow({ title = "linkright", host = "satvikjain@MacBook-Air", size = "120×36", children, style, dense }) {
  return (
    <div style={{
      background: LR.bg,
      borderRadius: 12,
      overflow: "hidden",
      boxShadow: "0 12px 32px rgba(15, 23, 42, 0.4)",
      border: `1px solid ${LR.border}`,
      fontFamily: "ui-monospace, 'SF Mono', Menlo, Consolas, monospace",
      color: LR.fg,
      display: "flex",
      flexDirection: "column",
      ...style,
    }}>
      <div style={{
        height: 28, background: LR.panel, borderBottom: `1px solid ${LR.border}`,
        display: "flex", alignItems: "center", padding: "0 12px", gap: 6, flex: "0 0 auto",
      }}>
        <span style={{ width: 11, height: 11, borderRadius: "50%", background: "#FF5F57" }} />
        <span style={{ width: 11, height: 11, borderRadius: "50%", background: "#FEBC2E" }} />
        <span style={{ width: 11, height: 11, borderRadius: "50%", background: "#28C840" }} />
        <span style={{ marginLeft: 10, fontSize: 11, color: LR.muted, letterSpacing: 0.2 }}>
          {host} — {title} — {size}
        </span>
      </div>
      <div style={{ padding: dense ? "10px 14px 12px" : "14px 18px 16px", lineHeight: 1.55, flex: 1, overflow: "hidden", fontSize: 12.5 }}>
        {children}
      </div>
    </div>
  );
}

/* ---------- Prompt — '%' shell line. */
function ShPrompt({ cwd = "~/linkright", children }) {
  return (
    <div style={{ display: "flex", gap: 6, alignItems: "baseline", fontSize: 12.5, marginBottom: 2 }}>
      <span style={{ color: LR.faint }}>●</span>
      <span style={{ color: LR.muted }}>(base)</span>
      <span style={{ color: LR.fg }}>{cwd}</span>
      <span style={{ color: LR.gold }}>%</span>
      <span style={{ color: LR.fg }}>{children}</span>
    </div>
  );
}

/* ---------- Input marker — ◇  label  (BMAD style). */
function ShInput({ label, value, focused, hint, accent = LR.cyan }) {
  return (
    <div style={{ margin: "6px 0" }}>
      <div style={{ display: "flex", alignItems: "baseline", gap: 8, fontSize: 12.5 }}>
        <span style={{ color: accent }}>◇</span>
        <span style={{ color: LR.fg, fontWeight: 500 }}>{label}</span>
      </div>
      <div style={{
        marginLeft: 22, marginTop: 4,
        border: `1px solid ${focused ? accent : LR.border}`,
        borderRadius: 6, padding: "6px 10px",
        background: focused ? "rgba(6,182,212,0.06)" : "transparent",
        color: value ? LR.fg : LR.faint, fontSize: 12,
        display: "flex", alignItems: "center", gap: 6,
      }}>
        {focused && <span style={{ color: accent, fontWeight: 700 }}>›</span>}
        <span>{value || "Type something…"}</span>
        {focused && <span style={{
          display: "inline-block", width: 7, height: 12, background: LR.fg, marginLeft: 2,
          animation: "pipBlink 1s steps(1) infinite",
        }} />}
      </div>
      {hint && (
        <div style={{ marginLeft: 22, marginTop: 4, fontSize: 10.5, color: LR.muted }}>
          └ {hint}
        </div>
      )}
    </div>
  );
}

/* ---------- Echo bullet — '●' high-contrast (user_input_echo) */
function ShEcho({ label, value }) {
  return (
    <div style={{ display: "flex", gap: 8, alignItems: "baseline", fontSize: 12.5, padding: "1px 0" }}>
      <span style={{ color: LR.fg, fontWeight: 700 }}>●</span>
      <span style={{ color: LR.fg }}>{label ? <><span style={{ fontWeight: 500 }}>{label}:</span> {value}</> : value}</span>
    </div>
  );
}

/* ---------- Working verb — '*  Verb… (telemetry)' */
function ShWork({ verb, telemetry, icon = "*" }) {
  const color = icon === "+" ? LR.good : LR.coral;
  return (
    <div style={{ display: "flex", gap: 8, alignItems: "baseline", fontSize: 12.5, padding: "1px 0" }}>
      <span style={{ color, fontWeight: 700 }}>{icon}</span>
      <span style={{ color: LR.coral }}>{verb}</span>
      {telemetry && <span style={{ color: LR.muted }}>{telemetry}</span>}
    </div>
  );
}

/* ---------- Status — ✓ / ✗ */
function ShStatus({ ok, label, detail }) {
  return (
    <div style={{ display: "flex", gap: 8, alignItems: "baseline", fontSize: 12.5, padding: "1px 0" }}>
      <span style={{ color: ok ? LR.good : LR.err, fontWeight: 700 }}>{ok ? "✓" : "✗"}</span>
      <span style={{ color: LR.fg }}>{label}</span>
      {detail && <span style={{ color: LR.muted }}>{detail}</span>}
    </div>
  );
}

/* ---------- Insight callout — coral ★ + rule. */
function ShInsight({ title = "Insight", children }) {
  return (
    <div style={{ margin: "10px 0", padding: "8px 0" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, color: LR.coral, fontSize: 12.5, fontWeight: 600 }}>
        <span>★</span><span>{title}</span>
        <span style={{ flex: 1, borderTop: `1px solid ${LR.coral}`, opacity: 0.5, marginLeft: 4 }} />
      </div>
      <div style={{ color: LR.fg, fontSize: 12, paddingLeft: 18, marginTop: 6, lineHeight: 1.55 }}>{children}</div>
      <div style={{ borderTop: `1px solid ${LR.coral}`, opacity: 0.35, marginTop: 8 }} />
    </div>
  );
}

/* ---------- L-branch tip / group */
function ShTip({ children, label = "Tip", connector = "└" }) {
  return (
    <div style={{ color: LR.muted, fontSize: 11.5, padding: "1px 0" }}>
      {connector} {label && <>{label}: </>}{children}
    </div>
  );
}

/* ---------- Result arrow — '→  text' */
function ShResult({ children }) {
  return (
    <div style={{ display: "flex", gap: 8, alignItems: "baseline", fontSize: 12.5, padding: "1px 0" }}>
      <span style={{ color: LR.mutedTeal }}>→</span>
      <span style={{ color: LR.fg }}>{children}</span>
    </div>
  );
}

/* ---------- Section header — ◆ */
function ShSection({ children, accent = LR.teal }) {
  return (
    <div style={{ margin: "10px 0 4px", display: "flex", alignItems: "baseline", gap: 8 }}>
      <span style={{ color: LR.gold }}>◆</span>
      <span style={{ color: LR.fg, fontWeight: 700, fontSize: 13 }}>{children}</span>
    </div>
  );
}

/* ---------- Horizontal divider */
function ShRule({ label }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, margin: "8px 0", color: LR.muted, fontSize: 11 }}>
      <span style={{ flex: 1, borderTop: `1px solid ${LR.border}` }} />
      {label && <span style={{ opacity: 0.8 }}>· {label} ·</span>}
      <span style={{ flex: 1, borderTop: `1px solid ${LR.border}` }} />
    </div>
  );
}

/* ---------- Sticky footer */
function ShFooter({ tier = "BASE", mode = "apply", status = "v0.9.2 · gemma3:1b · 1.2k tok" }) {
  return (
    <div style={{
      display: "flex", alignItems: "center", padding: "8px 14px",
      borderTop: `1px solid ${LR.border}`, background: LR.panel,
      fontSize: 11, fontFamily: "ui-monospace, monospace", flex: "0 0 auto",
    }}>
      <span style={{ color: LR.gold, fontWeight: 700 }}>[{tier}]</span>
      <span style={{ flex: 1, textAlign: "center", color: LR.muted }}>{status}</span>
      <span style={{ color: LR.good }}>In file · /{mode}</span>
    </div>
  );
}

/* ---------- Tab bar */
function ShTabs({ items, current = 0 }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 12, padding: "6px 4px" }}>
      <span style={{ color: LR.muted }}>←</span>
      {items.map((label, i) => (
        <span key={i} style={{
          padding: "3px 10px", borderRadius: 4,
          background: i === current ? "#0D2137" : "transparent",
          color: i === current ? LR.teal : LR.muted,
          fontWeight: i === current ? 700 : 400,
          border: i === current ? `1px solid ${LR.teal}` : "1px solid transparent",
        }}>
          {i === current ? "⊗" : "□"} {label}
        </span>
      ))}
      <span style={{ color: LR.good, fontWeight: 700, marginLeft: "auto" }}>✓ Done →</span>
    </div>
  );
}

/* ---------- Progress bar — pixel filled track */
function ShProgress({ value = 0.5, label, color = LR.teal }) {
  return (
    <div style={{ fontSize: 11.5, padding: "2px 0", color: LR.muted }}>
      {label && <div style={{ marginBottom: 4, color: LR.fg }}>{label}</div>}
      <div style={{ display: "flex", alignItems: "center", gap: 8, fontFamily: "ui-monospace, monospace" }}>
        <span style={{ color }}>{"█".repeat(Math.round(value * 24))}</span>
        <span style={{ color: LR.faint }}>{"░".repeat(24 - Math.round(value * 24))}</span>
        <span style={{ color: LR.fg, marginLeft: 4 }}>{Math.round(value * 100)}%</span>
      </div>
    </div>
  );
}

/* ---------- Picker — numbered list */
function ShPicker({ title, items, selected = 0 }) {
  return (
    <div style={{ margin: "6px 0" }}>
      {title && (
        <div style={{ display: "flex", gap: 8, alignItems: "baseline", fontSize: 12.5, marginBottom: 4 }}>
          <span style={{ color: LR.gold }}>◆</span>
          <span style={{ color: LR.fg, fontWeight: 600 }}>{title}</span>
        </div>
      )}
      {items.map((it, i) => (
        <div key={i} style={{
          display: "flex", gap: 6, alignItems: "baseline", fontSize: 12, padding: "1px 0",
          color: i === selected ? LR.fg : LR.muted,
        }}>
          <span style={{ color: i === selected ? LR.cyan : "transparent", fontWeight: 700 }}>›</span>
          <span style={{ color: LR.primary }}>{i + 1}.</span>
          <span style={{ fontWeight: i === selected ? 600 : 400 }}>{it}</span>
        </div>
      ))}
    </div>
  );
}

/* ---------- Box (success/info card) */
function ShBox({ title, accent = LR.good, icon = "✓", children, width }) {
  return (
    <div style={{
      border: `1px solid ${accent}`, borderRadius: 8,
      background: "rgba(52,168,83,0.06)",
      padding: "12px 14px", margin: "8px 0",
      width: width || "auto",
    }}>
      {title && (
        <div style={{ display: "flex", gap: 8, alignItems: "baseline", color: accent, fontSize: 12.5, fontWeight: 700, marginBottom: 6 }}>
          <span>{icon}</span><span>{title}</span>
        </div>
      )}
      <div style={{ color: LR.fg, fontSize: 12, lineHeight: 1.6 }}>{children}</div>
    </div>
  );
}

/* ---------- Telemetry foot — '· key: v · key: v' */
function ShMeta({ pairs }) {
  return (
    <div style={{ color: LR.muted, fontSize: 11, padding: "2px 0", fontFamily: "ui-monospace, monospace" }}>
      · {pairs.map(([k, v]) => `${k}: ${v}`).join("  ·  ")}
    </div>
  );
}

Object.assign(window, {
  LR,
  ShellWindow, ShPrompt, ShInput, ShEcho, ShWork, ShStatus, ShInsight,
  ShTip, ShResult, ShSection, ShRule, ShFooter, ShTabs, ShProgress,
  ShPicker, ShBox, ShMeta,
});
