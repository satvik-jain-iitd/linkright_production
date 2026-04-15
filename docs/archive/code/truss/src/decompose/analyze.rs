use colored::Colorize;
use std::collections::HashMap;
use std::path::Path;

use crate::analysis::{clustering, gitnexus};
use crate::models::decomposition::{CodeAnalysis, ContextBundle};

/// Step 2: Run code analysis — GitNexus for existing codebases, synthetic for greenfield.
pub fn run(
    context: &ContextBundle,
    codebase_path: Option<&Path>,
    is_greenfield: bool,
) -> Result<CodeAnalysis, String> {
    // Greenfield path: no codebase analysis
    if is_greenfield || codebase_path.is_none() {
        return run_greenfield(context);
    }

    let repo_path = codebase_path.unwrap();

    // Check gitnexus availability
    if !gitnexus::is_available() {
        eprintln!(
            "  {} gitnexus not found — falling back to directory-based clustering",
            "!".yellow()
        );
        return run_directory_fallback(repo_path, context);
    }

    // Ensure repo is indexed
    if !gitnexus::is_indexed(repo_path) {
        eprintln!("  {} Indexing codebase (this may take a minute)...", "…".dimmed());
        gitnexus::analyze(repo_path)?;
    }

    // Resolve repo name for cypher queries
    let repo_name = gitnexus::resolve_repo_name(repo_path)?;

    // Run GitNexus queries (log errors, continue with defaults)
    let communities = gitnexus::query_communities(&repo_name).unwrap_or_else(|e| {
        eprintln!("  {} query_communities: {}", "!".yellow(), e);
        vec![]
    });
    let community_files = gitnexus::query_community_files(&repo_name).unwrap_or_else(|e| {
        eprintln!("  {} query_community_files: {}", "!".yellow(), e);
        HashMap::new()
    });
    let imports = gitnexus::query_file_imports(&repo_name).unwrap_or_else(|e| {
        eprintln!("  {} query_file_imports: {}", "!".yellow(), e);
        vec![]
    });
    let cross_edges = gitnexus::query_cross_community_edges(&repo_name).unwrap_or_else(|e| {
        eprintln!("  {} query_cross_community_edges: {}", "!".yellow(), e);
        vec![]
    });
    let hot_spots = gitnexus::query_hot_spots(&repo_name).unwrap_or_else(|e| {
        eprintln!("  {} query_hot_spots: {}", "!".yellow(), e);
        vec![]
    });

    eprintln!(
        "  {} KG: {} communities, {} community-file maps, {} imports, {} cross-edges",
        "ℹ".dimmed(),
        communities.len(),
        community_files.len(),
        imports.len(),
        cross_edges.len()
    );

    if communities.is_empty() {
        eprintln!(
            "  {} No communities found in KG — falling back to directory-based clustering",
            "!".yellow()
        );
        return run_directory_fallback(repo_path, context);
    }

    // Build file list from community memberships + directory scan for orphans
    let mut all_files: Vec<String> = community_files
        .values()
        .flat_map(|files| files.iter().cloned())
        .collect::<std::collections::HashSet<String>>()
        .into_iter()
        .collect();

    // Add files from directory scan that aren't in any community
    if let Ok(dir_files) = collect_source_files(repo_path) {
        for f in dir_files {
            if !all_files.contains(&f) {
                all_files.push(f);
            }
        }
    }

    // Build clusters from communities + imports
    let clusters = clustering::build_clusters(
        &communities,
        &community_files,
        &all_files,
        &imports,
        context.max_streams,
    );

    // Build community → cluster name mapping
    let community_to_cluster = build_community_cluster_map(&communities, &community_files, &clusters);

    // Build dependencies from cross-community edges
    let dependencies =
        clustering::build_cluster_dependencies(&clusters, &community_to_cluster, &cross_edges);

    // Find shared files
    let shared_files = crate::analysis::graph::find_shared_files(&clusters);

    Ok(CodeAnalysis {
        clusters,
        dependencies,
        shared_files,
        hot_spots,
        is_greenfield: false,
        repo_path: Some(repo_path.to_path_buf()),
    })
}

