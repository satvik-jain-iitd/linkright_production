use std::collections::HashMap;
use std::path::Path;

use crate::models::decomposition::{DecompositionResult, StreamBrief};
use crate::models::grooming::{
    FileContent, GroomingContext, StreamSummary,
};

const MAX_FILE_LINES: u32 = 500;

/// Step 1: Load all artifacts for a single stream's grooming workflow.
pub fn load_stream_context(
    stream: &StreamBrief,
    decomposition: &DecompositionResult,
    domain_dir: &Path,
    codebase_root: Option<&Path>,
) -> Result<GroomingContext, String> {
    // 1. Load role prompts
    let role_prompts = load_role_prompts(domain_dir)?;

    // 2. Read reserved code files
    let file_contents = read_reserved_files(
        &stream.reserved_files,
        codebase_root,
    );

    // 3. Build other stream summaries for cross-reference
    let other_streams: Vec<StreamSummary> = decomposition
        .streams
        .iter()
        .filter(|s| s.name != stream.name)
        .map(|s| StreamSummary {
            name: s.name.clone(),
            objective: s.objective.clone(),
            shared_files: s.shared_files.iter().map(|sf| sf.path.clone()).collect(),
        })
        .collect();

    // 4. Coordinator role from domain config
    let domain_config = crate::models::domain::DomainConfig::load(domain_dir)?;

    Ok(GroomingContext {
        stream_name: stream.name.clone(),
        stream_objective: stream.objective.clone(),
        scope_items: stream.scope.clone(),
        reserved_files: stream.reserved_files.clone(),
        shared_files: stream.shared_files.iter().map(|sf| sf.path.clone()).collect(),
        dependencies: stream.dependencies.clone(),
        file_contents,
        role_prompts,
        coordinator_role: domain_config.team.coordinator_role.clone(),
        goal_summary: decomposition.goal_summary.clone(),
        other_streams,
    })
}

/// Load all 4 role prompts from the domain's roles/ directory.
fn load_role_prompts(domain_dir: &Path) -> Result<HashMap<String, String>, String> {
    let roles_dir = domain_dir.join("roles");
    if !roles_dir.exists() {
        return Err(format!("Roles directory not found: {}", roles_dir.display()));
    }

    let expected_roles = ["po", "designer", "architect", "qa"];
    let mut prompts = HashMap::new();

    for role in &expected_roles {
        let path = roles_dir.join(format!("{}.md", role));
        match std::fs::read_to_string(&path) {
            Ok(content) => {
                prompts.insert(role.to_string(), content);
            }
            Err(e) => {
                return Err(format!(
                    "Failed to read role prompt {}: {}",
                    path.display(),
                    e
                ));
            }
        }
    }

    Ok(prompts)
}

/// Read reserved code files, returning FileContent structs.
/// Missing files are marked as greenfield (exists: false).
fn read_reserved_files(
    files: &[String],
    codebase_root: Option<&Path>,
) -> HashMap<String, FileContent> {
    let mut contents = HashMap::new();

    for file_path in files {
        let full_path = match codebase_root {
            Some(root) => root.join(file_path),
            None => Path::new(file_path).to_path_buf(),
        };

        let fc = if full_path.exists() {
            match std::fs::read_to_string(&full_path) {
                Ok(content) => {
                    let lines: Vec<&str> = content.lines().collect();
                    let line_count = lines.len() as u32;
                    let truncated = line_count > MAX_FILE_LINES;
                    let content_str = if truncated {
                        lines[..MAX_FILE_LINES as usize].join("\n")
                    } else {
                        content
                    };

                    FileContent {
                        path: file_path.clone(),
                        exists: true,
                        content: Some(content_str),
                        truncated,
                        line_count,
                    }
                }
                Err(_) => FileContent {
                    path: file_path.clone(),
                    exists: true,
                    content: None,
                    truncated: false,
                    line_count: 0,
                },
            }
        } else {
            FileContent {
                path: file_path.clone(),
                exists: false,
                content: None,
                truncated: false,
                line_count: 0,
            }
        };

        contents.insert(file_path.clone(), fc);
    }

    contents
}

/// Print a summary of loaded context for a stream.
pub fn print_context_summary(ctx: &GroomingContext) {
    use colored::Colorize;

    println!("  {} Stream: {}", "✓".green(), ctx.stream_name.bold());
    println!("    Objective: {}", ctx.stream_objective);
    println!("    Scope items: {}", ctx.scope_items.len());
    println!("    Reserved files: {}", ctx.reserved_files.len());

    let existing: usize = ctx.file_contents.values().filter(|fc| fc.exists).count();
    let greenfield: usize = ctx.file_contents.values().filter(|fc| !fc.exists).count();
    println!(
        "    Files loaded: {} existing, {} greenfield",
        existing, greenfield
    );

    println!("    Role prompts: {}", ctx.role_prompts.len());
    println!("    Dependencies: {}", if ctx.dependencies.is_empty() {
        "none".to_string()
    } else {
        ctx.dependencies.join(", ")
    });
    println!(
        "    Cross-ref streams: {}",
        ctx.other_streams.len()
    );
}
