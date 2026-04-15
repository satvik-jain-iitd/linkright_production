use serde::{Deserialize, Serialize};

// ── Metrics bundle (Step 1) ─────────────────────────────────

#[derive(Debug, Serialize, Deserialize, Clone, Default)]
pub struct StreamMetrics {
    pub name: String,
    pub status: String,
    pub feature_count: u32,
    pub story_count: u32,
    pub task_count: u32,
    pub roles_completed: Vec<String>,
    pub grooming_complete: bool,
}

#[derive(Debug, Serialize, Deserialize, Clone, Default)]
pub struct RetroMetrics {
    pub streams: Vec<StreamMetrics>,
    pub streams_total: u32,
    pub streams_completed: u32,
    pub tasks_total: u32,
    pub conflicts_detected: u32,
    pub conflicts_critical: u32,
    pub gate_recommendation: String,
    pub gate_decision: String,
    pub overrides: u32,
    pub timing_available: bool,
    pub epic_id: String,
}

// ── Pattern analysis (Step 2) ───────────────────────────────

#[derive(Debug, Serialize, Deserialize, Clone, PartialEq)]
pub enum PatternType {
    Improvement,
    Reinforcement,
}

impl std::fmt::Display for PatternType {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            PatternType::Improvement => write!(f, "IMPROVEMENT"),
            PatternType::Reinforcement => write!(f, "REINFORCEMENT"),
        }
    }
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub enum PatternDimension {
    Decomposition,
    Roles,
    Sop,
    CrossImpact,
}

impl std::fmt::Display for PatternDimension {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            PatternDimension::Decomposition => write!(f, "decomposition"),
            PatternDimension::Roles => write!(f, "roles"),
            PatternDimension::Sop => write!(f, "sop"),
            PatternDimension::CrossImpact => write!(f, "cross-impact"),
        }
    }
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct RetroPattern {
    pub pattern_type: PatternType,
    pub dimension: PatternDimension,
    pub name: String,
    pub evidence: String,
    pub recommendation: String,
    pub mem0_entry: String,
}

// ── Retro report ────────────────────────────────────────────

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct RetroReport {
    pub epic_id: String,
    pub metrics: RetroMetrics,
    pub patterns: Vec<RetroPattern>,
    pub improvements: u32,
    pub reinforcements: u32,
    pub top_insight: String,
    pub timestamp: String,
}
