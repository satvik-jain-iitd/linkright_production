use petgraph::algo;
use petgraph::graph::{DiGraph, NodeIndex};
use std::collections::HashMap;

use crate::models::decomposition::{ClusterDependency, FileCluster, SharedFile};

/// Build a directed graph from cluster dependency edges.
/// Returns the graph and a map from cluster name to node index.
pub fn build_dependency_graph(
    deps: &[ClusterDependency],
) -> (DiGraph<String, ()>, HashMap<String, NodeIndex>) {
    let mut graph = DiGraph::new();
    let mut index_map: HashMap<String, NodeIndex> = HashMap::new();

    for dep in deps {
        let from_idx = *index_map
            .entry(dep.from_cluster.clone())
            .or_insert_with(|| graph.add_node(dep.from_cluster.clone()));
        let to_idx = *index_map
            .entry(dep.to_cluster.clone())
            .or_insert_with(|| graph.add_node(dep.to_cluster.clone()));
        graph.add_edge(from_idx, to_idx, ());
    }

    (graph, index_map)
}

/// Check if graph is acyclic. Returns Ok(topological_order) or Err(cycle description).
pub fn check_acyclicity(
    graph: &DiGraph<String, ()>,
) -> Result<Vec<String>, String> {
    match algo::toposort(graph, None) {
        Ok(order) => Ok(order.iter().map(|idx| graph[*idx].clone()).collect()),
        Err(cycle) => {
            let node_name = &graph[cycle.node_id()];
            Err(format!("Cycle detected involving stream: {}", node_name))
        }
    }
}

/// Compute the critical path length (longest chain from any root to any leaf).
pub fn critical_path_length(graph: &DiGraph<String, ()>) -> u32 {
    if graph.node_count() == 0 {
        return 0;
    }

    // Topological sort first (we know it's a DAG if this is called after acyclicity check)
    let topo = match algo::toposort(graph, None) {
        Ok(order) => order,
        Err(_) => return 0,
    };

    let mut dist: HashMap<NodeIndex, u32> = HashMap::new();
    for &node in &topo {
        dist.insert(node, 0);
    }

    for &node in &topo {
        let current_dist = dist[&node];
        for neighbor in graph.neighbors(node) {
            let entry = dist.entry(neighbor).or_insert(0);
            if current_dist + 1 > *entry {
                *entry = current_dist + 1;
            }
        }
    }

    dist.values().copied().max().unwrap_or(0) + 1
}

/// Compute max parallelism (nodes with no dependencies at any depth level).
pub fn max_parallelism(
    graph: &DiGraph<String, ()>,
    index_map: &HashMap<String, NodeIndex>,
) -> u32 {
    if graph.node_count() == 0 {
        return 0;
    }

    let topo = match algo::toposort(graph, None) {
        Ok(order) => order,
        Err(_) => return 0,
    };

    // Assign each node a depth (longest path from any root to this node)
    let mut depth: HashMap<NodeIndex, u32> = HashMap::new();
    for &node in &topo {
        depth.insert(node, 0);
    }
    for &node in &topo {
        let current_depth = depth[&node];
        for neighbor in graph.neighbors(node) {
            let entry = depth.entry(neighbor).or_insert(0);
            if current_depth + 1 > *entry {
                *entry = current_depth + 1;
            }
        }
    }

    // Also count nodes not in the graph (streams with no deps at all)
    let nodes_in_graph: usize = graph.node_count();
    let total_streams = index_map.len();
    let orphan_count = total_streams.saturating_sub(nodes_in_graph);

    // Count nodes per depth level
    let mut level_counts: HashMap<u32, u32> = HashMap::new();
    for &d in depth.values() {
        *level_counts.entry(d).or_insert(0) += 1;
    }

    let max_at_level = level_counts.values().copied().max().unwrap_or(0);
    // Orphans (no deps) run in parallel with depth-0 nodes
    max_at_level + orphan_count as u32
}

/// Detect files that appear in multiple clusters' file lists.
pub fn find_shared_files(clusters: &[FileCluster]) -> Vec<SharedFile> {
    let mut file_owners: HashMap<String, Vec<String>> = HashMap::new();

    for cluster in clusters {
        for file in &cluster.files {
            file_owners
                .entry(file.clone())
                .or_default()
                .push(cluster.name.clone());
        }
    }

    file_owners
        .into_iter()
        .filter(|(_, owners)| owners.len() > 1)
        .map(|(path, claimed_by)| SharedFile { path, claimed_by })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_acyclic_graph() {
        let deps = vec![
            ClusterDependency {
                from_cluster: "a".into(),
                to_cluster: "b".into(),
                shared_symbols: vec![],
            },
            ClusterDependency {
                from_cluster: "b".into(),
                to_cluster: "c".into(),
                shared_symbols: vec![],
            },
        ];
        let (graph, _) = build_dependency_graph(&deps);
        assert!(check_acyclicity(&graph).is_ok());
    }

    #[test]
    fn test_cyclic_graph() {
        let deps = vec![
            ClusterDependency {
                from_cluster: "a".into(),
                to_cluster: "b".into(),
                shared_symbols: vec![],
            },
            ClusterDependency {
                from_cluster: "b".into(),
                to_cluster: "a".into(),
                shared_symbols: vec![],
            },
        ];
        let (graph, _) = build_dependency_graph(&deps);
        assert!(check_acyclicity(&graph).is_err());
    }

    #[test]
    fn test_critical_path() {
        let deps = vec![
            ClusterDependency {
                from_cluster: "a".into(),
                to_cluster: "b".into(),
                shared_symbols: vec![],
            },
            ClusterDependency {
                from_cluster: "b".into(),
                to_cluster: "c".into(),
                shared_symbols: vec![],
            },
        ];
        let (graph, _) = build_dependency_graph(&deps);
        assert_eq!(critical_path_length(&graph), 3);
    }

    #[test]
    fn test_shared_files() {
        let clusters = vec![
            FileCluster {
                name: "a".into(),
                files: vec!["shared.rs".into(), "a.rs".into()],
                coupling_score: 0.9,
                entry_points: vec![],
            },
            FileCluster {
                name: "b".into(),
                files: vec!["shared.rs".into(), "b.rs".into()],
                coupling_score: 0.8,
                entry_points: vec![],
            },
        ];
        let shared = find_shared_files(&clusters);
        assert_eq!(shared.len(), 1);
        assert_eq!(shared[0].path, "shared.rs");
        assert_eq!(shared[0].claimed_by.len(), 2);
    }
}
