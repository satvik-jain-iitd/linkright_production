use std::path::Path;

use crate::models::decomposition::DecompositionResult;
use crate::models::grooming::{ConsolidatedGrooming, GroomingState, GroomingStatus};
use crate::models::inspection::GateReport;
use crate::models::retro::{RetroMetrics, StreamMetrics};

/// Step 1: Gather raw metrics from all state files.
pub fn collect_metrics(
    decomposition: &DecompositionResult,
    grooming_state: &GroomingState,
    gate_report: Option<&GateReport>,
) -> RetroMetrics {
    let mut stream_metrics = Vec::new();
    let mut tasks_total = 0u32;

    for stream in &decomposition.streams {
        let state = grooming_state.streams.get(&stream.name);

        let (feature_count, story_count, task_count) = load_counts(&stream.name);
        tasks_total += task_count;

        let roles_completed = state
            .map(|s| s.roles_completed.clone())
            .unwrap_or_default();

        let grooming_complete = state
            .map(|s| s.status == GroomingStatus::Completed)
            .unwrap_or(false);

        let status = state
            .map(|s| format!("{}", s.status))
            .unwrap_or_else(|| "unknown".to_string());

        stream_metrics.push(StreamMetrics {
            name: stream.name.clone(),
            status,
            feature_count,
            story_count,
            task_count,
            roles_completed,
            grooming_complete,
        });
    }

    let streams_completed = stream_metrics.iter().filter(|s| s.grooming_complete).count() as u32;
    let streams_total = stream_metrics.len() as u32;

    // Gate data
    let (gate_recommendation, gate_decision, overrides, conflicts_detected, conflicts_critical) =
        if let Some(gate) = gate_report {
            (
                format!("{}", gate.recommendation),
                format!("{}", gate.decision),
                gate.overrides.len() as u32,
                gate.cross_impact.conflicts.len() as u32,
                gate.cross_impact.critical_count,
            )
        } else {
            ("N/A".to_string(), "N/A".to_string(), 0, 0, 0)
        };

    // Epic ID from decomposition task_ids
    let epic_id = decomposition
        .task_ids
        .values()
        .next()
        .map(|t| t.epic_id.clone())
        .unwrap_or_default();

    RetroMetrics {
        streams: stream_metrics,
        streams_total,
        streams_completed,
        tasks_total,
        conflicts_detected,
        conflicts_critical,
        gate_recommendation,
        gate_decision,
        overrides,
        timing_available: false,
        epic_id,
    }
}

fn load_counts(stream_name: &str) -> (u32, u32, u32) {
    let path = format!(
        ".truss/_progress/outputs/{}-consolidated.yaml",
        stream_name
    );

    if !Path::new(&path).exists() {
        return (0, 0, 0);
    }

    let content = match std::fs::read_to_string(&path) {
        Ok(c) => c,
        Err(_) => return (0, 0, 0),
    };

    let consolidated: ConsolidatedGrooming = match serde_yaml::from_str(&content) {
        Ok(c) => c,
        Err(_) => return (0, 0, 0),
    };

    let features = consolidated.features.len() as u32;
    let stories: u32 = consolidated.features.iter().map(|f| f.stories.len() as u32).sum();
    let tasks: u32 = consolidated
        .features
        .iter()
        .flat_map(|f| &f.stories)
        .map(|s| s.tasks.len() as u32)
        .sum();

    (features, stories, tasks)
}
