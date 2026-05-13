# DOC 18 — Evaluation Framework

## 1. Purpose

This document defines the evaluation framework for Linkright.

It specifies:

- evaluation philosophy
- the distinction between testing and evaluation
- two evaluation axes: output quality and outcome effectiveness
- output quality metrics
- outcome effectiveness metrics
- evaluation pipeline design
- baseline and regression system
- human evaluation layer
- canary system
- evaluation-driven development
- integration with other system layers

This document governs how Linkright measures whether its outputs actually help the user, not just whether they are technically correct.

---

## 2. Evaluation Philosophy

Testing checks correctness.

Evaluation checks quality.

These are different problems requiring different methods.

A test can verify that the width engine produces a character count.

Only evaluation can answer whether the resume that emerged from that process would actually get a recruiter to respond.

Linkright must maintain both.

Testing is table stakes — it is handled in DOC 07.

Evaluation is the system's mechanism for improving strategic output quality over time.

The evaluation framework should remain:
- honest about what it can and cannot measure
- grounded in real pipeline outputs, not synthetic data
- linked to actual user outcomes where possible
- non-disruptive to the user's normal workflow

Evaluation is not a quality-theater system.

It exists to catch regressions, identify improvement opportunities, and give the development process a calibrated feedback signal.

---

## 3. Two Evaluation Axes

All evaluation in Linkright falls along two axes.

### Axis 1 — Output Quality

Did the pipeline produce a good resume for this user and this opportunity?

This is measurable immediately after generation.

It uses deterministic metrics plus heuristic scoring.

### Axis 2 — Outcome Effectiveness

Did the resume help the user achieve their career objective?

This accumulates over weeks or months as real applications produce responses.

It requires the closed-loop outcome data from DOC 24.

Both axes matter.

Output quality without outcome data is optimization in the dark.

Outcome data without output quality measurement cannot identify what to fix.

The two axes work together.

---

## 4. Output Quality Metrics

The following metrics are computed for every generated resume.

### Width Compliance

Percentage of bullets that fall within the 108-120 character target band (one-line per bullet).

Target: above 85%.

Bullets outside the band are flagged: over-long bullets inflate page height; under-short bullets waste signal density.

Computed deterministically by the width engine (DOC 07).

### Page Utilization

Percentage of the available page height used.

Target band: 85-92%.

Below 85% wastes premium resume real estate.

At or above 92%, risk of overflow on minor edits or format changes.

Above 100% is a hard failure.

Computed deterministically by the layout engine (DOC 07).

### Signal Coverage

Percentage of detected JD requirements that are addressed by at least one resume bullet.

High coverage means the resume answers the role's key requirements.

Low coverage means gaps that a recruiter will notice.

Computed using the deterministic JD parsing output and signal mapping (DOC 05, DOC 07).

### Archetype Consistency

Does the set of bullets collectively support the user's stated professional archetype?

Measured using embedding-based clustering: are bullets semantically coherent around the archetype, or are they scattered across unrelated signals?

Scored 0-1. Target above 0.7.

### AI-Smell Score

Prevalence of generic phrases, templated constructions, and syntactic symmetry patterns associated with AI-generated text.

Detected using phrase-pattern heuristics and semantic scoring (DOC 07, DOC 11).

Lower is better. The score is advisory, not a hard gate.

---

## 5. Outcome Effectiveness Metrics

These metrics accumulate from the closed-loop learning system (DOC 24).

### Application to Response Rate

Fraction of applications that received any employer response.

Segmented by: resume version, company type, role archetype.

### Response to Interview Rate

Fraction of employer responses that converted to a scheduled interview.

### Interview to Offer Rate

Fraction of completed interviews that led to an offer.

Segmented by: signal set active at interview time, archetype framing, company type.

Outcome metrics require a minimum event volume to be statistically meaningful.

The system should surface patterns only when thresholds from DOC 24 are met: minimum 3 same-type events before drawing any inference.

Outcome metrics inform retrieval weight updates (DOC 05) and opportunity targeting (DOC 23).

---

## 6. Evaluation Pipeline

Every generated resume passes through the output quality evaluation pipeline immediately.

The evaluation pipeline runs deterministically after generation is complete.

Stages:

```text
Width compliance check
→ Page utilization check
→ Signal coverage check
→ Archetype consistency scoring
→ AI-smell scoring
→ Aggregate quality score
→ Log to run record
```