/// Greenfield: parse goal text headings into synthetic clusters.
fn run_greenfield(context: &ContextBundle) -> Result<CodeAnalysis, String> {
    let clusters = clustering::build_greenfield_clusters(&context.goal_text);

    Ok(CodeAnalysis {
        clusters,
        dependencies: vec![],
        shared_files: vec![],
        hot_spots: vec![],
        is_greenfield: true,
        repo_path: None,
    })
}

/// Fallback: group files by directory when GitNexus is unavailable.
fn run_directory_fallback(
    repo_path: &Path,
    context: &ContextBundle,
) -> Result<CodeAnalysis, String> {
    let all_files = collect_source_files(repo_path)?;

    // Use empty communities/imports — clustering will rely on directory grouping
    let clusters = clustering::build_clusters(
        &[],
        &HashMap::new(),
        &all_files,
        &[],
        context.max_streams,
    );

    let shared_files = crate::analysis::graph::find_shared_files(&clusters);

    Ok(CodeAnalysis {
        clusters,
        dependencies: vec![],
        shared_files,
        hot_spots: vec![],
        is_greenfield: false,
        repo_path: Some(repo_path.to_path_buf()),
    })
}

/// Walk the directory tree to collect source file paths (relative to repo root).
fn collect_source_files(root: &Path) -> Result<Vec<String>, String> {
    let mut files = Vec::new();
    collect_files_recursive(root, root, &mut files)?;
    Ok(files)
}

fn collect_files_recursive(
    dir: &Path,
    root: &Path,
    files: &mut Vec<String>,
) -> Result<(), String> {
    let entries = std::fs::read_dir(dir)
        .map_err(|e| format!("Failed to read directory {}: {}", dir.display(), e))?;

    for entry in entries.flatten() {
        let path = entry.path();
        let name = entry.file_name().to_string_lossy().to_string();

        // Skip hidden dirs, build artifacts, node_modules, etc.
        if name.starts_with('.')
            || name == "node_modules"
            || name == "target"
            || name == "dist"
            || name == "build"
            || name == "__pycache__"
        {
            continue;
        }

        if path.is_dir() {
            collect_files_recursive(&path, root, files)?;
        } else if is_source_file(&name) {
            let relative = path
                .strip_prefix(root)
                .unwrap_or(&path)
                .to_string_lossy()
                .to_string();
            files.push(relative);
        }
    }

    Ok(())
}

fn is_source_file(name: &str) -> bool {
    let extensions = [
        "rs", "py", "ts", "tsx", "js", "jsx", "go", "java", "rb", "swift",
        "kt", "c", "cpp", "h", "hpp", "cs", "vue", "svelte",
    ];
    extensions
        .iter()
        .any(|ext| name.ends_with(&format!(".{}", ext)))
}

/// Map community IDs to cluster names based on file overlap.
fn build_community_cluster_map(
    communities: &[crate::analysis::gitnexus::GnCommunity],
    community_files: &HashMap<String, Vec<String>>,
    clusters: &[crate::models::decomposition::FileCluster],
) -> HashMap<String, String> {
    let mut mapping: HashMap<String, String> = HashMap::new();

    for comm in communities {
        let comm_files: std::collections::HashSet<&str> = community_files
            .get(&comm.id)
            .map(|f| f.iter().map(|s| s.as_str()).collect())
            .unwrap_or_default();

        // Find cluster with most file overlap
        let mut best_cluster: Option<&str> = None;
        let mut best_overlap = 0;

        for cluster in clusters {
            let overlap = cluster
                .files
                .iter()
                .filter(|f| comm_files.contains(f.as_str()))
                .count();
            if overlap > best_overlap {
                best_overlap = overlap;
                best_cluster = Some(&cluster.name);
            }
        }

        if let Some(name) = best_cluster {
            mapping.insert(comm.id.clone(), name.to_string());
        }
    }

    mapping
}
