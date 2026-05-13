# LinkRight CLI — Quality Validation Reference

## Gold Standard for BMAD Downstream Agents

This document captures the **exact quality checks, validation logic, and data schemas** used in the LinkRight CLI tool. This is the specification that the web app must match to ensure consistency across all outputs.

---

## 1. QUALITY JUDGE — Complete Validation Logic

### Location
`src/linkright/agents/quality_judge.py`

### Function Signature
```python
def judge_quality(
    written_bullets: list[WrittenBullet],
    jd_analysis: JDAnalysis,
    brand_primary: str = "#0066cc",
    background: str = "#ffffff",
) -> QualityReport
```

### Six Quality Checks (Exact Implementation)

#### Check 1: Keyword Coverage (30% weight)
- **What**: % of P0/P1 keywords from JD that appear in final resume bullets
- **Formula**: `matched_keywords / total_p0_p1_keywords * 100`
- **Implementation**:
  - Collects all bullet plain text (lowercased)
  - Extracts all JD keywords with priority "P0" or "P1"
  - Case-insensitive substring matching in bullet text
  - Rounds to 1 decimal place
- **Suggestion Trigger**: If missing_keywords exist, add suggestion listing first 5 missing keywords

#### Check 2: Width Fill Average & Min (25% weight)
- **What**: Average and minimum fill percentage across all bullets
- **Data Points**:
  - `width_fill_avg`: `sum(fills) / len(fills)`
  - `width_fill_min`: `min(fills)`
  - Rounds to 1 decimal place
- **Overflow Bullets**: If any bullet has `width_status == "OVERFLOW"`, add suggestion
- **Short Bullets**: If any bullet has `width_status == "TOO_SHORT"`, add suggestion

#### Check 3: Verb Deduplication (15% weight)
- **What**: Detects repeated action verbs across all bullets
- **Implementation**:
  - Collects `action_verb` field from each WrittenBullet
  - Uses set-based dedup to find duplicates
  - Returns unique list of duplicate verbs
- **Score Component**: 
  - If no duplicates: 100 points
  - If duplicates exist: 50 points
- **Suggestion Trigger**: List unique duplicate verbs in suggestion

#### Check 4: Page Fit (15% weight)
- **What**: Validates that resume content fits on one A4 page
- **Implementation**:
  - Estimates experience entries: `len(set(b.signal_id for b in written_bullets))`
  - Calculates bullets per entry: `total_bullets / max(entries, 1)`
  - Calls `validate_page_fit()` with SectionSpec array
  - Boolean result: `page_fit_result.fits_one_page`
- **Score Component**:
  - If fits: 100 points
  - If overflows: 0 points
- **Suggestion Trigger**: If not fits, add overflow amount in mm

#### Check 5: Color Contrast (10% weight)
- **What**: WCAG AA contrast validation for brand color on white background
- **Implementation**:
  - Calls `validate_contrast(ContrastInput(foreground_hex=brand_primary, background_hex=background))`
  - Checks `contrast_result.passes_wcag_aa_normal_text`
- **Score Component**:
  - If passes: 100 points
  - If fails: 50 points
- **Suggestion Trigger**: If fails, include recommendation from contrast tool

#### Check 6: ATS Compliance (5% weight)
- **What**: Detects common ATS-incompatible HTML tags
- **Implementation**:
  - Loops through each bullet's `html_text`
  - Checks for `<table` (case-insensitive): "Table HTML found in bullet — ATS may not parse"
  - Checks for `<img` (case-insensitive): "Image tag found in bullet — ATS will skip"
  - Collects all issues in `ats_issues` list
- **Score Component**:
  - If no issues: 100 points
  - If issues exist: 50 points

### Overall Grade Calculation

```python
score = 0.0
score += min(keyword_coverage, 100) * 0.30  # Keyword coverage (30%)
score += min(width_fill_avg, 100) * 0.25    # Width fill (25%)
score += (100 if not duplicates else 50) * 0.15  # Verbs (15%)
score += (100 if page_fits else 0) * 0.15   # Page fit (15%)
score += (100 if contrast_passes else 50) * 0.10  # Contrast (10%)
score += (100 if not ats_issues else 50) * 0.05   # ATS (5%)
```

