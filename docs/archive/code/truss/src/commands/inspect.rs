use colored::Colorize;
use std::path::Path;

use crate::inspect;
use crate::models::decomposition::DecompositionResult;
use crate::models::grooming::GroomingState;
use crate::models::inspection::{GateDecision, GateReport, InspectionState, InspectionStatus};

pub fn run(run_id: Option<&str>) {
    let _ = run_id; // reserved for future multi-run support

    println!("{}", "truss inspect".bold());
    println!("{}", "─".repeat(40));

    // ── Load decomposition ───────────────────────────────────
    let streams_path = Path::new(".truss/_progress/outputs/streams.yaml");
    if !streams_path.exists() {
        eprintln!(
            "{} No decomposition found. Run `truss decompose` first.",
            "✗".red()
        );
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

    if !decomposition.approved {
        eprintln!(
            "{} Decomposition not approved. Run `truss decompose --approve` first.",
            "✗".red()
        );
        std::process::exit(1);
    }

    // ── Load grooming state ──────────────────────────────────
    let grooming_state_path = Path::new(".truss/_progress/grooming-state.yaml");
    if !grooming_state_path.exists() {
        eprintln!(
            "{} No grooming state found. Run `truss groom` first.",
            "✗".red()
        );
        std::process::exit(1);
    }

    let groom_content = std::fs::read_to_string(grooming_state_path).unwrap_or_default();
    let grooming_state: GroomingState = match serde_yaml::from_str(&groom_content) {
        Ok(g) => g,
        Err(e) => {
            eprintln!("{} Failed to parse grooming-state.yaml: {}", "✗".red(), e);
            std::process::exit(1);
        }
    };

    // ── Load existing gate report if available ───────────────
    let gate_path = Path::new(".truss/_progress/gate-report.yaml");
    if gate_path.exists() {
        if let Ok(content) = std::fs::read_to_string(gate_path) {
            if let Ok(existing_gate) = serde_yaml::from_str::<GateReport>(&content) {
                if existing_gate.decision != GateDecision::Pending {
                    println!(
                        "{} Existing gate report found: {}",
                        "ℹ".dimmed(),
                        format!("{}", existing_gate.decision).yellow()
                    );
                    println!("  Run with --re-inspect to force re-inspection.");
                    return;
                }
            }
        }
    }

    // ── Epic ID from decomposition ───────────────────────────
    let epic_id = decomposition
        .task_ids
        .values()
        .next()
        .map(|t| t.epic_id.clone())
        .unwrap_or_else(|| "unknown".to_string());

    // ── Step 1: Stream completeness ──────────────────────────
    println!("\n{}", "Step 1/4: Stream Completeness".bold());
    let completeness = inspect::completeness::check_all_streams(&decomposition, &grooming_state);
    inspect::completeness::print_completeness_report(&completeness);

    // ── Step 2: Role coverage ────────────────────────────────
    println!("\n{}", "Step 2/4: Role Coverage".bold());
    let role_coverage = inspect::role_coverage::check_all_streams(&decomposition);
    inspect::role_coverage::print_role_coverage_report(&role_coverage);

    // ── Step 3: Cross-impact analysis ───────────────────────
    println!("\n{}", "Step 3/4: Cross-Impact Analysis".bold());
    let cross_impact = inspect::cross_impact::check_cross_impact(&decomposition);
    inspect::cross_impact::print_cross_impact_report(&cross_impact);

    // ── Step 4: Gate report + human decision ─────────────────
    println!("\n{}", "Step 4/4: Gate Report".bold());
    let mut gate_report = inspect::gate_report::build_gate_report(
        completeness,
        role_coverage,
        cross_impact,
        &epic_id,
    );

    let decision = inspect::gate_report::present_gate_report(&gate_report);
    gate_report.decision = decision.clone();

    // Save gate report
    inspect::gate_report::save_gate_report(&gate_report);

    // Update br epic with gate decision
    update_br_epic(&epic_id, &gate_report);

    // Save inspection state
    let state = InspectionState {
        status: match decision {
            GateDecision::Approved | GateDecision::ApprovedWithOverrides => InspectionStatus::Approved,
            GateDecision::Rejected => InspectionStatus::Rejected,
            GateDecision::Pending => InspectionStatus::AwaitingApproval,
        },
        gate_report: Some(gate_report.clone()),
        timestamp: chrono::Utc::now().to_rfc3339(),
    };

    let state_yaml = serde_yaml::to_string(&state).unwrap_or_default();
    let _ = std::fs::write(".truss/_progress/inspection-state.yaml", &state_yaml);

    // Final message
    println!();
    match gate_report.decision {
        GateDecision::Approved => {
            println!(
                "{} Inspection gate approved. Next: `truss retro` (Phase 5) or begin execution.",
                "✓".green().bold()
            );
        }
        GateDecision::ApprovedWithOverrides => {
            println!(
                "{} Gate approved with {} override(s). Proceed with caution.",
                "!".yellow().bold(),
                gate_report.overrides.len()
            );
        }
        GateDecision::Rejected => {
            println!(
                "{} Gate rejected. Fix blocking issues and re-run `truss inspect`.",
                "✗".red().bold()
            );
            std::process::exit(1);
        }
        GateDecision::Pending => {
            println!(
                "{} Gate pending. Run `truss inspect` again to decide.",
                "⏳".dimmed()
            );
        }
    }
}

fn update_br_epic(epic_id: &str, gate_report: &GateReport) {
    if epic_id == "unknown" {
        return;
    }

    let notes = format!(
        "Inspection gate: {}\nDate: {}\nBlocking issues: {}\nOverrides: {}",
        gate_report.decision,
        &gate_report.timestamp[..10],
        gate_report.blocking_issues.len(),
        gate_report.overrides.len()
    );

    let _ = std::process::Command::new("bd")
        .arg("update")
        .arg(epic_id)
        .arg(format!("--notes={}", notes))
        .output();
}
