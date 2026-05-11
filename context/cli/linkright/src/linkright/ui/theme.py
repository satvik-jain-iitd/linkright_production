"""LinkRight Rich theme — single source of truth for all CLI colour aliases."""
from rich.theme import Theme

LR_THEME = Theme({
    # LinkRight brand palette
    "brand.primary":   "#4285F4",   # blue  — primary CTA, info, links
    "brand.secondary": "#EA4335",   # red   — errors, destructive actions
    "metric.positive": "#34A853",   # green — success, positive metrics
    "metric.negative": "#EA4335",   # red   — negative metrics
    "text.secondary":  "#5F6368",   # grey  — dim annotations, metadata
    "divider":         "#DADCE0",   # light grey — horizontal rules
    "warning":         "yellow",
    "success":         "#34A853",
    "error":           "#EA4335",
    "info":            "#4285F4",
    # Semantic step-feedback aliases (compatible with banner gradient palette)
    "step.accent":     "#0FBEAF",   # teal  — step completions
    "step.gold":       "#E5B80B",   # gold  — section markers, icons
    "step.warn":       "#FF5733",   # coral — inline warnings
})
