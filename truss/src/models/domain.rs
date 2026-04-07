use serde::{Deserialize, Serialize};

/// Represents a domain's domain.yaml configuration.
#[derive(Debug, Serialize, Deserialize)]
pub struct DomainConfig {
    pub name: String,
    #[serde(default)]
    pub version: String,
    #[serde(default)]
    pub description: String,
    #[serde(default)]
    pub decomposition: DecompositionConfig,
    #[serde(default)]
    pub team: TeamConfig,
    #[serde(default)]
    pub gates: Vec<GateConfig>,
    #[serde(default)]
    pub workflows: Vec<WorkflowConfig>,
}

#[derive(Debug, Default, Serialize, Deserialize)]
pub struct DecompositionConfig {
    #[serde(default = "default_strategy")]
    pub strategy: String,
    #[serde(default = "default_max_streams")]
    pub max_streams: u32,
    #[serde(default)]
    pub default_roles: Vec<String>,
}

#[derive(Debug, Default, Serialize, Deserialize)]
pub struct TeamConfig {
    #[serde(default)]
    pub roles: Vec<String>,
    #[serde(default)]
    pub coordinator_role: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct GateConfig {
    pub name: String,
    #[serde(default)]
    pub workflow: String,
    #[serde(default)]
    pub required: bool,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct WorkflowConfig {
    pub name: String,
    #[serde(default, rename = "type")]
    pub workflow_type: String,
    #[serde(default)]
    pub path: String,
}

fn default_strategy() -> String {
    "code-graph".to_string()
}

fn default_max_streams() -> u32 {
    5
}

impl DomainConfig {
    /// Load a domain.yaml from a given directory path.
    pub fn load(domain_dir: &std::path::Path) -> Result<Self, String> {
        let path = domain_dir.join("domain.yaml");
        if !path.exists() {
            return Err(format!("No domain.yaml in {}", domain_dir.display()));
        }

        let content = std::fs::read_to_string(&path)
            .map_err(|e| format!("Failed to read {}: {}", path.display(), e))?;

        serde_yaml::from_str(&content)
            .map_err(|e| format!("Failed to parse {}: {}", path.display(), e))
    }
}
