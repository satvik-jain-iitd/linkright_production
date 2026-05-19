/* =========================================================================
   Pip v2 — the LinkRight mascot.

   Design changes from v1:
   1. Body color is now TEAL (brand primary), not coral. Teal has much
      higher luminance on dark navy terminal backgrounds.
   2. Accessories use only LIGHT colors that pop on dark bg:
      silver (tools), cream (paper, coffee), gold (star), purple (AI),
      coral (sparks / sweat / retry — coral becomes alert color, not body).
   3. Expressive states (happy, flat, surprised, confused) now include a
      MOUTH so emotion reads without relying on 1-pixel eye shifts.
   4. Composite sprites grew from 22×14 → 24×16 to give accessories room
      for clear, iconic silhouettes.
   5. Action states get visible sparks / motion lines.
   ========================================================================= */

const PIP_PALETTE = {
  ".": null,             // transparent

  // Body — teal primary + lighter highlight + darker shadow
  "T": "#0FBEAF",        // teal-500 (canonical body)
  "t": "#4DDCCE",        // teal-300 (top-left highlight pixel)
  "n": "#0C9A8E",        // teal-600 (faint shadow)

  // Eyes / face features — pure black for max contrast on teal
  "K": "#000000",

  // Light accents
  "W": "#FFFFFF",        // shine, steam, glass

  // Functional colors — each owns ONE meaning
  "G": "#E5B80B",        // gold — star, success
  "g": "#FCE98A",        // gold light
  "C": "#FF5733",        // coral — alert, sweat, sparks, retry
  "c": "#FF8D71",        // coral light
  "P": "#8B5CF6",        // purple — AI
  "p": "#C5A6E6",        // purple light (aura)
  "S": "#F05A79",        // pink — scout / human

  // Materials
  "L": "#FDF6F0",        // cream — paper, coffee mug body
  "l": "#F8E6D4",        // cream shadow
  "M": "#DCE5EA",        // silver light — hammer head, magnifier ring
  "m": "#94A3B0",        // silver dark — outline / handle
  "B": "#8B5A2B",        // brown — coffee inside
};

/* -----------------------------------------------------------------
   Core face states — 14×10. Flat teal body, black eyes,
   one lighter highlight pixel (top-left) for shine.
   Expressive states include a mouth row.
   ----------------------------------------------------------------- */
