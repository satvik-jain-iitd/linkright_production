use colored::Colorize;
use std::path::Path;

use crate::models::decomposition::DecompositionResult;
use crate::models::grooming::GroomingState;
use crate::models::inspection::GateReport;
use crate::retro;

pub fn run(run_id: Option<&str>) {
    let _ = run_id;

    println!("{}", "truss retro".bold());
    println!("{}", "─".repeat(40));

    // ── Load decomposition ───────────────────────────────────
    let streams_path = Path::new(".truss/_progress/outputs/streams.yaml");
    if !streams_path.exists() {
        eprintln!("{} No decomposition found.", "✗".red());
        std::process::exit(1);
    }

    let decomp_content = std::fs::read_to_string(streams_path).unwrap_or_default();
    let decomposition: DecompositionResult = match serde_yaml::from_str(&decomp_content) {
        Ok(d) => d,
        Err(e) => {
            eprintln!("{} Failed to parse streams.yaml: {}", "✗".red(), e);
            std::process::exit(1);
        }
    };

    // ── Load grooming state ──────────────────────────────────
    let groom_path = Path::new(".truss/_progress/grooming-state.yaml");
    let grooming_state: GroomingState = if groom_path.exists() {
        let content = std::fs::read_to_string(groom_path).unwrap_or_default();
        serde_yaml::from_str(&content).unwrap_or_else(|_| GroomingState {
            current_workflow: "grooming".to_string(),
            streams: std::collections::HashMap::new(),
            timestamp: String::new(),
        })
    } else {
        eprintln!("{} No grooming state found. Run `truss groom` first.", "✗".red());
        std::process::exit(1);
    };

    // ── Load gate report (optional) ──────────────────────────
    let gate_path = Path::new(".truss/_progress/gate-report.yaml");
    let gate_report: Option<GateReport> = if gate_path.exists() {
        let content = std::fs::read_to_string(gate_path).unwrap_or_default();
        serde_yaml::from_str(&content).ok()
    } else {
        println!(
            "  {} No gate report found — run `truss inspect` for full retrospective",
            "!".yellow()
        );
        None
    };

    // ── Step 1: Collect metrics ──────────────────────────────
    println!("\n{}", "Step 1/3: Collect Metrics".bold());
    let metrics = retro::collect::collect_metrics(
        &decomposition,
        &grooming_state,
        gate_report.as_ref(),
    );

    println!(
        "  Streams: {}/{} completed",
        metrics.streams_completed, metrics.streams_total
    );
    println!("  Tasks tracked: {}", metrics.tasks_total);
    println!(
        "  Conflicts: {} detected, {} critical",
        metrics.conflicts_detected, metrics.conflicts_critical
    );
    println!("  Timing: not available");

    // ── Step 2: Analyze patterns ─────────────────────────────
    println!("\n{}", "Step 2/3: Analyze Patterns".bold());
    let patterns = retro::analyze::analyze_patterns(&metrics);
    let improvements = patterns.iter().filter(|p| p.pattern_type == crate::models::retro::PatternType::Improvement).count();
    let reinforcements = patterns.len() - improvements;
    println!(
        "  {} patterns identified: {} improvements, {} reinforcements",
        patterns.len(),
        improvements,
        reinforcements
    );

    // ── Step 3: Generate report + mem0 entries ───────────────
    println!("\n{}", "Step 3/3: Store Insights".bold());
    let report = retro::store::generate_report(&metrics, patterns);
    retro::store::print_retro_report(&report);
    retro::store::save_retro_report(&report);

    // Update br epic
    update_br_epic(&metrics.epic_id, &report);

    println!();
    println!(
        "{}",
        "Retrospective complete. Store mem0 entries above to improve future orchestrations.".green()
    );
}

fn update_br_epic(epic_id: &str, report: &crate::models::retro::RetroReport) {
    if epic_id.is_empty() || epic_id == "unknown" {
        return;
    }

    let notes = format!(
        "RETROSPECTIVE COMPLETED\nDate: {}\nPatterns: {} improvements, {} reinforcements\nTop insight: {}",
        &report.timestamp[..10],
        report.improvements,
        report.reinforcements,
        report.top_insight
    );

    let _ = std::process::Command::new("bd")
        .arg("update")
        .arg(epic_id)
        .arg(format!("--notes={}", notes))
        .output();
}
