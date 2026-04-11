use crate::models::grooming::{
    ConsolidatedGrooming, GroomingValidationCheck, GroomingValidationReport,
    GroomingValidationStatus,
};

/// Step 5: Validate grooming completeness for a stream.
pub fn validate_grooming(grooming: &ConsolidatedGrooming) -> GroomingValidationReport {
    let mut checks = Vec::new();

    // Check 1: Feature coverage
    let feature_count = grooming.features.len();
    checks.push(GroomingValidationCheck {
        name: "Feature coverage".to_string(),
        passed: feature_count > 0,
        evidence: format!("{} features in hierarchy", feature_count),
        remediation: if feature_count == 0 {
            Some("Loop back to step-02: no features identified".to_string())
        } else {
            None
        },
    });

    // Check 2: Story coverage (every feature has at least 1 story)
    let features_without_stories: Vec<&str> = grooming
        .features
        .iter()
        .filter(|f| f.stories.is_empty())
        .map(|f| f.name.as_str())
        .collect();
    let stories_ok = features_without_stories.is_empty();
    checks.push(GroomingValidationCheck {
        name: "Story coverage".to_string(),
        passed: stories_ok,
        evidence: if stories_ok {
            "All features have stories".to_string()
        } else {
            format!(
                "Features without stories: {}",
                features_without_stories.join(", ")
            )
        },
        remediation: if !stories_ok {
            Some("Loop back to step-02: add stories for empty features".to_string())
        } else {
            None
        },
    });

    // Check 3: Task coverage (every story has at least 1 task)
    let mut stories_without_tasks = Vec::new();
    for feature in &grooming.features {
        for story in &feature.stories {
            if story.tasks.is_empty() {
                stories_without_tasks.push(format!(
                    "{}/{}",
                    feature.name, story.title
                ));
            }
        }
    }
    let tasks_ok = stories_without_tasks.is_empty();
    checks.push(GroomingValidationCheck {
        name: "Task coverage".to_string(),
        passed: tasks_ok,
        evidence: if tasks_ok {
            format!(
                "All stories have tasks ({})",
                grooming.summary.task_count
            )
        } else {
            format!(
                "{} stories without tasks: {}",
                stories_without_tasks.len(),
                stories_without_tasks.iter().take(5).cloned().collect::<Vec<_>>().join(", ")
            )
        },
        remediation: if !tasks_ok {
            Some("Loop back to step-04: derive tasks from role outputs".to_string())
        } else {
            None
        },
    });

    // Check 4: Acceptance criteria (every story has ACs)
    let mut stories_without_ac = Vec::new();
    for feature in &grooming.features {
        for story in &feature.stories {
            if story.acceptance_criteria.is_empty() {
                stories_without_ac.push(format!(
                    "{}/{}",
                    feature.name, story.title
                ));
            }
        }
    }
    let ac_ok = stories_without_ac.is_empty();
    checks.push(GroomingValidationCheck {
        name: "Acceptance criteria".to_string(),
        passed: ac_ok,
        evidence: if ac_ok {
            "All stories have acceptance criteria".to_string()
        } else {
            format!(
                "{} stories missing ACs: {}",
                stories_without_ac.len(),
                stories_without_ac.iter().take(5).cloned().collect::<Vec<_>>().join(", ")
            )
        },
        remediation: if !ac_ok {
            Some("Loop back to step-03: PO role must add ACs".to_string())
        } else {
            None
        },
    });

    // Check 5: Role representation (all 4 roles in integration notes)
    let expected_roles = ["po", "designer", "architect", "qa"];
    let mut features_missing_roles = Vec::new();
    for feature in &grooming.features {
        let notes_lower = feature.integration_notes.to_lowercase();
        let missing: Vec<&&str> = expected_roles
            .iter()
            .filter(|r| !notes_lower.contains(**r))
            .collect();
        if !missing.is_empty() {
            features_missing_roles.push(format!(
                "{} (missing: {})",
                feature.name,
                missing.iter().map(|r| **r).collect::<Vec<_>>().join(", ")
            ));
        }
    }
    let roles_ok = features_missing_roles.is_empty();
    checks.push(GroomingValidationCheck {
        name: "Role representation".to_string(),
        passed: roles_ok,
        evidence: if roles_ok {
            "All 4 roles represented in all features".to_string()
        } else {
            format!(
                "Missing role coverage: {}",
                features_missing_roles.join("; ")
            )
        },
        remediation: if !roles_ok {
            Some("Loop back to step-03: re-spawn missing role sub-agents".to_string())
        } else {
            None
        },
    });

    // Check 6: Conflict resolution (all found conflicts resolved)
    let unresolved = grooming.summary.conflicts_found - grooming.summary.conflicts_resolved;
    let conflicts_ok = unresolved == 0;
    checks.push(GroomingValidationCheck {
        name: "Conflict resolution".to_string(),
        passed: conflicts_ok,
        evidence: format!(
            "{} conflicts found, {} resolved",
            grooming.summary.conflicts_found,
            grooming.summary.conflicts_resolved
        ),
        remediation: if !conflicts_ok {
            Some(format!(
                "Loop back to step-04: {} unresolved conflicts",
                unresolved
            ))
        } else {
            None
        },
    });

    // Check 7: Hierarchy consistency (task_ids populated)
    let hierarchy_ok = !grooming.task_ids.is_empty() || grooming.features.is_empty();
    checks.push(GroomingValidationCheck {
        name: "Hierarchy consistency".to_string(),
        passed: hierarchy_ok,
        evidence: if hierarchy_ok {
            format!(
                "{} features with br task hierarchies",
                grooming.task_ids.len()
            )
        } else {
            "No br task hierarchies created".to_string()
        },
        remediation: if !hierarchy_ok {
            Some("Loop back to step-04: create br tasks from consolidated output".to_string())
        } else {
            None
        },
    });

    let all_passed = checks.iter().all(|c| c.passed);

    GroomingValidationReport {
        stream_name: grooming.stream_name.clone(),
        status: if all_passed {
            GroomingValidationStatus::Pass
        } else {
            GroomingValidationStatus::Fail
        },
        checks,
    }
}

/// Print grooming validation report.
pub fn print_validation_report(report: &GroomingValidationReport) {
    use colored::Colorize;

    println!();
    println!("{}", "GROOMING VALIDATION REPORT".bold());
    println!("{}", "═".repeat(40));
    println!("Stream: {}", report.stream_name);

    let status_str = match report.status {
        GroomingValidationStatus::Pass => "PASS".green().bold().to_string(),
        GroomingValidationStatus::Fail => "FAIL".red().bold().to_string(),
    };
    println!("Status: {}", status_str);
    println!();

    for check in &report.checks {
        let icon = if check.passed {
            "✓".green().to_string()
        } else {
            "✗".red().to_string()
        };
        println!("  [{}] {}: {}", icon, check.name, check.evidence);
        if let Some(ref rem) = check.remediation {
            println!("      → {}", rem.yellow());
        }
    }
}
