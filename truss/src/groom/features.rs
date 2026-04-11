use colored::Colorize;

use crate::models::grooming::{FeatureList, Priority};

/// Print feature identification summary for a stream.
pub fn print_feature_summary(features: &FeatureList) {
    println!();
    println!(
        "  {} Features for stream '{}':",
        "✓".green(),
        features.stream_name.bold()
    );

    let p1_count = features.features.iter().filter(|f| f.priority == Priority::P1).count();
    let p2_count = features.features.iter().filter(|f| f.priority == Priority::P2).count();
    let p3_count = features.features.iter().filter(|f| f.priority == Priority::P3).count();
    let total_stories: usize = features.features.iter().map(|f| f.stories.len()).sum();

    println!(
        "    {} features ({} p1, {} p2, {} p3)",
        features.features.len(),
        p1_count,
        p2_count,
        p3_count
    );
    println!("    {} stories total", total_stories);

    for (i, feature) in features.features.iter().enumerate() {
        println!(
            "    {}. [{}] {} — {} stories, {} files",
            i + 1,
            feature.priority,
            feature.name,
            feature.stories.len(),
            feature.files_affected.len(),
        );
    }

    // Coverage check
    let uncovered: Vec<&String> = features
        .coverage_map
        .iter()
        .filter(|(_, feature)| feature.is_empty())
        .map(|(item, _)| item)
        .collect();

    if uncovered.is_empty() {
        println!("    {} All scope items covered", "✓".green());
    } else {
        println!(
            "    {} {} scope items uncovered!",
            "✗".red(),
            uncovered.len()
        );
    }

    // Priority distribution check
    let total = features.features.len();
    if total > 0 {
        let p1_pct = (p1_count as f64 / total as f64) * 100.0;
        if p1_pct > 60.0 {
            println!(
                "    {} P1 features at {:.0}% (max 60%)",
                "!".yellow(),
                p1_pct
            );
        }
    }
}

/// Validate that features output meets grooming step-02 requirements.
pub fn validate_features(features: &FeatureList) -> Vec<String> {
    let mut issues = Vec::new();

    if features.features.is_empty() {
        issues.push("No features identified".to_string());
        return issues;
    }

    // Check: every feature has at least one story
    for feature in &features.features {
        if feature.stories.is_empty() {
            issues.push(format!("Feature '{}' has no stories", feature.name));
        }

        // Check: every story has acceptance criteria
        for story in &feature.stories {
            if story.acceptance_criteria.is_empty() {
                issues.push(format!(
                    "Story '{}' in feature '{}' has no acceptance criteria",
                    story.title, feature.name
                ));
            }
        }

        // Check: feature has files affected
        if feature.files_affected.is_empty() {
            issues.push(format!(
                "Feature '{}' has no files affected listed",
                feature.name
            ));
        }
    }

    // Check: priority distribution (max 60% p1)
    let total = features.features.len();
    let p1_count = features.features.iter().filter(|f| f.priority == Priority::P1).count();
    if total > 0 && (p1_count as f64 / total as f64) > 0.6 {
        issues.push(format!(
            "P1 features at {:.0}% ({}/{}) — max allowed is 60%",
            (p1_count as f64 / total as f64) * 100.0,
            p1_count,
            total
        ));
    }

    issues
}
