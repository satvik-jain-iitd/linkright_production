use colored::Colorize;
use std::io::{self, Write};

use crate::models::inspection::{
    BlockingIssue, CrossImpactResult, ConflictSeverity, GateDecision, GateRecommendation,
    GateReport, RoleCoverageResult, StreamCompletenessResult,
};

/// Step 4: Aggregate inspection results into a gate report.
pub fn build_gate_report(
    completeness: Vec<StreamCompletenessResult>,
    role_coverage: RoleCoverageResult,
    cross_impact: CrossImpactResult,
    epic_id: &str,
) -> GateReport {
    let mut blocking_issues: Vec<BlockingIssue> = Vec::new();
    let mut warnings: Vec<String> = Vec::new();

    // Completeness failures
    for stream in &completeness {
        if !stream.complete {
            for gap in &stream.gaps {
                blocking_issues.push(BlockingIssue {
                    category: "Completeness".to_string(),
                    description: format!("[{}] {}", stream.stream_name, gap),
                    remediation: format!(
                        "Re-run grooming: truss groom --stream {}",
                        stream.stream_name
                    ),
                });
            }
        }
    }

    // Role coverage failures — only Architect/QA are blocking
    for feature in &role_coverage.features {
        if !feature.architect {
            blocking_issues.push(BlockingIssue {
                category: "Role Coverage".to_string(),
                description: format!(
                    "[{}/{}] Missing Architect — no technical design",
                    feature.stream_name, feature.feature_name
                ),
                remediation: format!(
                    "Re-run role spawning: truss groom --stream {} --step 3",
                    feature.stream_name
                ),
            });
        }
        if !feature.qa {
            blocking_issues.push(BlockingIssue {
                category: "Role Coverage".to_string(),
                description: format!(
                    "[{}/{}] Missing QA — no test plan",
                    feature.stream_name, feature.feature_name
                ),
                remediation: format!(
                    "Re-run role spawning: truss groom --stream {} --step 3",
                    feature.stream_name
                ),
            });
        }
        if !feature.designer {
            warnings.push(format!(
                "[{}/{}] No Designer output — acceptable for backend-only features",
                feature.stream_name, feature.feature_name
            ));
        }
        if !feature.po {
            warnings.push(format!(
                "[{}/{}] No PO output — acceptable for infrastructure features",
                feature.stream_name, feature.feature_name
            ));
        }
    }

    // Cross-impact CRITICAL conflicts
    for conflict in &cross_impact.conflicts {
        if conflict.severity == ConflictSeverity::Critical {
            blocking_issues.push(BlockingIssue {
                category: "Cross-Impact".to_string(),
                description: format!(
                    "CRITICAL conflict: {} (streams: {})",
                    conflict.file_path,
                    conflict.streams.join(", ")
                ),
                remediation: conflict.resolution.clone(),
            });
        } else if conflict.severity == ConflictSeverity::High {
            warnings.push(format!(
                "HIGH conflict: {} (streams: {}) — {}",
                conflict.file_path,
                conflict.streams.join(", "),
                conflict.resolution
            ));
        }
    }

    // Determine recommendation
    let recommendation = if blocking_issues.is_empty() {
        GateRecommendation::Pass
    } else {
        GateRecommendation::Fail
    };

    GateReport {
        recommendation,
        decision: GateDecision::Pending,
        completeness,
        role_coverage,
        cross_impact,
        blocking_issues,
        warnings,
        overrides: vec![],
        timestamp: chrono::Utc::now().to_rfc3339(),
        epic_id: epic_id.to_string(),
    }
}