### Grade Thresholds
| Score Range | Grade |
|-------------|-------|
| >= 90      | A     |
| >= 75, < 90| B     |
| >= 60, < 75| C     |
| >= 40, < 60| D     |
| < 40       | F     |

### Output: QualityReport Schema
```python
class QualityReport(BaseModel):
    overall_grade: str              # "A"|"B"|"C"|"D"|"F"
    keyword_coverage: float         # % of P0/P1 keywords found (rounded 1 decimal)
    width_fill_avg: float           # Average fill % across bullets (rounded 1 decimal)
    width_fill_min: float           # Minimum fill % (rounded 1 decimal)
    verb_duplicates: list[str]      # Unique duplicate verbs (empty if none)
    page_fits: bool                 # True if all content fits on one page
    contrast_passes: bool           # True if brand color passes WCAG AA (4.5:1)
    ats_issues: list[str]           # List of ATS compatibility warnings
    suggestions: list[str]          # Human-readable improvement suggestions
```

---

## 2. BULLET WRITER — Width Retry Loop

### Location
`src/linkright/agents/bullet_writer.py`

### Function Signature
```python
def write_bullets(
    jd_analysis: JDAnalysis,
    scored_bullets: list[ScoredBullet],
    template_config: dict,
    max_bullets: int = 8,
) -> list[WrittenBullet]
```

### Retry Loop Algorithm

#### Initial Write (Attempt 0)
1. Claude writes XYZ-format bullet using system prompt
2. Extract bullet text, strip quotes/markdown
3. Enter width-check loop

#### Width-Check Loop (3 Maximum Attempts)
```
for attempt in range(3):
    1. measure_width() → MeasureWidthOutput
    
    if status == "PASS":
        break  # SUCCESS
    
    2. direction = "expand" if status == "TOO_SHORT" else "trim"
    
    3. suggest_synonyms() → SynonymOutput
    
    4. Build revision prompt with:
       - Current status (TOO_SHORT or OVERFLOW)
       - Current fill percentage
       - Top 3 synonym suggestions (if any)
       - Direction ("longer" or "shorter")
    
    5. Claude revises the bullet
    
    6. Extract revised text, strip quotes/markdown
```

### Key Parameters

| Parameter | Value |
|-----------|-------|
| Max retries | 3 |
| Success criteria | status == "PASS" (90-100% fill) |
| Retry triggers | "TOO_SHORT" or "OVERFLOW" |
| Min fill for PASS | 90% |
| Max fill for PASS | 100% |

### Synonym Suggestion Integration
- **When triggered**: After first failed width check
- **What's provided**: Top 3 synonym suggestions to Claude with:
  - Original word
  - Replacement word
  - Width delta (character units)
- **LLM decision**: Claude chooses whether to apply suggestions or rewrite freely

### Post-Retry Handling
- **After 3 attempts**: No more retries (accept final status even if OVERFLOW/TOO_SHORT)
- **Final width measurement**: Always run after retry loop completes
- **Verb registration**: Extract leading word (first token, lowercased) and register with `track_verbs()`

### Output: WrittenBullet Fields

```python
class WrittenBullet(BaseModel):
    signal_id: str              # Links to career_signals.yaml signal
    achievement_index: int      # Index in signal's achievements list
    section_type: str           # Always "experience" for bullets
    group: str                  # Bullet group name (optional)
    html_text: str              # Final HTML-formatted bullet with <b> tags
    plain_text: str             # Plain text version for width measurement
    width_total: float          # Weighted width in character-units
    fill_percentage: float      # Fill % against budget (0-100+)
    width_status: str           # "PASS"|"TOO_SHORT"|"OVERFLOW"
    action_verb: str            # Leading verb (lowercase, for dedup)
```

---

## 3. BRS SCORING — Bullet Relevance Score

### Location
`src/linkright/tools/score_bullets.py`

### Function Signature
```python
def score_bullets(params: ScoreBulletsInput) -> ScoreBulletsOutput
```

