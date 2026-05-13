# DOC 23 — Career Decision Engine

## 1. Purpose

This document defines the architecture of Linkright's Career Decision Engine.

It specifies:

- core philosophy: structured comparison, not prescriptive answers
- MVP scope: pairwise job comparison (Job A vs Job B)
- scoring dimensions and how they are computed
- output format: visual scorecard, narrative summary, recommendation with rationale
- decision memory: comparison history and closed-loop learning
- integration points with existing Linkright architecture
- human-in-loop guarantee
- Phase 2 hooks for career path modeling and market intelligence

This document governs how Linkright helps users make better career decisions without making decisions for them.

---

## 2. Core Philosophy

Career decisions are among the most consequential and emotionally charged decisions a person makes.

Linkright's role is not to replace judgment.
It is to structure tradeoffs so judgment can be applied more clearly.

The system should:
- surface what is knowable
- make tradeoffs explicit
- use the user's own profile signals to personalize the comparison
- recommend with rationale
- never decide unilaterally

The goal is not to tell the user what to do.
The goal is to compress complex multi-variable tradeoffs into a format the user can reason about.

This philosophy mirrors what is documented in the Research corpus on decision-making:
strong operators do not seek certainty — they seek clarity on tradeoffs and reversibility.

The Career Decision Engine operationalizes that principle.

---

## 3. Why a Decision Engine

Career navigation does not end at the resume.

The full lifecycle is:

```
discover → position → apply → interview → negotiate → decide → perform → promote → pivot
```

The current system is strongest in the discover-through-negotiate band.

The decision layer is the first step after the offer.

Without a structured decision engine:
- users default to compensation-only reasoning
- important but non-financial factors go unweighted
- users lack visibility into how each option aligns with their archetype
- decisions are made on feelings rather than on evidence

The Career Decision Engine gives users a structured alternative.

---

## 4. MVP Scope

MVP is pairwise comparison: Job A vs Job B.

