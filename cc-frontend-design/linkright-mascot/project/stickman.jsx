/* =========================================================================
   stickman.jsx — a line-art Pip.

   New direction: instead of a pixel blob, Pip is a hand-drawn stickman.
   Why: the LinkRight logo is itself a stickman climbing an arrow toward
   a star. Making the mascot a stickman makes it a direct visual extension
   of the logo, not a separate character.

   Stroke: teal #0FBEAF, single 3.5px weight, rounded caps + joins
   (matches the design system's illustration rule).

   Renders as inline SVG so it scales infinitely — same source asset
   works as a 32×32 favicon and a 600×800 hero illustration.
   ========================================================================= */

const STICK = {
  stroke: "#0FBEAF",
  strokeWidth: 3.5,
  accentGold: "#E5B80B",
  accentCoral: "#FF5733",
  accentPurple: "#8B5CF6",
  accentCream: "#FDF6F0",
  accentSilver: "#DCE5EA",
  accentPink: "#F05A79",
  black: "#1A202C",
};

/* The base body — head + neck + torso + 2 arms + 2 legs.
   Pose props are the joint coordinates. We pass the limbs in so
   each pose can fully rewrite arms/legs while keeping the head
   consistent. */
function StickBody({ pose = {}, accent = STICK.stroke, mouth, eyes = "open" }) {
  const head = pose.head || { cx: 40, cy: 24, r: 12 };
  const neckStart = pose.neckStart || { x: head.cx, y: head.cy + head.r };
  const shoulders = pose.shoulders || { x: head.cx, y: 42 };
  const hips = pose.hips || { x: head.cx, y: 68 };

  // Arms — pose can override with full path data
  const lArm = pose.leftArm || `M${shoulders.x} ${shoulders.y} L26 ${shoulders.y + 14}`;
  const rArm = pose.rightArm || `M${shoulders.x} ${shoulders.y} L54 ${shoulders.y + 14}`;

  // Legs
  const lLeg = pose.leftLeg || `M${hips.x} ${hips.y} L30 96`;
  const rLeg = pose.rightLeg || `M${hips.x} ${hips.y} L50 96`;

  // Eyes
  const eyeY = head.cy - 2;
  const eL = { x: head.cx - 4.5, y: eyeY };
  const eR = { x: head.cx + 4.5, y: eyeY };

  return (
    <g
      stroke={accent}
      strokeWidth={STICK.strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      fill="none"
    >
      {/* head */}
      <circle cx={head.cx} cy={head.cy} r={head.r} />

      {/* eyes */}
      {eyes === "open" && (
        <>
          <circle cx={eL.x} cy={eL.y} r={1.6} fill={accent} stroke="none" />
          <circle cx={eR.x} cy={eR.y} r={1.6} fill={accent} stroke="none" />
        </>
      )}
      {eyes === "happy" && (
        <>
          <path d={`M${eL.x - 2} ${eL.y + 1} Q${eL.x} ${eL.y - 2} ${eL.x + 2} ${eL.y + 1}`} />
          <path d={`M${eR.x - 2} ${eR.y + 1} Q${eR.x} ${eR.y - 2} ${eR.x + 2} ${eR.y + 1}`} />
        </>
      )}
      {eyes === "closed" && (
        <>
          <path d={`M${eL.x - 2} ${eL.y} L${eL.x + 2} ${eL.y}`} />
          <path d={`M${eR.x - 2} ${eR.y} L${eR.x + 2} ${eR.y}`} />
        </>
      )}
      {eyes === "focus" && (
        <>
          <path d={`M${eL.x - 2.5} ${eL.y - 1} L${eL.x + 2.5} ${eL.y + 1}`} />
          <path d={`M${eR.x - 2.5} ${eR.y + 1} L${eR.x + 2.5} ${eR.y - 1}`} />
        </>
      )}

      {/* mouth */}
      {mouth === "smile" && (
        <path d={`M${head.cx - 4} ${head.cy + 3} Q${head.cx} ${head.cy + 7} ${head.cx + 4} ${head.cy + 3}`} />
      )}
      {mouth === "flat" && (
        <path d={`M${head.cx - 3} ${head.cy + 5} L${head.cx + 3} ${head.cy + 5}`} />
      )}
      {mouth === "open" && (
        <circle cx={head.cx} cy={head.cy + 5} r={1.5} fill={accent} stroke="none" />
      )}
      {mouth === "frown" && (
        <path d={`M${head.cx - 4} ${head.cy + 7} Q${head.cx} ${head.cy + 3} ${head.cx + 4} ${head.cy + 7}`} />
      )}

      {/* neck */}
      <line x1={neckStart.x} y1={neckStart.y} x2={shoulders.x} y2={shoulders.y} />

      {/* torso */}
      <line x1={shoulders.x} y1={shoulders.y} x2={hips.x} y2={hips.y} />

      {/* arms */}
      <path d={lArm} />
      <path d={rArm} />

      {/* legs */}
      <path d={lLeg} />
      <path d={rLeg} />
    </g>
  );
}

/* ---------- 12 named poses ---------- */
const POSES = {
  // Standing relaxed, smile + open eyes
  idle: {
    eyes: "open", mouth: "smile",
    pose: {},
  },

  // Hand raised waving — boot greeting
  wave: {
    eyes: "happy", mouth: "smile",
    pose: {
      leftArm:  "M40 42 L24 50",
      rightArm: "M40 42 Q56 30 62 14",
    },
    extras: (
      <g stroke={STICK.stroke} strokeWidth={2.5} strokeLinecap="round" fill="none">
        <path d="M66 10 L70 6" />
        <path d="M64 16 L70 16" />
        <path d="M66 22 L70 24" />
      </g>
    ),
  },

  // Reading a JD on paper
  reading_jd: {
    eyes: "focus", mouth: "flat",
    pose: {
      head: { cx: 40, cy: 26, r: 12 },
      leftArm:  "M40 44 Q30 50 28 58",
      rightArm: "M40 44 Q50 50 52 58",
    },
    extras: (
      <g>
        {/* paper held in front */}
        <rect x="24" y="54" width="32" height="22" rx="2" fill={STICK.accentCream} stroke={STICK.stroke} strokeWidth={2} />
        <line x1="28" y1="60" x2="52" y2="60" stroke="#94A3B0" strokeWidth={1.5} />
        <line x1="28" y1="65" x2="48" y2="65" stroke="#94A3B0" strokeWidth={1.5} />
        <line x1="28" y1="70" x2="52" y2="70" stroke="#94A3B0" strokeWidth={1.5} />
      </g>
    ),
  },

  // At a desk, building resume — leaning forward, typing
  building: {
    eyes: "focus", mouth: "flat",
    pose: {
      head: { cx: 36, cy: 28, r: 12 },
      neckStart: { x: 36, y: 40 },
      shoulders: { x: 38, y: 46 },
      hips: { x: 40, y: 72 },
      leftArm:  "M38 48 L52 58",
      rightArm: "M38 48 L58 60",
      leftLeg:  "M40 72 L30 96",
      rightLeg: "M40 72 L52 96",
    },
    extras: (
      <g>
        {/* desk */}
        <line x1="20" y1="64" x2="68" y2="64" stroke={STICK.stroke} strokeWidth={3} strokeLinecap="round" />
        {/* laptop */}
        <rect x="48" y="56" width="14" height="8" fill={STICK.accentSilver} stroke={STICK.stroke} strokeWidth={2} />
        {/* coral spark */}
        <path d="M64 52 L66 50 M64 54 L67 54 M65 56 L67 58" stroke={STICK.accentCoral} strokeWidth={1.8} strokeLinecap="round" />
      </g>
    ),
  },

  // AI thinking — head tilted up, thought bubble with sparkles
  ai_thinking: {
    eyes: "open", mouth: "flat",
    pose: {
      head: { cx: 38, cy: 26, r: 12 },
      neckStart: { x: 39, y: 38 },
      shoulders: { x: 40, y: 44 },
    },
    extras: (
      <g>
        {/* thought bubble */}
        <circle cx="62" cy="20" r="11" fill="rgba(139,92,246,0.12)" stroke={STICK.accentPurple} strokeWidth={2} />
        <circle cx="50" cy="34" r="2.5" fill="rgba(139,92,246,0.12)" stroke={STICK.accentPurple} strokeWidth={1.5} />
        <circle cx="46" cy="40" r="1.5" fill="rgba(139,92,246,0.12)" stroke={STICK.accentPurple} strokeWidth={1.5} />
        {/* sparkle */}
        <path d="M62 16 L62 24 M58 20 L66 20" stroke={STICK.accentPurple} strokeWidth={2} strokeLinecap="round" />
        <circle cx="62" cy="20" r="1.5" fill={STICK.accentPurple} stroke="none" />
      </g>
    ),
  },

  // Success — arms up, jumping, star above
  success: {
    eyes: "happy", mouth: "smile",
    pose: {
      head: { cx: 40, cy: 30, r: 12 },
      neckStart: { x: 40, y: 42 },
      shoulders: { x: 40, y: 48 },
      hips: { x: 40, y: 70 },
      leftArm:  "M40 50 Q28 36 22 22",
      rightArm: "M40 50 Q52 36 58 22",
      leftLeg:  "M40 70 Q34 80 26 92",
      rightLeg: "M40 70 Q46 80 54 92",
    },
    extras: (
      <g>
        {/* star above */}
        <path d="M40 12 L42 8 L46 7 L43 4 L44 0 L40 2 L36 0 L37 4 L34 7 L38 8 Z"
              fill={STICK.accentGold} stroke={STICK.accentGold} strokeWidth={1.5} strokeLinejoin="round" />
        {/* ground motion lines */}
        <path d="M16 92 L22 92 M58 92 L64 92" stroke={STICK.stroke} strokeWidth={2} strokeLinecap="round" opacity={0.5} />
      </g>
    ),
  },

  // Retry — hand on forehead, slumped
  retry: {
    eyes: "closed", mouth: "frown",
    pose: {
      head: { cx: 40, cy: 26, r: 12 },
      shoulders: { x: 40, y: 44 },
      leftArm:  "M40 46 L26 60",
      rightArm: "M40 46 Q44 30 40 18",
    },
    extras: (
      <g>
        {/* coral sweat drop */}
        <path d="M58 14 Q60 18 58 22 Q56 18 58 14 Z" fill={STICK.accentCoral} stroke={STICK.accentCoral} strokeWidth={1} />
      </g>
    ),
  },

  // Sitting with coffee — long task
  coffee: {
    eyes: "open", mouth: "smile",
    pose: {
      head: { cx: 40, cy: 26, r: 12 },
      shoulders: { x: 40, y: 44 },
      hips: { x: 40, y: 64 },
      leftArm:  "M40 46 Q34 52 32 60",
      rightArm: "M40 46 Q52 50 54 56",
      leftLeg:  "M40 64 Q44 70 60 72",
      rightLeg: "M40 64 Q44 70 62 76",
    },
    extras: (
      <g>
        {/* coffee mug */}
        <rect x="46" y="48" width="10" height="10" rx="1" fill={STICK.accentCream} stroke={STICK.stroke} strokeWidth={2} />
        <path d="M56 51 Q60 53 56 56" stroke={STICK.stroke} strokeWidth={2} fill="none" strokeLinecap="round" />
        {/* steam */}
        <path d="M49 44 Q51 41 49 38 M53 44 Q55 41 53 38" stroke="#FFFFFF" strokeWidth={1.5} strokeLinecap="round" fill="none" />
      </g>
    ),
  },

  // Interview — standing tall, clipboard
  interview: {
    eyes: "open", mouth: "smile",
    pose: {
      leftArm:  "M40 44 L28 54 L28 64",
      rightArm: "M40 44 L52 56",
    },
    extras: (
      <g>
        {/* clipboard in left hand */}
        <rect x="20" y="58" width="14" height="18" rx="1" fill={STICK.accentCream} stroke={STICK.stroke} strokeWidth={2} />
        <rect x="24" y="56" width="6" height="3" fill={STICK.accentSilver} stroke={STICK.stroke} strokeWidth={1.5} />
        <line x1="22" y1="64" x2="32" y2="64" stroke="#94A3B0" strokeWidth={1.2} />
        <line x1="22" y1="68" x2="30" y2="68" stroke="#94A3B0" strokeWidth={1.2} />
        <line x1="22" y1="72" x2="32" y2="72" stroke="#94A3B0" strokeWidth={1.2} />
      </g>
    ),
  },

  // Negotiate — hand out, rupee symbol
  negotiate: {
    eyes: "focus", mouth: "smile",
    pose: {
      leftArm:  "M40 44 L28 56",
      rightArm: "M40 44 L62 50",
    },
    extras: (
      <g>
        {/* rupee floating above palm */}
        <text x="62" y="38" fontFamily="Inter, sans-serif" fontWeight="700" fontSize="14" fill={STICK.accentGold}>₹</text>
        <circle cx="66" cy="34" r="10" fill="none" stroke={STICK.accentGold} strokeWidth={1.5} strokeDasharray="2 2" opacity="0.6" />
      </g>
    ),
  },

  // Climbing reach — LOGO CALLBACK
  climb_reach: {
    eyes: "focus", mouth: "smile",
    pose: {
      head: { cx: 36, cy: 28, r: 12 },
      neckStart: { x: 37, y: 40 },
      shoulders: { x: 38, y: 46 },
      hips: { x: 42, y: 70 },
      leftArm:  "M38 48 Q44 38 60 22",
      rightArm: "M38 48 L24 58",
      leftLeg:  "M42 70 Q36 80 28 90",
      rightLeg: "M42 70 Q52 76 56 92",
    },
    extras: (
      <g>
        {/* gold star top right */}
        <path d="M68 14 L70 10 L74 9 L71 6 L72 2 L68 4 L64 2 L65 6 L62 9 L66 10 Z"
              fill={STICK.accentGold} stroke={STICK.accentGold} strokeWidth={1.2} strokeLinejoin="round" />
        {/* rising arrow Pip is climbing — direct logo callback */}
        <path d="M12 96 L60 32" stroke={STICK.stroke} strokeWidth={2.5} strokeDasharray="3 4" strokeLinecap="round" />
        <path d="M54 26 L60 32 L54 38" stroke={STICK.stroke} strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" fill="none" />
      </g>
    ),
  },

  // Running — career-running, legs spread, arms swinging
  run: {
    eyes: "focus", mouth: "open",
    pose: {
      head: { cx: 42, cy: 28, r: 12 },
      neckStart: { x: 41, y: 40 },
      shoulders: { x: 40, y: 46 },
      hips: { x: 38, y: 68 },
      leftArm:  "M40 48 Q30 56 26 50",
      rightArm: "M40 48 Q50 54 56 62",
      leftLeg:  "M38 68 Q28 78 18 90",
      rightLeg: "M38 68 Q48 76 56 94",
    },
    extras: (
      <g stroke={STICK.stroke} strokeWidth={2} strokeLinecap="round" opacity={0.4}>
        <path d="M6 50 L18 50" />
        <path d="M4 60 L14 60" />
        <path d="M8 70 L16 70" />
      </g>
    ),
  },
};

/* ---------- <Stickman pose size /> ---------- */
function Stickman({ pose = "idle", size = 140, accent, className, style }) {
  const def = POSES[pose] || POSES.idle;
  const W = 80, H = 110;
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width={size}
      height={Math.round(size * (H / W))}
      viewBox={`0 0 ${W} ${H}`}
      className={className}
      style={style}
    >
      <StickBody pose={def.pose} eyes={def.eyes} mouth={def.mouth} accent={accent || STICK.stroke} />
      {def.extras}
    </svg>
  );
}