### Five Scoring Factors (Exact Weights)

#### Factor 1: Keyword Overlap (35% weight)
- **Formula**: `matched_count / total_jd_keywords` (capped at 1.0)
- **Matching**: Case-insensitive substring match
- **Calculation**: 
  ```python
  if len(jd_keywords) == 0:
      overlap = 0.0
  else:
      overlap = min(len(matches) / len(jd_keywords), 1.0)
  ```

#### Factor 2: Metric Magnitude (25% weight)
- **Score Scale**: 0.3 to 1.0
- **Scoring Rules**:
  - `1.0` if text contains dollar amounts (`$[0-9,.KMB]+` or `[0-9,.]+[KMB]`)
  - `1.0` if text contains percentages (`\d+%`)
  - `0.7` if text contains any numbers (counts, rates, etc.)
  - `0.3` if text is qualitative-only (no quantification)

#### Factor 3: Recency (20% weight)
- **Score Scale**: 0.4 to 1.0
- **Based On**: `entry_index` from interview_data
- **Scoring Rules**:
  | entry_index | Score |
  |-------------|-------|
  | 0           | 1.0   |
  | 1           | 0.8   |
  | 2           | 0.6   |
  | 3+          | 0.4   |

#### Factor 4: Leadership (10% weight)
- **Score Scale**: 0.0 to 1.0
- **Strong Leadership Verbs** (→ 1.0): "lead", "manage", "mentor", "direct", "oversee", "coordinate", "led", "team"
- **Collaborative Verbs** (→ 0.5): "collaborate", "work with", "support", "contribute", "assist", "partner"
- **No match** (→ 0.0): Neither category present

#### Factor 5: Uniqueness (10% weight)
- **Score Scale**: 0.0 to 1.0
- **Algorithm**:
  1. Extract skills/verbs from current bullet
  2. Extract skills/verbs from all higher-scored bullets
  3. Compare sets:
     - No overlap (unique skills) → 1.0
     - Partial overlap (some unique, some shared) → 0.5
     - All duplicates → 0.0
     - No identifiable skills → 0.5
- **Recalculation**: Uniqueness is recalculated after initial sort by BRS

### BRS Calculation
```python
brs = (
    keyword_overlap * 0.35 +
    metric_magnitude * 0.25 +
    recency * 0.20 +
    leadership * 0.10 +
    uniqueness * 0.10
)
```
- **Range**: 0.0 to 1.0
- **Precision**: Rounded to 3 decimal places

### Tier Assignment
| BRS Range | Tier | Category      |
|-----------|------|---------------|
| >= 0.7    | 1    | must-include  |
| 0.4-0.7   | 2    | should-include|
| < 0.4     | 3    | nice-to-have  |

### Recommendation Logic
1. Sort all scored bullets by tier (1 → 2 → 3)
2. Within each tier, sort by BRS descending
3. Select top N bullets (where N = total_bullet_budget)
4. Return recommended project_ids and dropped project_ids

### Input: ScoreBulletsInput
```python
class ScoreBulletsInput(BaseModel):
    bullets: list[CandidateBullet]  # Candidate bullets with raw text
    jd_keywords: list[dict]         # [{"keyword": str, "category": str}, ...]
    career_level: str               # "fresher"|"entry"|"mid"|"senior"|"executive"
    total_bullet_budget: int        # Max bullets to recommend
```

### Output: ScoreBulletsOutput
```python
class ScoreBulletsOutput(BaseModel):
    scored_bullets: list[ScoredBullet]      # All bullets, sorted by BRS desc
    tier_1_count: int                       # Count of Tier 1 bullets
    tier_2_count: int                       # Count of Tier 2 bullets
    tier_3_count: int                       # Count of Tier 3 bullets
    recommended_bullets: list[str]          # project_ids to include
    dropped_bullets: list[str]              # project_ids over budget
```

### ScoredBullet Schema
```python
class ScoredBullet(BaseModel):
    project_id: str                         # Links to CandidateBullet
    raw_text: str                           # Original bullet text
    brs: float                              # Bullet Relevance Score (0.0-1.0)
    tier: int                               # 1, 2, or 3
    keyword_matches: list[str]              # JD keywords found in bullet
    score_breakdown: dict                   # {keyword_overlap, metric_magnitude, recency, leadership, uniqueness}
```

