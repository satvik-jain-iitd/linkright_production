use colored::Colorize;
use std::path::Path;

use crate::models::decomposition::DecompositionResult;
use crate::models::grooming::{GroomingState, GroomingStatus};

pub fn run(_run_id: Option<&str>) {
    println!("{}", "truss status".bold());
    println!("{}", "═".repeat(60));

    // ── Decomposition status ─────────────────────────────────
    let streams_path = Path::new(".truss/_progress/outputs/streams.yaml");
    if !streams_path.exists() {
        println!("Phase 2 (Decomposition): {}", "not started".dimmed());
        return;
    }

    let content = std::fs::read_to_string(streams_path).unwrap_or_default();
    let decomposition: Option<DecompositionResult> = serde_yaml::from_str(&content).ok();

    if let Some(ref d) = decomposition {
        let status = if d.approved {
            "approved".green().bold().to_string()
        } else {
            "pending approval".yellow().to_string()
        };
        println!("Phase 2 (Decomposition): {}", status);
        println!(
            "  {} streams, {} max parallelism",
            d.streams.len(),
            d.max_parallelism
        );
    } else {
        println!("Phase 2 (Decomposition): {}", "parse error".red());
    }

    // ── Grooming status ──────────────────────────────────────
    let grooming_path = Path::new(".truss/_progress/grooming-state.yaml");
    if !grooming_path.exists() {
        println!("\nPhase 3 (Grooming): {}", "not started".dimmed());
        return;
    }

    let groom_content = std::fs::read_to_string(grooming_path).unwrap_or_default();
    let grooming: Option<GroomingState> = serde_yaml::from_str(&groom_content).ok();

    if let Some(ref g) = grooming {
        let completed = g
            .streams
            .values()
            .filter(|s| s.status == GroomingStatus::Completed)
            .count();
        let in_progress = g
            .streams
            .values()
            .filter(|s| s.status == GroomingStatus::InProgress)
            .count();
        let blocked = g
            .streams
            .values()
            .filter(|s| s.status == GroomingStatus::Blocked)
            .count();
        let total = g.streams.len();

        println!(
            "\nPhase 3 (Grooming): {}/{} streams",
            completed, total
        );
        if in_progress > 0 {
            println!("  {} in progress", in_progress);
        }
        if blocked > 0 {
            println!("  {} blocked", blocked);
        }

        println!();
        println!(
            "{:<20} {:<14} {:<18} {:<10} {:<6}",
            "Stream", "Status", "Step", "Features", "Roles"
        );
        println!("{}", "─".repeat(60));

        for (name, ss) in &g.streams {
            let status_str = match ss.status {
                GroomingStatus::Pending => "pending".dimmed().to_string(),
                GroomingStatus::InProgress => "in_progress".yellow().to_string(),
                GroomingStatus::Blocked => "blocked".red().to_string(),
                GroomingStatus::Completed => "completed".green().to_string(),
                GroomingStatus::Failed => "failed".red().bold().to_string(),
            };

            println!(
                "{:<20} {:<14} {:<18} {:<10} {}/4",
                name,
                status_str,
                ss.current_step.replace("step-", ""),
                ss.features_identified,
                ss.roles_completed.len()
            );
        }
    } else {
        println!("\nPhase 3 (Grooming): {}", "parse error".red());
    }

    // ── Phases 4-5 ──────────────────────────────────────────
    println!("\nPhase 4 (Inspection): {}", "not started".dimmed());
    println!("Phase 5 (Retrospective): {}", "not started".dimmed());
}
