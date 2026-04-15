use std::collections::{HashMap, HashSet};

use crate::analysis::gitnexus::GnCommunity;
use crate::models::decomposition::{ClusterDependency, FileCluster};

/// Build file clusters from GitNexus community data + import coupling.
///
/// Algorithm:
/// 1. Seed clusters from top GitNexus Leiden communities (by symbol count)
/// 2. Assign remaining community files to nearest cluster by import coupling
/// 3. Group remaining orphans by parent directory
/// 4. Merge until count <= max_clusters
pub fn build_clusters(
    communities: &[GnCommunity],
    community_files: &HashMap<String, Vec<String>>,
    all_files: &[String],
    imports: &[(String, String)],
    max_clusters: u32,
) -> Vec<FileCluster> {
    let mut clusters: Vec<FileCluster> = Vec::new();
    let mut assigned: HashSet<String> = HashSet::new();

    // Take top communities by symbol count (cap at 3x max to keep merge fast)
    let top_limit = (max_clusters as usize) * 3;
    let mut sorted_communities: Vec<&GnCommunity> = communities.iter().collect();
    sorted_communities.sort_by(|a, b| b.symbol_count.cmp(&a.symbol_count));

    // Phase A: Seed from top communities
    for comm in sorted_communities.iter().take(top_limit) {
        let files = community_files
            .get(&comm.id)
            .cloned()
            .unwrap_or_default();

        if files.is_empty() {
            continue;
        }

        for f in &files {
            assigned.insert(f.clone());
        }

        let entry_points = find_entry_points(&files, imports);

        clusters.push(FileCluster {
            name: sanitize_cluster_name(&comm.heuristic_label, &clusters),
            files,
            coupling_score: comm.cohesion,
            entry_points,
        });
    }

    // Phase A2: Assign files from remaining communities to nearest existing cluster
    for comm in sorted_communities.iter().skip(top_limit) {
        let files = community_files
            .get(&comm.id)
            .cloned()
            .unwrap_or_default();

        for f in &files {
            if !assigned.contains(f) {
                if let Some(idx) = find_best_cluster_by_imports(f, &clusters, imports) {
                    clusters[idx].files.push(f.clone());
                }
                assigned.insert(f.clone());
            }
        }
    }

    // Phase B: Assign orphans by import coupling
    let orphans: Vec<String> = all_files
        .iter()
        .filter(|f| !assigned.contains(*f))
        .cloned()
        .collect();

    for orphan in &orphans {
        if let Some(best_cluster_idx) = find_best_cluster_by_imports(orphan, &clusters, imports) {
            clusters[best_cluster_idx].files.push(orphan.clone());
            assigned.insert(orphan.clone());
        }
    }

    // Phase C: Directory locality fallback for remaining orphans
    let still_orphaned: Vec<String> = all_files
        .iter()
        .filter(|f| !assigned.contains(*f))
        .cloned()
        .collect();

    if !still_orphaned.is_empty() {
        let dir_groups = group_by_directory(&still_orphaned);
        for (dir_name, files) in dir_groups {
            let name = sanitize_cluster_name(&dir_name, &clusters);
            clusters.push(FileCluster {
                name,
                files,
                coupling_score: 0.5, // default for directory-based clusters
                entry_points: vec![],
            });
        }
    }

    // Phase D: Merge until count <= max_clusters
    merge_small_clusters(&mut clusters, imports, max_clusters);

    // Phase E: Deduplicate files within each cluster and recompute coupling scores
    for cluster in &mut clusters {
        cluster.files.sort();
        cluster.files.dedup();
        cluster.coupling_score = compute_coupling_score(&cluster.files, imports);
    }

    clusters
}

/// Build synthetic clusters from goal document text for greenfield projects.
/// Parses `##` headings as cluster boundaries.
pub fn build_greenfield_clusters(goal_text: &str) -> Vec<FileCluster> {
    let mut clusters: Vec<FileCluster> = Vec::new();
    let mut current_name: Option<String> = None;
    let mut current_scope: Vec<String> = Vec::new();

    for line in goal_text.lines() {
        let trimmed = line.trim();

        if trimmed.starts_with("## ") {
            // Save previous cluster
            if let Some(name) = current_name.take() {
                if !current_scope.is_empty() {
                    clusters.push(FileCluster {
                        name: slug(&name),
                        files: vec![], // greenfield — no files yet
                        coupling_score: 1.0,
                        entry_points: vec![],
                    });
                }
            }
            current_name = Some(trimmed.trim_start_matches('#').trim().to_string());
            current_scope = vec![];
        } else if !trimmed.is_empty() {
            current_scope.push(trimmed.to_string());
        }
    }

    // Save last cluster
    if let Some(name) = current_name {
        clusters.push(FileCluster {
            name: slug(&name),
            files: vec![],
            coupling_score: 1.0,
            entry_points: vec![],
        });
    }

    // If no ## headings found, create a single cluster
    if clusters.is_empty() {
        let name = goal_text
            .lines()
            .find(|l| !l.trim().is_empty())
            .unwrap_or("project")
            .trim()
            .trim_start_matches('#')
            .trim();
        clusters.push(FileCluster {
            name: slug(name),
            files: vec![],
            coupling_score: 1.0,
            entry_points: vec![],
        });
    }

    clusters
}

