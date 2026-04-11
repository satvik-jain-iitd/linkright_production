use colored::Colorize;
use std::fs;
use std::path::{Path, PathBuf};

fn global_truss_dir() -> PathBuf {
    dirs::home_dir()
        .expect("Could not determine home directory")
        .join(".truss")
}

fn project_truss_dir() -> PathBuf {
    PathBuf::from(".truss")
}

fn create_dir(path: &Path) {
    if !path.exists() {
        fs::create_dir_all(path).unwrap_or_else(|e| {
            eprintln!("{} Failed to create {}: {}", "✗".red(), path.display(), e);
            std::process::exit(1);
        });
    }
}

fn write_if_missing(path: &Path, content: &str) {
    if !path.exists() {
        fs::write(path, content).unwrap_or_else(|e| {
            eprintln!("{} Failed to write {}: {}", "✗".red(), path.display(), e);
            std::process::exit(1);
        });
        println!("  {} {}", "created".green(), path.display());
    } else {
        println!("  {} {} (exists)", "skipped".yellow(), path.display());
    }
}

pub fn run() {
    println!("{}", "truss init".bold());
    println!("{}", "─".repeat(40));

    // ── Global ~/.truss/ ────────────────────────────────────────
    let global = global_truss_dir();
    create_dir(&global);
    create_dir(&global.join("domains"));
    create_dir(&global.join("core"));

    // Global manifest
    write_if_missing(
        &global.join("manifest.yaml"),
        "# Truss Manifest — installed domains and versions\n\
         version: 0.1.0\n\
         domains: []\n",
    );

    // Global core config
    write_if_missing(
        &global.join("core").join("config.yaml"),
        "# Truss Core Configuration\n\
         user_name: \"\"\n\
         communication_language: English\n\
         document_output_language: English\n\
         default_mode: autonomous  # autonomous | interactive\n\
         mem0_enabled: true\n\
         gitnexus_enabled: true\n",
    );

    // Routing table
    write_if_missing(
        &global.join("truss-help.csv"),
        "domain,workflow,name,code,description,sequence,required\n",
    );

    println!("\n{} Global ~/.truss/ initialized", "✓".green());

    // ── Project .truss/ ─────────────────────────────────────────
    let project = project_truss_dir();
    create_dir(&project);
    create_dir(&project.join("_progress"));
    create_dir(&project.join("_progress").join("outputs"));
    create_dir(&project.join("runs"));

    // Project config
    write_if_missing(
        &project.join("config.yaml"),
        "# Project-specific truss configuration\n\
         # Overrides global ~/.truss/core/config.yaml values\n\
         # domain: bmad-dev\n\
         # output_folder: .truss/_progress/outputs\n",
    );

    // State file
    write_if_missing(
        &project.join("_progress").join("state.yaml"),
        "# Truss execution state (machine-readable)\n\
         current_workflow: null\n\
         current_step: null\n\
         completed: []\n\
         streams: {}\n",
    );

    // Decisions log
    write_if_missing(
        &project.join("_progress").join("decisions.md"),
        "# Truss Decision Log\n\n\
         Rationale for key decisions made during execution.\n",
    );

    println!("{} Project .truss/ initialized", "✓".green());

    // ── Initialize .beads/ if not present ───────────────────────
    if !Path::new(".beads").exists() {
        println!("\n{}", "Initializing beads (br)...".dimmed());
        let output = std::process::Command::new("br")
            .arg("init")
            .output();
        match output {
            Ok(o) if o.status.success() => {
                println!("{} .beads/ initialized", "✓".green());
            }
            Ok(o) => {
                let stderr = String::from_utf8_lossy(&o.stderr);
                eprintln!("{} br init failed: {}", "✗".red(), stderr.trim());
            }
            Err(e) => {
                eprintln!("{} br not found: {} — install with: curl -fsSL https://raw.githubusercontent.com/Dicklesworthstone/beads_rust/main/install.sh | bash", "✗".red(), e);
            }
        }
    } else {
        println!("{} .beads/ already exists", "✓".green());
    }

    println!("\n{}", "Ready. Next: truss domain install <path>".bold());
}
