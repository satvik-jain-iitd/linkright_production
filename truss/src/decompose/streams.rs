use colored::Colorize;
use std::collections::HashMap;

use crate::analysis::graph;
use crate::models::decomposition::*;

/// Step 3: Map clusters to streams, generate briefs, produce DecompositionResult.
pub fn run(
    context: &ContextBundle,
    analysis: &CodeAnalysis,
) -> Result<DecompositionResult, String> {
    // 1. Map clusters to stream briefs
    let streams = clusters_to_streams(&analysis.clusters, &analysis.dependencies, context);

    // 2. Build dependency graph edges from cluster deps
    let dep_edges: Vec<(String, String)> = analysis
        .dependencies
        .iter()
        .map(|d| (d.from_cluster.clone(), d.to_cluster.clone()))
        .collect();

    // 3. Compute graph metrics
    let (dep_graph, index_map) = graph::build_dependency_graph(&analysis.dependencies);
    let crit_path = graph::critical_path_length(&dep_graph);
    let max_par = graph::max_parallelism(&dep_graph, &index_map);

    // 4. Generate goal summary (first meaningful line of goal text)
    let goal_summary = context
        .goal_text
        .lines()
        .find(|l| {
            let t = l.trim();
            !t.is_empty() && !t.starts_with('#')
        })
        .unwrap_or(&context.goal_text)
        .trim()
        .chars()
        .take(200)
        .collect::<String>();

    let result = DecompositionResult {
        goal_summary,
        streams,
        task_ids: HashMap::new(),
        dependency_graph: dep_edges,
        max_parallelism: max_par.max(1),
        critical_path_length: crit_path,
        approved: false,
        timestamp: chrono::Utc::now().to_rfc3339(),
    };

    Ok(result)
}

/// Print the decomposition summary to stdout.
pub fn print_summary(result: &DecompositionResult, context: &ContextBundle) {
    println!();
    println!("{}", "DECOMPOSITION SUMMARY".bold());
    println!("{}", "═".repeat(60));
    println!("Goal: {}", result.goal_summary);
    println!("Streams: {}", result.streams.len());
    println!("Max parallelism: {}", result.max_parallelism);
    println!("Critical path: {} steps", result.critical_path_length);
    println!();

    println!("{}", "STREAMS:".bold());
    for (i, stream) in result.streams.iter().enumerate() {
        println!(
            "  {}. {} — {}",
            i + 1,
            stream.name.bold(),
            stream.objective
        );
        println!(
            "     Files: {} reserved, {} shared",
            stream.reserved_files.len(),
            stream.shared_files.len()
        );
        if stream.dependencies.is_empty() {
            println!("     Depends on: {}", "none".dimmed());
        } else {
            println!("     Depends on: {}", stream.dependencies.join(", "));
        }
        println!();
    }

    // Shared files
    let total_shared: usize = result.streams.iter().map(|s| s.shared_files.len()).sum();
    if total_shared > 0 {
        println!("{}", format!("SHARED FILES ({}):", total_shared).bold());
        for stream in &result.streams {
            for sf in &stream.shared_files {
                println!(
                    "  - {}: owned by {}, needed by {}",
                    sf.path, sf.owned_by, stream.name
                );
            }
        }
        println!();
    }

    // Roles
    println!("Roles per stream: {}", context.default_roles.join(", "));
    println!();
}

/// Create br tasks: 1 epic for the goal, 1 feature per stream.
pub fn create_br_tasks(result: &mut DecompositionResult) -> Result<(), String> {
    // Create epic
    let epic_output = std::process::Command::new("bd")
        .arg("create")
        .arg("--type=epic")
        .arg(format!("--title=Truss: {}", truncate(&result.goal_summary, 80)))
        .arg(format!(
            "--description={} streams, {} max parallelism",
            result.streams.len(),
            result.max_parallelism
        ))
        .arg("--priority=1")
        .output();

    let epic_id = match epic_output {
        Ok(o) if o.status.success() => {
            let stdout = String::from_utf8_lossy(&o.stdout);
            parse_bd_id(&stdout).unwrap_or_else(|| "unknown".to_string())
        }
        Ok(o) => {
            let stderr = String::from_utf8_lossy(&o.stderr);
            eprintln!("  {} bd create epic failed: {}", "!".yellow(), stderr.trim());
            "unknown".to_string()
        }
        Err(e) => {
            eprintln!("  {} bd not found: {}", "!".yellow(), e);
            "unknown".to_string()
        }
    };

    // Create feature per stream
    for stream in &result.streams {
        let feature_output = std::process::Command::new("bd")
            .arg("create")
            .arg("--type=feature")
            .arg(format!("--title=Stream: {}", stream.name))
            .arg(format!("--parent={}", epic_id))
            .arg(format!(
                "--description={}. Files: {}. Dependencies: {}.",
                stream.objective,
                stream.reserved_files.len(),
                if stream.dependencies.is_empty() {
                    "none".to_string()
                } else {
                    stream.dependencies.join(", ")
                }
            ))
            .arg("--priority=2")
            .output();

        let feature_id = match feature_output {
            Ok(o) if o.status.success() => {
                let stdout = String::from_utf8_lossy(&o.stdout);
                parse_bd_id(&stdout).unwrap_or_else(|| "unknown".to_string())
            }
            _ => "unknown".to_string(),
        };

        result
            .task_ids
            .entry(stream.name.clone())
            .or_insert_with(TaskIds::default)
            .epic_id = epic_id.clone();
        result
            .task_ids
            .entry(stream.name.clone())
            .or_default()
            .feature_ids
            .push(feature_id);
    }

    Ok(())
}