const PIP_SPRITES = {
  idle: [
    "..TTTTTTTTTT..",
    ".TtTTTTTTTTTT.",
    "TTTTTTTTTTTTTT",
    "TTTKKTTTTKKTTT",
    "TTTKKTTTTKKTTT",
    "TTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTT",
    ".TTTTTTTTTTTT.",
    "..TTTTTTTTTT..",
  ],

  // Mid-blink — eyes 1 row tall
  blink_mid: [
    "..TTTTTTTTTT..",
    ".TtTTTTTTTTTT.",
    "TTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTT",
    "TTTKKTTTTKKTTT",
    "TTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTT",
    ".TTTTTTTTTTTT.",
    "..TTTTTTTTTT..",
  ],

  // Fully closed
  blink_closed: [
    "..TTTTTTTTTT..",
    ".TtTTTTTTTTTT.",
    "TTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTT",
    "TTKKKTTTTKKKTT",
    "TTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTT",
    ".TTTTTTTTTTTT.",
    "..TTTTTTTTTT..",
  ],

  // Happy / squint + smile MOUTH — clear win signal
  happy: [
    "..TTTTTTTTTT..",
    ".TtTTTTTTTTTT.",
    "TTTTTTTTTTTTTT",
    "TTKTKTTTTKTKTT",
    "TTTKTTTTTTKTTT",
    "TTTTTTTTTTTTTT",
    "TTTTTKTTTTKTTT",
    "TTTTTTKKKKTTTT",
    ".TTTTTTTTTTTT.",
    "..TTTTTTTTTT..",
  ],

  // Looking up — thinking
  look_up: [
    "..TTTTTTTTTT..",
    ".TtTTTTTTTTTT.",
    "TTTKKTTTTKKTTT",
    "TTTKKTTTTKKTTT",
    "TTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTT",
    ".TTTTTTTTTTTT.",
    "..TTTTTTTTTT..",
  ],

  // Looking left
  look_left: [
    "..TTTTTTTTTT..",
    ".TtTTTTTTTTTT.",
    "TTTTTTTTTTTTTT",
    "TTKKTTTTTKKTTT",
    "TTKKTTTTTKKTTT",
    "TTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTT",
    ".TTTTTTTTTTTT.",
    "..TTTTTTTTTT..",
  ],

  // Looking right
  look_right: [
    "..TTTTTTTTTT..",
    ".TtTTTTTTTTTT.",
    "TTTTTTTTTTTTTT",
    "TTTKKTTTTTKKTT",
    "TTTKKTTTTTKKTT",
    "TTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTT",
    ".TTTTTTTTTTTT.",
    "..TTTTTTTTTT..",
  ],

  // Surprised — wide eyes with white shine + open mouth
  surprised: [
    "..TTTTTTTTTT..",
    ".TtTTTTTTTTTT.",
    "TTTKKKTTKKKTTT",
    "TTTKWKTTKWKTTT",
    "TTTKKKTTKKKTTT",
    "TTTTTTTTTTTTTT",
    "TTTTTTKKTTTTTT",
    "TTTTTTKKTTTTTT",
    ".TTTTTTTTTTTT.",
    "..TTTTTTTTTT..",
  ],

  // Flat / disappointed — half-closed eyes + straight mouth
  flat: [
    "..TTTTTTTTTT..",
    ".TtTTTTTTTTTT.",
    "TTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTT",
    "TTKKKTTTTKKKTT",
    "TTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTT",
    "TTTTKKKKKKTTTT",
    ".TTTTTTTTTTTT.",
    "..TTTTTTTTTT..",
  ],

  // Sleeping — eyelash lines + ZZZ is in composite below
  sleep: [
    "..TTTTTTTTTT..",
    ".TtTTTTTTTTTT.",
    "TTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTT",
    "TTKKKTTTTKKKTT",
    "TTKTKTTTTKTKTT",
    "TTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTT",
    ".TTTTTTTTTTTT.",
    "..TTTTTTTTTT..",
  ],

  // Focused / determined — narrowed eyes, slight frown
  focus: [
    "..TTTTTTTTTT..",
    ".TtTTTTTTTTTT.",
    "TTTTTTTTTTTTTT",
    "TTTKKTTTTKKTTT",
    "TTTTKTTTTKTTTT",
    "TTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTT",
    "TTTTTKKKKTTTTT",
    ".TTTTTTTTTTTT.",
    "..TTTTTTTTTT..",
  ],

  // Confused — asymmetric eye + lopsided mouth
  confused: [
    "..TTTTTTTTTT..",
    ".TtTTTTTTTTTT.",
    "TTTTTTTTTTTTTT",
    "TTTKKTTTTKTTTT",
    "TTTKKTTTTKKTTT",
    "TTTTTTTTTTTTTT",
    "TTTTTKKKTTTTTT",
    "TTTTTTTKKKTTTT",
    ".TTTTTTTTTTTT.",
    "..TTTTTTTTTT..",
  ],
};

/* -----------------------------------------------------------------
   Composite states — 24 wide × 16 tall.
   Pip anchored at cols 5–18 (14 wide), rows 5–14 (10 tall),
   leaving ~5 cols of margin and 5 rows of headroom for the prop.

   Every prop renders in a LIGHT color (silver / cream / gold /
   purple / coral) so it stands out on dark navy terminal bg.
   ----------------------------------------------------------------- */