The aggregate quality score is a weighted composite.

No single metric should dominate; the system should flag which specific metrics are below threshold when a resume falls short.

Evaluation outputs are attached to the run record (DOC 08, DOC 11) alongside generation metadata.

The user can inspect evaluation results:

```text
linkright resume evaluate <run_id>
```

---

## 7. Baseline and Regression System

A baseline file — `e2e-baseline-latest.json` — stores the metric values for the most recent known-good generation across canonical test cases.

Every new generation run should be compared against baseline.

If any metric regresses below the baseline by more than the allowed tolerance, the system surfaces a warning before delivering the artifact.

Regression thresholds (examples):
- width compliance: must not drop more than 5 percentage points below baseline
- page utilization: must stay within 85-92% band
- signal coverage: must not drop more than 10 percentage points below baseline

When a regression is detected:
- the run is flagged
- the specific failing metric is identified
- the user is informed before the artifact is opened

Baseline is updated intentionally — when a new pipeline version has been verified to produce equal or better quality than the previous baseline.

Baseline updates should not happen automatically.

They should be triggered explicitly after a validated improvement.

---

## 8. Human Evaluation Layer

Automated metrics measure what is measurable.

Some quality dimensions require human judgment:
- recruiter clarity: does a reader immediately understand who this person is?
- story coherence: do the bullets build a credible narrative arc?
- authenticity: does this read like a real person or like an AI output that passed a filter?

A structured scorecard captures these dimensions.

The scorecard is not required for every run.

It is used during explicit improvement cycles — when the team is iterating on generation quality, evaluating a new model, or investigating a pipeline regression.

Scorecard prompts are fixed across evaluations to enable comparison.

Results are stored alongside run metadata.

The human evaluation layer complements automated metrics; it does not replace them.

---

## 9. Canary System

Two to three canonical resumes serve as permanent canary inputs.

A canary is defined by:
- a fixed profile snapshot
- a fixed JD
- expected metric ranges for each output quality metric

Every release of the pipeline runs the canary suite before shipping.

If any canary metric falls outside its expected range, the release is blocked.

Canaries catch regressions that unit tests and automated metrics miss — specifically, regressions in LLM output quality, prompt format drift, and layout behavior under real profile content.

Canary inputs use real profile and JD data from the test corpus.

They are never synthetic.

---

## 10. Evaluation-Driven Development

Before any new pipeline step is added or an existing step is modified, the team must define what improvement looks like in metric terms.

The sequence:

```text
Define metric impact hypothesis
→ Implement change
→ Run evaluation suite on same corpus
→ Compare metrics before and after
→ Ship only if at least one metric improves and none regress materially
```

This prevents development effort from being spent on changes that do not measurably improve output quality.

It also prevents well-intentioned changes from silently degrading quality in dimensions the author was not focused on.

Evaluation is not the last step.

It is the frame that gives the development process direction.

---

## 11. Integration

The evaluation framework integrates with:

### DOC 07 — Deterministic Engines and Validation Systems

Width compliance, page utilization, and signal coverage are computed using deterministic infrastructure defined in DOC 07.

Evaluation consumes validation outputs; it does not duplicate them.

### DOC 11 — Observability, Logging & Explainability Framework

Evaluation results are stored in the run record alongside execution traces.

The user can inspect quality scores for any historical run through the same observability layer used for debugging.

### DOC 24 — Closed-Loop Learning System

Outcome effectiveness metrics are sourced from the append-only outcome event log defined in DOC 24.

The evaluation framework reads outcome data; it does not write to or modify it.

### DOC 06 — Resume Generation Engine

Evaluation acts as the quality gate for generation output.

The generation engine emits artifacts; the evaluation pipeline scores them.

Scores feed back into the optimization loop when generation is run in iterative mode.

---

## 12. Document Dependencies

This document depends on:
- DOC 01 — Vision, Philosophy & System Principles
- DOC 06 — Resume, Positioning & Artifact Generation Engine
- DOC 07 — Deterministic Engines & Validation Systems
- DOC 11 — Observability, Logging & Explainability Framework
- DOC 24 — Closed-Loop Learning System

This document influences:
- DOC 05 — Retrieval, Ranking & Strategic Intelligence System
- DOC 23 — Career Decision Engine

This document should be treated as the canonical evaluation framework reference for Linkright.
