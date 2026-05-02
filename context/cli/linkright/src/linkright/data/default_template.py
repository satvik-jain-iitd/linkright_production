"""Default template configuration for A4 Standard resume layout.

Pre-computed values for Template.html extracted from Section 3 of SPEC-v2-resume-mcp.
This is a Python dict (not a Pydantic model). The Pydantic models are defined in tools.

Embedded data: all line budgets, vertical heights, and brand CSS variables.
"""

DEFAULT_TEMPLATE_CONFIG = {
    "template_id": "cv-a4-standard",
    "page_format": "A4",
    "page_width_px": 793.7,        # 210mm @ 96dpi
    "page_height_mm": 297.0,
    "content_width_px": 697.7,     # 210mm - 2×12.7mm margins
    "usable_height_mm": 271.6,     # 297mm - header - margins
    "font_family": "Roboto",
    "budgets": {
        "bullet": {
            "available_px": 681.4,
            "raw_budget": 101.4,
            "target_95": 96.4,
            "range_min_90": 91.3,
            "range_max_100": 101.4,
            "font_size_pt": 9.5,
            "font_weight": "regular",
            "letter_spacing_px": 0.0,
            "font_family": "Roboto"
        },
        "edge_to_edge": {
            "available_px": 697.7,
            "raw_budget": 103.9,
            "target_95": 98.7,
            "range_min_90": 93.5,
            "range_max_100": 103.9,
            "font_size_pt": 9.5,
            "font_weight": "regular",
            "letter_spacing_px": 0.0,
            "font_family": "Roboto"
        },
        "entry_header": {
            "available_px": 697.7,
            "raw_budget": 94.0,
            "target_95": 89.3,
            "range_min_90": 84.6,
            "range_max_100": 94.0,
            "font_size_pt": 10.5,
            "font_weight": "bold",
            "letter_spacing_px": 0.0,
            "font_family": "Roboto"
        },
        "entry_subhead": {
            "available_px": 697.7,
            "raw_budget": 94.0,
            "target_95": 89.3,
            "range_min_90": 84.6,
            "range_max_100": 94.0,
            "font_size_pt": 10.5,
            "font_weight": "regular",
            "letter_spacing_px": 0.0,
            "font_family": "Roboto"
        },
        "project_title": {
            "available_px": 697.7,
            "raw_budget": 101.4,
            "target_95": 96.4,
            "range_min_90": 91.3,
            "range_max_100": 101.4,
            "font_size_pt": 9.5,
            "font_weight": "bold",
            "letter_spacing_px": 0.0,
            "font_family": "Roboto"
        },
        "section_title": {
            "available_px": 697.7,
            "raw_budget": 75.9,
            "target_95": 72.1,
            "range_min_90": 68.3,
            "range_max_100": 75.9,
            "font_size_pt": 13.0,
            "font_weight": "regular",
            "letter_spacing_px": 0.0,
            "font_family": "Roboto"
        },
        "name": {
            "available_px": 697.7,
            "raw_budget": 49.3,
            "target_95": 46.9,
            "range_min_90": 44.4,
            "range_max_100": 49.3,
            "font_size_pt": 20.0,
            "font_weight": "bold",
            "letter_spacing_px": -0.2,
            "font_family": "Roboto"
        },
        "role": {
            "available_px": 697.7,
            "raw_budget": 49.3,
            "target_95": 46.9,
            "range_min_90": 44.4,
            "range_max_100": 49.3,
            "font_size_pt": 20.0,
            "font_weight": "light",
            "letter_spacing_px": 1.5,
            "font_family": "Roboto"
        },
        "summary_line": {
            "available_px": 697.7,
            "raw_budget": 103.9,
            "target_95": 98.7,
            "range_min_90": 93.5,
            "range_max_100": 103.9,
            "font_size_pt": 9.5,
            "font_weight": "regular",
            "letter_spacing_px": 0.0,
            "font_family": "Roboto"
        },
        "contact_item": {
            "available_px": 697.7,
            "raw_budget": 109.4,
            "target_95": 104.0,
            "range_min_90": 98.5,
            "range_max_100": 109.4,
            "font_size_pt": 9.0,
            "font_weight": "regular",
            "letter_spacing_px": 0.0,
            "font_family": "Roboto"
        },
    },
    "vertical_heights_mm": {
        "identity_horizon": 1.06,
        "header_block": 21.34,
        "section_title": 7.68,
        "section_spacing": 4.0,
        "entry_header": 4.44,
        "entry_subhead": 5.24,
        "entry_spacing": 2.5,
        "project_title": 5.52,
        "bullet_line": 4.52,
        "edge_to_edge_line": 4.02,
        "summary_line": 4.02,
    },
    "brand_css_vars": [
        "--brand-primary-color",
        "--brand-secondary-color",
        "--brand-tertiary-color",
        "--brand-quaternary-color",
        "--ui-canvas-bg-color",
        "--ui-page-bg-color",
        "--ui-text-primary-color",
        "--ui-text-secondary-color",
        "--ui-divider-color",
    ],
    "logo_width_px": 0,
}