const PIP_COMPOSITES = {
  /* ===== Career-workflow accessory states ===== */

  // Pip + magnifier — JD analysis.
  // Magnifier on the upper-left: silver ring + white glass + handle.
  // Pip's eyes look LEFT at it.
  with_magnifier: [
    "........................",
    ".mMMMMMm................",
    ".MWWWWWM................",
    ".MWWWWWM................",
    ".MWWWWWM................",
    ".mMMMMMm................",
    "......mm................",
    ".......mm.TTTTTTTTTT....",
    "........m.TtTTTTTTTT....",
    "........TTTTTTTTTTTTTT..",
    "........TTKKTTTTTKKTTT..",
    "........TTKKTTTTTKKTTT..",
    "........TTTTTTTTTTTTTT..",
    "........TTTTTTTTTTTTTT..",
    ".........TTTTTTTTTTTT...",
    "..........TTTTTTTTTT....",
  ],

  // Pip + hammer — building. Big silver hammer head above,
  // handle coming down toward Pip, coral sparks flying off.
  with_hammer: [
    "........................",
    ".......MMMMMM...........",
    "......MmMMMMMm..........",
    ".......MmMMMm...........",
    "..........mm............",
    "..........mm............",
    "..........mm...C........",
    "..........mm..CcC.......",
    ".......TTTmmTTTcC.......",
    "......TTTTTTTTTTTTT.....",
    "......TtTTTTTTTTTTT.....",
    "......TTKKTTTTKKTTTT....",
    "......TTKKTTTTKKTTTT....",
    "......TTTTTTTTTTTTTT....",
    ".......TTTTTTTTTTTT.....",
    "........TTTTTTTTTT......",
  ],

  // Pip + coffee mug — long task. Cream mug, brown coffee,
  // visible steam curling up.
  with_coffee: [
    "...............W........",
    "..............W.W.......",
    "...............W........",
    "..............WW........",
    "..............LLLLM.....",
    ".............LBBBBLM....",
    ".............LBBBBLM....",
    ".............LLLLLLM....",
    "......TTTTTTTTLLLL......",
    "......TtTTTTTTTTTT......",
    "......TTKKTTTTKKTTT.....",
    "......TTKKTTTTKKTTT.....",
    "......TTTTTTTTTTTTT.....",
    "......TTTTTTTTTTTT......",
    ".......TTTTTTTTTT.......",
    "........TTTTTTTT........",
  ],

  // Pip + page — carrying / output. Clear document silhouette
  // with header line + body lines.
  with_page: [
    "........................",
    "........LLLLLLLLLL......",
    "........LLLLLLLLLL......",
    "........LmmmmmmmmL......",
    "........LLLLLLLLLL......",
    "........LmmmmmmLLL......",
    "........LmmmmmmmmL......",
    "........LmmmmLLLLL......",
    "......TTLmmmmmmLLLT.....",
    ".....TTtLLLLLLLLLLTT....",
    ".....TTKKLLLLLLLLKKT....",
    ".....TTKKTTTTTTKKTTT....",
    ".....TTTTTTTTTTTTTTT....",
    ".....TTTTTTTTTTTTTT.....",
    "......TTTTTTTTTTTT......",
    ".......TTTTTTTTTT.......",
  ],

  // Pip + gold star — success
  with_star: [
    "..........G.............",
    "..........G.............",
    "........GGgGG...........",
    ".........gGg............",
    "........GG.GG...........",
    "........................",
    "......TTTTTTTTTT........",
    ".....TTtTTTTTTTTT.......",
    ".....TTTTTTTTTTTTT......",
    ".....TTKTKTTTTKTKT......",
    ".....TTTKTTTTTTKTT......",
    ".....TTTTTTTTTTTTT......",
    ".....TTTTTKKKKTTTT......",
    "......TTTTTTTTTTT.......",
    ".......TTTTTTTTT........",
    "........TTTTTTT.........",
  ],

  // Pip jumping — motion lines beneath, star above, mid-air pose
  jump_up: [
    "..........G.............",
    "........GGgGG...........",
    "..........G.............",
    "........................",
    "......TTTTTTTTTT........",
    ".....TTtTTTTTTTTT.......",
    ".....TTTTTTTTTTTTT......",
    ".....TTKTKTTTTKTKT......",
    ".....TTTKTTTTTTKTT......",
    ".....TTTTTTTTTTTTT......",
    ".....TTTTTKKKKTTTT......",
    "......TTTTTTTTTTT.......",
    ".......TTTTTTTTT........",
    "........................",
    "...mmm..........mmm.....",
    "....mmm........mmm......",
  ],

  // Pip reaching up — direct logo callback (climbing toward star)
  reaching: [
    "..........G.............",
    "..........G.............",
    "........GGgGG...........",
    ".........gGg............",
    "........GG.GG...........",
    ".........TTT............",
    "........TTTTT...........",
    "......TTTTTTTTTT........",
    ".....TTtTTTTTTTTT.......",
    ".....TTTTTTTTTTTTT......",
    ".....TTKKTTTTTKKTT......",
    ".....TTKKTTTTTKKTT......",
    ".....TTTTTTTTTTTTT......",
    ".....TTTTTTTTTTTT.......",
    "......TTTTTTTTTT........",
    ".......TTTTTTTT.........",
  ],

  // Sweat / retry — clear coral drop, flat eyes + slight frown
  sweat: [
    "........................",
    "............C...........",
    "...........CcC..........",
    "...........CcC..........",
    "............C...........",
    "........................",
    "......TTTTTTTTTT........",
    ".....TTtTTTTTTTTT.......",
    ".....TTTTTTTTTTTTT......",
    ".....TTKKKTTTTKKKT......",
    ".....TTTTTTTTTTTTT......",
    ".....TTTTTTTTTTTTT......",
    ".....TTTTKKKKKKTTT......",
    "......TTTTTTTTTTT.......",
    ".......TTTTTTTTT........",
    "........TTTTTTT.........",
  ],

  // Sleeping — eyelash eyes + clear ZZZ trail in cream/white
  sleep_z: [
    "...........WWW..........",
    "..........W..W..........",
    ".........W..W...........",
    "........WWWW............",
    "...........WW...........",
    "..........WWWW..........",
    "......TTTTTTTTTT........",
    ".....TTtTTTTTTTTT.......",
    ".....TTTTTTTTTTTTT......",
    ".....TTKKKTTTTKKKT......",
    ".....TTKTKTTTTKTKT......",
    ".....TTTTTTTTTTTTT......",
    ".....TTTTTTTTTTTTT......",
    "......TTTTTTTTTTT.......",
    ".......TTTTTTTTT........",
    "........TTTTTTT.........",
  ],

  // AI mode — thick purple aura ring around Pip
  ai_aura: [
    "...pppppppppppppp.......",
    "..ppPPPPPPPPPPPPpp......",
    ".pPPPPPPPPPPPPPPPPp.....",
    ".pPPTTTTTTTTTTTTPPp.....",
    ".pPPTtTTTTTTTTTTPPp.....",
    ".pPPTTTTTTTTTTTTPPp.....",
    ".pPPTTKKTTTTKKTTPPp.....",
    ".pPPTTKKTTTTKKTTPPp.....",
    ".pPPTTTTTTTTTTTTPPp.....",
    ".pPPTTTTTTTTTTTTPPp.....",
    ".pPPTTTTTTTTTTTTPPp.....",
    ".pPPTTTTTTTTTTTTPPp.....",
    ".pPPPTTTTTTTTTTPPPp.....",
    ".pPPPPPPPPPPPPPPPPp.....",
    "..ppPPPPPPPPPPPPpp......",
    "...pppppppppppppp.......",
  ],

  // Negotiating — clear gold ₹ symbol to the right of Pip
  with_rupee: [
    "........................",
    ".........GGGGGG.........",
    "..........G............G",
    ".........GGGGGG.........",
    "..........G.G...........",
    ".........G.G............",
    "......TTTTTTTTTT........",
    ".....TTtTTTTTTTTT.......",
    ".....TTTTTTTTTTTTT......",
    ".....TTKTKTTTTKTKT......",
    ".....TTTKTTTTTTKTT......",
    ".....TTTTTTTTTTTTT......",
    ".....TTTTTKKKKTTTT......",
    "......TTTTTTTTTTT.......",
    ".......TTTTTTTTT........",
    "........TTTTTTT.........",
  ],

  // Scout — clear pink crosshair / telescope above Pip
  scout: [
    "............S...........",
    "...........SSS..........",
    "..........SSWSS.........",
    ".........SSWWWSS........",
    "...S....SSSWWWSSS.......",
    "..SSS....SSWWWSS........",
    "...S......SSWSS.........",
    "...........SSS.S........",
    "............S..SSS......",
    "......TTTTTTTTTTS.......",
    ".....TTtTTTTTTTTT.......",
    ".....TTTTTTTTTTTTT......",
    ".....TTKKTTTTTKKTT......",
    ".....TTKKTTTTTKKTT......",
    ".....TTTTTTTTTTTTT......",
    "......TTTTTTTTTTT.......",
  ],

  // Pip + open book — interview prep / story bank.
  // Two pages with spine in the middle, text lines on each page.
  with_book: [
    "........................",
    "........................",
    "........LLLLLLLLLL......",
    ".......LLmLLLLmLLL......",
    ".......LmLmLLmLmLL......",
    ".......LLmLLLLmLLL......",
    ".......LmLmLLmLmLL......",
    ".......LLLLLLLLLLL......",
    "......TTLLLLLLLLLTT.....",
    ".....TTtLLLLLLLLLLTT....",
    ".....TTKKLLLLLLLLKKT....",
    ".....TTKKTTTTTTTKKTTT...",
    ".....TTTTTTTTTTTTTTTT...",
    ".....TTTTTTTTTTTTTTT....",
    "......TTTTTTTTTTTT......",
    ".......TTTTTTTTTT.......",
  ],

  // Boot / wave-hello — small white speech glint above
  boot_wave: [
    "................W.......",
    "...............WWW......",
    "................W.......",
    "........................",
    "......TTTTTTTTTT........",
    ".....TTtTTTTTTTTT.......",
    ".....TTTTTTTTTTTTT......",
    ".....TTKTKTTTTKTKT......",
    ".....TTTKTTTTTTKTT......",
    ".....TTTTTTTTTTTTT......",
    ".....TTTTTKKKKTTTT......",
    "......TTTTTTTTTTT.......",
    ".......TTTTTTTTT........",
    "........TTTTTTT.........",
    "........................",
    "........................",
  ],
};

