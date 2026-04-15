use colored::Colorize;
use std::path::Path;

use crate::models::grooming::{GroomingState, GroomingStatus};

pub fn run(stream: &str, role: Option<&str>) {
    println!("{}", format!("truss log {}", stream).bold());
    println!("{}", "─".repeat(40));

    // Load grooming state
    let state_path = Path::new(".truss/_progress/grooming-state.yaml");
    if !state_path.exists() {
        eprintln!("{} No grooming state found. Run `truss groom` first.", "✗".red());
        std::process::exit(1);
    }

    let content = std::fs::read_to_string(state_path).unwrap_or_default();
    let state: GroomingState = match serde_yaml::from_str(&content) {
        Ok(s) => s,
        Err(e) => {
            eprintln!("{} Failed to parse grooming state: {}", "✗".red(), e);
            std::process::exit(1);
        }
    };

    // Find the stream
    let stream_state = match state.streams.get(stream) {
        Some(s) => s,
        None => {
            eprintln!("{} Stream '{}' not found.", "✗".red(), stream);
            let available: Vec<&String> = state.streams.keys().collect();
            eprintln!("  Available: {}", available.iter().map(|s| s.as_str()).collect::<Vec<_>>().join(", "));
            std::process::exit(1);
        }
    };

    // Print stream status
    let status_str = match stream_state.status {
        GroomingStatus::Pending => "pending".dimmed().to_string(),
        GroomingStatus::InProgress => "in_progress".yellow().to_string(),
        GroomingStatus::Blocked => "BLOCKED".red().to_string(),
        GroomingStatus::Completed => "COMPLETED".green().bold().to_string(),
        GroomingStatus::Failed => "FAILED".red().bold().to_string(),
    };

    println!("Stream:  {}", stream.bold());
    println!("Status:  {}", status_str);
    println!("Step:    {}", stream_state.current_step);
    println!("Features: {}", stream_state.features_identified);
    println!(
        "Roles:   {}/4 ({})",
        stream_state.roles_completed.len(),
        if stream_state.roles_completed.is_empty() {
            "none".to_string()
        } else {
            stream_state.roles_completed.join(", ")
        }
    );
    println!(
        "Consolidated: {}",
        if stream_state.consolidated { "yes".green().to_string() } else { "no".dimmed().to_string() }
    );
    println!(
        "Verified:     {}",
        if stream_state.verified { "yes".green().to_string() } else { "no".dimmed().to_string() }
    );
    println!();

    // Role output file status
    let roles_to_show: Vec<&str> = if let Some(r) = role {
        vec![r]
    } else {
        vec!["po", "designer", "architect", "qa"]
    };

    println!("{}", "Role output files:".bold());
    for r in &roles_to_show {
        let role_path = format!(".truss/_progress/outputs/{}-role-{}.yaml", stream, r);
        let icon = if Path::new(&role_path).exists() { "✓".green() } else { "⏳".dimmed() };
        println!("  [{}] {}", icon, role_path);
    }

    // Artifact files
    println!();
    println!("{}", "Artifact files:".bold());
    print_file_status(&format!(".truss/_progress/outputs/{}-grooming-context.yaml", stream), "Context");
    print_file_status(&format!(".truss/_progress/outputs/{}-features.yaml", stream), "Features");
    print_file_status(&format!(".truss/_progress/outputs/{}-consolidated.yaml", stream), "Consolidated");

    // Consolidated summary if available
    let consolidated_path = format!(".truss/_progress/outputs/{}-consolidated.yaml", stream);
    if Path::new(&consolidated_path).exists() {
        if let Ok(c_content) = std::fs::read_to_string(&consolidated_path) {
            if let Ok(c) = serde_yaml::from_str::<crate::models::grooming::ConsolidatedGrooming>(&c_content) {
                println!();
                println!("{}", "Consolidated summary:".bold());
                println!(
                    "  {} features / {} stories / {} tasks",
                    c.summary.feature_count, c.summary.story_count, c.summary.task_count
                );
                println!(
                    "  Conflicts: {} found, {} resolved",
                    c.summary.conflicts_found, c.summary.conflicts_resolved
                );
                println!();
                println!("{}", "Features:".bold());
                for (i, f) in c.features.iter().enumerate() {
                    println!(
                        "  {}. [{}] {} — {} stories",
                        i + 1, f.priority, f.name, f.stories.len()
                    );
                }
            }
        }
    }
}

fn print_file_status(path: &str, label: &str) {
    let exists = Path::new(path).exists();
    let (icon, size_str) = if exists {
        let size = std::fs::metadata(path)
            .map(|m| format!("({} bytes)", m.len()))
            .unwrap_or_default();
        ("✓".green().to_string(), size)
    } else {
        ("⏳".dimmed().to_string(), "not yet".to_string())
    };
    println!("  [{}] {}: {}", icon, label, size_str);
}
