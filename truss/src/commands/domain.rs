use colored::Colorize;
use std::fs;
use std::path::Path;

use crate::models::{DomainConfig, Manifest};

fn global_domains_dir() -> std::path::PathBuf {
    dirs::home_dir()
        .expect("Could not determine home directory")
        .join(".truss")
        .join("domains")
}

pub fn list() {
    let domains_dir = global_domains_dir();
    println!("{}", "Installed domains:".bold());
    println!("{}", "─".repeat(50));

    if !domains_dir.exists() {
        println!("  (none — run truss domain install <path>)");
        return;
    }

    let mut found = false;
    if let Ok(entries) = fs::read_dir(&domains_dir) {
        for entry in entries.flatten() {
            if entry.path().is_dir() {
                let domain_dir = entry.path();
                match DomainConfig::load(&domain_dir) {
                    Ok(config) => {
                        found = true;
                        let name_str = format!("{} v{}", config.name, config.version);
                        println!("  {} {}", "•".green(), name_str.bold());

                        if !config.description.is_empty() {
                            println!("    {}", config.description.dimmed());
                        }

                        let wf_count = config.workflows.len();
                        let role_count = config.team.roles.len();
                        let gate_count = config.gates.len();

                        let mut stats = vec![];
                        if wf_count > 0 {
                            stats.push(format!("{} workflows", wf_count));
                        }
                        if role_count > 0 {
                            stats.push(format!("{} roles", role_count));
                        }
                        if gate_count > 0 {
                            stats.push(format!("{} gates", gate_count));
                        }

                        if !stats.is_empty() {
                            println!("    {}", stats.join(" | ").dimmed());
                        }

                        // Show strategy
                        println!(
                            "    strategy: {} | max streams: {}",
                            config.decomposition.strategy.cyan(),
                            config.decomposition.max_streams
                        );
                        println!();
                    }
                    Err(e) => {
                        let name = entry.file_name().to_string_lossy().to_string();
                        println!("  {} {} ({})", "•".yellow(), name, e);
                    }
                }
            }
        }
    }

    if !found {
        println!("  (none — run truss domain install <path>)");
    }
}

pub fn build() {
    println!("{}", "truss domain build".bold());
    println!("Interactive domain builder — not yet implemented.");
    println!("This will interview you to generate a custom domain plugin.");
}

pub fn install(path: &Path) {
    let domains_dir = global_domains_dir();

    if !path.exists() || !path.is_dir() {
        eprintln!(
            "{} Path does not exist or is not a directory: {}",
            "✗".red(),
            path.display()
        );
        std::process::exit(1);
    }

    let domain_yaml = path.join("domain.yaml");
    if !domain_yaml.exists() {
        eprintln!(
            "{} No domain.yaml found in {}",
            "✗".red(),
            path.display()
        );
        std::process::exit(1);
    }

    // Parse domain.yaml to get name and version
    let domain_config = match DomainConfig::load(path) {
        Ok(c) => c,
        Err(e) => {
            eprintln!("{} Failed to parse domain.yaml: {}", "✗".red(), e);
            std::process::exit(1);
        }
    };

    let domain_name = &domain_config.name;
    let domain_version = &domain_config.version;
    let target = domains_dir.join(domain_name);

    if target.exists() {
        println!(
            "{} Domain '{}' already installed — updating",
            "⟳".yellow(),
            domain_name
        );
        fs::remove_dir_all(&target).ok();
    }

    // Copy domain directory
    copy_dir_recursive(path, &target).unwrap_or_else(|e| {
        eprintln!("{} Failed to install domain: {}", "✗".red(), e);
        std::process::exit(1);
    });

    println!(
        "{} Domain '{}' v{} installed to {}",
        "✓".green(),
        domain_name,
        domain_version,
        target.display()
    );

    // Update manifest.yaml
    match Manifest::load() {
        Ok(mut manifest) => {
            manifest.upsert_domain(
                domain_name,
                domain_version,
                &target.display().to_string(),
            );
            match manifest.save() {
                Ok(_) => {
                    println!(
                        "{} Updated manifest.yaml",
                        "✓".green()
                    );
                }
                Err(e) => {
                    eprintln!("{} Failed to update manifest: {}", "✗".red(), e);
                }
            }
        }
        Err(e) => {
            eprintln!(
                "{} Failed to load manifest (domain installed but manifest not updated): {}",
                "✗".red(),
                e
            );
        }
    }

    // Show domain summary
    println!("\n{}", "Domain summary:".bold());
    if !domain_config.description.is_empty() {
        println!("  {}", domain_config.description);
    }
    println!(
        "  {} workflows, {} roles, {} gates",
        domain_config.workflows.len(),
        domain_config.team.roles.len(),
        domain_config.gates.len()
    );
    println!(
        "  strategy: {} | max streams: {}",
        domain_config.decomposition.strategy,
        domain_config.decomposition.max_streams
    );
}

fn copy_dir_recursive(src: &Path, dst: &Path) -> std::io::Result<()> {
    fs::create_dir_all(dst)?;
    for entry in fs::read_dir(src)? {
        let entry = entry?;
        let src_path = entry.path();
        let dst_path = dst.join(entry.file_name());
        if src_path.is_dir() {
            copy_dir_recursive(&src_path, &dst_path)?;
        } else {
            fs::copy(&src_path, &dst_path)?;
        }
    }
    Ok(())
}
