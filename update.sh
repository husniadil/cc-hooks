#!/bin/bash
# Update script for cc-hooks
# Safely pulls latest changes from origin/main and updates dependencies

set -e  # Exit on error

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO_DIR"

echo "🔄 cc-hooks update starting..."

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    print_error "Not a git repository"
    exit 1
fi

# Check for network connectivity
print_info "Checking network connectivity..."
if ! git ls-remote origin &> /dev/null; then
    print_error "Cannot reach remote repository. Check your network connection."
    exit 1
fi
print_success "Network OK"

# Check for uncommitted changes
print_info "Checking for uncommitted changes..."
if ! git diff-index --quiet HEAD --; then
    print_warning "You have uncommitted changes!"
    echo ""
    git status --short
    echo ""

    read -p "Do you want to stash your changes and continue? (y/N) " -n 1 -r
    echo

    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Update cancelled"
        exit 0
    fi

    print_info "Stashing uncommitted changes..."
    git stash push -m "Auto-stash before cc-hooks update at $(date)"
    STASHED=1
    print_success "Changes stashed"
else
    print_success "Working directory clean"
    STASHED=0
fi

# Fetch latest from remote
print_info "Fetching latest from origin..."
if ! git fetch origin; then
    print_error "Failed to fetch from remote"

    # Restore stash if we stashed earlier
    if [ "$STASHED" -eq 1 ]; then
        print_info "Restoring stashed changes..."
        git stash pop
    fi

    exit 1
fi
print_success "Fetch completed"

# Check if we're behind
COMMITS_BEHIND=$(git rev-list --count HEAD..origin/main 2>/dev/null || echo "0")

if [ "$COMMITS_BEHIND" -eq 0 ]; then
    print_success "Already up to date!"

    # Restore stash if we stashed earlier
    if [ "$STASHED" -eq 1 ]; then
        print_info "Restoring stashed changes..."
        git stash pop
        print_success "Stash restored"
    fi

    exit 0
fi

print_info "Updates available: $COMMITS_BEHIND commits behind origin/main"

# Pull latest changes
print_info "Pulling latest changes..."
if ! git pull origin main; then
    print_error "Failed to pull changes"

    # Restore stash if we stashed earlier
    if [ "$STASHED" -eq 1 ]; then
        print_info "Restoring stashed changes..."
        git stash pop
    fi

    exit 1
fi
print_success "Pull completed"

# Update dependencies with uv
print_info "Updating dependencies..."
if command -v uv &> /dev/null; then
    if ! uv sync; then
        print_warning "Failed to update dependencies with uv"
        print_warning "You may need to run 'uv sync' manually"
    else
        print_success "Dependencies updated"
    fi
else
    print_warning "uv not found, skipping dependency update"
    print_warning "Install uv with: curl -LsSf https://astral.sh/uv/install.sh | sh"
fi

# Restore stash if we stashed earlier
if [ "$STASHED" -eq 1 ]; then
    print_info "Restoring stashed changes..."

    if ! git stash pop; then
        print_warning "Failed to restore stash automatically"
        print_warning "You may have merge conflicts. Run 'git stash list' to see your stashed changes."
        print_warning "Use 'git stash pop' to restore them manually after resolving conflicts."
    else
        print_success "Stash restored"
    fi
fi

echo ""
print_success "Update completed successfully!"
echo ""
print_info "Current version: $(git describe --tags --always --dirty)"
echo ""
print_warning "Please restart your Claude Code session to use the updated version."
echo ""
