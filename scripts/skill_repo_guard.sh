#!/usr/bin/env bash
# Validates paths/repos to prevent accidental use of skill repository
#
# Usage:
#   source ${CLAUDE_SKILL_DIR}/../scripts/skill_repo_guard.sh
#   validate_local_path "$target_dir" "$FORCE_OUTPUT_DIR" || exit 1
#   validate_remote_repo "$target_repo" || exit 1

set -e

# Get the skill repository root directory
get_skill_repo_root() {
    cd "${CLAUDE_SKILL_DIR}/../.." && git rev-parse --show-toplevel 2>/dev/null || echo ""
}

# Get the skill repository remote (owner/repo format)
get_skill_repo_remote() {
    local root=$(get_skill_repo_root)
    if [ -n "$root" ]; then
        cd "$root" && git config --get remote.origin.url 2>/dev/null | sed -E 's/.*github\.com[:/]([^/]+\/[^.]+)(\.git)?/\1/' || echo ""
    else
        echo ""
    fi
}

# Validate that a local path is NOT inside the skill repository
# Args:
#   $1 - path to validate
#   $2 - force flag (true/false, defaults to false)
# Returns:
#   0 if valid (not in skill repo or force=true)
#   1 if invalid (in skill repo and force=false)
validate_local_path() {
    local path="$1"
    local force="${2:-false}"

    # If force flag is set, skip validation
    if [ "$force" = "true" ]; then
        return 0
    fi

    local skill_root=$(get_skill_repo_root)

    # If we can't detect skill repo, allow creation
    if [ -z "$skill_root" ]; then
        return 0
    fi

    # Get absolute path of target directory
    local path_abs=$(cd "$path" 2>/dev/null && pwd || echo "$path")

    # Check if path is inside skill repo
    if [[ "$path_abs" == "$skill_root"* ]]; then
        echo "❌ ERROR: Cannot create artifacts in skill repository ($skill_root)" >&2
        echo "Please specify a different directory." >&2
        echo "" >&2
        echo "Tip: Use --output-dir flag to force creation in current directory if needed." >&2
        return 1
    fi

    return 0
}

# Validate that a remote repository is NOT the skill repository
# Args:
#   $1 - remote repo in owner/repo format
# Returns:
#   0 if valid (not skill repo)
#   1 if invalid (is skill repo)
validate_remote_repo() {
    local repo="$1"
    local skill_remote=$(get_skill_repo_remote)

    # If we can't detect skill repo, allow publish
    if [ -z "$skill_remote" ]; then
        return 0
    fi

    # Check if target repo matches skill repo
    if [ "$repo" = "$skill_remote" ]; then
        echo "❌ ERROR: Cannot publish to skill repository ($skill_remote)" >&2
        echo "Test plans must be published to a separate repository." >&2
        return 1
    fi

    return 0
}
