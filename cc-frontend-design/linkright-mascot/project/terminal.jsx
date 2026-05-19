/* =========================================================================
   <Terminal> — a stylized CLI window that hosts Pip and the LINKRIGHT
   banner. Mac-style chrome, deep navy paper, monospace body. Children
   are rendered inside the terminal canvas.
   ========================================================================= */

function TerminalChrome({ title = "linkright", host = "satvikjain@MacBook-Air", children, style }) {
  return (
    <div
      style={{
        background: "#0E1620",
        borderRadius: 12,
        overflow: "hidden",
        boxShadow: "0 12px 32px rgba(15, 23, 42, 0.4)",
        border: "1px solid #253140",
        fontFamily: "ui-monospace, 'SF Mono', Menlo, Consolas, monospace",
        color: "#EEF5F2",
        ...style,
      }}
    >
      {/* Title bar */}
      <div
        style={{
          height: 32,
          background: "#151F2B",
          borderBottom: "1px solid #253140",
          display: "flex",
          alignItems: "center",
          padding: "0 14px",
          gap: 6,
        }}
      >
        <span style={{ width: 12, height: 12, borderRadius: "50%", background: "#FF5F57" }} />
        <span style={{ width: 12, height: 12, borderRadius: "50%", background: "#FEBC2E" }} />
        <span style={{ width: 12, height: 12, borderRadius: "50%", background: "#28C840" }} />
        <span
          style={{
            marginLeft: 12,
            fontSize: 12,
            color: "#8FA3B1",
            letterSpacing: 0.2,
            fontWeight: 500,
          }}
        >
          {host} — {title} — 120×36
        </span>
      </div>
      <div style={{ padding: "16px 18px", lineHeight: 1.5 }}>{children}</div>
    </div>
  );
}

/* ---------- Prompt + cursor primitives ---------- */
function Prompt({ host = "satvikjain@MacBook-Air", cwd = "linkright_production", children }) {
  return (
    <div style={{ display: "flex", gap: 6, alignItems: "baseline", fontSize: 13 }}>
      <span style={{ color: "#3B475A" }}>● </span>
      <span style={{ color: "#8FA3B1" }}>(base)</span>
      <span style={{ color: "#EEF5F2" }}>{host}</span>
      <span style={{ color: "#8FA3B1" }}>{cwd}</span>
      <span style={{ color: "#E5B80B" }}>%</span>
      <span style={{ color: "#EEF5F2" }}>{children}</span>
    </div>
  );
}

function Cursor() {
  return (
    <span
      style={{
        display: "inline-block",
        width: 8,
        height: 14,
        background: "#EEF5F2",
        verticalAlign: "middle",
        animation: "pipBlink 1s steps(1) infinite",
        marginLeft: 2,
      }}
    />
  );
}

/* ---------- A line of CLI output, optionally with a glyph bullet ---------- */
function Line({ icon, color = "#EEF5F2", weight = 400, children, style }) {
  return (
    <div style={{ display: "flex", gap: 8, alignItems: "baseline", fontSize: 13, color, fontWeight: weight, ...style }}>
      {icon && <span style={{ color: "#E5B80B", fontSize: 11 }}>{icon}</span>}
      <span>{children}</span>
    </div>
  );
}

function Dim({ children, color = "#5A6B7C" }) {
  return <span style={{ color }}>{children}</span>;
}
function Accent({ children, color = "#0FBEAF" }) {
  return <span style={{ color, fontWeight: 600 }}>{children}</span>;
}
function Gold({ children }) {
  return <span style={{ color: "#E5B80B", fontWeight: 600 }}>{children}</span>;
}
function Coral({ children }) {
  return <span style={{ color: "#FF8D71", fontWeight: 600 }}>{children}</span>;
}
function Purple({ children }) {
  return <span style={{ color: "#C5A6E6", fontWeight: 600 }}>{children}</span>;
}

/* ---------- A "thinking" dot animation, three pulsing dots ---------- */
function Dots({ color = "#8FA3B1" }) {
  return (
    <span style={{ color, display: "inline-flex", gap: 2 }}>
      <span style={{ animation: "pipDot 1.4s infinite", animationDelay: "0s" }}>.</span>
      <span style={{ animation: "pipDot 1.4s infinite", animationDelay: "0.2s" }}>.</span>
      <span style={{ animation: "pipDot 1.4s infinite", animationDelay: "0.4s" }}>.</span>
    </span>
  );
}

/* ---------- Spinner — single teal ring matching design system loader ---------- */
function Spinner() {
  return (
    <span
      style={{
        display: "inline-block",
        width: 12,
        height: 12,
        borderRadius: "50%",
        border: "2px solid rgba(15,190,175,0.25)",
        borderTopColor: "#0FBEAF",
        animation: "pipSpin 0.9s linear infinite",
        verticalAlign: "middle",
        marginRight: 6,
      }}
    />
  );
}

/* ---------- Pip slot — fixes Pip's position beside the banner ---------- */
function PipSlot({ children, align = "right", offsetY = 0 }) {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: align === "right" ? "flex-end" : "flex-start",
        alignItems: "flex-end",
        transform: `translateY(${offsetY}px)`,
      }}
    >
      {children}
    </div>
  );
}

Object.assign(window, {
  TerminalChrome, Prompt, Cursor, Line, Dim, Accent, Gold, Coral, Purple,
  Dots, Spinner, PipSlot,
});
