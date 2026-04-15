use serde::{Deserialize, Serialize};

/// Represents ~/.truss/manifest.yaml — the registry of installed domains.
#[derive(Debug, Serialize, Deserialize)]
pub struct Manifest {
    #[serde(default = "default_version")]
    pub version: String,
    #[serde(default)]
    pub domains: Vec<DomainEntry>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct DomainEntry {
    pub name: String,
    #[serde(default)]
    pub version: String,
    #[serde(default)]
    pub path: String,
}

fn default_version() -> String {
    "0.1.0".to_string()
}

impl Manifest {
    /// Load manifest from ~/.truss/manifest.yaml
    pub fn load() -> Result<Self, String> {
        let path = dirs::home_dir()
            .ok_or("Could not determine home directory")?
            .join(".truss")
            .join("manifest.yaml");

        if !path.exists() {
            return Ok(Manifest {
                version: default_version(),
                domains: vec![],
            });
        }

        let content = std::fs::read_to_string(&path)
            .map_err(|e| format!("Failed to read {}: {}", path.display(), e))?;

        serde_yaml::from_str(&content)
            .map_err(|e| format!("Failed to parse {}: {}", path.display(), e))
    }

    /// Save manifest back to ~/.truss/manifest.yaml
    pub fn save(&self) -> Result<(), String> {
        let path = dirs::home_dir()
            .ok_or("Could not determine home directory")?
            .join(".truss")
            .join("manifest.yaml");

        let content = serde_yaml::to_string(self)
            .map_err(|e| format!("Failed to serialize manifest: {}", e))?;

        std::fs::write(&path, content)
            .map_err(|e| format!("Failed to write {}: {}", path.display(), e))
    }

    /// Add or update a domain entry in the manifest.
    pub fn upsert_domain(&mut self, name: &str, version: &str, path: &str) {
        if let Some(existing) = self.domains.iter_mut().find(|d| d.name == name) {
            existing.version = version.to_string();
            existing.path = path.to_string();
        } else {
            self.domains.push(DomainEntry {
                name: name.to_string(),
                version: version.to_string(),
                path: path.to_string(),
            });
        }
    }
}
