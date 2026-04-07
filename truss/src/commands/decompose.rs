use colored::Colorize;
use std::path::Path;

use crate::decompose;
use crate::models::decomposition::{DecompositionResult, ValidationReport, ValidationStatus};

/// Main decompose command entry point.
pub fn run(
    goal: &Path,
    domain: &str,
    codebase: Option<&Path>,
    greenfield: bool,
    approve: bool,
) {
    if approve {
        run_approve(goal, domain);
    } else {
        run_decompose(goal, domain, codebase, greenfield);
    }
}

fn run_approve(goal: &Path, domain: &str) {
    println!("{}", "truss decompose --approve".bold());
    println!("{}", "─".repeat(40));

    // Load pending decomposition
    let streams_path = Path::new(".truss/_progress/outputs/streams.yaml");
    if !streams_path.exists() {
        eprintln!(
            "{} No pending decomposition found at {}",
            "✗".red(),
            streams_path.display()
        );
        eprintln!("Run `truss decompose --goal <path> --domain <name>` first.");
        std::process::exit(1);
    }

    let content = match std::fs::read_to_string(streams_path) {
        Ok(c) => c,
        Err(e) => {
            eprintln!("{} Failed to read streams.yaml: {}", "✗".red(), e);
            std::process::exit(1);
        }
    };

    let mut result: DecompositionResult = match serde_yaml::from_str(&content) {
        Ok(r) => r,
        Err(e) => {
            eprintln!("{} Failed to parse streams.yaml: {}", "✗".red(), e);
            std::process::exit(1);
        }
    };

    if result.approved {
        eprintln!(
            "{} Decomposition already approved. Nothing to do.",
            "!".yellow()
        );
        return;
    }

    // Load context for validation
    let context = match decompose::init::run(goal, domain) {
        Ok(ctx) => ctx,
        Err(e) => {
            eprintln!("{} Failed to load context: {}", "✗".red(), e);
            std::process::exit(1);
        }
    };

    // Validate
    let report = crate::commands::verify::validate_decomposition(
        &result,
        context.max_streams,
        &context.default_roles,
    );

    if report.status == ValidationStatus::Fail {
        print_validation_report(&report);
        eprintln!(
            "\n{} Fix the issues above before approving.",
            "✗".red()
        );
        std::process::exit(1);
    }

    println!("{} Validation passed", "✓".green());

    // Create br tasks
    println!("\n{}", "Creating br tasks...".dimmed());
    if let Err(e) = decompose::streams::create_br_tasks(&mut result) {
        eprintln!("{} Failed to create br tasks: {}", "✗".red(), e);
    }

    // Mark approved
    result.approved = true;
    result.timestamp = chrono::Utc::now().to_rfc3339();

    // Write back
    let yaml = serde_yaml::to_string(&result).unwrap_or_default();
    if let Err(e) = std::fs::write(streams_path, &yaml) {
        eprintln!("{} Failed to write streams.yaml: {}", "✗".red(), e);
    }

    // Update state
    update_state("approved", &result);

    println!("\n{} Decomposition approved!", "✓".green().bold());
    println!("  Streams: {}", result.streams.len());
    for (name, ids) in &result.task_ids {
        println!(
            "  {} → epic: {}, features: {}",
            name,
            ids.epic_id,
            ids.feature_ids.join(", ")
        );
    }
    println!(
        "\nNext: grooming phase (truss groom — Phase 3)"
    );
}

