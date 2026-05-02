#!/usr/bin/env bash
# LinkRight one-line installer
#
# Usage:
#   curl -fsSL https://install.linkright.in | bash
#   curl -fsSL https://install.linkright.in | bash -s -- --no-setup-hint
#
# What it does:
#   1. Detects OS + architecture (macOS Intel/ARM, Linux Debian/Ubuntu/Arch/Fedora)
#   2. Ensures Python 3.9+ is installed (uses Homebrew on macOS, apt/dnf/pacman on Linux)
#   3. Ensures pipx is installed (industry-standard isolated CLI installer)
#   4. Installs linkright[full] via pipx (core + fastembed + playwright)
#   5. Prints next-steps for setup wizard + free LLM key
#
# Idempotent: safe to re-run. Already-installed deps are skipped.
# No sudo for the package install itself; only for system-package-manager
# tasks (apt/dnf/pacman) which require root by design.
#
# License: MIT — https://github.com/satvik-jain-iitd/linkright_production

set -euo pipefail

readonly INSTALLER_VERSION="0.1.0"
readonly LINKRIGHT_PACKAGE="linkright[full]"
readonly MIN_PYTHON_MAJOR=3
readonly MIN_PYTHON_MINOR=9
readonly REPO_URL="https://github.com/satvik-jain-iitd/linkright_production"
readonly DOCS_URL="https://pypi.org/project/linkright/"

# ── Output helpers ──────────────────────────────────────────────────────────
# All progress goes to stderr so that piping works cleanly. Stdout is reserved
# for any future "machine-readable" output the script might emit (--json etc).

USE_COLOR=1
if [[ ! -t 1 ]] || [[ "${NO_COLOR:-}" == "1" ]] || [[ "${TERM:-}" == "dumb" ]]; then
  USE_COLOR=0
fi

if [[ "$USE_COLOR" == "1" ]]; then
  C_RESET=$'\033[0m'
  C_BOLD=$'\033[1m'
  C_DIM=$'\033[2m'
  C_RED=$'\033[31m'
  C_GREEN=$'\033[32m'
  C_YELLOW=$'\033[33m'
  C_BLUE=$'\033[34m'
  C_CYAN=$'\033[36m'
else
  C_RESET=""; C_BOLD=""; C_DIM=""
  C_RED=""; C_GREEN=""; C_YELLOW=""; C_BLUE=""; C_CYAN=""
fi

say() { printf "%s%s%s\n" "$C_DIM" "$*" "$C_RESET" >&2; }
info() { printf "%s→%s %s\n" "$C_BLUE" "$C_RESET" "$*" >&2; }
ok() { printf "%s✓%s %s\n" "$C_GREEN" "$C_RESET" "$*" >&2; }
warn() { printf "%s⚠%s %s\n" "$C_YELLOW" "$C_RESET" "$*" >&2; }
err() { printf "%s✗%s %s\n" "$C_RED" "$C_RESET" "$*" >&2; }
heading() { printf "\n%s%s%s\n" "$C_BOLD$C_CYAN" "$*" "$C_RESET" >&2; }

die() {
  err "$*"
  err ""
  err "Need help? Open an issue: ${REPO_URL}/issues"
  exit 1
}

# ── CLI flag parsing ────────────────────────────────────────────────────────

NO_SETUP_HINT=0
DRY_RUN=0
SHOW_HELP=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-setup-hint) NO_SETUP_HINT=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    --no-color) USE_COLOR=0; C_RESET=""; C_BOLD=""; C_DIM=""; C_RED=""; C_GREEN=""; C_YELLOW=""; C_BLUE=""; C_CYAN=""; shift ;;
    -h|--help) SHOW_HELP=1; shift ;;
    -v|--version) echo "linkright-installer $INSTALLER_VERSION"; exit 0 ;;
    *) warn "Unknown flag: $1 (ignored)"; shift ;;
  esac
done

if [[ "$SHOW_HELP" == "1" ]]; then
  cat <<EOF
LinkRight installer v${INSTALLER_VERSION}

Usage:
  curl -fsSL https://install.linkright.in | bash
  curl -fsSL https://install.linkright.in | bash -s -- [FLAGS]

Flags:
  --no-setup-hint   Skip the post-install "next steps" message
  --dry-run         Print what would happen without making changes
  --no-color        Disable colored output
  -h, --help        Show this message
  -v, --version     Print installer version