/// Build cluster dependencies from cross-community call edges.
pub fn build_cluster_dependencies(
    clusters: &[FileCluster],
    community_to_cluster: &HashMap<String, String>,
    cross_edges: &[(String, String)],
) -> Vec<ClusterDependency> {
    let mut seen: HashSet<(String, String)> = HashSet::new();
    let mut deps: Vec<ClusterDependency> = Vec::new();

    for (from_comm, to_comm) in cross_edges {
        let from_cluster = community_to_cluster.get(from_comm);
        let to_cluster = community_to_cluster.get(to_comm);

        if let (Some(from), Some(to)) = (from_cluster, to_cluster) {
            if from != to && seen.insert((from.clone(), to.clone())) {
                deps.push(ClusterDependency {
                    from_cluster: from.clone(),
                    to_cluster: to.clone(),
                    shared_symbols: vec![],
                });
            }
        }
    }

    // Filter to only include clusters that actually exist
    let cluster_names: HashSet<&str> = clusters.iter().map(|c| c.name.as_str()).collect();
    deps.retain(|d| {
        cluster_names.contains(d.from_cluster.as_str())
            && cluster_names.contains(d.to_cluster.as_str())
    });

    deps
}

// ── Internal helpers ───────────────────────────────────────

/// Find files that are imported by files in other clusters (entry points).
fn find_entry_points(cluster_files: &[String], imports: &[(String, String)]) -> Vec<String> {
    let file_set: HashSet<&str> = cluster_files.iter().map(|f| f.as_str()).collect();
    let mut entry_points: HashSet<String> = HashSet::new();

    for (from, to) in imports {
        // If an external file imports a file in this cluster, that file is an entry point
        if !file_set.contains(from.as_str()) && file_set.contains(to.as_str()) {
            entry_points.insert(to.clone());
        }
    }

    entry_points.into_iter().collect()
}

/// Find the cluster with the strongest import coupling to a given file.
fn find_best_cluster_by_imports(
    file: &str,
    clusters: &[FileCluster],
    imports: &[(String, String)],
) -> Option<usize> {
    let mut scores: Vec<(usize, usize)> = Vec::new();

    for (idx, cluster) in clusters.iter().enumerate() {
        let file_set: HashSet<&str> = cluster.files.iter().map(|f| f.as_str()).collect();
        let coupling_count = imports
            .iter()
            .filter(|(from, to)| {
                (from == file && file_set.contains(to.as_str()))
                    || (to == file && file_set.contains(from.as_str()))
            })
            .count();

        if coupling_count > 0 {
            scores.push((idx, coupling_count));
        }
    }

    scores.sort_by(|a, b| b.1.cmp(&a.1));
    scores.first().map(|(idx, _)| *idx)
}

/// Group files by their parent directory.
fn group_by_directory(files: &[String]) -> Vec<(String, Vec<String>)> {
    let mut groups: HashMap<String, Vec<String>> = HashMap::new();

    for file in files {
        let dir = file
            .rsplit_once('/')
            .map(|(d, _)| d.to_string())
            .unwrap_or_else(|| "root".to_string());
        groups.entry(dir).or_default().push(file.clone());
    }

    groups.into_iter().collect()
}

/// Merge clusters iteratively until count <= max.
/// Uses smallest-file-count heuristic instead of O(n^2) cross-import scan.
fn merge_small_clusters(
    clusters: &mut Vec<FileCluster>,
    _imports: &[(String, String)],
    max: u32,
) {
    while clusters.len() > max as usize && clusters.len() > 1 {
        // Find the smallest cluster
        let smallest_idx = clusters
            .iter()
            .enumerate()
            .min_by_key(|(_, c)| c.files.len())
            .map(|(i, _)| i)
            .unwrap();

        let smallest = clusters.remove(smallest_idx);

        // Merge into the next smallest cluster
        let target_idx = clusters
            .iter()
            .enumerate()
            .min_by_key(|(_, c)| c.files.len())
            .map(|(i, _)| i)
            .unwrap();

        clusters[target_idx].files.extend(smallest.files);
        clusters[target_idx]
            .entry_points
            .extend(smallest.entry_points);
    }
}

/// Compute coupling score: intra-edges / (intra-edges + inter-edges).
fn compute_coupling_score(cluster_files: &[String], imports: &[(String, String)]) -> f64 {
    let file_set: HashSet<&str> = cluster_files.iter().map(|f| f.as_str()).collect();

    let mut intra = 0usize;
    let mut inter = 0usize;

    for (from, to) in imports {
        let from_in = file_set.contains(from.as_str());
        let to_in = file_set.contains(to.as_str());

        if from_in && to_in {
            intra += 1;
        } else if from_in || to_in {
            inter += 1;
        }
    }

    let total = intra + inter;
    if total == 0 {
        return 0.5; // no data
    }

    intra as f64 / total as f64
}

/// Ensure cluster names are unique by appending a suffix if needed.
fn sanitize_cluster_name(raw: &str, existing: &[FileCluster]) -> String {
    let base = slug(raw);
    let names: HashSet<&str> = existing.iter().map(|c| c.name.as_str()).collect();

    if !names.contains(base.as_str()) {
        return base;
    }

    for i in 2..100 {
        let candidate = format!("{}-{}", base, i);
        if !names.contains(candidate.as_str()) {
            return candidate;
        }
    }

    format!("{}-{}", base, existing.len())
}

/// Convert a label to a URL-safe slug.
fn slug(s: &str) -> String {
    let raw: String = s
        .to_lowercase()
        .chars()
        .map(|c| if c.is_alphanumeric() || c == '-' { c } else { '-' })
        .collect();

    // Collapse consecutive dashes
    let mut result = String::with_capacity(raw.len());
    let mut prev_dash = false;
    for c in raw.chars() {
        if c == '-' {
            if !prev_dash {
                result.push(c);
            }
            prev_dash = true;
        } else {
            result.push(c);
            prev_dash = false;
        }
    }
    result.trim_matches('-').to_string()
}
