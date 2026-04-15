use serde::{Deserialize, Serialize};
use std::collections::HashMap;

// ── Stream completeness (Step 1) ────────────────────────────

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct StreamCompletenessResult {
    pub stream_name: String,
    pub feature_count: u32,
    pub story_count: u32,
    pub task_count: u32,
    pub complete: bool,
    pub gaps: Vec<String>,
}

// ── Role coverage (Step 2) ──────────────────────────────────

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct FeatureRoleCoverage {
    pub stream_name: String,
    pub feature_name: String,
    pub po: bool,
    pub designer: bool,
    pub architect: bool,
    pub qa: bool,
    pub fully_covered: bool,
    pub gaps: Vec<String>,
    pub blocking: bool,
}

#[derive(Debug, Serialize, Deserialize, Clone, Default)]
pub struct RoleCoverageResult {
    pub features: Vec<FeatureRoleCoverage>,
    pub total_features: u32,
    pub fully_covered: u32,
    pub missing_architect: u32,
    pub missing_qa: u32,
    pub missing_designer: u32,
    pub missing_po: u32,
}

// ── Cross-impact (Step 3) ───────────────────────────────────

#[derive(Debug, Serialize, Deserialize, Clone, PartialEq)]
pub enum ConflictSeverity {
    Critical,
    High,
    Medium,
    Low,
}

impl std::fmt::Display for ConflictSeverity {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            ConflictSeverity::Critical => write!(f, "CRITICAL"),
            ConflictSeverity::High => write!(f, "HIGH"),
            ConflictSeverity::Medium => write!(f, "MEDIUM"),
            ConflictSeverity::Low => write!(f, "LOW"),
        }
    }
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct FileConflict {
    pub file_path: String,
    pub streams: Vec<String>,
    pub severity: ConflictSeverity,
    pub resolution: String,
}

#[derive(Debug, Serialize, Deserialize, Clone, Default)]
pub struct CrossImpactResult {
    pub files_scanned: u32,
    pub conflicts: Vec<FileConflict>,
    pub critical_count: u32,
    pub high_count: u32,
    pub medium_count: u32,
    pub low_count: u32,
    pub impact_check_enabled: bool,
}

// ── Gate report (Step 4) ─────────────────────────────────────

#[derive(Debug, Serialize, Deserialize, Clone, PartialEq)]
pub enum GateRecommendation {
    Pass,
    Fail,
}

impl std::fmt::Display for GateRecommendation {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            GateRecommendation::Pass => write!(f, "PASS"),
            GateRecommendation::Fail => write!(f, "FAIL"),
        }
    }
}

#[derive(Debug, Serialize, Deserialize, Clone, PartialEq)]
pub enum GateDecision {
    Approved,
    Rejected,
    ApprovedWithOverrides,
    Pending,
}

impl std::fmt::Display for GateDecision {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            GateDecision::Approved => write!(f, "APPROVED"),
            GateDecision::Rejected => write!(f, "REJECTED"),
            GateDecision::ApprovedWithOverrides => write!(f, "APPROVED WITH OVERRIDES"),
            GateDecision::Pending => write!(f, "PENDING"),
        }
    }
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct BlockingIssue {
    pub category: String,
    pub description: String,
    pub remediation: String,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct GateReport {
    pub recommendation: GateRecommendation,
    pub decision: GateDecision,
    pub completeness: Vec<StreamCompletenessResult>,
    pub role_coverage: RoleCoverageResult,
    pub cross_impact: CrossImpactResult,
    pub blocking_issues: Vec<BlockingIssue>,
    pub warnings: Vec<String>,
    pub overrides: Vec<String>,
    pub timestamp: String,
    pub epic_id: String,
}

impl Default for GateReport {
    fn default() -> Self {
        GateReport {
            recommendation: GateRecommendation::Fail,
            decision: GateDecision::Pending,
            completeness: vec![],
            role_coverage: RoleCoverageResult::default(),
            cross_impact: CrossImpactResult::default(),
            blocking_issues: vec![],
            warnings: vec![],
            overrides: vec![],
            timestamp: String::new(),
            epic_id: String::new(),
        }
    }
}

// ── Inspection state ────────────────────────────────────────

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct InspectionState {
    pub status: InspectionStatus,
    pub gate_report: Option<GateReport>,
    pub timestamp: String,
}

#[derive(Debug, Serialize, Deserialize, Clone, PartialEq)]
pub enum InspectionStatus {
    #[serde(rename = "not_started")]
    NotStarted,
    #[serde(rename = "running")]
    Running,
    #[serde(rename = "awaiting_approval")]
    AwaitingApproval,
    #[serde(rename = "approved")]
    Approved,
    #[serde(rename = "rejected")]
    Rejected,
}

impl std::fmt::Display for InspectionStatus {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            InspectionStatus::NotStarted => write!(f, "not_started"),
            InspectionStatus::Running => write!(f, "running"),
            InspectionStatus::AwaitingApproval => write!(f, "awaiting_approval"),
            InspectionStatus::Approved => write!(f, "approved"),
            InspectionStatus::Rejected => write!(f, "rejected"),
        }
    }
}