/// Print the gate report and wait for human decision.
pub fn present_gate_report(report: &GateReport) -> GateDecision {
    println!();
    println!("{}", "═".repeat(64));
    println!(
        "{}",
        "           INSPECTION GATE REPORT".bold()
    );
    println!("{}", "═".repeat(64));

    let rec_str = match report.recommendation {
        GateRecommendation::Pass => format!("Recommendation: {}", "PASS".green().bold()),
        GateRecommendation::Fail => format!("Recommendation: {}", "FAIL".red().bold()),
    };
    println!("{}", rec_str);
    println!();

    // Stream completeness section
    println!("{}", "─".repeat(64));
    println!("{}", "STREAM COMPLETENESS".bold());
    println!("{}", "─".repeat(64));
    let complete_count = report.completeness.iter().filter(|s| s.complete).count();
    println!("Streams: {}/{}", complete_count, report.completeness.len());
    for s in &report.completeness {
        let icon = if s.complete { "✓".green() } else { "✗".red() };
        println!(
            "  [{}] {} — {} features, {} stories, {} tasks",
            icon, s.stream_name, s.feature_count, s.story_count, s.task_count
        );
    }
    println!();

    // Role coverage section
    println!("{}", "─".repeat(64));
    println!("{}", "ROLE COVERAGE".bold());
    println!("{}", "─".repeat(64));
    let pct = if report.role_coverage.total_features > 0 {
        (report.role_coverage.fully_covered as f64 / report.role_coverage.total_features as f64) * 100.0
    } else {
        100.0
    };
    println!(
        "Features fully covered: {}/{} ({:.0}%)",
        report.role_coverage.fully_covered,
        report.role_coverage.total_features,
        pct
    );
    let blocking_features: Vec<_> = report.role_coverage.features.iter().filter(|f| f.blocking).collect();
    if blocking_features.is_empty() {
        println!("  {} No blocking role gaps", "✓".green());
    } else {
        println!("  Blocking gaps: {}", blocking_features.len());
        for f in blocking_features {
            println!("    {} {}/{}: missing {}", "✗".red(), f.stream_name, f.feature_name, f.gaps.join(", "));
        }
    }
    println!();

    // Cross-impact section
    println!("{}", "─".repeat(64));
    println!("{}", "CROSS-IMPACT ANALYSIS".bold());
    println!("{}", "─".repeat(64));
    println!(
        "Conflicts: {} CRITICAL, {} HIGH, {} MEDIUM, {} LOW",
        report.cross_impact.critical_count,
        report.cross_impact.high_count,
        report.cross_impact.medium_count,
        report.cross_impact.low_count
    );
    if report.cross_impact.critical_count == 0 && report.cross_impact.high_count == 0 {
        println!("  {} No critical/high conflicts", "✓".green());
    }
    println!();

    // Blocking issues
    println!("{}", "─".repeat(64));
    println!("{}", "BLOCKING ISSUES".bold());
    println!("{}", "─".repeat(64));
    if report.blocking_issues.is_empty() {
        println!("  {} No blocking issues found", "✓".green());
    } else {
        for (i, issue) in report.blocking_issues.iter().enumerate() {
            println!(
                "  {}. [{}] {}",
                i + 1,
                issue.category.yellow(),
                issue.description
            );
            println!("     Fix: {}", issue.remediation.dimmed());
        }
    }
    println!();

    // Warnings
    if !report.warnings.is_empty() {
        println!("{}", "─".repeat(64));
        println!("{}", "WARNINGS".bold());
        println!("{}", "─".repeat(64));
        for (i, w) in report.warnings.iter().enumerate() {
            println!("  {}. {}", i + 1, w.yellow());
        }
        println!();
    }

    println!("{}", "═".repeat(64));

    // Human decision prompt
    if report.blocking_issues.is_empty() {
        println!(
            "{}",
            "ACTION REQUIRED: Approve to proceed to execution".bold()
        );
        println!("[A]pprove  [R]eject  [O]verride and approve: ");
    } else {
        println!(
            "{}",
            "ACTION REQUIRED: Fix blocking issues or override".red().bold()
        );
        println!(
            "[R]eject (fix issues)  [O]verride (approve anyway): "
        );
    }
    println!("{}", "═".repeat(64));

    // Read user input
    print!("Enter decision (a/r/o): ");
    io::stdout().flush().unwrap();

    let mut input = String::new();
    match io::stdin().read_line(&mut input) {
        Ok(_) => {
            let choice = input.trim().to_lowercase();
            match choice.as_str() {
                "a" | "approve" => {
                    println!("{} Gate approved", "✓".green().bold());
                    GateDecision::Approved
                }
                "o" | "override" => {
                    println!("{} Gate approved with overrides", "!".yellow().bold());
                    GateDecision::ApprovedWithOverrides
                }
                _ => {
                    println!("{} Gate rejected — fix blocking issues and re-inspect", "✗".red().bold());
                    GateDecision::Rejected
                }
            }
        }
        Err(_) => {
            // Non-interactive (e.g., piped) — default to pending
            println!("  (Non-interactive mode — gate left as PENDING)");
            GateDecision::Pending
        }
    }
}

/// Save gate report to file.
pub fn save_gate_report(report: &GateReport) {
    let path = ".truss/_progress/gate-report.yaml";
    let yaml = serde_yaml::to_string(report).unwrap_or_default();
    let _ = std::fs::write(path, &yaml);
}
