use colored::Colorize;
use std::fs;
use std::path::PathBuf;

fn global_config_path() -> PathBuf {
    dirs::home_dir()
        .expect("Could not determine home directory")
        .join(".truss")
        .join("core")
        .join("config.yaml")
}

fn project_config_path() -> PathBuf {
    PathBuf::from(".truss").join("config.yaml")
}

pub fn run() {
    println!("{}", "truss config".bold());
    println!("{}", "─".repeat(40));

    // Show global config
    let global = global_config_path();
    println!("\n{} {}", "Global:".bold(), global.display());
    match fs::read_to_string(&global) {
        Ok(content) => {
            for line in content.lines() {
                if line.starts_with('#') {
                    println!("  {}", line.dimmed());
                } else if !line.trim().is_empty() {
                    println!("  {}", line);
                }
            }
        }
        Err(_) => println!("  {} Not found — run truss init", "(missing)".yellow()),
    }

    // Show project config if present
    let project = project_config_path();
    if project.exists() {
        println!("\n{} {}", "Project:".bold(), project.display());
        match fs::read_to_string(&project) {
            Ok(content) => {
                for line in content.lines() {
                    if line.starts_with('#') {
                        println!("  {}", line.dimmed());
                    } else if !line.trim().is_empty() {
                        println!("  {}", line);
                    }
                }
            }
            Err(e) => println!("  {} {}", "Error:".red(), e),
        }
    } else {
        println!("\n{} No project config (not in a truss project)", "Project:".bold());
    }

    println!("\n{}", "Edit directly or use: truss resolve-config to merge".dimmed());
}
