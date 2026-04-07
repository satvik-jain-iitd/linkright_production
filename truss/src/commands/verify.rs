use colored::Colorize;
use std::collections::{HashMap, HashSet};
use std::path::Path;

use crate::analysis::graph;
use crate::models::decomposition::*;

/// Standalone verify command: load decomposition result and run validation.
pub fn run(step_id: &str) {
    if step_id != "step-01-decomposition-quality" {
        eprintln!(
            "{} Unknown validation step: {}",
            "✗".red(),
            step_id
        );
        eprintln!("Available: step-01-decomposition-quality");
        std::process::exit(1);
    }

    let streams_path = Path::new(".truss/_progress/outputs/streams.yaml");
    if !streams_path.exists() {
        eprintln!(
            "{} No decomposition found at {}",
            "✗".red(),
            streams_path.display()
        );
        eprintln!("Run `truss decompose` first.");
        std::process::exit(1);
    }

    let content = match std::fs::read_to_string(streams_path) {
        Ok(c) => c,
        Err(e) => {
            eprintln!("{} Failed to read: {}", "✗".red(), e);
            std::process::exit(1);
        }
    };

    let result: DecompositionResult = match serde_yaml::from_str(&content) {
        Ok(r) => r,
        Err(e) => {
            eprintln!("{} Failed to parse: {}", "✗".red(), e);
            std::process::exit(1);
        }
    };

    // Load domain config for max_streams and roles
    let domain_dir = dirs::home_dir()
        .expect("home dir")
        .join(".truss/domains/bmad-dev");
    let domain_config = crate::models::domain::DomainConfig::load(&domain_dir)
        .unwrap_or_else(|e| {
            eprintln!("{} {}", "✗".red(), e);
            std::process::exit(1);
        });

    let report = validate_decomposition(
        &result,
        domain_config.decomposition.max_streams,
        &domain_config.decomposition.default_roles,
    );

    // Print report
    println!("{}", "DECOMPOSITION VALIDATION REPORT".bold());
    println!("{}", "═".repeat(40));

    let status_str = match report.status {
        ValidationStatus::Pass => "PASS".green().bold().to_string(),
        ValidationStatus::Fail => "FAIL".red().bold().to_string(),
    };
    println!("Status: {}", status_str);
    println!();

    for check in &report.checks {
        let icon = if check.passed {
            "✓".green().to_string()
        } else {
            "✗".red().to_string()
        };
        println!("[{}] {}: {}", icon, check.name, check.evidence);
        if let Some(ref rem) = check.remediation {
            println!("    Remediation: {}", rem.yellow());
        }
    }

    let fail_count = report.checks.iter().filter(|c| !c.passed).count();
    if fail_count > 0 {
        println!(
            "\nIssues requiring remediation: {}",
            fail_count.to_string().red()
        );
        std::process::exit(1);
    }
}