// ── Internal helpers ───────────────────────────────────────

fn clusters_to_streams(
    clusters: &[FileCluster],
    dependencies: &[ClusterDependency],
    context: &ContextBundle,
) -> Vec<StreamBrief> {
    // For greenfield, extract scope items from goal text sections
    let goal_sections = parse_goal_sections(&context.goal_text);

    clusters
        .iter()
        .map(|cluster| {
            let shared_files: Vec<StreamSharedFile> = vec![];

            let deps: Vec<String> = dependencies
                .iter()
                .filter(|d| d.from_cluster == cluster.name)
                .map(|d| d.to_cluster.clone())
                .collect();

            let roles: HashMap<String, String> = context
                .default_roles
                .iter()
                .map(|role| {
                    (
                        role.clone(),
                        format!("{} responsibilities for {}", role, cluster.name),
                    )
                })
                .collect();

            // Scope: from files if available, else from goal text sections
            let scope = if !cluster.files.is_empty() {
                cluster
                    .files
                    .iter()
                    .take(10)
                    .map(|f| format!("Modify/create {}", f))
                    .collect()
            } else {
                // Greenfield: find matching section in goal text
                goal_sections
                    .get(&cluster.name)
                    .cloned()
                    .unwrap_or_else(|| vec![format!("Define and implement {}", cluster.name)])
            };

            let objective = if cluster.files.is_empty() {
                format!("Design and implement {}", cluster.name)
            } else {
                format!("Implement {} ({} files)", cluster.name, cluster.files.len())
            };

            StreamBrief {
                name: cluster.name.clone(),
                objective,
                scope,
                out_of_scope: vec![],
                reserved_files: cluster.files.clone(),
                shared_files,
                dependencies: deps,
                roles,
            }
        })
        .collect()
}

/// Parse goal document into section name (slugified) → bullet items.
fn parse_goal_sections(goal_text: &str) -> HashMap<String, Vec<String>> {
    let mut sections: HashMap<String, Vec<String>> = HashMap::new();
    let mut current_slug: Option<String> = None;

    for line in goal_text.lines() {
        let trimmed = line.trim();
        if trimmed.starts_with("## ") {
            let heading = trimmed.trim_start_matches('#').trim();
            let slug = heading
                .to_lowercase()
                .chars()
                .map(|c| if c.is_alphanumeric() || c == '-' { c } else { '-' })
                .collect::<String>()
                .split('-')
                .filter(|s| !s.is_empty())
                .collect::<Vec<_>>()
                .join("-");
            current_slug = Some(slug);
        } else if let Some(ref slug) = current_slug {
            if trimmed.starts_with("- ") {
                sections
                    .entry(slug.clone())
                    .or_default()
                    .push(trimmed.trim_start_matches("- ").to_string());
            }
        }
    }

    sections
}

/// Parse a bd issue ID from bd create output.
/// Expected format: "Created issue: LR-xxx — ..."
fn parse_bd_id(output: &str) -> Option<String> {
    for line in output.lines() {
        if let Some(rest) = line.strip_prefix("✓ Created issue: ") {
            if let Some(id) = rest.split_whitespace().next() {
                return Some(id.to_string());
            }
        }
        // Also try without checkmark
        if let Some(rest) = line.strip_prefix("Created issue: ") {
            if let Some(id) = rest.split_whitespace().next() {
                return Some(id.to_string());
            }
        }
    }
    None
}

fn truncate(s: &str, max: usize) -> String {
    if s.len() <= max {
        s.to_string()
    } else {
        format!("{}...", &s[..max - 3])
    }
}
