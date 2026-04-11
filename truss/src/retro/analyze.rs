use crate::models::retro::{PatternDimension, PatternType, RetroMetrics, RetroPattern};

/// Step 2: Analyze metrics and produce prioritized patterns.
pub fn analyze_patterns(metrics: &RetroMetrics) -> Vec<RetroPattern> {
    let mut patterns: Vec<RetroPattern> = Vec::new();

    // ── Decomposition quality ──────────────────────────────────

    // Pattern: stream count
    let total = metrics.streams_total;
    if total > 4 {
        patterns.push(RetroPattern {
            pattern_type: PatternType::Improvement,
            dimension: PatternDimension::Decomposition,
            name: "Too many streams".to_string(),
            evidence: format!("{} streams produced — overhead may exceed parallelism benefit", total),
            recommendation: "Prefer 2-4 streams. Merge streams with <3 features each.".to_string(),
            mem0_entry: format!(
                "truss bmad-dev retrospective: {} streams is too many for a single goal. Overhead exceeds benefit. Rule: merge streams until each has 3-5 features minimum. Applies when: goal produces >4 streams in decompose.",
                total
            ),
        });
    } else if total >= 2 && total <= 4 {
        patterns.push(RetroPattern {
            pattern_type: PatternType::Reinforcement,
            dimension: PatternDimension::Decomposition,
            name: "Appropriate stream count".to_string(),
            evidence: format!("{} streams — good balance of parallelism and overhead", total),
            recommendation: "Keep doing this — stream count was appropriate".to_string(),
            mem0_entry: format!(
                "truss bmad-dev retrospective: {} streams — WORKS WELL. Parallelism benefit exceeded overhead. Keep using this stream count range for similar-sized goals.",
                total
            ),
        });
    }

    // Pattern: completion rate
    let completion_pct = if total > 0 {
        (metrics.streams_completed as f64 / total as f64) * 100.0
    } else {
        0.0
    };

    if completion_pct < 100.0 && total > 0 {
        let incomplete = total - metrics.streams_completed;
        patterns.push(RetroPattern {
            pattern_type: PatternType::Improvement,
            dimension: PatternDimension::Sop,
            name: "Incomplete streams at retro time".to_string(),
            evidence: format!(
                "{}/{} streams completed ({:.0}%)", metrics.streams_completed, total, completion_pct
            ),
            recommendation: format!(
                "{} streams incomplete — run `truss groom` to complete them before retrospective",
                incomplete
            ),
            mem0_entry: format!(
                "truss bmad-dev retrospective: retro ran before all streams completed ({:.0}% done). Rule: run `truss groom` until all streams show Completed before `truss retro`. Applies when: running retrospective mid-execution.",
                completion_pct
            ),
        });
    }

    // ── Role output quality ────────────────────────────────────

    // Check for streams where roles were all completed vs missing
    let streams_with_all_roles: usize = metrics.streams.iter()
        .filter(|s| s.roles_completed.len() == 4)
        .count();

    if streams_with_all_roles == metrics.streams_total as usize && metrics.streams_total > 0 {
        patterns.push(RetroPattern {
            pattern_type: PatternType::Reinforcement,
            dimension: PatternDimension::Roles,
            name: "All 4 roles completed for all streams".to_string(),
            evidence: format!("All {} streams had PO, Designer, Architect, QA outputs", streams_with_all_roles),
            recommendation: "Role isolation working well — keep spawning all 4 roles in parallel".to_string(),
            mem0_entry: "truss bmad-dev retrospective: All 4 role sub-agents completed for all streams — WORKS WELL. Role isolation produces genuinely different perspectives. Keep spawning all 4 in parallel per stream.".to_string(),
        });
    }

    // ── Cross-impact ───────────────────────────────────────────

    if metrics.conflicts_critical == 0 && metrics.conflicts_detected == 0 {
        patterns.push(RetroPattern {
            pattern_type: PatternType::Reinforcement,
            dimension: PatternDimension::CrossImpact,
            name: "Zero file conflicts".to_string(),
            evidence: "No cross-stream file reservation conflicts detected".to_string(),
            recommendation: "File reservation strategy working well — keep enforcing exclusivity".to_string(),
            mem0_entry: "truss bmad-dev retrospective: Zero cross-stream file conflicts — WORKS WELL. File exclusivity enforcement in decomposition prevents merge conflicts. Keep validating before approve.".to_string(),
        });
    } else if metrics.conflicts_critical > 0 {
        patterns.push(RetroPattern {
            pattern_type: PatternType::Improvement,
            dimension: PatternDimension::CrossImpact,
            name: "Critical file conflicts detected".to_string(),
            evidence: format!("{} CRITICAL conflicts — streams tried to modify the same files", metrics.conflicts_critical),
            recommendation: "Add shared_files section in decomposition for shared files. Enforce single-owner rule.".to_string(),
            mem0_entry: format!(
                "truss bmad-dev retrospective: {} CRITICAL file conflicts found. Root cause: decomposition did not enforce file exclusivity. Rule: run `truss verify step-01-decomposition-quality` before approve to catch these early.",
                metrics.conflicts_critical
            ),
        });
    }

    // ── SOP / gate decisions ───────────────────────────────────

    if metrics.overrides > 0 {
        patterns.push(RetroPattern {
            pattern_type: PatternType::Improvement,
            dimension: PatternDimension::Sop,
            name: "Gate approved with overrides".to_string(),
            evidence: format!("{} blocking issues overridden at gate", metrics.overrides),
            recommendation: "Review what was overridden — fix root cause in SOPs so these don't recur".to_string(),
            mem0_entry: format!(
                "truss bmad-dev retrospective: {} issues overridden at inspection gate. Overrides indicate SOP gaps or time pressure. Rule: document what was overridden and update relevant step instructions.",
                metrics.overrides
            ),
        });
    }

    // Limit to top 7 patterns (most impactful first — improvements before reinforcements)
    patterns.sort_by(|a, b| {
        match (&a.pattern_type, &b.pattern_type) {
            (PatternType::Improvement, PatternType::Reinforcement) => std::cmp::Ordering::Less,
            (PatternType::Reinforcement, PatternType::Improvement) => std::cmp::Ordering::Greater,
            _ => std::cmp::Ordering::Equal,
        }
    });

    patterns.truncate(7);
    patterns
}