---

## 4. STATE LOGGING — Pipeline Checkpoints

### Location
`src/linkright/pipeline.py`

### Function: `_save_state(state_dir, filename, data)`
```python
def _save_state(state_dir: Path, filename: str, data: dict):
    """Save pipeline state to JSON file (crash-safe, Rule 8)."""
    state_dir.mkdir(parents=True, exist_ok=True)
    path = state_dir / filename
    path.write_text(json.dumps(data, indent=2, default=str))
```

### State Files Saved at Each Step

| Step | Filename | Content | Format |
|------|----------|---------|--------|
| 1 | `1_inputs_loaded.json` | resume_path, jd_path, signals_count, achievements_count | JSON |
| 2 | `2_jd_analysis.json` | Full JDAnalysis.model_dump() | JSON |
| 3 | `3_scored_bullets.json` | ScoreBulletsOutput.model_dump() | JSON |
| 4 | `4_written_bullets.json` | List[WrittenBullet.model_dump()] | JSON |
| 5 | `5_assembled.json` | {status: "success", html_length: int} | JSON |
| 6 | `6_quality_report.json` | QualityReport.model_dump() | JSON |

### State Directory Location
```
.linkright/state/
  ├── 1_inputs_loaded.json
  ├── 2_jd_analysis.json
  ├── 3_scored_bullets.json
  ├── 4_written_bullets.json
  ├── 5_assembled.json
  └── 6_quality_report.json
```

### Data Captured Per Step
- **Step 1**: Input validation (file paths, counts)
- **Step 2**: JD parsing (keywords, strategy, requirements, career level)
- **Step 3**: Bullet scoring (BRS, tiers, recommendations, breakdowns)
- **Step 4**: Width-fitted bullet content (all WrittenBullet fields)
- **Step 5**: HTML assembly status (success flag, output size)
- **Step 6**: Quality assessment (grades, coverage, suggestions, issues)

---

## 5. PYDANTIC SCHEMAS — Complete Reference

### 5.1 JDAnalysis Schema
**File**: `src/linkright/schemas/jd_analysis.py`

```python
class JDKeyword(BaseModel):
    keyword: str                           # Text to match
    category: str                          # "skill"|"tool"|"action"|"domain"|"certification"
    priority: str = "P1"                   # "P0" (must-have) | "P1" (should-have) | "P2" (nice-to-have)

class BrandColors(BaseModel):
    primary: Optional[str] = None          # Primary hex color
    secondary: Optional[str] = None        # Secondary hex color
    tertiary: Optional[str] = None         # Tertiary hex color
    quaternary: Optional[str] = None       # Quaternary hex color

class JDAnalysis(BaseModel):
    company_name: str                      # Target company name
    role_title: str                        # Target job title
    career_level: str                      # "fresher"|"entry"|"mid"|"senior"|"executive"
    strategy: str                          # "METRIC_BOMBARDMENT"|"SKILL_MATCHING"|"LEADERSHIP_NARRATIVE"|"TRANSFORMATION_STORY"|"BALANCED"
    keywords: list[JDKeyword]              # All extracted keywords with priorities
    brand_colors: Optional[BrandColors]    # Optional brand colors from JD
    requirements_p0: list[str]             # Must-have requirements (P0)
    requirements_p1: list[str]             # Should-have requirements (P1)
    requirements_p2: list[str]             # Nice-to-have requirements (P2)
    summary: Optional[str]                 # Brief role summary for context
```

### 5.2 WrittenBullet Schema
**File**: `src/linkright/schemas/pipeline_state.py`

