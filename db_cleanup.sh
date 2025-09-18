#!/bin/bash

# Database Cleanup Script for cc-hooks
# Truncate database or show statistics

set -euo pipefail

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Default values
DB_PATH="events.db"
STATS_ONLY=false
DRY_RUN=false
INTERACTIVE=true

# Help function
show_help() {
    cat << EOF
Database Cleanup Script for cc-hooks

USAGE:
    $0 [OPTIONS]

OPTIONS:
    --stats-only        Show statistics only, no cleanup
    --dry-run           Preview truncate operation without executing
    --force             Skip confirmation prompts
    --db PATH           Database file path (default: events.db)
    --help              Show this help message

EXAMPLES:
    $0                  # Interactive truncate (complete database reset)
    $0 --stats-only     # Show database statistics
    $0 --dry-run        # Preview truncate operation
    $0 --force          # Truncate without confirmation

NPM SHORTCUTS:
    npm run db:cleanup  # Truncate all events (complete reset)
    npm run db:stats    # Show statistics only
EOF
}

# Check if sqlite3 is available
check_sqlite3() {
    if ! command -v sqlite3 &> /dev/null; then
        echo -e "${RED}Error: sqlite3 is not installed or not in PATH${NC}"
        echo
        echo "To install sqlite3:"
        case "$(uname -s)" in
            Darwin*)
                echo "  brew install sqlite3"
                ;;
            Linux*)
                echo "  # Ubuntu/Debian:"
                echo "  sudo apt-get install sqlite3"
                echo
                echo "  # CentOS/RHEL/Fedora:"
                echo "  sudo yum install sqlite3      # CentOS/RHEL"
                echo "  sudo dnf install sqlite3      # Fedora"
                ;;
            *)
                echo "  Please install sqlite3 for your operating system"
                ;;
        esac
        echo
        exit 1
    fi
}

# Check if database exists
check_database() {
    if [[ ! -f "$DB_PATH" ]]; then
        echo -e "${RED}Error: Database file '$DB_PATH' not found${NC}"
        echo "Make sure you're running this from the cc-hooks project directory"
        exit 1
    fi
}

# Get database statistics
get_stats() {
    local total_events
    local completed_events
    local failed_events
    local pending_events
    local processing_events

    total_events=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM events;")
    completed_events=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM events WHERE status = 'completed';")
    failed_events=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM events WHERE status = 'failed';")
    pending_events=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM events WHERE status = 'pending';")
    processing_events=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM events WHERE status = 'processing';")

    echo -e "${BLUE}=== Database Statistics ===${NC}"
    echo -e "Database: ${YELLOW}$DB_PATH${NC}"
    echo -e "Total events: ${GREEN}$total_events${NC}"
    echo
    echo -e "${BLUE}By Status:${NC}"
    echo -e "  ✅ Completed: ${GREEN}$completed_events${NC}"
    echo -e "  ❌ Failed: ${RED}$failed_events${NC}"
    echo -e "  ⏳ Pending: ${YELLOW}$pending_events${NC}"
    echo -e "  🔄 Processing: ${BLUE}$processing_events${NC}"
    echo

    if [[ $total_events -gt 0 ]]; then
        echo -e "${BLUE}Top Event Types:${NC}"
        sqlite3 "$DB_PATH" "SELECT '  ' || hook_event_name || ': ' || COUNT(*) FROM events GROUP BY hook_event_name ORDER BY COUNT(*) DESC LIMIT 5;"
    fi

    # Show database file size
    if command -v du &> /dev/null; then
        local db_size
        db_size=$(du -h "$DB_PATH" | cut -f1)
        echo -e "Database size: ${YELLOW}$db_size${NC}"
    fi
}

# Truncate all events
clean_truncate() {
    local count
    count=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM events;")

    if [[ $count -eq 0 ]]; then
        echo -e "${GREEN}Database is already empty${NC}"
        return 0
    fi

    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${YELLOW}[DRY RUN] Would delete ALL $count events (complete database reset)${NC}"
        return 0
    fi

    if [[ "$INTERACTIVE" == "true" ]]; then
        echo -e "${RED}⚠️  WARNING: This will delete ALL $count events from the database!${NC}"
        echo -e "${YELLOW}This is a complete database reset and cannot be undone.${NC}"
        read -p "Are you absolutely sure? Type 'TRUNCATE' to confirm: " -r
        echo
        if [[ "$REPLY" != "TRUNCATE" ]]; then
            echo "Truncate cancelled"
            return 0
        fi
    fi

    sqlite3 "$DB_PATH" "DELETE FROM events;"
    sqlite3 "$DB_PATH" "VACUUM;"
    echo -e "${GREEN}Successfully deleted all $count events and optimized database${NC}"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --stats-only)
            STATS_ONLY=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --force)
            INTERACTIVE=false
            shift
            ;;
        --db)
            DB_PATH="$2"
            shift 2
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Main execution
main() {
    echo -e "${BLUE}CC-Hooks Database Cleanup${NC}"
    echo

    # Check prerequisites
    check_sqlite3
    check_database

    # Show stats
    get_stats

    # Exit if stats only
    if [[ "$STATS_ONLY" == "true" ]]; then
        exit 0
    fi

    echo
    echo -e "${BLUE}=== Cleanup Operations ===${NC}"

    # Perform truncate
    clean_truncate

    echo
    echo -e "${GREEN}Cleanup completed!${NC}"

    # Show updated stats if not dry run
    if [[ "$DRY_RUN" == "false" ]]; then
        echo
        get_stats
    fi
}

# Run main function
main