"""LinkRight Rich theme — single source of truth for all CLI colour aliases.

UAT cluster-E1 additions (2026-05-13): extended palette to match Claude Code
TUI design language per `specs/cluster-e-ui-design-system.md`. New aliases
are additive — old aliases preserved for backward compatibility.

UAT bugs addressed: #18 (consistent palette across commands), #21 (coral
progress verbs), #30 (Claude Code muted sub-context).
"""
from rich.theme import Theme

LR_THEME = Theme({
    # ── LinkRight brand palette (V1, unchanged) ─────────────────────────
    "brand.primary":   "#4285F4",   # blue   — primary CTA, info, links
    "brand.secondary": "#EA4335",   # red    — errors, destructive actions
    "metric.positive": "#34A853",   # green  — success, positive metrics
    "metric.negative": "#EA4335",   # red    — negative metrics
    "text.secondary":  "#5F6368",   # grey   — dim annotations, metadata
    "divider":         "#DADCE0",   # light grey — horizontal rules
    "warning":         "yellow",
    "success":         "#34A853",
    "error":           "#EA4335",
    "info":            "#4285F4",
    # Semantic step-feedback aliases (compatible with banner gradient palette)
    "step.accent":     "#0FBEAF",   # teal   — step completions
    "step.gold":       "#E5B80B",   # gold   — section markers, icons
    "step.warn":       "#FF5733",   # coral  — inline warnings

    # ── Cluster E1 additions (Claude Code TUI alignment) ────────────────
    "tui.coral":       "#EE6F4F",   # coral  — working-state '*' progress verb
    "tui.salmon":      "#FF8B6E",   # salmon — secondary coral accent
    "tui.green":       "#34A853",   # green  — thinking-state '+' progress verb
    "tui.gold":        "#F4B400",   # gold   — tier badge, highlights '🌟'
    "tui.cyan":        "#06B6D4",   # cyan   — '›' active prompt indicator
    "tui.cyan_bold":   "#0891B2",   # cyan bold — '❯' bold prompt variant
    "tui.muted":       "#8E8E93",   # muted gray — '└' branch lines + tips + telemetry
    "tui.muted_teal":  "#5EB3A8",   # muted teal — '→' result/answer markers
    "tui.hi_white":    "#F5F5F7",   # high-contrast white — '●' user-input echo bullet
    "tui.tier_badge":  "#F4B400",   # gold/orange — sticky footer tier badge
    "tui.mode_badge":  "#34A853",   # mint/teal  — sticky footer mode badge

    # ── BMAD standard semantic aliases (UAT bug #23) ────────────────────
    "bmad.input":      "#06B6D4",   # ◇ input-field marker
    "bmad.info":       "#5F6368",   # ● info-bullet color
    "bmad.highlight":  "#F4B400",   # 🌟 highlight
    "bmad.success":    "#34A853",   # ✓ success
})
