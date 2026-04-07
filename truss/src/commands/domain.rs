use colored::Colorize;
use std::fs;
use std::path::Path;

fn global_domains_dir() -> std::path::PathBuf {
    dirs::home_dir()
        .expect("Could not determine home directory")
        .join(".truss")
        .join("domains")
}

pub fn list() {
    let domains_dir = global_domains_dir();
    println!("{}", "Installed domains:".bold());
    println!("{}", "─".repeat(40));

    if !domains_dir.exists() {
        println!("  (none — run truss domain install <path>)");
        return;
    }

    let mut found = false;
    if let Ok(entries) = fs::read_dir(&domains_dir) {
        for entry in entries.flatten() {
            if entry.path().is_dir() {
                let name = entry.file_name().to_string_lossy().to_string();
                let config_path = entry.path().join("domain.yaml");
                if config_path.exists() {
                    println!("  {} {}", "•".green(), name);
                    found = true;
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
        eprintln!("{} Path does not exist or is not a directory: {}", "✗".red(), path.display());
        std::process::exit(1);
    }

    let domain_yaml = path.join("domain.yaml");
    if !domain_yaml.exists() {
        eprintln!("{} No domain.yaml found in {}", "✗".red(), path.display());
        std::process::exit(1);
    }

    let domain_name = path.file_name().unwrap().to_string_lossy().to_string();
    let target = domains_dir.join(&domain_name);

    if target.exists() {
        println!("{} Domain '{}' already installed — updating", "⟳".yellow(), domain_name);
        fs::remove_dir_all(&target).ok();
    }

    // Copy domain directory
    copy_dir_recursive(path, &target).unwrap_or_else(|e| {
        eprintln!("{} Failed to install domain: {}", "✗".red(), e);
        std::process::exit(1);
    });

    println!("{} Domain '{}' installed to {}", "✓".green(), domain_name, target.display());
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
