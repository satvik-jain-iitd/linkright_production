use serde::{Deserialize, Serialize};
use std::collections::HashMap;

// ── Grooming context (Step 1 output) ────────────────────────

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct GroomingContext {
    pub stream_name: String,
    pub stream_objective: String,
    pub scope_items: Vec<String>,
    pub reserved_files: Vec<String>,
    pub shared_files: Vec<String>,
    pub dependencies: Vec<String>,
    pub file_contents: HashMap<String, FileContent>,
    pub role_prompts: HashMap<String, String>,
    pub coordinator_role: String,
    pub goal_summary: String,
    pub other_streams: Vec<StreamSummary>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct FileContent {
    pub path: String,
    pub exists: bool,
    pub content: Option<String>,
    pub truncated: bool,
    pub line_count: u32,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct StreamSummary {
    pub name: String,
    pub objective: String,
    pub shared_files: Vec<String>,
}

// ── Feature identification (Step 2 output) ──────────────────

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct FeatureList {
    pub stream_name: String,
    pub features: Vec<Feature>,
    pub coverage_map: HashMap<String, String>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct Feature {
    pub name: String,
    pub priority: Priority,
    pub description: String,
    pub scope_items_covered: Vec<usize>,
    pub stories: Vec<Story>,
    pub files_affected: Vec<String>,
    pub dependencies: Vec<String>,
}

#[derive(Debug, Serialize, Deserialize, Clone, PartialEq)]
pub enum Priority {
    #[serde(rename = "p1")]
    P1,
    #[serde(rename = "p2")]
    P2,
    #[serde(rename = "p3")]
    P3,
}

impl std::fmt::Display for Priority {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Priority::P1 => write!(f, "p1"),
            Priority::P2 => write!(f, "p2"),
            Priority::P3 => write!(f, "p3"),
        }
    }
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct Story {
    pub title: String,
    pub description: String,
    pub acceptance_criteria: Vec<String>,
}

// ── Role outputs (Step 3 output) ────────────────────────────

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct RoleOutput {
    pub role: String,
    pub stream_name: String,
    pub feature_analyses: Vec<RoleFeatureAnalysis>,
    pub completed: bool,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct RoleFeatureAnalysis {
    pub feature_name: String,
    pub analysis: String,
    pub tasks: Vec<RoleTask>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct RoleTask {
    pub title: String,
    pub task_type: TaskType,
    pub description: String,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub enum TaskType {
    #[serde(rename = "implementation")]
    Implementation,
    #[serde(rename = "test")]
    Test,
    #[serde(rename = "design")]
    Design,
    #[serde(rename = "review")]
    Review,
}

impl std::fmt::Display for TaskType {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            TaskType::Implementation => write!(f, "implementation"),
            TaskType::Test => write!(f, "test"),
            TaskType::Design => write!(f, "design"),
            TaskType::Review => write!(f, "review"),
        }
    }
}

// ── Consolidation (Step 4 output) ───────────────────────────

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ConsolidatedGrooming {
    pub stream_name: String,
    pub features: Vec<ConsolidatedFeature>,
    pub conflicts: Vec<ConflictResolution>,
    pub task_ids: HashMap<String, TaskHierarchy>,
    pub summary: GroomingSummary,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ConsolidatedFeature {
    pub name: String,
    pub priority: Priority,
    pub stories: Vec<ConsolidatedStory>,
    pub integration_notes: String,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ConsolidatedStory {
    pub title: String,
    pub acceptance_criteria: Vec<String>,
    pub tasks: Vec<ConsolidatedTask>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ConsolidatedTask {
    pub title: String,
    pub task_type: TaskType,
    pub description: String,
    pub source_role: String,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ConflictResolution {
    pub feature: String,
    pub conflict_type: String,
    pub positions: HashMap<String, String>,
    pub decision: String,
    pub rationale: String,
    pub impact: String,
}

#[derive(Debug, Serialize, Deserialize, Clone, Default)]
pub struct TaskHierarchy {
    pub feature_id: String,
    pub story_ids: Vec<String>,
    pub task_ids: Vec<String>,
}

#[derive(Debug, Serialize, Deserialize, Clone, Default)]
pub struct GroomingSummary {
    pub feature_count: u32,
    pub story_count: u32,
    pub task_count: u32,
    pub conflicts_found: u32,
    pub conflicts_resolved: u32,
    pub gaps: u32,
}

// ── Grooming state ──────────────────────────────────────────

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct GroomingState {
    pub current_workflow: String,
    pub streams: HashMap<String, StreamGroomingState>,
    pub timestamp: String,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct StreamGroomingState {
    pub status: GroomingStatus,
    pub current_step: String,
    pub features_identified: u32,
    pub roles_completed: Vec<String>,
    pub consolidated: bool,
    pub verified: bool,
}

#[derive(Debug, Serialize, Deserialize, Clone, PartialEq)]
pub enum GroomingStatus {
    #[serde(rename = "pending")]
    Pending,
    #[serde(rename = "in_progress")]
    InProgress,
    #[serde(rename = "blocked")]
    Blocked,
    #[serde(rename = "completed")]
    Completed,
    #[serde(rename = "failed")]
    Failed,
}

impl std::fmt::Display for GroomingStatus {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            GroomingStatus::Pending => write!(f, "pending"),
            GroomingStatus::InProgress => write!(f, "in_progress"),
            GroomingStatus::Blocked => write!(f, "blocked"),
            GroomingStatus::Completed => write!(f, "completed"),
            GroomingStatus::Failed => write!(f, "failed"),
        }
    }
}

// ── Grooming validation (Step 5) ────────────────────────────

#[derive(Debug, Serialize, Deserialize, Clone, PartialEq)]
pub enum GroomingValidationStatus {
    Pass,
    Fail,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct GroomingValidationCheck {
    pub name: String,
    pub passed: bool,
    pub evidence: String,
    pub remediation: Option<String>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct GroomingValidationReport {
    pub stream_name: String,
    pub status: GroomingValidationStatus,
    pub checks: Vec<GroomingValidationCheck>,
}
