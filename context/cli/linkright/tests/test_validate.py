"""Unit tests for validation tools — contrast and page fit."""
from linkright.tools.validate_contrast import validate_contrast, ContrastInput
from linkright.tools.validate_page_fit import validate_page_fit, PageFitInput, SectionSpec


class TestContrast:
    def test_black_on_white_passes(self):
        result = validate_contrast(ContrastInput(
            foreground_hex="#000000",
            background_hex="#FFFFFF",
        ))
        assert result.contrast_ratio >= 21.0
        assert result.passes_wcag_aa_normal_text is True

    def test_white_on_white_fails(self):
        result = validate_contrast(ContrastInput(
            foreground_hex="#FFFFFF",
            background_hex="#FFFFFF",
        ))
        assert result.contrast_ratio == 1.0
        assert result.passes_wcag_aa_normal_text is False

    def test_brand_blue_on_white(self):
        result = validate_contrast(ContrastInput(
            foreground_hex="#0066cc",
            background_hex="#FFFFFF",
        ))
        assert result.contrast_ratio > 1.0
        # Should provide recommendation
        assert result.recommendation is not None


class TestPageFit:
    def test_minimal_resume_fits(self):
        result = validate_page_fit(PageFitInput(
            sections=[
                SectionSpec(section_type="header"),
                SectionSpec(section_type="experience", entry_count=2, bullets_per_project=3),
            ],
            career_level="mid",
        ))
        assert result.fits_one_page is True
        assert result.remaining_mm > 0

    def test_overloaded_resume_overflows(self):
        result = validate_page_fit(PageFitInput(
            sections=[
                SectionSpec(section_type="header"),
                SectionSpec(section_type="summary", summary_lines=5),
                SectionSpec(section_type="experience", entry_count=8, bullets_per_project=6),
                SectionSpec(section_type="education", entry_count=3),
                SectionSpec(section_type="skills", edge_to_edge_lines=5),
            ],
            career_level="executive",
        ))
        assert result.fits_one_page is False
        assert result.remaining_mm < 0

    def test_height_breakdown_present(self):
        result = validate_page_fit(PageFitInput(
            sections=[
                SectionSpec(section_type="header"),
                SectionSpec(section_type="experience", entry_count=1, bullets_per_project=2),
            ],
        ))
        assert result.total_height_mm > 0
        assert len(result.breakdown) > 0