/// Validate a DecompositionResult against domain constraints.
/// Used by both the verify command and the decompose orchestrator.
pub fn validate_decomposition(
    result: &DecompositionResult,
    max_streams: u32,
    default_roles: &[String],
) -> ValidationReport {
    let mut checks: Vec<ValidationCheck> = Vec::new();

    // Check 1: Stream count
    let stream_count = result.streams.len() as u32;
    let count_ok = stream_count >= 1 && stream_count <= max_streams;
    checks.push(ValidationCheck {
        name: "Stream count".to_string(),
        passed: count_ok,
        evidence: format!(
            "{} streams (allowed: 1-{})",
            stream_count, max_streams
        ),
        remediation: if !count_ok {
            Some(format!(
                "Merge streams to reduce count to {} or fewer",
                max_streams
            ))
        } else {
            None
        },
    });

    // Check 2: Brief completeness
    let mut incomplete_streams: Vec<String> = Vec::new();
    for stream in &result.streams {
        let mut missing: Vec<&str> = Vec::new();
        if stream.objective.is_empty() {
            missing.push("objective");
        }
        if stream.scope.is_empty() {
            missing.push("scope");
        }
        if stream.reserved_files.is_empty() && stream.scope.is_empty() {
            missing.push("file reservations or scope");
        }
        if stream.roles.is_empty() {
            missing.push("roles");
        }
        if !missing.is_empty() {
            incomplete_streams.push(format!("{} (missing: {})", stream.name, missing.join(", ")));
        }
    }
    let brief_ok = incomplete_streams.is_empty();
    checks.push(ValidationCheck {
        name: "Brief completeness".to_string(),
        passed: brief_ok,
        evidence: if brief_ok {
            format!("All {} streams have complete briefs", stream_count)
        } else {
            format!("Incomplete: {}", incomplete_streams.join("; "))
        },
        remediation: if !brief_ok {
            Some("Add missing sections to incomplete stream briefs".to_string())
        } else {
            None
        },
    });

    // Check 3: File exclusivity
    let mut file_claims: HashMap<String, Vec<String>> = HashMap::new();
    for stream in &result.streams {
        for file in &stream.reserved_files {
            file_claims
                .entry(file.clone())
                .or_default()
                .push(stream.name.clone());
        }
    }
    let conflicts: Vec<(String, Vec<String>)> = file_claims
        .into_iter()
        .filter(|(_, owners)| owners.len() > 1)
        .collect();
    let excl_ok = conflicts.is_empty();
    checks.push(ValidationCheck {
        name: "File exclusivity".to_string(),
        passed: excl_ok,
        evidence: if excl_ok {
            "No file reservation conflicts".to_string()
        } else {
            let descs: Vec<String> = conflicts
                .iter()
                .take(5)
                .map(|(f, owners)| format!("{} claimed by: {}", f, owners.join(", ")))
                .collect();
            format!("{} conflicts: {}", conflicts.len(), descs.join("; "))
        },
        remediation: if !excl_ok {
            Some("Move conflicting files to shared_files with a single owner".to_string())
        } else {
            None
        },
    });

    // Check 4: Dependency acyclicity
    let deps: Vec<ClusterDependency> = result
        .dependency_graph
        .iter()
        .map(|(from, to)| ClusterDependency {
            from_cluster: from.clone(),
            to_cluster: to.clone(),
            shared_symbols: vec![],
        })
        .collect();
    let (dep_graph, _) = graph::build_dependency_graph(&deps);
    let acyclic_result = graph::check_acyclicity(&dep_graph);
    let acyclic_ok = acyclic_result.is_ok();
    checks.push(ValidationCheck {
        name: "Dependency acyclicity".to_string(),
        passed: acyclic_ok,
        evidence: if acyclic_ok {
            "Topological sort successful — no cycles".to_string()
        } else {
            acyclic_result.unwrap_err()
        },
        remediation: if !acyclic_ok {
            Some("Break the cycle by removing the weakest dependency or extracting a shared stream".to_string())
        } else {
            None
        },
    });

    // Check 5: Role coverage
    let role_set: HashSet<&str> = default_roles.iter().map(|r| r.as_str()).collect();
    let mut missing_roles: Vec<String> = Vec::new();
    for stream in &result.streams {
        let stream_roles: HashSet<&str> = stream.roles.keys().map(|r| r.as_str()).collect();
        let missing: Vec<&&str> = role_set.difference(&stream_roles).collect();
        if !missing.is_empty() {
            missing_roles.push(format!(
                "{} missing: {}",
                stream.name,
                missing.iter().map(|r| **r).collect::<Vec<_>>().join(", ")
            ));
        }
    }
    let roles_ok = missing_roles.is_empty();
    checks.push(ValidationCheck {
        name: "Role coverage".to_string(),
        passed: roles_ok,
        evidence: if roles_ok {
            format!(
                "All streams have all {} roles",
                default_roles.len()
            )
        } else {
            format!("Missing roles: {}", missing_roles.join("; "))
        },
        remediation: if !roles_ok {
            Some("Assign all default roles to every stream".to_string())
        } else {
            None
        },
    });

    // Overall status
    let all_passed = checks.iter().all(|c| c.passed);
    ValidationReport {
        status: if all_passed {
            ValidationStatus::Pass
        } else {
            ValidationStatus::Fail
        },
        checks,
    }
}