```python
class WrittenBullet(BaseModel):
    signal_id: str                         # Links to career_signals.yaml signal
    achievement_index: int = 0             # Index in signal's achievements list
    section_type: str = "experience"       # "experience"|"education"|"awards"|"projects"
    group: str = ""                        # Bullet group name for visual clustering
    html_text: str                         # Final HTML with <b> tags, ready for template
    plain_text: str                        # Plain text (no HTML) for width measurement
    width_total: float                     # Weighted width in character-units
    fill_percentage: float                 # Fill % against budget (0-100+)
    width_status: str                      # "PASS"|"TOO_SHORT"|"OVERFLOW"
    action_verb: str                       # Leading action verb (lowercase, for dedup)
```

### 5.3 QualityReport Schema
**File**: `src/linkright/schemas/pipeline_state.py`

```python
class QualityReport(BaseModel):
    overall_grade: str                     # "A"|"B"|"C"|"D"|"F"
    keyword_coverage: float                # % of P0/P1 keywords in resume (0-100)
    width_fill_avg: float                  # Average fill % across all bullets
    width_fill_min: float                  # Worst bullet fill %
    verb_duplicates: list[str]             # List of repeated verbs (empty if none)
    page_fits: bool = True                 # True if content fits on one page
    contrast_passes: bool = True           # True if brand color passes WCAG AA
    ats_issues: list[str]                  # List of ATS compliance warnings
    suggestions: list[str]                 # Human-readable improvement suggestions
```

### 5.4 CareerSignals Schema
**File**: `src/linkright/schemas/career_signals.py`

```python
class Achievement(BaseModel):
    raw: str                               # Raw bullet text
    fit_tags: list[str] = []               # Skill/domain tags
    signal_strength: Optional[float] = None # Score 0-10 (optional)

class SignalContext(BaseModel):
    team_size: Optional[int] = None        # Number of team members
    scope: Optional[str] = None            # "global"|"national"|"regional"|"local"
    budget: Optional[float] = None         # Budget managed (if applicable)
    tech_stack: list[str] = []             # Technologies used

class Signal(BaseModel):
    id: str                                # Unique signal ID (e.g., "sig-001")
    company: str                           # Company name
    role: str                              # Job title/role
    tenure: Optional[str] = None           # Duration (e.g., "2 years 3 months")
    signal_type: str = "job"               # "job"|"internship"|"freelance"|"project"|"venture"|"research"|"open-source"
    narrative: Optional[str] = None        # Context story or narrative
    achievements: list[Achievement] = []   # List of achievements
    context: Optional[SignalContext] = None # Additional context data

class Education(BaseModel):
    degree: Optional[str] = None           # Degree type (e.g., "B.S.")
    field: Optional[str] = None            # Field of study
    institution: Optional[str] = None      # School/university name
    year: Optional[str] = None             # Graduation year or date range

class VoluntaryWork(BaseModel):
    org: str                               # Organization name
    role: Optional[str] = None             # Role title
    tenure: Optional[str] = None           # Duration
    description: str                       # Description of work

class StaticSection(BaseModel):
    role_title: Optional[str] = None       # Professional role title
    skills: list[str] = []                 # Core skills/competencies
    education: Optional[Education] = None  # Education entry
    achievements: list[str] = []           # Scholastic achievements
    voluntary_work: list[VoluntaryWork] = [] # Voluntary work entries
    interests: list[str] = []              # Personal interests

class Metadata(BaseModel):
    user: str                              # Full name
    email: Optional[str] = None            # Email address
    phone: Optional[str] = None            # Phone number
    linkedin_url: Optional[str] = None     # LinkedIn profile URL
    tagline: Optional[str] = None          # Short tagline/headline
    summary: Optional[str] = None          # Professional summary
    profession: str = "product-manager"    # Default profession
    region: Optional[str] = None           # Geographic region
    yoe_override: Optional[int] = None     # Override years of experience
    anchor_signals: list[str] = []         # Anchor/featured signals

class CareerSignals(BaseModel):
    metadata: Metadata                     # User metadata
    static: Optional[StaticSection] = None # Static content sections
    signals: list[Signal]                  # Dynamic career signals (min 1)
```

---

## 6. Supporting Tools & Utilities

### 6.1 Measure Width Tool
**File**: `src/linkright/tools/measure_width.py`

