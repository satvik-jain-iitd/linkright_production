use colored::Colorize;

use crate::models::retro::{PatternType, RetroMetrics, RetroPattern, RetroReport};

/// Step 3: Format output — print retro report and mem0 commands.
pub fn generate_report(metrics: &RetroMetrics, patterns: Vec<RetroPattern>) -> RetroReport {
    let improvements = patterns.iter().filter(|p| p.pattern_type == PatternType::Improvement).count() as u32;
    let reinforcements = patterns.iter().filter(|p| p.pattern_type == PatternType::Reinforcement).count() as u32;

    let top_insight = patterns
        .first()
        .map(|p| format!("{}: {}", p.name, p.recommendation))
        .unwrap_or_else(|| "No patterns identified — orchestration ran cleanly".to_string());

    RetroReport {
        epic_id: metrics.epic_id.clone(),
        metrics: metrics.clone(),
        patterns,
        improvements,
        reinforcements,
        top_insight,
        timestamp: chrono::Utc::now().to_rfc3339(),
    }
}

pub fn print_retro_report(report: &RetroReport) {
    println!();
    println!("{}", "═".repeat(64));
    println!("{}", "           RETROSPECTIVE REPORT".bold());
    println!("{}", "═".repeat(64));
    println!("Epic: {}", report.epic_id);
    println!("Date: {}", &report.timestamp[..10]);
    println!();

    // Metrics summary
    println!("{}", "METRICS".bold());
    println!("{}", "─".repeat(40));
    println!(
        "  Streams: {}/{} completed",
        report.metrics.streams_completed, report.metrics.streams_total
    );
    println!("  Total tasks: {}", report.metrics.tasks_total);
    println!(
        "  Conflicts: {} detected, {} critical",
        report.metrics.conflicts_detected, report.metrics.conflicts_critical
    );
    println!(
        "  Gate: {} → {}",
        report.metrics.gate_recommendation, report.metrics.gate_decision
    );
    if !report.metrics.timing_available {
        println!("  Timing: not available (add timestamp logging for future runs)");
    }
    println!();

    // Patterns
    println!("{}", "PATTERNS".bold());
    println!("{}", "─".repeat(40));
    println!(
        "  {} improvements, {} reinforcements",
        report.improvements, report.reinforcements
    );
    println!();

    for (i, pattern) in report.patterns.iter().enumerate() {
        let type_str = match pattern.pattern_type {
            PatternType::Improvement => "IMPROVEMENT".yellow().to_string(),
            PatternType::Reinforcement => "REINFORCE".green().to_string(),
        };
        println!(
            "  {}. [{}] [{}] {}",
            i + 1,
            type_str,
            pattern.dimension,
            pattern.name.bold()
        );
        println!("     Evidence: {}", pattern.evidence);
        println!("     → {}", pattern.recommendation);
        println!();
    }

    // mem0 commands to run
    println!("{}", "─".repeat(64));
    println!("{}", "MEM0 ENTRIES TO STORE".bold());
    println!("{}", "(run these in the Claude skill layer)".dimmed());
    println!("{}", "─".repeat(64));
    println!();

    for pattern in &report.patterns {
        println!("add_memory(\"{}\")", pattern.mem0_entry);
        println!();
    }

    println!("{}", "─".repeat(64));
    println!("Top insight: {}", report.top_insight.bold());
    println!("{}", "═".repeat(64));
}

pub fn save_retro_report(report: &RetroReport) {
    let path = ".truss/_progress/retro-report.yaml";
    let yaml = serde_yaml::to_string(report).unwrap_or_default();
    let _ = std::fs::write(path, &yaml);
    println!("  {} Retro saved: {}", "✓".green(), path);
}
