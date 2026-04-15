use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::Path;

/// A flexible config map that supports cascading merges.
/// Each level (core, domain, project) is loaded as a flat key-value map.
#[derive(Debug, Default, Serialize, Deserialize, Clone)]
pub struct ConfigMap(pub HashMap<String, serde_yaml::Value>);

impl ConfigMap {
    /// Load a config.yaml file into a ConfigMap.
    /// Returns an empty map if the file doesn't exist.
    pub fn load(path: &Path) -> Result<Self, String> {
        if !path.exists() {
            return Ok(ConfigMap::default());
        }

        let content = std::fs::read_to_string(path)
            .map_err(|e| format!("Failed to read {}: {}", path.display(), e))?;

        // Handle empty files or files with only comments
        let parsed: Option<HashMap<String, serde_yaml::Value>> =
            serde_yaml::from_str(&content)
                .map_err(|e| format!("Failed to parse {}: {}", path.display(), e))?;

        Ok(ConfigMap(parsed.unwrap_or_default()))
    }

    /// Merge another ConfigMap into this one (other's values take precedence).
    pub fn merge(&mut self, other: &ConfigMap) {
        for (key, value) in &other.0 {
            self.0.insert(key.clone(), value.clone());
        }
    }

    /// Get a string value by key.
    pub fn get_str(&self, key: &str) -> Option<String> {
        self.0.get(key).and_then(|v| match v {
            serde_yaml::Value::String(s) => Some(s.clone()),
            _ => None,
        })
    }

    /// Serialize to a YAML string for display or writing.
    pub fn to_yaml(&self) -> Result<String, String> {
        serde_yaml::to_string(&self.0)
            .map_err(|e| format!("Failed to serialize config: {}", e))
    }
}
