#!/usr/bin/env bash
# release-cli.sh — compile changelog fragments, bump version, push to trigger PyPI CI.
#
# Usage:
#   bash scripts/release-cli.sh patch    # 0.5.24 → 0.5.25 (default)
#   bash scripts/release-cli.sh minor    # 0.5.24 → 0.6.0
#   bash scripts/release-cli.sh major    # 0.5.24 → 1.0.0
#
# Run from repo root (linkright_production/) after ALL sprint PRs are merged to main.
# This is the ONLY command that touches pyproject.toml and CHANGELOG.md.
#
# What it does:
#   1. Pull latest main (fail-safe if branch is stale)
#   2. Read current version from pyproject.toml
#   3. Compute next version based on bump type
#   4. Compile changelogs/unreleased/*.md → prepend to CHANGELOG.md
#   5. Bump version in pyproject.toml
#   6. Delete compiled fragment files
#   7. Commit (pyproject.toml + CHANGELOG.md + deleted fragments)
#   8. Push → triggers cli-publish.yml → auto-publishes to PyPI

set -euo pipefail

BUMP="${1:-patch}"
PYPROJECT="context/cli/linkright/pyproject.toml"
CHANGELOG="context/cli/linkright/CHANGELOG.md"
FRAGMENTS_DIR="context/cli/linkright/changelogs/unreleased"
TODAY=$(date +%Y-%m-%d)
AUTHOR="satvik-jain-iitd <satvik.jain@iitdalumni.com>"

# ── 1. Safety checks ────────────────────────────────────────────────────────
echo "→ Checking working tree..."
if [[ -n "$(git status --porcelain)" ]]; then
  echo "ERROR: Working tree is dirty. Commit or stash changes first." >&2
  exit 1
fi

CURRENT_BRANCH=$(git branch --show-current)
if [[ "$CURRENT_BRANCH" != "main" ]]; then
  echo "ERROR: Must run from main branch (currently on '$CURRENT_BRANCH')." >&2
  exit 1
fi

git pull --rebase origin main

# ── 2. Read current version ──────────────────────────────────────────────────
CURRENT_VER=$(grep -E '^version = ' "$PYPROJECT" | head -1 | cut -d'"' -f2)
if [[ -z "$CURRENT_VER" ]]; then
  echo "ERROR: Could not read version from $PYPROJECT" >&2
  exit 1
fi
echo "→ Current version: $CURRENT_VER"

# ── 3. Compute next version ──────────────────────────────────────────────────
IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT_VER"
case "$BUMP" in
  major) NEXT_VER="$((MAJOR+1)).0.0" ;;
  minor) NEXT_VER="${MAJOR}.$((MINOR+1)).0" ;;
  patch) NEXT_VER="${MAJOR}.${MINOR}.$((PATCH+1))" ;;
  *)
    echo "ERROR: Unknown bump type '$BUMP'. Use patch, minor, or major." >&2
    exit 1
    ;;
esac
echo "→ Next version:    $NEXT_VER ($BUMP bump)"

# ── 4. Collect fragments ─────────────────────────────────────────────────────
FRAGMENT_FILES=( "$FRAGMENTS_DIR"/*.md )
# Filter out TEMPLATE.md and non-existent glob
REAL_FRAGMENTS=()
for f in "${FRAGMENT_FILES[@]}"; do
  [[ -f "$f" && "$(basename "$f")" != "TEMPLATE.md" ]] && REAL_FRAGMENTS+=("$f")
done

if [[ ${#REAL_FRAGMENTS[@]} -eq 0 ]]; then
  echo "ERROR: No changelog fragments found in $FRAGMENTS_DIR/" >&2
  echo "       Each merged PR should have written a fragment file there." >&2
  exit 1
fi

echo "→ Found ${#REAL_FRAGMENTS[@]} fragment(s):"
for f in "${REAL_FRAGMENTS[@]}"; do echo "    $(basename "$f")"; done

# ── 5. Build the new CHANGELOG entry ────────────────────────────────────────
NEW_ENTRY="## [$NEXT_VER] - $TODAY"$'\n'
NEW_ENTRY+=$'\n'

# Group bullets by type — bash 3.x compatible (temp files instead of declare -A)
BULLETS_TMPDIR=$(mktemp -d)
for f in "${REAL_FRAGMENTS[@]}"; do
  TYPE=""
  while IFS= read -r line; do
    if [[ "$line" =~ ^##\ \[type:\ ([A-Za-z]+)\] ]]; then
      TYPE="${BASH_REMATCH[1]}"
    elif [[ "$line" =~ ^-\  && -n "$TYPE" ]]; then
      printf '%s\n' "$line" >> "${BULLETS_TMPDIR}/${TYPE}"
    elif [[ "$line" =~ ^\ \  && -n "$TYPE" ]]; then
      printf '%s\n' "$line" >> "${BULLETS_TMPDIR}/${TYPE}"
    fi
  done < "$f"
done

for TYPE in Added Fixed Changed Removed; do
  if [[ -f "${BULLETS_TMPDIR}/${TYPE}" ]]; then
    NEW_ENTRY+="### $TYPE"$'\n'
    NEW_ENTRY+="$(cat "${BULLETS_TMPDIR}/${TYPE}")"$'\n'
    NEW_ENTRY+=$'\n'
  fi
done
rm -rf "${BULLETS_TMPDIR}"

# ── 6. Prepend to CHANGELOG.md ───────────────────────────────────────────────
echo "→ Prepending to $CHANGELOG..."
EXISTING=$(tail -n +2 "$CHANGELOG")   # strip first "# Changelog" line
{
  echo "# Changelog"
  echo ""
  printf '%s' "$NEW_ENTRY"
  echo "$EXISTING"
} > "${CHANGELOG}.tmp"
mv "${CHANGELOG}.tmp" "$CHANGELOG"

# ── 7. Bump version in pyproject.toml ───────────────────────────────────────
echo "→ Bumping version $CURRENT_VER → $NEXT_VER in $PYPROJECT..."
sed -i.bak "s/^version = \"${CURRENT_VER}\"/version = \"${NEXT_VER}\"/" "$PYPROJECT"
rm -f "${PYPROJECT}.bak"

# Verify the sed worked
VERIFY=$(grep -E '^version = ' "$PYPROJECT" | head -1 | cut -d'"' -f2)
if [[ "$VERIFY" != "$NEXT_VER" ]]; then
  echo "ERROR: Version bump failed. Expected $NEXT_VER, got $VERIFY" >&2
  exit 1
fi

# ── 8. Delete fragment files ─────────────────────────────────────────────────
echo "→ Deleting ${#REAL_FRAGMENTS[@]} fragment file(s)..."
for f in "${REAL_FRAGMENTS[@]}"; do
  git rm "$f"
done

# ── 9. Commit + push ─────────────────────────────────────────────────────────
echo "→ Committing..."
git add "$PYPROJECT" "$CHANGELOG"
git commit \
  --author="$AUTHOR" \
  -m "chore(release): bump CLI to v${NEXT_VER}

Compiled ${#REAL_FRAGMENTS[@]} changelog fragment(s). PyPI publish triggered automatically via cli-publish.yml.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"

echo "→ Pushing to origin/main..."
git push origin main

echo ""
echo "✓ Done. v${NEXT_VER} is on its way to PyPI."
echo "  Watch: https://github.com/satvik-jain-iitd/linkright_production/actions"
