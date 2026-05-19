/* =========================================================================
   LINKRIGHT block-letter banner.
   Renders "LINKRIGHT" as pixel blocks (the way the CLI does) with the
   signature horizontal teal→purple→pink gradient sweeping across all
   8 letters together. Built from a custom 7-row × 5-col pixel font that
   matches the CLI's chunky figlet vibe.
   ========================================================================= */

// 5-wide × 7-tall block font. 'X' = filled pixel.
// Only the letters in LINKRIGHT; outline-style strokes for fidelity.
const BANNER_FONT = {
  L: [
    "X....",
    "X....",
    "X....",
    "X....",
    "X....",
    "X....",
    "XXXXX",
  ],
  I: [
    "XXXXX",
    "..X..",
    "..X..",
    "..X..",
    "..X..",
    "..X..",
    "XXXXX",
  ],
  N: [
    "X...X",
    "XX..X",
    "XX..X",
    "X.X.X",
    "X..XX",
    "X..XX",
    "X...X",
  ],
  K: [
    "X...X",
    "X..X.",
    "X.X..",
    "XX...",
    "X.X..",
    "X..X.",
    "X...X",
  ],
  R: [
    "XXXX.",
    "X...X",
    "X...X",
    "XXXX.",
    "X.X..",
    "X..X.",
    "X...X",
  ],
  G: [
    ".XXXX",
    "X....",
    "X....",
    "X..XX",
    "X...X",
    "X...X",
    ".XXXX",
  ],
  H: [
    "X...X",
    "X...X",
    "X...X",
    "XXXXX",
    "X...X",
    "X...X",
    "X...X",
  ],
  T: [
    "XXXXX",
    "..X..",
    "..X..",
    "..X..",
    "..X..",
    "..X..",
    "..X..",
  ],
};

// Gradient stops along the horizontal axis (0..1).
// Teal → cyan → indigo → purple → lilac → pink → coral.
const BANNER_STOPS = [
  { t: 0.00, color: "#0FBEAF" },
  { t: 0.14, color: "#4DDCCE" },
  { t: 0.30, color: "#6B8CF5" },
  { t: 0.48, color: "#8B5CF6" },
  { t: 0.65, color: "#C5A6E6" },
  { t: 0.82, color: "#F05A79" },
  { t: 1.00, color: "#FF8D71" },
];

function hexToRgb(hex) {
  const h = hex.replace("#", "");
  return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
}
function rgbToHex([r, g, b]) {
  const toHex = (n) => Math.round(n).toString(16).padStart(2, "0");
  return "#" + toHex(r) + toHex(g) + toHex(b);
}
function sampleBannerGradient(t) {
  // clamp
  if (t <= 0) return BANNER_STOPS[0].color;
  if (t >= 1) return BANNER_STOPS[BANNER_STOPS.length - 1].color;
  for (let i = 0; i < BANNER_STOPS.length - 1; i++) {
    const a = BANNER_STOPS[i];
    const b = BANNER_STOPS[i + 1];
    if (t >= a.t && t <= b.t) {
      const k = (t - a.t) / (b.t - a.t);
      const ca = hexToRgb(a.color);
      const cb = hexToRgb(b.color);
      return rgbToHex([
        ca[0] + (cb[0] - ca[0]) * k,
        ca[1] + (cb[1] - ca[1]) * k,
        ca[2] + (cb[2] - ca[2]) * k,
      ]);
    }
  }
  return BANNER_STOPS[BANNER_STOPS.length - 1].color;
}

/* ---------------------------------------------------------------
   <LinkrightBanner word pixel gap kern /> — renders pixel-block
   LINKRIGHT (or any subset) with the gradient sweeping across.
   --------------------------------------------------------------- */
function LinkrightBanner({
  word = "LINKRIGHT",
  pixel = 8,        // edge length of one block in CSS px
  gap = 6,          // gap between letters (in pixel units)
  outline = false,  // if true, render only outline + faint inner stripe (matches CLI screenshot)
  className,
  style,
}) {
  const letters = word.split("").map((ch) => ({ ch, grid: BANNER_FONT[ch] })).filter((l) => l.grid);
  const letterCols = 5;
  const letterRows = 7;
  const totalCols = letters.length * letterCols + (letters.length - 1) * gap;
  const totalRows = letterRows;
  const w = totalCols * pixel;
  const h = totalRows * pixel;

  const rects = [];
  for (let i = 0; i < letters.length; i++) {
    const xOffset = i * (letterCols + gap);
    const grid = letters[i].grid;
    for (let y = 0; y < letterRows; y++) {
      const row = grid[y];
      for (let x = 0; x < letterCols; x++) {
        if (row[x] !== "X") continue;
        const absoluteX = xOffset + x;
        const t = absoluteX / (totalCols - 1);
        const fill = sampleBannerGradient(t);
        rects.push(
          <rect
            key={`${i}-${y}-${x}`}
            x={absoluteX * pixel}
            y={y * pixel}
            width={pixel}
            height={pixel}
            fill={fill}
          />
        );
        if (outline) {
          // Faint inner shadow to match the "drawn / outlined" CLI font
          rects.push(
            <rect
              key={`${i}-${y}-${x}-i`}
              x={absoluteX * pixel + Math.max(1, pixel / 6)}
              y={y * pixel + Math.max(1, pixel / 6)}
              width={pixel - Math.max(1, pixel / 3)}
              height={pixel - Math.max(1, pixel / 3)}
              fill="rgba(14,22,32,0.55)"
            />
          );
        }
      }
    }
  }

  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width={w}
      height={h}
      viewBox={`0 0 ${w} ${h}`}
      shapeRendering="crispEdges"
      className={className}
      style={style}
    >
      {rects}
    </svg>
  );
}

Object.assign(window, { LinkrightBanner, BANNER_FONT, sampleBannerGradient });
