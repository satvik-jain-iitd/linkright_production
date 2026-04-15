use serde::Deserialize;
use std::collections::HashMap;
use std::path::Path;
use std::process::Command;

// ── Parsed types from GitNexus KG ──────────────────────────

#[derive(Debug, Deserialize, Clone)]
pub struct GnFile {
    pub file_path: String,
    pub name: String,
}

#[derive(Debug, Deserialize, Clone)]
pub struct GnCommunity {
    pub id: String,
    pub heuristic_label: String,
    pub cohesion: f64,
    pub symbol_count: i32,
}

#[derive(Debug, Deserialize)]
struct CypherOutput {
    markdown: Option<String>,
    row_count: Option<i64>,
    error: Option<String>,
}

// ── Public API ─────────────────────────────────────────────

/// Check if gitnexus CLI is available on PATH.
pub fn is_available() -> bool {
    Command::new("gitnexus")
        .arg("--version")
        .output()
        .is_ok()
}

/// Run `gitnexus analyze <path>` to index a repository.
pub fn analyze(repo_path: &Path) -> Result<(), String> {
    let output = Command::new("gitnexus")
        .arg("analyze")
        .arg(repo_path)
        .output()
        .map_err(|e| format!("Failed to run gitnexus analyze: {}", e))?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        return Err(format!("gitnexus analyze failed: {}", stderr.trim()));
    }

    Ok(())
}

/// Check if a repo is already indexed by running `gitnexus status` in the repo dir.
pub fn is_indexed(repo_path: &Path) -> bool {
    let output = Command::new("gitnexus")
        .arg("status")
        .current_dir(repo_path)
        .output();

    match output {
        Ok(o) => {
            let stdout = String::from_utf8_lossy(&o.stdout);
            !stdout.contains("not indexed")
        }
        Err(_) => false,
    }
}

/// Resolve the repo name for a given path from `gitnexus list`.
///
/// gitnexus list output format:
/// ```
/// Indexed Repositories (N)
///
///   RepoName
///     Path:    /full/path/to/repo
///     ...
/// ```
pub fn resolve_repo_name(repo_path: &Path) -> Result<String, String> {
    let canonical = repo_path
        .canonicalize()
        .map_err(|e| format!("Cannot resolve path: {}", e))?;
    let canonical_str = canonical.to_string_lossy().to_string();

    let output = Command::new("gitnexus")
        .arg("list")
        .output()
        .map_err(|e| format!("Failed to run gitnexus list: {}", e))?;

    let stdout = String::from_utf8_lossy(&output.stdout);
    let lines: Vec<&str> = stdout.lines().collect();

    // Find the line containing our path, then look backwards for the repo name
    for (i, line) in lines.iter().enumerate() {
        if line.contains(&canonical_str) {
            // Walk backwards to find the repo name (first non-empty, non-header line above)
            for j in (0..i).rev() {
                let candidate = lines[j].trim();
                if candidate.is_empty()
                    || candidate.starts_with("Indexed")
                    || candidate.contains(':')
                {
                    continue;
                }
                return Ok(candidate.to_string());
            }
        }
    }

    // Fallback: use the directory name
    let name = canonical
        .file_name()
        .map(|n| n.to_string_lossy().to_string())
        .unwrap_or_else(|| "repo".to_string());
    Ok(name)
}

/// Run a Cypher query against a repo and return raw JSON output.
fn cypher_raw(query: &str, repo_name: &str) -> Result<CypherOutput, String> {
    let output = Command::new("gitnexus")
        .arg("cypher")
        .arg(query)
        .arg("-r")
        .arg(repo_name)
        .output()
        .map_err(|e| format!("Failed to run gitnexus cypher: {}", e))?;

    let stdout = String::from_utf8_lossy(&output.stdout);

    let parsed: CypherOutput = serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse cypher output: {} — raw: {}", e, stdout))?;

    if let Some(ref err) = parsed.error {
        return Err(format!("Cypher error: {}", err));
    }

    Ok(parsed)
}

/// Parse a markdown table from cypher output into rows of column values.
/// Returns (headers, rows) where each row is a Vec<String>.
fn parse_markdown_table(markdown: &str) -> (Vec<String>, Vec<Vec<String>>) {
    let lines: Vec<&str> = markdown.lines().collect();
    if lines.len() < 3 {
        return (vec![], vec![]);
    }

    let parse_row = |line: &str| -> Vec<String> {
        line.split('|')
            .map(|cell| cell.trim().to_string())
            .filter(|cell| !cell.is_empty())
            .collect()
    };

    let headers = parse_row(lines[0]);
    // lines[1] is the separator (| --- | --- |)
    let rows: Vec<Vec<String>> = lines[2..]
        .iter()
        .map(|line| parse_row(line))
        .filter(|row| !row.is_empty())
        .collect();

    (headers, rows)
}

