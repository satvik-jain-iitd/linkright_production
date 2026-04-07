use clap::{Parser, Subcommand};
use std::path::PathBuf;

mod commands;

#[derive(Parser)]
#[command(name = "truss", version, about = "Parallel Agent Orchestration Framework")]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Initialize .truss/ in current project
    Init,

    /// Domain management
    Domain {
        #[command(subcommand)]
        action: DomainAction,
    },

    /// Decompose goal into parallel streams
    Decompose {
        /// Path to goal document
        #[arg(long)]
        goal: PathBuf,

        /// Domain to use for decomposition
        #[arg(long)]
        domain: String,
    },

    /// Show execution dashboard
    Status {
        /// Run ID to check
        #[arg(long)]
        run: Option<String>,
    },

    /// Run quality gate inspection
    Inspect {
        /// Run ID to inspect
        #[arg(long)]
        run: Option<String>,
    },

    /// Run retrospective and output mem0 patterns
    Retro {
        /// Run ID for retrospective
        #[arg(long)]
        run: Option<String>,
    },

    /// Tail stream/role progress
    Log {
        /// Stream name to tail
        stream: String,

        /// Role to filter
        #[arg(long)]
        role: Option<String>,
    },

    /// Edit truss configuration
    Config,

    /// Pre-resolve config cascade into resolved-config.yaml
    ResolveConfig,

    /// Verify a step's output against its verify block
    Verify {
        /// Step ID to verify
        step_id: String,
    },
}

#[derive(Subcommand)]
enum DomainAction {
    /// List installed domains
    List,

    /// Build a new domain via interactive interview
    Build,

    /// Install a domain plugin
    Install {
        /// Path to domain directory
        path: PathBuf,
    },
}

fn main() {
    let cli = Cli::parse();

    match cli.command {
        Commands::Init => commands::init::run(),
        Commands::Domain { action } => match action {
            DomainAction::List => commands::domain::list(),
            DomainAction::Build => commands::domain::build(),
            DomainAction::Install { path } => commands::domain::install(&path),
        },
        Commands::Decompose { goal, domain } => commands::decompose::run(&goal, &domain),
        Commands::Status { run } => commands::status::run(run.as_deref()),
        Commands::Inspect { run } => commands::inspect::run(run.as_deref()),
        Commands::Retro { run } => commands::retro::run(run.as_deref()),
        Commands::Log { stream, role } => commands::log::run(&stream, role.as_deref()),
        Commands::Config => commands::config::run(),
        Commands::ResolveConfig => commands::resolve_config::run(),
        Commands::Verify { step_id } => commands::verify::run(&step_id),
    }
}