fn run_decompose(goal: &Path, domain: &str, codebase: Option<&Path>, greenfield: bool) {
    println!("{}", "truss decompose".bold());
    println!("{}", "─".repeat(40));

    // ── Step 1: Init ───────────────────────────────────────
    println!("\n{}", "Step 1/3: Initialize".bold());
    let context = match decompose::init::run(goal, domain) {
        Ok(ctx) => {
            println!(
                "  {} Goal loaded ({} bytes)",
                "✓".green(),
                ctx.goal_text.len()
            );
            println!("  {} Domain '{}' validated", "✓".green(), ctx.domain_name);
            println!(
                "  {} Strategy: {}, max streams: {}",
                "✓".green(),
                ctx.strategy,
                ctx.max_streams
            );
            ctx
        }
        Err(e) => {
            eprintln!("  {} {}", "✗".red(), e);
            std::process::exit(1);
        }
    };

    update_state("step-01-init", &DecompositionResult {
        goal_summary: String::new(),
        streams: vec![],
        task_ids: std::collections::HashMap::new(),
        dependency_graph: vec![],
        max_parallelism: 0,
        critical_path_length: 0,
        approved: false,
        timestamp: chrono::Utc::now().to_rfc3339(),
    });

    // ── Step 2: Analyze ────────────────────────────────────
    println!("\n{}", "Step 2/3: Analyze codebase".bold());

    // Determine codebase path
    let effective_codebase = if greenfield {
        None
    } else if let Some(p) = codebase {
        Some(p.to_path_buf())
    } else if Path::new(".git").exists() {
        Some(std::env::current_dir().unwrap_or_else(|_| ".".into()))
    } else {
        None
    };

    let analysis = match decompose::analyze::run(
        &context,
        effective_codebase.as_deref(),
        greenfield || effective_codebase.is_none(),
    ) {
        Ok(a) => {
            if a.is_greenfield {
                println!(
                    "  {} Greenfield — {} synthetic clusters",
                    "✓".green(),
                    a.clusters.len()
                );
            } else {
                println!(
                    "  {} {} clusters, {} dependencies, {} shared files",
                    "✓".green(),
                    a.clusters.len(),
                    a.dependencies.len(),
                    a.shared_files.len()
                );
            }
            if !a.hot_spots.is_empty() {
                println!(
                    "  {} Hot spots: {}",
                    "ℹ".dimmed(),
                    a.hot_spots.iter().take(3).cloned().collect::<Vec<_>>().join(", ")
                );
            }
            a
        }
        Err(e) => {
            eprintln!("  {} {}", "✗".red(), e);
            std::process::exit(1);
        }
    };

    // Write analysis output
    let analysis_yaml = serde_yaml::to_string(&analysis).unwrap_or_default();
    let _ = std::fs::create_dir_all(".truss/_progress/outputs");
    let _ = std::fs::write(".truss/_progress/outputs/analysis.yaml", &analysis_yaml);

    // ── Step 3: Decompose ──────────────────────────────────
    println!("\n{}", "Step 3/3: Decompose into streams".bold());

    let result = match decompose::streams::run(&context, &analysis) {
        Ok(r) => r,
        Err(e) => {
            eprintln!("  {} {}", "✗".red(), e);
            std::process::exit(1);
        }
    };

    // Write streams output
    let streams_yaml = serde_yaml::to_string(&result).unwrap_or_default();
    let _ = std::fs::write(".truss/_progress/outputs/streams.yaml", &streams_yaml);

    // Print summary
    decompose::streams::print_summary(&result, &context);

    // Run validation inline
    let report = crate::commands::verify::validate_decomposition(
        &result,
        context.max_streams,
        &context.default_roles,
    );
    print_validation_report(&report);

    // Update state
    update_state("step-03-decompose", &result);

    // Halt for human approval
    println!();
    println!(
        "{}",
        "AWAITING APPROVAL".yellow().bold()
    );
    println!("Review the decomposition summary above.");
    println!(
        "To approve: {} {} {} {} {}",
        "truss decompose".bold(),
        "--goal".dimmed(),
        goal.display(),
        "--domain".dimmed(),
        domain
    );
    println!("            {}", "--approve".bold());
}

fn print_validation_report(report: &ValidationReport) {
    println!();
    println!("{}", "VALIDATION REPORT".bold());
    println!("{}", "─".repeat(40));

    let status_str = match report.status {
        ValidationStatus::Pass => "PASS".green().bold().to_string(),
        ValidationStatus::Fail => "FAIL".red().bold().to_string(),
    };
    println!("Status: {}", status_str);

    for check in &report.checks {
        let icon = if check.passed {
            "✓".green().to_string()
        } else {
            "✗".red().to_string()
        };
        println!("  {} {}: {}", icon, check.name, check.evidence);
        if let Some(ref rem) = check.remediation {
            println!("    → {}", rem.yellow());
        }
    }
}

fn update_state(step: &str, result: &DecompositionResult) {
    let state_path = Path::new(".truss/_progress/state.yaml");

    let mut streams_map = std::collections::HashMap::new();
    for stream in &result.streams {
        let status = if result.approved { "ready" } else { "pending" };
        streams_map.insert(stream.name.clone(), status.to_string());
    }

    let state = serde_yaml::Mapping::from_iter([
        (
            serde_yaml::Value::String("current_workflow".into()),
            serde_yaml::Value::String("decomposition".into()),
        ),
        (
            serde_yaml::Value::String("current_step".into()),
            serde_yaml::Value::String(step.into()),
        ),
        (
            serde_yaml::Value::String("streams".into()),
            serde_yaml::to_value(&streams_map).unwrap_or_default(),
        ),
    ]);

    let yaml = serde_yaml::to_string(&state).unwrap_or_default();
    let _ = std::fs::write(state_path, &yaml);
}