/* ---------------------------------------------------------------
   <PipSprite name pixel size palette /> — render any sprite by name.
   --------------------------------------------------------------- */
function PipSprite({
  name = "idle",
  pixel,
  size,
  palette,
  className,
  style,
  shapeRendering = "crispEdges",
  ...rest
}) {
  const grid = PIP_SPRITES[name] || PIP_COMPOSITES[name];
  if (!grid) {
    return <span style={{ color: "red" }}>?{name}?</span>;
  }
  const cols = grid[0].length;
  const rows = grid.length;
  const px = size != null ? Math.max(1, Math.floor(size / cols)) : (pixel || 6);
  const w = cols * px;
  const h = rows * px;
  const pal = palette ? { ...PIP_PALETTE, ...palette } : PIP_PALETTE;

  const cells = [];
  for (let y = 0; y < rows; y++) {
    const row = grid[y];
    for (let x = 0; x < cols; x++) {
      const ch = row[x];
      const fill = pal[ch];
      if (!fill) continue;
      cells.push(
        <rect
          key={y * cols + x}
          x={x * px}
          y={y * px}
          width={px}
          height={px}
          fill={fill}
        />
      );
    }
  }

  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width={w}
      height={h}
      viewBox={`0 0 ${w} ${h}`}
      shapeRendering={shapeRendering}
      className={className}
      style={style}
      {...rest}
    >
      {cells}
    </svg>
  );
}

