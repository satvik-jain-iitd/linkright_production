/* =========================================================================
   ascii-pip.jsx — Pip as ASCII art.

   The argument: a pose is a 4-line string. To add a new state, a dev
   writes 4 lines of characters. No palette system, no SVG, no pixel grids.
   Maintainable forever; works in any terminal, any editor, any code review.

   Character set: ASCII + the universally-supported Unicode box-drawing
   subset (single-line + double-line + rounded + heavy). Avoids exotic glyphs.
   ========================================================================= */

const ASCII_POSES = {
  /* ----- Face states (head only) ----- */

  idle:        ["┌───┐",
                "│• •│",
                "└───┘"],

  blink:       ["┌───┐",
                "│- -│",
                "└───┘"],

  happy:       ["┌───┐",
                "│^ ^│",
                "└─⌣─┘"],

  surprised:   ["┌───┐",
                "│O O│",
                "└─o─┘"],

  flat:        ["┌───┐",
                "│- -│",
                "└─━─┘"],

  focus:       ["┌───┐",
                "│> <│",
                "└───┘"],

  /* ----- Action states (head + accessory) ----- */

  // Success — gold star floating above
  with_star:   ["  ★  ",
                "┌───┐",
                "│^ ^│",
                "└─⌣─┘"],

  // Reaching for the star — logo callback (arm-stroke connects head to star)
  reaching:    ["   ★ ",
                "  ╱  ",
                " ╱   ",
                "┌───┐",
                "│• •│",
                "└───┘"],

  // Reading JD — magnifier on a handle
  reading_jd:  ["  ⊙  ",
                "   ╲ ",
                "┌───┐",
                "│• •│",
                "└───┘"],

  // Building / tailoring resume — Pip looks DOWN at a page he's editing.
  // Eyes flip from • to v (looking down). Below the jaw: three lines of
  // resume copy with one bullet now checked (✓) — "tailoring in progress."
  // Reads instantly as "working on the document" without needing a hammer.
  building:    ["       ",
                "┌───┐  ",
                "│v v│  ",
                "└─┬─┘  ",
                " ═══   ",
                " ✓══   ",
                " ═══   "],

  // AI generating — soft glow / sparkle (purple in render)
  ai_thinking: ["  ✦  ",
                " ✦ ✦ ",
                "┌───┐",
                "│• •│",
                "└───┘"],

  // Long task — coffee mug beside, steam curling up
  coffee:      ["     ~",
                "     ~",
                "┌───┐ ┌─┐",
                "│• •│ │═│",
                "└───┘ └─┘"],

  // Sleeping — Zs floating up
  sleep:       ["     z",
                "    Z ",
                "   Z  ",
                "┌───┐ ",
                "│- -│ ",
                "└───┘ "],

  // Blocked / retry — sweat drop falling
  retry:       ["   ,  ",
                "   '  ",
                "┌───┐ ",
                "│- -│ ",
                "└─━─┘ "],

  // Interview prep — open book in front
  interview:   ["       ",
                "┌───┐  ",
                "│• •│  ",
                "└─┬─┘  ",
                " ┌╧┐   ",
                " │═│   ",
                " └─┘   "],

  // Negotiating — rupee symbol floating (legacy; kept for compat)
  negotiate:   ["       ",
                "   ₹   ",
                "┌───┐  ",
                "│• •│  ",
                "└───┘  "],

  // Negotiating (v2) — balance scales: two weighted decisions, a pivot.
  // Universal metaphor for "weighing tradeoffs" — no currency, no geography.
  negotiating: [" ◆───◆ ",
                "   │   ",
                "   ┴   ",
                " ┌───┐ ",
                " │• •│ ",
                " └───┘ "],

  // Applying — momentum: focused eyes, two applications flying out.
  // Replaces generic "building" for the Apply lifecycle stop.
  applying:    ["       ",
                "  ──→  ",
                "  ──→  ",
                " ┌───┐ ",
                " │> <│ ",
                " └───┘ "],

  // Money / value (generic) — coin stack going up, no currency symbol.
  // Use anywhere you'd previously reach for $ or ₹.
  money:       ["   ↑   ",
                " ┌─┐   ",
                " │◯│   ",
                " ├─┤   ",
                " │◯│   ",
                "┌┴─┴┐  ",
                "│^ ^│  ",
                "└───┘  "],

  // Running — career-running, motion lines behind
  run:         ["       ",
                "  ┌───┐",
                "≈ │> <│",
                "  └─┬─┘",
                "  ╱ ╲  "],

  // Boot greeting — small wave
  wave:        ["     v ",
                "┌───┐  ",
                "│^ ^│  ",
                "└─⌣─┘  "],

  // Typing — caret beside head
  typing:      ["┌───┐ ▌",
                "│• •│  ",
                "└───┘  "],

  // Listening (coach mode) — ear cup tilt
  listening:   ["┌───┐ )",
                "│o •│  ",
                "└───┘  "],

  // Thinking — small thought bubble with dots
  thinking:    ["    ° ",
                "   ° °",
                "┌───┐ ",
                "│- -│ ",
                "└───┘ "],

  // Working / typing fast — two motion lines after head
  working:     ["       ",
                "┌───┐ ≈",
                "│> <│ ≈",
                "└───┘  "],

  // Error / red flag (gentle, no panic)
  error:       ["   !  ",
                "┌───┐ ",
                "│× ×│ ",
                "└─━─┘ "],

  // Saluting — small flag/banner above
  salute:      ["  ▌▬▬",
                "┌───┐",
                "│^ ^│",
                "└───┘"],

  // Scout — scanning binoculars
  scout:       ["       ",
                "┌─┬─┐  ",
                "│⊙ ⊙│  ",
                "└───┘  "],

  // Pointing — arrow extends to the right
  pointing:    ["       ",
                "┌───┐──→",
                "│• •│  ",
                "└───┘  "],
};

