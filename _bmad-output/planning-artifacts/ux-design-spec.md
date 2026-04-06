# UX Design Spec — Quality Dashboard + Scenarios

## 5 User Scenarios
1. **Happy Path** — Grade A, all green, collapsed suggestions, download
2. **Quality Failure** — Grade C, amber badge, auto-expanded suggestions, chat edit, stale warning
3. **Partial Failure** — 0 chunks, career_text fallback, info banner, Grade D
4. **Career Processing** — Upload → spinner → "Chunking...Embedding..." → green "Ready"
5. **Width Failure** — 2 bullets yellow-bordered in iframe, Grade B, width cards amber

## 5 UI Components

### 1. QualityGradeBadge — 64x64 circle, letter + score
Colors: A=emerald, B=blue, C=amber, D=orange, F=red
ARIA: role="status", aria-label includes grade + score

### 2. QualityMetricsRow — 5 mini-cards (same pattern as stats)
- Keyword Coverage: % + progress bar (green/amber/red thresholds)
- Width Fill: avg + min dual progress bars
- Verb Dupes: count + checkmark or warning
- Contrast: Pass/Fail + color swatch
- ATS: Ready or N issues

### 3. SuggestionsPanel — collapsible, auto-expand for C/D/F
Bulleted actionable suggestions with warning/tip icons

### 4. StaleGradeWarning — yellow banner after any chat edit
"Grade may be outdated" — dismissible

### 5. CareerProcessingIndicator — in StepCareer
Phases: idle → chunking → embedding → done/fallback

## Data Contract (TypeScript)
```typescript
interface QualityStats {
  quality_grade: "A"|"B"|"C"|"D"|"F";
  quality_score: number;
  keyword_coverage: number;
  width_fill_avg: number;
  width_fill_min: number;
  width_fill_failures: {bullet_index: number; fill_pct: number; section: string}[];
  verb_duplicates: string[];
  contrast_passes: boolean;
  contrast_details?: {ratio: number; foreground: string; background: string};
  ats_issues: string[];
  validation_warnings: string[];
  retrieval_method: "hybrid"|"vector_only"|"fts_only"|"career_text_fallback";
  phase_checkpoints: {phase: string; duration_ms: number; status: "ok"|"warn"|"error"}[];
}
```
Backward compat: if quality_grade undefined (old jobs), quality UI doesn't render.