What gets installed:
  • Python 3.9+ (via Homebrew/apt/dnf/pacman if missing)
  • pipx (isolated venv installer for CLI tools)
  • linkright[full] = LinkRight core + fastembed (embedder) + playwright (PDF)

After install, run \`linkright setup\` to configure LLM/embedder/PDF interactively.

More: ${REPO_URL}
EOF
  exit 0
fi

run() {
  if [[ "$DRY_RUN" == "1" ]]; then
    say "  [dry-run] $*"
  else
    "$@"
  fi
}

# ── Banner ──────────────────────────────────────────────────────────────────

cat <<EOF >&2
${C_BOLD}${C_CYAN}
   ╭─────────────────────────────────────────────────╮
   │  LinkRight — local-first career OS installer    │
   │  Tailor resumes, prep interviews, find jobs     │
   ╰─────────────────────────────────────────────────╯
${C_RESET}
EOF

if [[ "$DRY_RUN" == "1" ]]; then
  warn "DRY RUN mode — no changes will be made"
fi

# ── OS + arch detection ─────────────────────────────────────────────────────

heading "1/4  Detecting your platform"

OS_KIND="unknown"
LINUX_DISTRO=""
case "$(uname -s)" in
  Darwin*)  OS_KIND="macos" ;;
  Linux*)   OS_KIND="linux" ;;
  MINGW*|MSYS*|CYGWIN*) OS_KIND="windows" ;;
esac

ARCH="$(uname -m)"

if [[ "$OS_KIND" == "windows" ]]; then
  err "Native Windows detected. This installer requires bash."
  err "Use WSL2: https://learn.microsoft.com/en-us/windows/wsl/install"
  err "Or install manually: pip install 'linkright[full]'"
  exit 1
fi

if [[ "$OS_KIND" == "linux" ]] && [[ -r /etc/os-release ]]; then
  LINUX_DISTRO="$(. /etc/os-release && echo "$ID")"
fi

case "$OS_KIND" in
  macos) ok "macOS / $ARCH" ;;
  linux) ok "Linux ($LINUX_DISTRO) / $ARCH" ;;
  *) die "Unsupported OS: $(uname -s)" ;;
esac

# ── Step 2: Ensure Python 3.9+ ──────────────────────────────────────────────

heading "2/4  Checking Python (need ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR}+)"

PYTHON_BIN=""
for candidate in python3.13 python3.12 python3.11 python3.10 python3.9 python3 python; do
  if command -v "$candidate" >/dev/null 2>&1; then
    if "$candidate" -c "import sys; sys.exit(0 if sys.version_info >= (${MIN_PYTHON_MAJOR},${MIN_PYTHON_MINOR}) else 1)" 2>/dev/null; then
      PYTHON_BIN="$(command -v "$candidate")"
      break
    fi
  fi
done

if [[ -n "$PYTHON_BIN" ]]; then
  PY_VERSION="$("$PYTHON_BIN" --version 2>&1 | awk '{print $2}')"
  ok "Python $PY_VERSION at $PYTHON_BIN"
else
  warn "No suitable Python ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR}+ found — installing"

  case "$OS_KIND" in
    macos)
      if ! command -v brew >/dev/null 2>&1; then
        info "Installing Homebrew first (required for Python)"
        say "  This will run the official Homebrew installer:"
        say "    /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        run /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        # Add brew to PATH for this script run (Apple Silicon vs Intel)
        if [[ -x /opt/homebrew/bin/brew ]]; then
          eval "$(/opt/homebrew/bin/brew shellenv)"
        elif [[ -x /usr/local/bin/brew ]]; then
          eval "$(/usr/local/bin/brew shellenv)"
        fi
      fi
      info "brew install python@3.13"
      run brew install python@3.13
      PYTHON_BIN="$(command -v python3.13 || command -v python3)"
      ;;
    linux)
      case "$LINUX_DISTRO" in
        ubuntu|debian)
          info "sudo apt-get install -y python3 python3-pip python3-venv"
          run sudo apt-get update
          run sudo apt-get install -y python3 python3-pip python3-venv
          PYTHON_BIN="$(command -v python3)"
          ;;
        fedora|rhel|centos)
          info "sudo dnf install -y python3 python3-pip"
          run sudo dnf install -y python3 python3-pip
          PYTHON_BIN="$(command -v python3)"
          ;;
        arch|manjaro)
          info "sudo pacman -S --noconfirm python python-pip"
          run sudo pacman -S --noconfirm python python-pip
          PYTHON_BIN="$(command -v python)"
          ;;
        *)
          die "Don't know how to install Python on '$LINUX_DISTRO'. Install Python ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR}+ manually, then re-run."
          ;;
      esac
      ;;
  esac

  ok "Python installed at $PYTHON_BIN"
fi

# ── Step 3: Ensure pipx ─────────────────────────────────────────────────────

heading "3/4  Checking pipx (isolated CLI installer)"

if command -v pipx >/dev/null 2>&1; then
  ok "pipx already installed at $(command -v pipx)"
else
  warn "pipx not found — installing via pip"
  info "$PYTHON_BIN -m pip install --user pipx"
  run "$PYTHON_BIN" -m pip install --user --upgrade pipx

  # Add pipx-installed binaries to PATH for the rest of THIS script run.
  # Persistent PATH update happens via `pipx ensurepath` below.
  USER_BASE="$("$PYTHON_BIN" -m site --user-base 2>/dev/null || echo "$HOME/.local")"
  export PATH="$USER_BASE/bin:$PATH"

  if [[ "$DRY_RUN" == "0" ]] && ! command -v pipx >/dev/null 2>&1; then
    die "pipx install succeeded but binary not on PATH. Restart your shell and re-run."
  fi

  info "pipx ensurepath  (adds ~/.local/bin to your shell PATH)"
  run pipx ensurepath >/dev/null 2>&1 || true
  if [[ "$DRY_RUN" == "0" ]]; then
    ok "pipx ready at $(command -v pipx)"
  else
    ok "pipx would be ready (dry-run)"
  fi
fi

# ── Step 4: Install LinkRight ───────────────────────────────────────────────

heading "4/4  Installing $LINKRIGHT_PACKAGE"

# If linkright already exists, upgrade rather than reinstall.
if pipx list 2>/dev/null | grep -q "package linkright "; then
  info "linkright already installed — upgrading"
  run pipx upgrade linkright || run pipx install --force "$LINKRIGHT_PACKAGE"
else
  info "pipx install '$LINKRIGHT_PACKAGE'"
  say "  This pulls ~250MB total (LinkRight + fastembed model + playwright)."
  run pipx install "$LINKRIGHT_PACKAGE"
fi

# Sanity check
if [[ "$DRY_RUN" == "0" ]]; then
  if command -v linkright >/dev/null 2>&1; then
    LR_VERSION="$(linkright --version 2>&1 | awk '{print $NF}')"
    ok "linkright $LR_VERSION installed"
  else
    err "linkright binary not on PATH yet."
    err "Open a NEW terminal (or run: source ~/.bashrc) and try: linkright --version"
    exit 1
  fi
fi

# ── Done — next steps ───────────────────────────────────────────────────────

if [[ "$NO_SETUP_HINT" == "0" ]]; then
  cat <<EOF >&2

${C_BOLD}${C_GREEN}🎉  LinkRight installed successfully!${C_RESET}

${C_BOLD}Next steps:${C_RESET}

  ${C_CYAN}1. Get a free LLM key${C_RESET} (any one — Groq is fastest)
     https://console.groq.com → Sign up → API Keys → Create
     Then save it:
       ${C_DIM}mkdir -p ~/.linkright && echo "GROQ_API_KEY=<paste-key>" >> ~/.linkright/.env${C_RESET}

  ${C_CYAN}2. Run the setup wizard${C_RESET} (interactive — picks LLM/embedder/PDF)
       ${C_DIM}linkright setup${C_RESET}

  ${C_CYAN}3. Verify everything works${C_RESET}
       ${C_DIM}linkright doctor${C_RESET}

  ${C_CYAN}4. Create your career profile${C_RESET} (one-time, ~1 min)
       ${C_DIM}linkright profile create -r ~/Documents/your_resume.pdf${C_RESET}

  ${C_CYAN}5. Tailor your first resume${C_RESET}
       ${C_DIM}linkright tailor -j /path/to/job-description.md${C_RESET}

${C_BOLD}Quick commands:${C_RESET}
  ${C_DIM}linkright tldr${C_RESET}        — one-page cheat sheet
  ${C_DIM}linkright --help${C_RESET}      — all commands
  ${C_DIM}linkright doctor${C_RESET}      — health check anytime

${C_BOLD}Docs / issues:${C_RESET} ${REPO_URL}

${C_DIM}If \`linkright\` is "command not found", open a new terminal — pipx added
~/.local/bin (or equivalent) to your PATH but the current shell may not have
picked it up yet. Or run:  source ~/.bashrc  (or ~/.zshrc).${C_RESET}

EOF
fi