/* ---------- Highlight palette — which characters in each pose
   should be tinted with what accent. We re-render the ASCII string
   character-by-character, applying these colors. ---------- */
const ASCII_TINTS = {
  // accent character → color
  "★": "#E5B80B",   // gold
  "✦": "#8B5CF6",   // purple — AI
  "⊙": "#DCE5EA",   // silver — magnifier
  "₹": "#E5B80B",   // gold — rupee (legacy)
  "◆": "#E5B80B",   // gold — balance weights / decision points
  "┴": "#DCE5EA",   // silver — balance pivot
  "◯": "#E5B80B",   // gold — coin
  "↑": "#34A853",   // green — value going up
  "v": "#0FBEAF",   // teal — wave
  ",": "#FF5733",   // coral — sweat
  "'": "#FF5733",   // coral — sweat
  "~": "#FFFFFF",   // white — steam
  "z": "#FDF6F0",   // cream — zzz
  "Z": "#FDF6F0",   // cream — ZZZ
  "≈": "#FF5733",   // coral — motion
  "═": "#FDF6F0",   // cream — book pages, mug rim, resume lines
  "✓": "#34A853",   // green — checkmark · bullet kept
  "╧": "#FDF6F0",   // cream — book base
  "╔": "#DCE5EA",   // silver — hammer head
  "╗": "#DCE5EA",
  "║": "#DCE5EA",
  "╨": "#DCE5EA",
  "▌": "#26D4C2",   // teal — caret / banner pole
  "▬": "#FF8D71",   // coral — flag
  ")": "#0FBEAF",   // teal — ear cup
  "!": "#FF8D71",   // coral — gentle warn
  "°": "#C5A6E6",   // purple — thought bubble
  "→": "#0FBEAF",   // teal — pointing
};

const PIP_TEAL = "#0FBEAF";

/* ---------- <AsciiPip pose size /> ---------- */
function AsciiPip({ pose = "idle", size = 36, weight = 700, accent, className, style, glow = true }) {
  const lines = ASCII_POSES[pose] || ASCII_POSES.idle;

  return (
    <pre
      className={className}
      style={{
        margin: 0,
        fontFamily: "ui-monospace, 'SF Mono', Menlo, Consolas, monospace",
        fontSize: size,
        lineHeight: 1.1,
        fontWeight: weight,
        color: accent || PIP_TEAL,
        letterSpacing: 0,
        textShadow: glow ? `0 0 ${size * 0.4}px ${(accent || PIP_TEAL) + "40"}` : "none",
        whiteSpace: "pre",
        ...style,
      }}
    >
      {lines.map((line, lineIdx) => (
        <div key={lineIdx} style={{ height: "1.1em" }}>
          {line.split("").map((ch, i) => {
            const tint = ASCII_TINTS[ch];
            if (tint) {
              return (
                <span
                  key={i}
                  style={{
                    color: tint,
                    textShadow: glow ? `0 0 ${size * 0.5}px ${tint}80` : "none",
                  }}
                >
                  {ch}
                </span>
              );
            }
            return ch;
          })}
        </div>
      ))}
    </pre>
  );
}

/* ---------- Animated AsciiPip — cycles between poses ---------- */
function AsciiPipAnimated({ poses, durations, size = 36, accent, style }) {
  const [idx, setIdx] = React.useState(0);
  React.useEffect(() => {
    const d = durations[idx] || 600;
    const t = setTimeout(() => setIdx((idx + 1) % poses.length), d);
    return () => clearTimeout(t);
  }, [idx, poses, durations]);
  return <AsciiPip pose={poses[idx]} size={size} accent={accent} style={style} />;
}

/* ---------- Idle preset ---------- */
function AsciiIdle({ size = 36, accent, style }) {
  return (
    <AsciiPipAnimated
      poses={["idle", "idle", "blink", "idle", "idle", "idle"]}
      durations={[2400, 1800, 140, 3200, 2000, 2400]}
      size={size}
      accent={accent}
      style={style}
    />
  );
}

Object.assign(window, { AsciiPip, AsciiPipAnimated, AsciiIdle, ASCII_POSES, ASCII_TINTS });