The user provides:
- two opportunities (from the system's tracked opportunity list, or new JD inputs)
- any available offer details (compensation, title, team size, start date)
- optional qualitative notes per option

The system:
- retrieves the user's profile signals and current identity state
- scores both opportunities across six dimensions
- generates a comparison scorecard
- provides a narrative summary of tradeoffs
- provides a recommendation with explicit rationale

The recommendation is always labeled as a suggestion.
The user decides.

---

## 5. Scoring Dimensions

The engine scores each opportunity across six dimensions.

### 5.1 Compensation

Factors:
- base salary
- equity (type, vesting schedule, cliff, current estimated value)
- cash bonuses or variable pay
- benefits (health, retirement, perks)
- total compensation estimate at 1 year and 3 years

Data sources:
- user-provided offer details
- Outcome history (what compensation ranges the user has encountered)
- optional: market benchmarks from cached external sources

Scoring logic:
Absolute compensation is scored against the user's current baseline and stated target range.
Relative compensation between the two options is also scored.

---

### 5.2 Growth Trajectory

Factors:
- promotion velocity at the company (inferred from JD seniority language + company signals)
- organizational scale (does this role expand scope over time)
- team size and maturity (small team = more leverage but less safety)
- company growth stage (seed / Series B / public / enterprise)

Data sources:
- parsed JD signals
- company type inferred from JD language
- user-stated growth preferences from profile

---

### 5.3 Company Brand and Credibility

Factors:
- brand recognition in the user's target career ecosystem
- company stage and funding status
- whether the company name provides career optionality downstream
- known reputation signals (from JD research layer or user notes)

Data sources:
- user notes per opportunity
- JD-derived company signals
- company stage inferred from JD language

Note:
Brand scoring is subjective and context-dependent.
The engine should surface the relevant factors without inflating brand weight beyond user intent.

---

### 5.4 Culture and Working Style Fit

Factors:
- pace signal (startup speed vs enterprise stability)
- decision-making style (autonomous vs consensus-driven)
- communication norms (explicit vs implicit)
- remote/hybrid/onsite alignment with user preference
- management style inference from JD language

Data sources:
- JD culture signals from jd_intelligence parsing layer (see Research doc)
- user-stated working style preferences from profile
- prior outcome events that reveal what environments the user converted in

Scoring logic:
Match JD culture signals against user's stated and inferred working style preferences.
Surface mismatches explicitly — do not suppress them.

---

### 5.5 Skill Development Alignment

Factors:
- which skills the role emphasizes vs which skills the user has already mastered
- which skills the role develops that are missing from the user's current signal set
- whether the role deepens existing signals or broadens into new territory
- alignment with user's stated skill-development goals

Data sources:
- user's Signal graph (existing signals and their confidence levels)
- JD skill requirements extracted during opportunity parsing
- user-stated growth goals from profile

Scoring logic:
High score = role fills meaningful signal gaps without requiring unrealistic leaps.
Low score = role either repeats what user already has, or requires signals not present at all.

---

### 5.6 PM Archetype Alignment

Factors:
- which PM archetype does this role require
- how closely does that archetype match the user's current Identity.current_archetype
- is this role an archetype stretch (growth opportunity) or an archetype mismatch (positioning risk)

Data sources:
- user's Identity schema (current_archetype, archetype_confidence)
- JD archetype signals extracted during opportunity parsing
- Signal graph for archetype-alignment signals

Scoring logic:
Exact match = highest alignment score.
Adjacent archetype = moderate score — flag as growth opportunity with explanation.
Distant archetype = low score — flag as positioning risk with explanation.

The engine should never penalize ambition, but should surface realistic gaps.

---

## 6. Score Computation

For each scoring dimension:

1. Retrieve the relevant data from the user's profile, Signal graph, Identity schema, and parsed opportunity data.
2. Compute a dimension score from 0.0 to 10.0.
3. Apply a user-stated weight if one exists (users may weight dimensions themselves).
4. Compute a weighted composite score for each opportunity.

Default weights if user has not customized:

```
Compensation            25%
Growth trajectory       20%
Skill development       20%
Archetype alignment     15%
Culture fit             15%
Company brand           5%
```

Users may override weights to match their stated priorities.

Computed scores should never be presented as objective measurements.
They should be presented as structured estimates based on available information.

The engine should display confidence levels per dimension.
Low-confidence dimensions should be visually marked.

---

## 7. Output Format

The engine produces three output layers:

### 7.1 Visual Scorecard

A structured comparison table:

```
Dimension             Job A     Job B     Weight   Notes
Compensation          8.2       6.7       25%      Job A: $145K base + equity cliff Y1; Job B: $130K + cash bonus
Growth trajectory     7.0       8.5       20%      Job B: Series B, faster promotion signals
Skill development     6.5       9.0       20%      Job B: fills AI product gap in your profile
Archetype alignment   9.0       7.5       15%      Job A: Execution PM match; Job B: mild stretch
Culture fit           7.5       8.0       15%      Both match; Job B has stronger async signals
Company brand         8.0       5.5       5%       Job A: established brand; Job B: less recognizable
---
Weighted total        7.75      7.85
```

### 7.2 Narrative Summary

A short prose summary explaining the key tradeoffs in plain language.

It should:
- avoid repeating the table mechanically
- name the 2-3 dimensions where the choices most meaningfully diverge
- explain what the divergence means for the user's career trajectory
- highlight any high-confidence vs low-confidence signals explicitly

### 7.3 Recommendation with Rationale

A single recommendation sentence, followed by 3–5 explicit reasons.

Format:

```
Recommendation: Job B, with the primary driver being skill development alignment.

Rationale:
1. Job B fills the most significant gap in your signal profile (AI product workflows).
2. Job A scores higher on compensation but the gap narrows significantly at the 3-year mark.
3. Job B's archetype stretch (from Execution PM toward AI-native PM) is within achievable range given your current signals.
4. Culture signals suggest both are viable — Job B has a slight edge on async working style match.
5. Company brand risk for Job B is low given the role's skill-development upside.
```

The recommendation block must always include a disclaimer:

```
This recommendation reflects your current profile signals and stated preferences.
It is a structured input to your decision — not a directive.
```

---

## 8. Decision Memory

Every completed comparison is persisted as a ComparisonEvent.

Fields:

```
id                   string
user_id              string
opportunity_id_a     string
opportunity_id_b     string
dimension_scores_a   object
dimension_scores_b   object
composite_score_a    float
composite_score_b    float
recommendation       string      which option was recommended
user_decision        string | null   which option the user chose
decided_at           datetime | null
outcome_ids          []string    linked outcome events after decision
created_at           datetime
```

Over time, ComparisonEvents enable the system to learn:

- whether the recommended option led to better outcomes
- which scoring dimensions were most predictive of user satisfaction
- which dimensions the user consistently overrides (revealing implicit priorities)
- whether archetype alignment predictions held up

This learning feeds back into retrieval weight adjustments over time.

---

## 9. Human-in-Loop Guarantee

The Career Decision Engine must never:

- automatically select an opportunity for the user
- send applications on behalf of a decision
- modify the user's active opportunity list based on a comparison result
- suppress options that score below a threshold

The engine may:

- recommend one option over another with explicit rationale
- suggest that both options score similarly and that the decision is personal
- surface unstated risks the user may not have considered
- flag low-confidence inputs and invite the user to provide better data

Every recommendation output must include visible reasoning.
The user must be able to disagree without fighting the system.

This is a core implementation of the human-in-loop principle from DOC 01 §4.5.

---

## 10. Phase 2 Hooks

The following capabilities are documented here for architectural awareness but are not in MVP scope.

### Career Path Modeling

Description:
The system models 3-5 year career trajectory implications of each option.

For example:
- Job A leads to Staff PM role at the company within 2 years given its promotion patterns.
- Job B provides signals that typically enable a move to AI PM roles at seed startups within 18 months.

This requires:
- accumulated outcome data from other users (not available at MVP)
- career graph modeling (future layer)

### Market Intelligence

Description:
The system retrieves current market data — compensation benchmarks, role supply/demand signals, company hiring velocity — to inform scoring.

This requires:
- persistent external data integration (not in scope at MVP)
- cached market intelligence from job search layer

These hooks are reserved for Phase 2.
Implementation documents should not build toward them until the MVP scoring and decision memory layers are stable.

---

## 11. Integration Points

The Career Decision Engine integrates with the following system layers:

### DOC 03 — Canonical Profile & Memory Graph

Source of:
- Signal graph (skill development scoring, archetype alignment scoring)
- Identity schema (current_archetype, archetype_confidence)
- CareerProfile (total years, current compensation baseline)

### DOC 04 — Opportunity Lifecycle & Workflow Architecture

Source of:
- Opportunity records and their parsed JD data
- JD signal maps
- Archetype inference from JD language

### DOC 05 — Retrieval, Ranking & Strategic Intelligence System

Used for:
- retrieving signals relevant to each scoring dimension
- identifying which signals in the profile are most relevant to each opportunity archetype

### DOC 14 — Canonical Schemas & Data Contracts

Governance of:
- ComparisonEvent schema
- Outcome linkage schema
- Identity schema (pending_suggested_upgrade may be triggered after a decision)

---

## 12. Non-Goals

The Career Decision Engine does not:

- make final decisions
- contact recruiters on behalf of the user
- provide legal or financial advice on compensation
- model compensation tax implications
- compare more than two options simultaneously at MVP
- support group or household decision modeling
- predict company performance or valuation

---

## 13. Document Dependencies

This document depends on:
- DOC 01 — Vision, Philosophy & System Principles
- DOC 02 — Core Ontology & Semantic Architecture
- DOC 03 — Canonical Profile & Memory Graph Architecture
- DOC 04 — Opportunity Lifecycle & Workflow Architecture
- DOC 05 — Retrieval, Ranking & Strategic Intelligence System
- DOC 14 — Canonical Schemas, Entity Contracts & State Models

This document influences:
- DOC 22 — Phased Execution Roadmap & Delivery Strategy
