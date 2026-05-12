#!/usr/bin/env bash
# Sprint-end CLI release: compile changelog fragments → bump version → push → PyPI
# Usage (from linkright_production/ root, on main branch):
#   bash scripts/release-cli.sh patch   # 0.9.0 → 0.9.1
#   bash scripts/release-cli.sh minor   # 0.9.0 → 0.10.0
set -euo pipefail

BUMP="${1:-}"
if [[ "$BUMP" != "patch" && "$BUMP" != "minor" ]]; then
    echo "Usage: bash scripts/release-cli.sh patch|minor"
    exit 1
fi

PYPROJECT="context/cli/linkright/pyproject.toml"
if [[ ! -f "$PYPROJECT" ]]; then
    echo "Error: run from linkright_production/ root (pyproject.toml not found)"
    exit 1
fi

BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [[ "$BRANCH" != "main" ]]; then
    echo "Error: must run from main branch (currently on: $BRANCH)"
    echo "       git checkout main && git pull --rebase"
    exit 1
fi

CHANGELOG="context/cli/linkright/CHANGELOG.md"
UNRELEASED_DIR="context/cli/linkright/changelogs/unreleased"

# Compile fragments, bump version, update CHANGELOG — all in one Python step
NEW_VERSION=$(python3 - "$BUMP" "$PYPROJECT" "$CHANGELOG" "$UNRELEASED_DIR" <<'PYEOF'
import sys, re
from pathlib import Path
from datetime import date

bump, pyproject_path, changelog_path, unreleased_dir = sys.argv[1:]

# --- Read + bump version ---
pyproject = Path(pyproject_path).read_text()
m = re.search(r'^version = "(\d+)\.(\d+)\.(\d+)"', pyproject, re.MULTILINE)
if not m:
    sys.exit("Error: cannot parse version from pyproject.toml")
major, minor, patch = int(m[1]), int(m[2]), int(m[3])
if bump == "patch":
    new_ver = f"{major}.{minor}.{patch + 1}"
else:
    new_ver = f"{major}.{minor + 1}.0"

# --- Parse fragments ---
buckets = {"Added": [], "Fixed": [], "Changed": []}
fragment_files = sorted(Path(unreleased_dir).glob("*.md"))
if not fragment_files:
    sys.exit("Error: no fragments in changelogs/unreleased/ — nothing to release")

for fpath in fragment_files:
    text = fpath.read_text()
    current_type = None
    for line in text.splitlines():
        m_type = re.match(r'^##\s+\[type:\s*([A-Za-z]+)\]', line)
        if m_type:
            t = m_type[1].capitalize()
            current_type = t if t in buckets else None
        elif line.startswith("- ") and current_type:
            buckets[current_type].append(line)

# --- Build new CHANGELOG section ---
today = date.today().isoformat()
section = f"## [{new_ver}] - {today}\n\n"
for heading, bullets in buckets.items():
    if bullets:
        section += f"### {heading}\n" + "\n".join(bullets) + "\n\n"

# --- Prepend to CHANGELOG ---
changelog = Path(changelog_path).read_text()
header = "# Changelog\n"
if header not in changelog:
    sys.exit("Error: CHANGELOG.md missing '# Changelog' header")
idx = changelog.index(header) + len(header)
new_changelog = changelog[:idx] + "\n" + section + changelog[idx:].lstrip("\n")
Path(changelog_path).write_text(new_changelog)

# --- Bump pyproject.toml ---
new_pyproject = re.sub(
    r'^version = "\d+\.\d+\.\d+"',
    f'version = "{new_ver}"',
    pyproject,
    flags=re.MULTILINE
)
Path(pyproject_path).write_text(new_pyproject)

# --- Delete fragments ---
for fpath in fragment_files:
    fpath.unlink()

print(new_ver)
PYEOF
)

echo "→ Bumped to v$NEW_VERSION"

# Stage only the CLI release files
git add \
    "$PYPROJECT" \
    "$CHANGELOG" \
    "$UNRELEASED_DIR"

git commit \
    --author="satvik-jain-iitd <satvik.jain@iitdalumni.com>" \
    -m "release(cli): v$NEW_VERSION — $BUMP bump

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"

git push

echo ""
echo "✓ v$NEW_VERSION pushed → cli-publish.yml will build + upload to PyPI"
echo "  Watch: https://github.com/satvik-jain-iitd/linkright_production/actions"
