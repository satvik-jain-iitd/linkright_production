use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::PathBuf;

// ── Step 1 output ──────────────────────────────────────────

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ContextBundle {
    pub goal_text: String,
    pub goal_path: PathBuf,
    pub domain_name: String,
    pub max_streams: u32,
    pub default_roles: Vec<String>,
    pub coordinator_role: String,
    pub strategy: String,
    pub mem0_scope: Option<String>,
    pub prior_patterns: Vec<String>,
}

// ── Step 2 output ──────────────────────────────────────────

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct FileCluster {
    pub name: String,
    pub files: Vec<String>,
    pub coupling_score: f64,
    pub entry_points: Vec<String>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ClusterDependency {
    pub from_cluster: String,
    pub to_cluster: String,
    pub shared_symbols: Vec<String>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct SharedFile {
    pub path: String,
    pub claimed_by: Vec<String>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct CodeAnalysis {
    pub clusters: Vec<FileCluster>,
    pub dependencies: Vec<ClusterDependency>,
    pub shared_files: Vec<SharedFile>,
    pub hot_spots: Vec<String>,
    pub is_greenfield: bool,
    pub repo_path: Option<PathBuf>,
}

// ── Step 3 output ──────────────────────────────────────────

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct StreamSharedFile {
    pub path: String,
    pub owned_by: String,
    pub coordination: String,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct StreamBrief {
    pub name: String,
    pub objective: String,
    pub scope: Vec<String>,
    pub out_of_scope: Vec<String>,
    pub reserved_files: Vec<String>,
    pub shared_files: Vec<StreamSharedFile>,
    pub dependencies: Vec<String>,
    pub roles: HashMap<String, String>,
}

#[derive(Debug, Serialize, Deserialize, Clone, Default)]
pub struct TaskIds {
    pub epic_id: String,
    pub feature_ids: Vec<String>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct DecompositionResult {
    pub goal_summary: String,
    pub streams: Vec<StreamBrief>,
    pub task_ids: HashMap<String, TaskIds>,
    pub dependency_graph: Vec<(String, String)>,
    pub max_parallelism: u32,
    pub critical_path_length: u32,
    pub approved: bool,
    pub timestamp: String,
}

// ── Step 4 output (validation) ─────────────────────────────

#[derive(Debug, Serialize, Deserialize, Clone, PartialEq)]
pub enum ValidationStatus {
    Pass,
    Fail,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ValidationCheck {
    pub name: String,
    pub passed: bool,
    pub evidence: String,
    pub remediation: Option<String>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ValidationReport {
    pub status: ValidationStatus,
    pub checks: Vec<ValidationCheck>,
}
