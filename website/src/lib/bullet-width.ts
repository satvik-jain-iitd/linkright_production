/**
 * Bullet width measurement using Roboto font metrics.
 *
 * Port of worker/app/tools/measure_width.py + worker/app/data/roboto_weights.py
 * for client-side / API-side width checks without calling the Python worker.
 *
 * All widths in CU (character-units), normalized to digit (0-9) = 1.000.
 */

// ── Roboto character weights (from hmtx advance-width, unitsPerEm=2048, digit=1086) ──

const REGULAR: Record<string, number> = {
  "i": 0.445, "j": 0.445, "l": 0.445, "\u2019": 0.445, "'": 0.445,
  "I": 0.516, " ": 0.516, ".": 0.516, ",": 0.516, ":": 0.516,
  ";": 0.516, "|": 0.516,
  "f": 0.589, "!": 0.589, "-": 0.589, "(": 0.589, ")": 0.589,
  "r": 0.657, "J": 0.657, "/": 0.657, "\"": 0.657,
  "\u201c": 0.657, "\u201d": 0.657,
  "t": 0.727,
  "*": 0.801, "\u2022": 0.801,
  "s": 0.860,
  "c": 0.930, "z": 0.930, "F": 0.930, "L": 0.930, "?": 0.930,
  "a": 1.000, "e": 1.000, "k": 1.000, "v": 1.000, "x": 1.000,
  "y": 1.000, "E": 1.000, "S": 1.000, "$": 1.000,
  "\u2013": 1.000, // en-dash
  "0": 1.000, "1": 1.000, "2": 1.000, "3": 1.000, "4": 1.000,
  "5": 1.000, "6": 1.000, "7": 1.000, "8": 1.000, "9": 1.000,
  "T": 1.029, "Z": 1.029,
  "b": 1.071, "d": 1.071, "g": 1.071, "h": 1.071, "n": 1.071,
  "o": 1.071, "p": 1.071, "q": 1.071, "u": 1.071,
  "B": 1.099, "C": 1.099, "K": 1.099, "P": 1.099, "X": 1.099,
  "Y": 1.099, "+": 1.099, "#": 1.099,
  "A": 1.169, "R": 1.169, "V": 1.169, "&": 1.169,
  "D": 1.239, "G": 1.239, "H": 1.239, "N": 1.239, "U": 1.239,
  "O": 1.309, "Q": 1.309,
  "w": 1.385, "M": 1.385, "%": 1.385,
  "\u2191": 1.385, "\u2193": 1.385, "\u2192": 1.385,
  "m": 1.599, "W": 1.599,
  "\u2014": 1.599, // em-dash
  "@": 1.740,
};
const REGULAR_DEFAULT = 1.000;

const BOLD: Record<string, number> = {
  "i": 0.495, "j": 0.495, "l": 0.495, "\u2019": 0.495, "'": 0.495,
  "I": 0.565, " ": 0.516, ".": 0.565, ",": 0.565, ":": 0.565,
  ";": 0.565, "|": 0.565,
  "f": 0.639, "!": 0.639, "-": 0.639, "(": 0.639, ")": 0.639,
  "r": 0.707, "J": 0.707, "/": 0.707, "\"": 0.707,
  "\u201c": 0.707, "\u201d": 0.707,
  "t": 0.777,
  "*": 0.851, "\u2022": 0.851,
  "s": 0.910,
  "c": 0.980, "z": 0.980, "F": 0.980, "L": 0.980, "?": 0.980,
  "a": 1.052, "e": 1.052, "k": 1.052, "v": 1.052, "x": 1.052,
  "y": 1.052, "E": 1.052, "S": 1.052, "$": 1.052,
  "0": 1.052, "1": 1.052, "2": 1.052, "3": 1.052, "4": 1.052,
  "5": 1.052, "6": 1.052, "7": 1.052, "8": 1.052, "9": 1.052,
  "T": 1.081, "Z": 1.081,
  "b": 1.118, "d": 1.118, "g": 1.118, "h": 1.118, "n": 1.118,
  "o": 1.118, "p": 1.118, "q": 1.118, "u": 1.118,
  "B": 1.149, "C": 1.149, "K": 1.149, "P": 1.149, "X": 1.149,
  "Y": 1.149, "+": 1.149, "#": 1.149,
  "A": 1.219, "R": 1.219, "V": 1.219, "&": 1.219,
  "D": 1.289, "G": 1.289, "H": 1.289, "N": 1.289, "U": 1.289,
  "O": 1.359, "Q": 1.359,
  "w": 1.455, "M": 1.455, "%": 1.455,
  "\u2191": 1.455, "\u2193": 1.455, "\u2192": 1.455,
  "m": 1.658, "W": 1.658,
  "\u2014": 1.658,
  "@": 1.790,
};
const BOLD_DEFAULT = 1.052;