```python
def measure_width(
    params: MeasureWidthInput,
    template_config: dict = None
) -> MeasureWidthOutput

class MeasureWidthOutput(BaseModel):
    weighted_total: float              # Total width in character-units (after letter-spacing correction)
    target_95: float                   # Target fill target (95% of raw_budget)
    raw_budget: float                  # Maximum budget for this line_type
    fill_percentage: float             # (weighted_total / raw_budget) x 100
    status: str                        # "PASS" | "TOO_SHORT" | "OVERFLOW"
    rendered_text: str                 # Visible text after HTML removal
    rendered_char_count: int           # Total characters
    bold_char_count: int               # Characters in <b> tags
    surplus_or_deficit: float          # positive = over target_95, negative = under
```

**Status Rules**:
- `fill < 90%` → "TOO_SHORT"
- `90% <= fill <= 100%` → "PASS"
- `fill > 100%` → "OVERFLOW"

### 6.2 Suggest Synonyms Tool
**File**: `src/linkright/tools/suggest_synonyms.py`

```python
def suggest_synonyms(params: SynonymInput) -> SynonymOutput

class SynonymSuggestion(BaseModel):
    original_word: str                 # Word in the text
    replacement_word: str              # Suggested synonym
    width_delta: float                 # Change in character-units
    estimated_new_total: float         # Projected width after substitution
    position_in_text: int              # Character index where word starts

class SynonymOutput(BaseModel):
    suggestions: list[SynonymSuggestion]  # Top 10 suggestions (sorted by proximity to target)
    gap_to_close: float                # Remaining character-units to reach target
```

### 6.3 Track Verbs Tool
**File**: `src/linkright/tools/track_verbs.py`

```python
class TrackVerbsInput(BaseModel):
    action: str                        # "check"|"register"|"list"|"reset"
    verbs: list[str] = []              # Verbs to check/register

class TrackVerbsOutput(BaseModel):
    action_performed: str              # Echo of action
    results: dict[str, bool]           # Verb -> available/registered
    conflicts: list[str]               # Verbs already used
    total_used: int                    # Total unique verbs registered
    all_used_verbs: list[str]          # Complete list of registered verbs
```

### 6.4 Validate Page Fit Tool
**File**: `src/linkright/tools/validate_page_fit.py`

```python
class PageFitOutput(BaseModel):
    total_height_mm: float             # Total computed height
    usable_height_mm: float            # Available height (271.6mm for A4)
    fits_one_page: bool                # True if total_height <= usable_height
    remaining_mm: float                # Space left (positive) or overflow (negative)
    breakdown: list[dict]              # Per-section height details
    recommendation: str                # "fits"|"tight"|"overflow"
```

### 6.5 Validate Contrast Tool
**File**: `src/linkright/tools/validate_contrast.py`

```python
class ContrastOutput(BaseModel):
    contrast_ratio: float              # WCAG contrast ratio
    passes_wcag_aa_normal_text: bool   # True if ratio >= 4.5
    passes_wcag_aa_large_text: bool    # True if ratio >= 3.0
    recommendation: str                # "OK" or suggested hex color
```

**WCAG AA Standards**:
- Normal text (< 18pt or < 14pt bold): **4.5:1**
- Large text (>= 18pt or >= 14pt bold): **3.0:1**
- Resume body text (9.5pt) = normal text → requires **4.5:1**

---

## 7. Testing Reference

### Test Files
- `tests/test_quality_judge.py` — Quality Judge validation tests
- `tests/test_score_bullets.py` — BRS scoring tests
- `tests/test_width_calc.py` — Width measurement tests
- `tests/conftest.py` — Shared fixtures

