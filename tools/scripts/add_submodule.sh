#!/bin/bash
set -e

# Optional argument: path to target git repo (defaults to current dir)
if [ -z "$1" ]; then
    repo_path="$(pwd)"
else
    repo_path="$1"
fi

# Check it's a git repo
if [ ! -d "$repo_path/.git" ]; then
    echo "❌ Error: '$repo_path' is not a Git repository."
    exit 1
fi

# Prompt for Git URL
read -rp "Enter the Git URL (SSH or HTTPS): " repo_url

# Prompt for branch
read -rp "Enter the branch to use: " branch

# Parse namespace and repo name from SSH or HTTPS URL
if [[ "$repo_url" =~ ^git@[^:]+:([^/]+)/([^/]+)\.git$ ]]; then
    namespace="${BASH_REMATCH[1]}"
    repo_name="${BASH_REMATCH[2]}"
elif [[ "$repo_url" =~ ^https?://[^/]+/([^/]+)/([^/]+)\.git$ ]]; then
    namespace="${BASH_REMATCH[1]}"
    repo_name="${BASH_REMATCH[2]}"
else
    echo "❌ Error: Unsupported Git URL format."
    exit 1
fi

# Define target path and name
target_path="${repo_path}/.third-party/${namespace}/${repo_name}"
submodule_name="${repo_name}"

# Create directory if needed
mkdir -p "$(dirname "$target_path")"

# Display info
echo "🔧 Adding submodule:"
echo "  Repository : $repo_url"
echo "  Branch     : $branch"
echo "  Target     : $target_path"
echo "  --name     : $submodule_name"

# Add submodule
(
    cd "$repo_path"
    git submodule add -b "$branch" --name "$submodule_name" "$repo_url" ".third-party/${namespace}/${repo_name}"
)

echo "✅ Submodule added successfully."