// ── Bullet line budget (from default_template.py) ──

export const BULLET_BUDGET = {
  raw_budget: 101.4,
  target_95: 96.4,
  range_min_90: 91.3,
  range_max_100: 101.4,
  font_size_pt: 9.5,
  letter_spacing_px: 0.0,
};

// ── Parse HTML bold segments ──

interface Segment { text: string; bold: boolean }

function parseBoldSegments(html: string): Segment[] {
  const segments: Segment[] = [];
  // Resolve HTML entities first
  let resolved = html
    .replace(/&ndash;/g, "\u2013")
    .replace(/&mdash;/g, "\u2014")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&#8211;/g, "\u2013")
    .replace(/&#8212;/g, "\u2014")
    .replace(/&#x2013;/g, "\u2013")
    .replace(/&#x2014;/g, "\u2014");

  // Split on <b>, <strong>, </b>, </strong> tags
  const regex = /<(b|strong)(?:\s[^>]*)?>|<\/(b|strong)>/gi;
  let isBold = false;
  let lastIndex = 0;

  let match;
  while ((match = regex.exec(resolved)) !== null) {
    // Text before this tag
    if (match.index > lastIndex) {
      const text = resolved.slice(lastIndex, match.index);
      if (text) segments.push({ text, bold: isBold });
    }
    // Toggle bold state
    isBold = match[1] ? true : false;  // Opening tag → bold, closing → not bold
    lastIndex = regex.lastIndex;
  }
  // Remaining text after last tag
  if (lastIndex < resolved.length) {
    segments.push({ text: resolved.slice(lastIndex), bold: isBold });
  }

  // Strip any remaining HTML tags in text segments
  return segments.map((s) => ({
    ...s,
    text: s.text.replace(/<[^>]+>/g, ""),
  }));
}

// ── Measure width ──

export interface MeasureResult {
  weighted_total: number;
  fill_pct: number;
  status: "PASS" | "TOO_SHORT" | "OVERFLOW";
  surplus_or_deficit: number;
  rendered_text: string;
}

export function measureBulletWidth(textHtml: string): MeasureResult {
  const segments = parseBoldSegments(textHtml);
  const rendered = segments.map((s) => s.text).join("");

  let weightedTotal = 0;
  for (const seg of segments) {
    const weights = seg.bold ? BOLD : REGULAR;
    const fallback = seg.bold ? BOLD_DEFAULT : REGULAR_DEFAULT;
    for (const ch of seg.text) {
      weightedTotal += weights[ch] ?? fallback;
    }
  }

  // Letter-spacing correction (0 for bullet line type, but included for completeness)
  // digit_width_px = (1086/2048) * (font_size_pt/72) * 96
  const digitWidthPx = (1086 / 2048) * (BULLET_BUDGET.font_size_pt / 72) * 96;
  const charCount = rendered.length;
  if (BULLET_BUDGET.letter_spacing_px !== 0 && charCount > 1) {
    const actualWidthPx =
      weightedTotal * digitWidthPx + (charCount - 1) * BULLET_BUDGET.letter_spacing_px;
    weightedTotal = actualWidthPx / digitWidthPx;
  }

  const fillPct = (weightedTotal / BULLET_BUDGET.raw_budget) * 100;
  const status: "PASS" | "TOO_SHORT" | "OVERFLOW" =
    weightedTotal < BULLET_BUDGET.range_min_90
      ? "TOO_SHORT"
      : weightedTotal > BULLET_BUDGET.range_max_100
        ? "OVERFLOW"
        : "PASS";

  return {
    weighted_total: Math.round(weightedTotal * 100) / 100,
    fill_pct: Math.round(fillPct * 10) / 10,
    status,
    surplus_or_deficit: Math.round((weightedTotal - BULLET_BUDGET.target_95) * 100) / 100,
    rendered_text: rendered,
  };
}
