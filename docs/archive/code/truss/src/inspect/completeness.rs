use std::path::Path;

use crate::models::decomposition::DecompositionResult;
use crate::models::grooming::{ConsolidatedGrooming, GroomingState, GroomingStatus};
use crate::models::inspection::StreamCompletenessResult;

/// Step 1: Check every stream has features > stories > tasks.
pub fn check_all_streams(
    decomposition: &DecompositionResult,
    grooming_state: &GroomingState,
) -> Vec<StreamCompletenessResult> {
    let mut results = Vec::new();

    for stream in &decomposition.streams {
        let result = check_stream(stream.name.as_str(), grooming_state);
        results.push(result);
    }

    results
}

fn check_stream(stream_name: &str, grooming_state: &GroomingState) -> StreamCompletenessResult {
    let stream_state = grooming_state.streams.get(stream_name);

    // Check if grooming completed
    let grooming_done = stream_state
        .map(|s| s.status == GroomingStatus::Completed || s.verified)
        .unwrap_or(false);

    if !grooming_done {
        let status = stream_state
            .map(|s| format!("{}", s.status))
            .unwrap_or_else(|| "unknown".to_string());

        return StreamCompletenessResult {
            stream_name: stream_name.to_string(),
            feature_count: 0,
            story_count: 0,
            task_count: 0,
            complete: false,
            gaps: vec![format!(
                "Grooming not complete (status: {}). Run `truss groom --stream {}`",
                status, stream_name
            )],
        };
    }

    // Load consolidated output
    let consolidated_path = format!(
        ".truss/_progress/outputs/{}-consolidated.yaml",
        stream_name
    );

    if !Path::new(&consolidated_path).exists() {
        return StreamCompletenessResult {
            stream_name: stream_name.to_string(),
            feature_count: 0,
            story_count: 0,
            task_count: 0,
            complete: false,
            gaps: vec![format!(
                "No consolidated output found at {}. Re-run grooming.",
                consolidated_path
            )],
        };
    }

    match load_consolidated(&consolidated_path) {
        Ok(consolidated) => {
            let mut gaps = Vec::new();

            if consolidated.features.is_empty() {
                gaps.push("Zero features — grooming produced no features".to_string());
            }

            let total_stories: u32 = consolidated
                .features
                .iter()
                .map(|f| f.stories.len() as u32)
                .sum();

            let total_tasks: u32 = consolidated
                .features
                .iter()
                .flat_map(|f| &f.stories)
                .map(|s| s.tasks.len() as u32)
                .sum();

            // Check for features without stories
            for feature in &consolidated.features {
                if feature.stories.is_empty() {
                    gaps.push(format!("Feature '{}' has no stories", feature.name));
                }
                for story in &feature.stories {
                    if story.tasks.is_empty() {
                        gaps.push(format!(
                            "Story '{}/{}' has no tasks",
                            feature.name, story.title
                        ));
                    }
                    if story.acceptance_criteria.is_empty() {
                        gaps.push(format!(
                            "Story '{}/{}' has no acceptance criteria",
                            feature.name, story.title
                        ));
                    }
                }
            }

            StreamCompletenessResult {
                stream_name: stream_name.to_string(),
                feature_count: consolidated.features.len() as u32,
                story_count: total_stories,
                task_count: total_tasks,
                complete: gaps.is_empty(),
                gaps,
            }
        }
        Err(e) => StreamCompletenessResult {
            stream_name: stream_name.to_string(),
            feature_count: 0,
            story_count: 0,
            task_count: 0,
            complete: false,
            gaps: vec![format!("Failed to load consolidated output: {}", e)],
        },
    }
}

fn load_consolidated(path: &str) -> Result<ConsolidatedGrooming, String> {
    let content = std::fs::read_to_string(path)
        .map_err(|e| format!("Failed to read: {}", e))?;
    serde_yaml::from_str(&content)
        .map_err(|e| format!("Failed to parse: {}", e))
}

pub fn print_completeness_report(results: &[StreamCompletenessResult]) {
    use colored::Colorize;

    println!("{}", "STREAM COMPLETENESS".bold());
    println!("{}", "─".repeat(60));

    let complete_count = results.iter().filter(|r| r.complete).count();
    let total = results.len();

    println!("Streams complete: {}/{}", complete_count, total);
    println!();

    for r in results {
        let icon = if r.complete {
            "✓".green().to_string()
        } else {
            "✗".red().to_string()
        };

        println!(
            "  [{}] {} — {} features / {} stories / {} tasks",
            icon, r.stream_name, r.feature_count, r.story_count, r.task_count
        );

        for gap in &r.gaps {
            println!("      → {}", gap.yellow());
        }
    }
}