/* ---------- ASCII stickman — for plain terminals ---------- */
const ASCII_STICK = ` ╭─╮
 │·│
 ╰┬╯
╱ │ ╲
  │
 ╱ ╲`;

/* ---------- Chunky pixel stickman — for truecolor terminals (CLI) ---------- */
// 16 wide × 22 tall. Single teal color.
const PIXEL_STICK = [
  ".....TTTT.......",
  "....TWWWWT......",
  "...TWWKWKWT.....",
  "...TWWWWWWT.....",
  "....TWWWWT......",
  ".....TWWT.......",
  "......T.........",
  "......T.........",
  ".....TTT........",
  "....T.T.T.......",
  "...T..T..T......",
  "..T...T...T.....",
  ".T....T....T....",
  "......T.........",
  "......T.........",
  "......T.........",
  ".....T.T........",
  "....T...T.......",
  "...T.....T......",
  "..T.......T.....",
  "..T.......T.....",
  ".TT.......TT....",
];

const PIXEL_STICK_PALETTE = {
  ".": null,
  "T": "#0FBEAF",
  "W": "#0E1620",  // body interior (negative space, terminal bg)
  "K": "#FFFFFF",  // eyes — white dots on dark head interior
};

function PixelStickman({ pixel = 6, className, style }) {
  const cols = PIXEL_STICK[0].length;
  const rows = PIXEL_STICK.length;
  const rects = [];
  for (let y = 0; y < rows; y++) {
    for (let x = 0; x < cols; x++) {
      const ch = PIXEL_STICK[y][x];
      const fill = PIXEL_STICK_PALETTE[ch];
      if (!fill) continue;
      rects.push(
        <rect key={y * cols + x} x={x * pixel} y={y * pixel} width={pixel} height={pixel} fill={fill} />
      );
    }
  }
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width={cols * pixel}
      height={rows * pixel}
      viewBox={`0 0 ${cols * pixel} ${rows * pixel}`}
      shapeRendering="crispEdges"
      className={className}
      style={style}
    >
      {rects}
    </svg>
  );
}

Object.assign(window, { Stickman, PixelStickman, ASCII_STICK, STICK, POSES });
