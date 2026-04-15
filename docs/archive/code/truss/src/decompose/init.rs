use std::path::Path;

use crate::models::config::ConfigMap;
use crate::models::decomposition::ContextBundle;
use crate::models::domain::DomainConfig;

/// Step 1: Load goal document, validate domain config, build ContextBundle.
pub fn run(goal_path: &Path, domain_name: &str) -> Result<ContextBundle, String> {
    // 1. Load goal document
    if !goal_path.exists() {
        return Err(format!("Goal document not found: {}", goal_path.display()));
    }

    let goal_text = std::fs::read_to_string(goal_path)
        .map_err(|e| format!("Failed to read goal document: {}", e))?;

    if goal_text.trim().is_empty() {
        return Err("Goal document is empty".to_string());
    }

    // 2. Validate domain config
    let domain_dir = dirs::home_dir()
        .ok_or("Could not determine home directory")?
        .join(".truss")
        .join("domains")
        .join(domain_name);

    let domain_config = DomainConfig::load(&domain_dir)?;
    validate_domain_config(&domain_config)?;

    // 3. Validate runtime config
    let runtime_config_path = domain_dir.join("config.yaml");
    let runtime_config = ConfigMap::load(&runtime_config_path)?;
    validate_runtime_config(&runtime_config)?;

    let mem0_scope = runtime_config.get_str("mem0_scope");

    // 4. Build context bundle
    Ok(ContextBundle {
        goal_text,
        goal_path: goal_path.to_path_buf(),
        domain_name: domain_config.name.clone(),
        max_streams: domain_config.decomposition.max_streams,
        default_roles: domain_config.decomposition.default_roles.clone(),
        coordinator_role: domain_config.team.coordinator_role.clone(),
        strategy: domain_config.decomposition.strategy.clone(),
        mem0_scope,
        prior_patterns: vec![], // mem0 integration is handled by the Claude skill layer
    })
}

fn validate_domain_config(config: &DomainConfig) -> Result<(), String> {
    if config.name.is_empty() {
        return Err("domain.yaml: 'name' field is empty".to_string());
    }
    if config.decomposition.strategy.is_empty() {
        return Err("domain.yaml: 'decomposition.strategy' is empty".to_string());
    }
    if config.decomposition.max_streams == 0 {
        return Err("domain.yaml: 'decomposition.max_streams' must be > 0".to_string());
    }
    if config.decomposition.default_roles.is_empty() {
        return Err("domain.yaml: 'decomposition.default_roles' is empty".to_string());
    }
    if config.team.roles.is_empty() {
        return Err("domain.yaml: 'team.roles' is empty".to_string());
    }
    if config.team.coordinator_role.is_empty() {
        return Err("domain.yaml: 'team.coordinator_role' is empty".to_string());
    }
    if !config.gates.iter().any(|g| g.required) {
        return Err("domain.yaml: at least one gate must be required".to_string());
    }

    Ok(())
}

fn validate_runtime_config(config: &ConfigMap) -> Result<(), String> {
    // max_concurrent_streams — optional but must be positive if present
    if let Some(val) = config.0.get("max_concurrent_streams") {
        if let Some(n) = val.as_u64() {
            if n == 0 {
                return Err("config.yaml: 'max_concurrent_streams' must be > 0".to_string());
            }
        }
    }

    Ok(())
}
