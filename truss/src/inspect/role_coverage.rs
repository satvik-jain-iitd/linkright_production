use std::path::Path;

use crate::models::decomposition::DecompositionResult;
use crate::models::grooming::ConsolidatedGrooming;
use crate::models::inspection::{FeatureRoleCoverage, RoleCoverageResult};

/// Step 2: Check all 4 roles are represented in every feature across all streams.
pub fn check_all_streams(decomposition: &DecompositionResult) -> RoleCoverageResult {
    let mut all_features: Vec<FeatureRoleCoverage> = Vec::new();

    for stream in &decomposition.streams {
        let path = format!(
            ".truss/_progress/outputs/{}-consolidated.yaml",
            stream.name
        );

        if !Path::new(&path).exists() {
            continue;
        }

        let content = match std::fs::read_to_string(&path) {
            Ok(c) => c,
            Err(_) => continue,
        };

        let consolidated: ConsolidatedGrooming = match serde_yaml::from_str(&content) {
            Ok(c) => c,
            Err(_) => continue,
        };

        for feature in &consolidated.features {
            let coverage = check_feature_coverage(
                &stream.name,
                &feature.name,
                &feature.integration_notes,
                &feature.stories.iter()
                    .flat_map(|s| &s.tasks)
                    .map(|t| format!("{} {} {}", t.title, t.description, t.source_role))
                    .collect::<Vec<_>>()
                    .join(" "),
            );
            all_features.push(coverage);
        }
    }

    // Aggregate stats
    let total = all_features.len() as u32;
    let fully_covered = all_features.iter().filter(|f| f.fully_covered).count() as u32;
    let missing_architect = all_features.iter().filter(|f| !f.architect).count() as u32;
    let missing_qa = all_features.iter().filter(|f| !f.qa).count() as u32;
    let missing_designer = all_features.iter().filter(|f| !f.designer).count() as u32;
    let missing_po = all_features.iter().filter(|f| !f.po).count() as u32;

    RoleCoverageResult {
        features: all_features,
        total_features: total,
        fully_covered,
        missing_architect,
        missing_qa,
        missing_designer,
        missing_po,
    }
}

fn check_feature_coverage(
    stream_name: &str,
    feature_name: &str,
    integration_notes: &str,
    tasks_text: &str,
) -> FeatureRoleCoverage {
    let notes_lower = integration_notes.to_lowercase();
    let tasks_lower = tasks_text.to_lowercase();
    let combined = format!("{} {}", notes_lower, tasks_lower);

    // PO: stories, user-facing, acceptance criteria, business value
    let po = combined.contains("po")
        || combined.contains("story")
        || combined.contains("user stor")
        || combined.contains("acceptance")
        || combined.contains("product owner")
        || integration_notes.contains("PO");

    // Designer: UX, design, wireframe, interaction, UI, frontend, visual
    let designer = combined.contains("designer")
        || combined.contains("ux")
        || combined.contains("design")
        || combined.contains("wireframe")
        || combined.contains("ui ")
        || combined.contains("interaction")
        || combined.contains("visual")
        || combined.contains("figma");

    // Architect: technical, implementation, api, database, architecture, file
    let architect = combined.contains("architect")
        || combined.contains("technical")
        || combined.contains("implementation")
        || combined.contains("api")
        || combined.contains("database")
        || combined.contains("schema")
        || combined.contains("service")
        || combined.contains("module")
        || combined.contains("file change");

    // QA: test, edge case, regression, validation, assert
    let qa = combined.contains("qa")
        || combined.contains("test")
        || combined.contains("edge case")
        || combined.contains("regression")
        || combined.contains("validation")
        || combined.contains("assert")
        || combined.contains("coverage");

    let mut gaps = Vec::new();
    if !po { gaps.push("PO".to_string()); }
    if !designer { gaps.push("Designer".to_string()); }
    if !architect { gaps.push("Architect".to_string()); }
    if !qa { gaps.push("QA".to_string()); }

    let blocking = !architect || !qa;
    let fully_covered = gaps.is_empty();

    FeatureRoleCoverage {
        stream_name: stream_name.to_string(),
        feature_name: feature_name.to_string(),
        po,
        designer,
        architect,
        qa,
        fully_covered,
        gaps,
        blocking,
    }
}

pub fn print_role_coverage_report(result: &RoleCoverageResult) {
    use colored::Colorize;

    println!("{}", "ROLE COVERAGE".bold());
    println!("{}", "─".repeat(60));

    let pct = if result.total_features > 0 {
        (result.fully_covered as f64 / result.total_features as f64) * 100.0
    } else {
        100.0
    };

    println!(
        "Features fully covered: {}/{} ({:.0}%)",
        result.fully_covered, result.total_features, pct
    );
    println!(
        "Missing: PO={}, Designer={}, Architect={}, QA={}",
        result.missing_po, result.missing_designer, result.missing_architect, result.missing_qa
    );
    println!();

    // Only show features with gaps
    let with_gaps: Vec<&FeatureRoleCoverage> = result.features.iter().filter(|f| !f.fully_covered).collect();

    if with_gaps.is_empty() {
        println!("  {} All features have complete role coverage", "✓".green());
    } else {
        println!("  Coverage gaps ({}):", with_gaps.len());
        for f in &with_gaps {
            let severity = if f.blocking { "BLOCKING".red() } else { "INFO".yellow() };
            println!(
                "  [{}] {}/{} — missing: {}",
                severity,
                f.stream_name,
                f.feature_name,
                f.gaps.join(", ")
            );
        }
    }
}