### Key Test Fixtures
```python
@pytest.fixture
def sample_jd_analysis():
    """Standard test JD for Attentive Senior PM role"""
    return JDAnalysis(
        company_name="Attentive",
        role_title="Senior Product Manager",
        career_level="senior",
        strategy="BALANCED",
        keywords=[
            JDKeyword(keyword="AI/ML", category="skill", priority="P0"),
            JDKeyword(keyword="product strategy", category="skill", priority="P0"),
            JDKeyword(keyword="cross-functional", category="action", priority="P1"),
            JDKeyword(keyword="A/B testing", category="tool", priority="P1"),
            JDKeyword(keyword="SMS marketing", category="domain", priority="P0"),
        ],
        ...
    )

@pytest.fixture
def sample_written_bullets():
    """Three sample XYZ bullets with different verbs and metrics"""
    return [
        # "reduced" verb, 95% fill
        WrittenBullet(signal_id="cdl-amex", action_verb="reduced", fill_percentage=95.0, ...),
        # "drove" verb, 93% fill
        WrittenBullet(signal_id="cdl-amex", action_verb="drove", fill_percentage=93.0, ...),
        # "increased" verb, 92% fill
        WrittenBullet(signal_id="crr-amex", action_verb="increased", fill_percentage=92.0, ...),
    ]
```

---

## 8. Quality Checklist for Web App Implementation

When implementing the quality system in the web app, verify these exact behaviors:

### Quality Judge
- [ ] Keyword coverage uses case-insensitive substring matching
- [ ] P0/P1 keywords only (ignore P2)
- [ ] 6 checks all implemented with exact weights (30, 25, 15, 15, 10, 5)
- [ ] Grade thresholds match exactly (90, 75, 60, 40 for A, B, C, D)
- [ ] Suggestions list is non-empty and actionable
- [ ] Width fill uses min() of actual fill for both checks
- [ ] Verb deduplication is case-insensitive and detects exact duplicates

### BRS Scoring
- [ ] 5 factors with exact weights (35, 25, 20, 10, 10)
- [ ] Keyword overlap capped at 1.0
- [ ] Metric magnitude uses regex patterns for $, %, and numbers
- [ ] Recency uses entry_index tiers (0→1.0, 1→0.8, 2→0.6, 3+→0.4)
- [ ] Leadership checks specific verb lists
- [ ] Uniqueness recalculates after initial BRS sort
- [ ] Tier assignment matches thresholds (>=0.7 = Tier 1, etc.)
- [ ] Bullet recommendations prioritize by tier first, then BRS

### Width Fitting
- [ ] 3 retries maximum
- [ ] Success condition: 90-100% fill (PASS)
- [ ] Synonyms provided in revision prompt
- [ ] Direction = "expand" for TOO_SHORT, "trim" for OVERFLOW

### State Logging
- [ ] All 6 JSON files saved in .linkright/state/
- [ ] Files saved after each step
- [ ] JSON format with proper indentation
- [ ] Use model_dump() for Pydantic models

### Contrast Validation
- [ ] WCAG AA 4.5:1 for normal text (9.5pt)
- [ ] Hex color validation
- [ ] Recommendation generation if fails

### Page Fit Validation
- [ ] A4 usable height = 271.6mm
- [ ] Section height calculation includes all components
- [ ] Remaining_mm can be negative (overflow)
- [ ] Recommendation = "fits"|"tight"|"overflow"

---

## 9. Example Quality Report Output

```json
{
  "overall_grade": "A",
  "keyword_coverage": 80.0,
  "width_fill_avg": 93.7,
  "width_fill_min": 92.0,
  "verb_duplicates": [],
  "page_fits": true,
  "contrast_passes": true,
  "ats_issues": [],
  "suggestions": []
}
```

```json
{
  "overall_grade": "B",
  "keyword_coverage": 65.0,
  "width_fill_avg": 88.5,
  "width_fill_min": 75.0,
  "verb_duplicates": ["led", "managed"],
  "page_fits": true,
  "contrast_passes": false,
  "ats_issues": ["Image tag found in bullet — ATS will skip"],
  "suggestions": [
    "Missing P0/P1 keywords: machine learning, cloud architecture",
    "2 bullets are too short (< 90% fill)",
    "Duplicate verbs: led, managed",
    "Brand color #FF0000 fails WCAG AA. Suggestion: #CC0000"
  ]
}
```

---

## Document Info

**Source**: LinkRight CLI v1.0 (April 2026)
**Last Updated**: 2026-04-06
**Maintainer**: BMAD Quality Assurance
**Scope**: Gold standard specification for downstream web app implementation