/* ---------------------------------------------------------------
   <PipAnimated> — cycle frames on a timeline.
   --------------------------------------------------------------- */
function PipAnimated({ states, durations, pixel = 6, size, palette, className, style }) {
  const [idx, setIdx] = React.useState(0);
  React.useEffect(() => {
    const d = durations[idx] || 600;
    const t = setTimeout(() => setIdx((idx + 1) % states.length), d);
    return () => clearTimeout(t);
  }, [idx, states, durations]);
  return (
    <PipSprite
      name={states[idx]}
      pixel={pixel}
      size={size}
      palette={palette}
      className={className}
      style={style}
    />
  );
}

/* ---------------------------------------------------------------
   <PipIdle> — preset idle blink loop.
   --------------------------------------------------------------- */
function PipIdle({ pixel = 7, size, palette, className, style }) {
  return (
    <PipAnimated
      states={["idle", "idle", "idle", "idle", "blink_mid", "blink_closed", "blink_mid"]}
      durations={[2400, 1800, 3200, 2000, 80, 140, 80]}
      pixel={pixel}
      size={size}
      palette={palette}
      className={className}
      style={style}
    />
  );
}

Object.assign(window, { PipSprite, PipAnimated, PipIdle, PIP_SPRITES, PIP_COMPOSITES, PIP_PALETTE });
