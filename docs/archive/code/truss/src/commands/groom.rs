use colored::Colorize;
use std::collections::HashMap;
use std::path::Path;

use crate::groom;
use crate::models::decomposition::DecompositionResult;
use crate::models::grooming::{
    GroomingState, StreamGroomingState, GroomingStatus,
    GroomingContext, FeatureList, ConsolidatedGrooming,
    GroomingValidationStatus,
};

/// Entry point for `truss groom`.
pub fn run(
    stream_filter: Option<&str>,
    step_filter: Option<&str>,
    codebase: Option<&Path>,
    output_context: bool,
) {
    println!("{}", "truss groom".bold());
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

    let content = match std::fs::read_to_string(streams_path) {
        Ok(c) => c,
        Err(e) => {
            eprintln!("{} Failed to read streams.yaml: {}", "✗".red(), e);
            std::process::exit(1);
        }
    };

    let decomposition: DecompositionResult = match serde_yaml::from_str(&content) {
        Ok(r) => r,
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

    // ── Determine domain ─────────────────────────────────────
    let domain_dir = dirs::home_dir()
        .expect("home dir")
        .join(".truss/domains/bmad-dev");

    if !domain_dir.exists() {
        eprintln!("{} Domain 'bmad-dev' not found", "✗".red());
        std::process::exit(1);
    }

    // ── Filter streams ───────────────────────────────────────
    let streams_to_groom: Vec<_> = if let Some(filter) = stream_filter {
        decomposition
            .streams
            .iter()
            .filter(|s| s.name == filter)
            .collect()
    } else {
        decomposition.streams.iter().collect()
    };

    if streams_to_groom.is_empty() {
        eprintln!(
            "{} No streams match filter '{}'",
            "✗".red(),
            stream_filter.unwrap_or("*")
        );
        std::process::exit(1);
    }

    // ── Load or initialize grooming state ────────────────────
    let mut state = load_or_init_state(&decomposition);

    // ── Resolve codebase path ────────────────────────────────
    let effective_codebase = codebase.map(|p| p.to_path_buf()).or_else(|| {
        if Path::new(".git").exists() {
            Some(std::env::current_dir().unwrap_or_else(|_| ".".into()))
        } else {
            None
        }
    });

    // ── Determine execution order (topological) ──────────────
    let order = topological_stream_order(&decomposition);
    println!(
        "\n{} Grooming order: {}",
        "ℹ".dimmed(),
        order.join(" → ")
    );

    let filtered_order: Vec<&str> = order
        .iter()
        .filter(|name| streams_to_groom.iter().any(|s| &s.name == *name))
        .map(|s| s.as_str())
        .collect();

    // ── Process each stream ──────────────────────────────────
    for stream_name in &filtered_order {
        let stream = decomposition
            .streams
            .iter()
            .find(|s| s.name == *stream_name)
            .unwrap();

        println!("\n{}", format!("STREAM: {}", stream_name).bold());
        println!("{}", "─".repeat(40));

        // Check dependency readiness
        let blocked_by = check_dependencies(stream, &state);
        if !blocked_by.is_empty() {
            println!(
                "  {} Blocked by: {}",
                "!".yellow(),
                blocked_by.join(", ")
            );
            state.streams.get_mut(*stream_name).unwrap().status = GroomingStatus::Blocked;
            save_state(&state);
            continue;
        }

        // Update state: in_progress
        if let Some(ss) = state.streams.get_mut(*stream_name) {
            ss.status = GroomingStatus::InProgress;
        }
        save_state(&state);

        // Determine which step to run (or all)
        let step = step_filter.unwrap_or("all");

        match step {
            "1" | "read-artifacts" | "all" => {
                println!("\n{}", "Step 1/5: Read Artifacts".bold());
                match groom::context::load_stream_context(
                    stream,
                    &decomposition,
                    &domain_dir,
                    effective_codebase.as_deref(),
                ) {
                    Ok(ctx) => {
                        groom::context::print_context_summary(&ctx);

                        if let Some(ss) = state.streams.get_mut(*stream_name) {
                            ss.current_step = "step-01-read-artifacts".to_string();
                        }
                        save_state(&state);

                        // Write context to output file for Claude skill layer
                        let ctx_path = format!(
                            ".truss/_progress/outputs/{}-grooming-context.yaml",
                            stream_name
                        );
                        let ctx_yaml = serde_yaml::to_string(&ctx).unwrap_or_default();
                        let _ = std::fs::write(&ctx_path, &ctx_yaml);
                        println!("  {} Context saved: {}", "✓".green(), ctx_path);

                        if output_context {
                            print_coordinator_prompt(&ctx);
                        }

                        if step != "all" {
                            continue;
                        }
                    }
                    Err(e) => {
                        eprintln!("  {} {}", "✗".red(), e);
                        if let Some(ss) = state.streams.get_mut(*stream_name) {
                            ss.status = GroomingStatus::Failed;
                        }
                        save_state(&state);
                        continue;
                    }
                }
            }
            _ => {}
        }

        match step {
            "2" | "identify-features" | "all" => {
                println!("\n{}", "Step 2/5: Identify Features".bold());
                println!(
                    "  {} This step runs in the Claude skill layer",
                    "ℹ".dimmed()
                );
                println!("  The coordinator agent will:");
                println!("  1. Extract scope items from stream brief");
                println!("  2. Group into features with priorities");
                println!("  3. Write stories with acceptance criteria");
                println!("  4. Validate coverage and priority distribution");
                println!();
                println!(
                    "  Output file: .truss/_progress/outputs/{}-features.yaml",
                    stream_name
                );

                // Check if features file already exists (resume scenario)
                let features_path = format!(
                    ".truss/_progress/outputs/{}-features.yaml",
                    stream_name
                );
                if Path::new(&features_path).exists() {
                    match load_features(&features_path) {
                        Ok(features) => {
                            groom::features::print_feature_summary(&features);
                            let issues = groom::features::validate_features(&features);
                            if issues.is_empty() {
                                println!("  {} Features validated", "✓".green());
                            } else {
                                for issue in &issues {
                                    println!("  {} {}", "!".yellow(), issue);
                                }
                            }

                            if let Some(ss) = state.streams.get_mut(*stream_name) {
                                ss.current_step = "step-02-identify-features".to_string();
                                ss.features_identified = features.features.len() as u32;
                            }
                            save_state(&state);
                        }
                        Err(e) => {
                            println!("  {} Failed to load features: {}", "!".yellow(), e);
                        }
                    }
                } else {
                    println!(
                        "  {} Awaiting Claude skill layer to produce features",
                        "⏳".dimmed()
                    );
                    if let Some(ss) = state.streams.get_mut(*stream_name) {
                        ss.current_step = "step-02-identify-features".to_string();
                    }
                    save_state(&state);

                    if step != "all" {
                        continue;
                    }
                }
            }
            _ => {}
        }

        match step {
            "3" | "spawn-roles" | "all" => {
                println!("\n{}", "Step 3/5: Spawn Role Sub-Agents".bold());
                println!(
                    "  {} This step spawns 4 parallel agents via the Claude skill layer",
                    "ℹ".dimmed()
                );
                println!("  Roles: PO, Designer, Architect, QA");
                println!("  Mode: parallel, isolated context per role");
                println!("  Coordination: mcp_agent_mail inboxes");
                println!();

                // Print expected inbox names
                println!("  AgentMail inboxes:");
                for role in &["po", "designer", "architect", "qa"] {
                    println!(
                        "    truss-bmad-{}-{}",
                        stream_name, role
                    );
                }

                // Check for existing role outputs
                let roles = ["po", "designer", "architect", "qa"];
                let mut completed_roles = Vec::new();
                for role in &roles {
                    let role_path = format!(
                        ".truss/_progress/outputs/{}-role-{}.yaml",
                        stream_name, role
                    );
                    if Path::new(&role_path).exists() {
                        completed_roles.push(role.to_string());
                    }
                }

                if completed_roles.len() == 4 {
                    println!("  {} All 4 roles completed", "✓".green());
                } else if completed_roles.is_empty() {
                    println!(
                        "  {} Awaiting role sub-agent outputs",
                        "⏳".dimmed()
                    );
                } else {
                    println!(
                        "  {} {}/4 roles completed: {}",
                        "…".yellow(),
                        completed_roles.len(),
                        completed_roles.join(", ")
                    );
                }

                if let Some(ss) = state.streams.get_mut(*stream_name) {
                    ss.current_step = "step-03-spawn-roles".to_string();
                    ss.roles_completed = completed_roles;
                }
                save_state(&state);
            }
            _ => {}
        }

        match step {
            "4" | "consolidate" | "all" => {
                println!("\n{}", "Step 4/5: Consolidate".bold());
                println!(
                    "  {} Consolidation runs in the Claude skill layer",
                    "ℹ".dimmed()
                );
                println!("  Architect role coordinates conflict resolution");
                println!("  Creates unified br task hierarchy");
                println!();
                println!(
                    "  Output: .truss/_progress/outputs/{}-consolidated.yaml",
                    stream_name
                );

                let consolidated_path = format!(
                    ".truss/_progress/outputs/{}-consolidated.yaml",
                    stream_name
                );
                if Path::new(&consolidated_path).exists() {
                    match load_consolidated(&consolidated_path) {
                        Ok(consolidated) => {
                            print_consolidation_summary(&consolidated);
                            if let Some(ss) = state.streams.get_mut(*stream_name) {
                                ss.current_step = "step-04-consolidate".to_string();
                                ss.consolidated = true;
                            }
                            save_state(&state);
                        }
                        Err(e) => {
                            println!("  {} Failed to load: {}", "!".yellow(), e);
                        }
                    }
                } else {
                    println!(
                        "  {} Awaiting consolidation",
                        "⏳".dimmed()
                    );
                }
            }
            _ => {}
        }

        match step {
            "5" | "verify" | "all" => {
                println!("\n{}", "Step 5/5: Verify".bold());

                let consolidated_path = format!(
                    ".truss/_progress/outputs/{}-consolidated.yaml",
                    stream_name
                );
                if Path::new(&consolidated_path).exists() {
                    match load_consolidated(&consolidated_path) {
                        Ok(consolidated) => {
                            let report = groom::validate::validate_grooming(&consolidated);
                            groom::validate::print_validation_report(&report);

                            let passed = report.status == GroomingValidationStatus::Pass;
                            if let Some(ss) = state.streams.get_mut(*stream_name) {
                                ss.current_step = "step-05-verify".to_string();
                                ss.verified = passed;
                                ss.status = if passed {
                                    GroomingStatus::Completed
                                } else {
                                    GroomingStatus::InProgress
                                };
                            }
                            save_state(&state);
                        }
                        Err(e) => {
                            println!("  {} No consolidated output to verify: {}", "!".yellow(), e);
                        }
                    }
                } else {
                    println!(
                        "  {} Complete step 4 first",
                        "⏳".dimmed()
                    );
                }
            }
            _ => {}
        }
    }

    // ── Print dashboard ──────────────────────────────────────
    println!();
    print_dashboard(&state);
}

// ── Helpers ──────────────────────────────────────────────────

fn load_or_init_state(decomposition: &DecompositionResult) -> GroomingState {
    let state_path = Path::new(".truss/_progress/grooming-state.yaml");
    if state_path.exists() {
        if let Ok(content) = std::fs::read_to_string(state_path) {
            if let Ok(state) = serde_yaml::from_str::<GroomingState>(&content) {
                return state;
            }
        }
    }

    let mut streams = HashMap::new();
    for stream in &decomposition.streams {
        streams.insert(
            stream.name.clone(),
            StreamGroomingState {
                status: GroomingStatus::Pending,
                current_step: "not_started".to_string(),
                features_identified: 0,
                roles_completed: vec![],
                consolidated: false,
                verified: false,
            },
        );
    }

    GroomingState {
        current_workflow: "grooming".to_string(),
        streams,
        timestamp: chrono::Utc::now().to_rfc3339(),
    }
}

fn save_state(state: &GroomingState) {
    let state_path = Path::new(".truss/_progress/grooming-state.yaml");
    let yaml = serde_yaml::to_string(state).unwrap_or_default();
    let _ = std::fs::write(state_path, &yaml);
}

fn check_dependencies(
    stream: &crate::models::decomposition::StreamBrief,
    state: &GroomingState,
) -> Vec<String> {
    let mut blocked_by = Vec::new();
    for dep in &stream.dependencies {
        if let Some(dep_state) = state.streams.get(dep) {
            if dep_state.status != GroomingStatus::Completed {
                blocked_by.push(dep.clone());
            }
        }
    }
    blocked_by
}

fn topological_stream_order(decomposition: &DecompositionResult) -> Vec<String> {
    // Simple topological sort using Kahn's algorithm
    let mut in_degree: HashMap<String, usize> = HashMap::new();
    let mut adj: HashMap<String, Vec<String>> = HashMap::new();

    for stream in &decomposition.streams {
        in_degree.entry(stream.name.clone()).or_insert(0);
        adj.entry(stream.name.clone()).or_default();
    }

    for (from, to) in &decomposition.dependency_graph {
        *in_degree.entry(to.clone()).or_insert(0) += 1;
        adj.entry(from.clone()).or_default().push(to.clone());
    }

    let mut queue: Vec<String> = in_degree
        .iter()
        .filter(|(_, &deg)| deg == 0)
        .map(|(name, _)| name.clone())
        .collect();
    queue.sort();

    let mut order = Vec::new();
    while let Some(node) = queue.pop() {
        order.push(node.clone());
        if let Some(neighbors) = adj.get(&node) {
            for neighbor in neighbors {
                if let Some(deg) = in_degree.get_mut(neighbor) {
                    *deg -= 1;
                    if *deg == 0 {
                        queue.push(neighbor.clone());
                        queue.sort();
                    }
                }
            }
        }
    }

    // If cycle exists, add remaining streams at end
    for stream in &decomposition.streams {
        if !order.contains(&stream.name) {
            order.push(stream.name.clone());
        }
    }

    order
}

fn load_features(path: &str) -> Result<FeatureList, String> {
    let content = std::fs::read_to_string(path)
        .map_err(|e| format!("Failed to read: {}", e))?;
    serde_yaml::from_str(&content)
        .map_err(|e| format!("Failed to parse: {}", e))
}

fn load_consolidated(path: &str) -> Result<ConsolidatedGrooming, String> {
    let content = std::fs::read_to_string(path)
        .map_err(|e| format!("Failed to read: {}", e))?;
    serde_yaml::from_str(&content)
        .map_err(|e| format!("Failed to parse: {}", e))
}

fn print_consolidation_summary(consolidated: &ConsolidatedGrooming) {
    println!(
        "  {} features, {} stories, {} tasks",
        consolidated.summary.feature_count,
        consolidated.summary.story_count,
        consolidated.summary.task_count,
    );
    println!(
        "  Conflicts: {} found, {} resolved",
        consolidated.summary.conflicts_found,
        consolidated.summary.conflicts_resolved,
    );
}

fn print_dashboard(state: &GroomingState) {
    println!("{}", "GROOMING DASHBOARD".bold());
    println!("{}", "═".repeat(60));
    println!(
        "{:<20} {:<14} {:<12} {:<10} {:<6}",
        "Stream", "Status", "Step", "Features", "Roles"
    );
    println!("{}", "─".repeat(60));

    for (name, ss) in &state.streams {
        let status_str = match ss.status {
            GroomingStatus::Pending => "pending".dimmed().to_string(),
            GroomingStatus::InProgress => "in_progress".yellow().to_string(),
            GroomingStatus::Blocked => "blocked".red().to_string(),
            GroomingStatus::Completed => "completed".green().to_string(),
            GroomingStatus::Failed => "failed".red().bold().to_string(),
        };

        let step_short = ss
            .current_step
            .replace("step-", "")
            .replace("not_started", "—");

        println!(
            "{:<20} {:<14} {:<12} {:<10} {}/4",
            name,
            status_str,
            step_short,
            ss.features_identified,
            ss.roles_completed.len()
        );
    }

    let completed = state
        .streams
        .values()
        .filter(|s| s.status == GroomingStatus::Completed)
        .count();
    let total = state.streams.len();

    println!();
    println!("Progress: {}/{} streams groomed", completed, total);

    if completed == total && total > 0 {
        println!(
            "\n{}",
            "All streams groomed! Next: truss inspect (Phase 4)".green().bold()
        );
    }
}

/// Print the coordinator prompt that the Claude skill layer will use.
fn print_coordinator_prompt(ctx: &GroomingContext) {
    println!();
    println!("{}", "COORDINATOR PROMPT".bold());
    println!("{}", "═".repeat(60));
    println!("Stream: {}", ctx.stream_name);
    println!("Objective: {}", ctx.stream_objective);
    println!("Goal: {}", ctx.goal_summary);
    println!();
    println!("Scope items ({}):", ctx.scope_items.len());
    for (i, item) in ctx.scope_items.iter().enumerate() {
        println!("  {}. {}", i + 1, item);
    }
    println!();
    println!("File status:");
    for (path, fc) in &ctx.file_contents {
        let status = if fc.exists {
            format!("{} lines{}", fc.line_count, if fc.truncated { " (truncated)" } else { "" })
        } else {
            "greenfield".to_string()
        };
        println!("  {} — {}", path, status);
    }
    println!();
    println!("Dependencies: {}", if ctx.dependencies.is_empty() {
        "none".to_string()
    } else {
        ctx.dependencies.join(", ")
    });
    println!("Coordinator: {}", ctx.coordinator_role);
    println!("Roles loaded: {}", ctx.role_prompts.keys().cloned().collect::<Vec<_>>().join(", "));
    println!();
    println!("Cross-reference streams:");
    for other in &ctx.other_streams {
        println!("  - {} — {}", other.name, other.objective);
    }
    println!("{}", "═".repeat(60));
}