/// Query file count from the KG (lightweight check, no 64KB limit risk).
pub fn query_file_count(repo_name: &str) -> Result<usize, String> {
    let output = cypher_raw(
        "MATCH (f:File) RETURN count(f) AS cnt",
        repo_name,
    )?;

    let markdown = output.markdown.unwrap_or_default();
    let (_, rows) = parse_markdown_table(&markdown);

    Ok(rows
        .first()
        .and_then(|row| row.first())
        .and_then(|v| v.parse().ok())
        .unwrap_or(0))
}

/// Query file-to-file IMPORTS edges (paginated to avoid 64KB limit).
pub fn query_file_imports(repo_name: &str) -> Result<Vec<(String, String)>, String> {
    let mut results: Vec<(String, String)> = Vec::new();
    let page_size = 300;
    let mut offset = 0;

    loop {
        let query = format!(
            "MATCH (a:File)-[r {{type: 'IMPORTS'}}]->(b:File) RETURN a.filePath AS from_file, b.filePath AS to_file SKIP {} LIMIT {}",
            offset, page_size
        );

        let output = cypher_raw(&query, repo_name)?;
        let markdown = output.markdown.unwrap_or_default();
        let (_, rows) = parse_markdown_table(&markdown);

        if rows.is_empty() {
            break;
        }

        for row in &rows {
            if row.len() >= 2 {
                results.push((row[0].clone(), row[1].clone()));
            }
        }

        if rows.len() < page_size {
            break;
        }

        offset += page_size;
    }

    Ok(results)
}

/// Query all Community nodes.
pub fn query_communities(repo_name: &str) -> Result<Vec<GnCommunity>, String> {
    let output = cypher_raw(
        "MATCH (c:Community) RETURN c.id, c.heuristicLabel, c.cohesion, c.symbolCount",
        repo_name,
    )?;

    let markdown = output.markdown.unwrap_or_default();
    let (_, rows) = parse_markdown_table(&markdown);

    Ok(rows
        .into_iter()
        .filter_map(|row| {
            if row.len() >= 4 {
                Some(GnCommunity {
                    id: row[0].clone(),
                    heuristic_label: row[1].clone(),
                    cohesion: row[2].parse().unwrap_or(0.0),
                    symbol_count: row[3].parse().unwrap_or(0),
                })
            } else {
                None
            }
        })
        .collect())
}

/// Query community membership: community_id → list of unique file paths.
/// Uses pagination (SKIP/LIMIT) to avoid GitNexus 64KB output limit.
pub fn query_community_files(repo_name: &str) -> Result<HashMap<String, Vec<String>>, String> {
    let mut community_files: HashMap<String, Vec<String>> = HashMap::new();
    let page_size = 500;
    let mut offset = 0;

    loop {
        let query = format!(
            "MATCH (sym)-[r {{type: 'MEMBER_OF'}}]->(c:Community) RETURN c.id AS community_id, sym.filePath AS file_path SKIP {} LIMIT {}",
            offset, page_size
        );

        let output = cypher_raw(&query, repo_name)?;
        let markdown = output.markdown.unwrap_or_default();
        let (_, rows) = parse_markdown_table(&markdown);

        if rows.is_empty() {
            break;
        }

        for row in &rows {
            if row.len() >= 2 {
                let community_id = &row[0];
                let file_path = &row[1];
                if !file_path.is_empty() {
                    community_files
                        .entry(community_id.clone())
                        .or_default()
                        .push(file_path.clone());
                }
            }
        }

        if rows.len() < page_size {
            break;
        }

        offset += page_size;
    }

    // Deduplicate file paths per community
    for files in community_files.values_mut() {
        files.sort();
        files.dedup();
    }

    Ok(community_files)
}

/// Query cross-community edges (calls between different communities).
pub fn query_cross_community_edges(
    repo_name: &str,
) -> Result<Vec<(String, String)>, String> {
    let output = cypher_raw(
        "MATCH (a)-[r {type: 'CALLS'}]->(b), (a)-[{type: 'MEMBER_OF'}]->(ca:Community), (b)-[{type: 'MEMBER_OF'}]->(cb:Community) WHERE ca.id <> cb.id RETURN DISTINCT ca.id AS from_comm, cb.id AS to_comm",
        repo_name,
    )?;

    let markdown = output.markdown.unwrap_or_default();
    let (_, rows) = parse_markdown_table(&markdown);

    Ok(rows
        .into_iter()
        .filter_map(|row| {
            if row.len() >= 2 {
                Some((row[0].clone(), row[1].clone()))
            } else {
                None
            }
        })
        .collect())
}

/// Query hot spot files (most symbols defined).
pub fn query_hot_spots(repo_name: &str) -> Result<Vec<String>, String> {
    let output = cypher_raw(
        "MATCH (f:File)-[r {type: 'DEFINES'}]->(sym) RETURN f.filePath, count(sym) AS cnt ORDER BY cnt DESC LIMIT 10",
        repo_name,
    )?;

    let markdown = output.markdown.unwrap_or_default();
    let (_, rows) = parse_markdown_table(&markdown);

    Ok(rows
        .into_iter()
        .filter_map(|row| {
            if !row.is_empty() {
                Some(row[0].clone())
            } else {
                None
            }
        })
        .collect())
}
