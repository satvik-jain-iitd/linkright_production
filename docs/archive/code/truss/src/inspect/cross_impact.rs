use std::collections::HashMap;

use crate::models::decomposition::DecompositionResult;
use crate::models::inspection::{ConflictSeverity, CrossImpactResult, FileConflict};

/// Step 3: Check for cross-stream file reservation conflicts.
pub fn check_cross_impact(decomposition: &DecompositionResult) -> CrossImpactResult {
    // Build file → streams map
    let mut file_claims: HashMap<String, Vec<String>> = HashMap::new();
    let mut total_files = 0u32;

    for stream in &decomposition.streams {
        for file in &stream.reserved_files {
            file_claims
                .entry(file.clone())
                .or_default()
                .push(stream.name.clone());
            total_files += 1;
        }
    }

    // Detect direct conflicts
    let mut conflicts: Vec<FileConflict> = Vec::new();

    for (file, streams) in &file_claims {
        if streams.len() > 1 {
            // Both modify — CRITICAL
            let conflict = FileConflict {
                file_path: file.clone(),
                streams: streams.clone(),
                severity: ConflictSeverity::Critical,
                resolution: format!(
                    "Assign {} to a single owning stream. Other streams read via interface boundary.",
                    file
                ),
            };
            conflicts.push(conflict);
        }
    }

    // Detect transitive conflicts from dependency graph
    // Two streams in the same dependency chain that modify overlapping directories
    let mut transitive: Vec<FileConflict> = Vec::new();
    for (from, to) in &decomposition.dependency_graph {
        let from_stream = decomposition.streams.iter().find(|s| &s.name == from);
        let to_stream = decomposition.streams.iter().find(|s| &s.name == to);

        if let (Some(from_s), Some(to_s)) = (from_stream, to_stream) {
            // Check if they share common parent directories (might indicate coupling)
            let from_dirs: std::collections::HashSet<String> = from_s.reserved_files
                .iter()
                .filter_map(|f| {
                    std::path::Path::new(f)
                        .parent()
                        .map(|p| p.to_string_lossy().to_string())
                })
                .collect();

            let to_dirs: std::collections::HashSet<String> = to_s.reserved_files
                .iter()
                .filter_map(|f| {
                    std::path::Path::new(f)
                        .parent()
                        .map(|p| p.to_string_lossy().to_string())
                })
                .collect();

            let shared_dirs: Vec<&String> = from_dirs.intersection(&to_dirs).collect();
            if !shared_dirs.is_empty() && shared_dirs.len() > 1 {
                // Multiple shared directories between dependent streams — potential coupling
                transitive.push(FileConflict {
                    file_path: format!("shared dirs: {}", shared_dirs.iter().take(3).map(|s| s.as_str()).collect::<Vec<_>>().join(", ")),
                    streams: vec![from.clone(), to.clone()],
                    severity: ConflictSeverity::Medium,
                    resolution: format!(
                        "Streams {} and {} share {} directories. Verify interface boundaries are stable.",
                        from, to, shared_dirs.len()
                    ),
                });
            }
        }
    }

    conflicts.extend(transitive);

    let critical_count = conflicts.iter().filter(|c| c.severity == ConflictSeverity::Critical).count() as u32;
    let high_count = conflicts.iter().filter(|c| c.severity == ConflictSeverity::High).count() as u32;
    let medium_count = conflicts.iter().filter(|c| c.severity == ConflictSeverity::Medium).count() as u32;
    let low_count = conflicts.iter().filter(|c| c.severity == ConflictSeverity::Low).count() as u32;

    CrossImpactResult {
        files_scanned: total_files,
        conflicts,
        critical_count,
        high_count,
        medium_count,
        low_count,
        impact_check_enabled: true,
    }
}

pub fn print_cross_impact_report(result: &CrossImpactResult) {
    use colored::Colorize;

    println!("{}", "CROSS-IMPACT ANALYSIS".bold());
    println!("{}", "─".repeat(60));

    if !result.impact_check_enabled {
        println!("  {} Cross-impact analysis disabled by config", "ℹ".dimmed());
        return;
    }

    println!(
        "Files scanned: {}  Conflicts: {} CRITICAL, {} HIGH, {} MEDIUM, {} LOW",
        result.files_scanned,
        result.critical_count,
        result.high_count,
        result.medium_count,
        result.low_count
    );
    println!();

    if result.conflicts.is_empty() {
        println!("  {} No file conflicts detected", "✓".green());
        return;
    }

    for (i, conflict) in result.conflicts.iter().enumerate() {
        let severity_str = match conflict.severity {
            ConflictSeverity::Critical => "CRITICAL".red().bold().to_string(),
            ConflictSeverity::High => "HIGH".red().to_string(),
            ConflictSeverity::Medium => "MEDIUM".yellow().to_string(),
            ConflictSeverity::Low => "LOW".dimmed().to_string(),
        };

        println!(
            "  {}. [{}] {}",
            i + 1,
            severity_str,
            conflict.file_path
        );
        println!(
            "     Streams: {}",
            conflict.streams.join(" ↔ ")
        );
        println!("     Resolution: {}", conflict.resolution);
        println!();
    }
}
