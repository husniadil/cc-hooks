# Changelog

All notable changes to the Claude Code hooks processing system will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.3] - 2025-12-05

### Fixed

- **Bun-Compiled Binary PID Detection**: Fixed Claude process detection for Bun-compiled binaries
  - Bun-compiled Claude CLI uses version number (e.g., "2.0.59") as process name instead of "claude"
  - Added path-based detection strategy: checks if first cmdline argument ends with `/claude`
  - Updated detection logic in three files for consistency:
    - `hooks.py`: `detect_claude_pid()` function
    - `status-lines/status_line.py`: `_detect_claude_pid()` method
    - `app/event_db.py`: `_is_claude_process()` function
  - Detection now uses three strategies: name-based, cmdline-based, and path-based
  - Maintains backward compatibility with Node.js-based Claude CLI

## [1.0.2] - 2025-10-31

### Removed

- **Deprecated Output Style Feature**: Removed all references to deprecated output_style
  functionality
  - Removed `output_style` from status line Features list in docstring
  - Removed `output_style` variable extraction from data model
  - Removed output_style display logic from status line rendering (lines 908-909)
  - Removed unused `style_color()` method that was only used for output_style display
  - Anthropic has deprecated output styles in Claude Code, so this feature is no longer needed
  - Status line now displays: directory, git, model, usage, and session information only

## [1.0.1] - 2025-10-25

### Fixed

- **STANDALONE_README.md Corruption**: Fixed critical file corruption where STANDALONE_README.md
  contained server.py content instead of proper markdown documentation
  - File was corrupted in v1.0.0 release (commit 4e8fadd)
  - Recreated with complete standalone installation guide (475 lines)
  - Includes: installation steps, manual hooks configuration, usage examples, troubleshooting,
    development workflow
  - Mirrors README.md structure for standalone mode users (developers/contributors)

### Added

- **Troubleshooting Documentation**: New troubleshooting entry for `--dangerously-skip-permissions`
  flag issue
  - Documents issue where hooks don't execute with flag in new/untrusted folders
  - Root cause: Claude Code trust prompt requires explicit acceptance before hooks can run
  - Solution: Run without flag first to accept trust prompt, then subsequent runs work normally
  - Added to both README.md and STANDALONE_README.md for consistency
  - Affects both plugin and standalone installation modes

## [1.0.0] - 2025-10-18

### Added

- **Plugin Marketplace Integration**: Official Claude Code plugin system with marketplace support
  - New `.claude-plugin/` directory structure for plugin metadata and configuration
  - `plugin.json` with comprehensive plugin metadata (name, version, author, keywords)
  - `marketplace.json` defining marketplace structure with plugin listings and owner information
  - Plugin discovery and installation via Claude Code plugin marketplace
  - 14 comprehensive keywords for better discoverability (audio, tts, productivity, ai-translation,
    multilingual, etc.)
  - MIT license specification for open-source distribution
  - Repository and homepage links for community engagement

- **Slash Commands**: Interactive setup and update commands for plugin users
  - `/cc-hooks-plugin:setup [check|apikeys|test]` - Comprehensive setup wizard with system checks
  - `/cc-hooks-plugin:update` - One-command update workflow with auto-detection of installation mode
  - Setup wizard covers: uv installation, shell alias configuration, API key setup, audio testing
  - Update command automatically detects plugin vs standalone mode and uses correct update method
  - Interactive UI with preset configurations (Basic, Enhanced, Full, Premium)
  - Built-in audio testing with volume control and provider selection

- **YAML Configuration System**: Global configuration file for persistent preferences
  - New `~/.claude/.cc-hooks/config.yaml` for default settings across both installation modes
  - Supports audio settings (providers, language, cache), ElevenLabs, silent modes, OpenRouter
  - Config file creator utility: `uv run utils/config_loader.py --create-example`
  - Layered configuration: Session DB > CLI flags > YAML config > Shell env > Hardcoded defaults
  - Enables customization for editors (Zed) that can't pass CLI flags
  - Terminal users get "set once, forget" experience without typing flags every session
  - Config persists across updates (shared data directory)

- **Enhanced Documentation System**: Comprehensive documentation for plugin users and marketplace
  - New `README.md` (plugin mode) as primary installation guide with marketplace setup
  - New `STANDALONE_README.md` for developers/contributors with manual installation steps
  - New `MIGRATION.md` guide for seamless transition from standalone to plugin mode
  - Plugin-specific documentation in `docs/plugins.md` covering plugin architecture
  - `docs/plugins-reference.md` with technical plugin system reference
  - `docs/plugin-marketplace.md` with marketplace submission guidelines
  - Enhanced hooks documentation split into user guide (`docs/hooks.md`) and technical reference
    (`docs/hooks-reference.md`)
  - Restructured documentation hierarchy for better navigation and accessibility

### Enhanced

- **Editor Detection System**: Automatic detection of parent editor for intelligent behavior
  - New `utils/editor_detector.py` module for process chain analysis
  - Detects VSCode, Zed, Cursor, Windsurf, and terminal sessions
  - Multi-signature detection (extension dirs, unique agents, app names)
  - Powers intelligent SessionEnd behavior (silent for VSCode extension workaround)
  - CLI interface: `uv run utils/editor_detector.py <claude_pid>` or `--test` mode
  - Enables context-aware audio behavior based on execution environment

- **Type Safety**: Comprehensive type definitions for improved code quality
  - New `app/types.py` module with TypedDict definitions for data structures
  - `EventData` type for hook event payloads with optional fields
  - `SessionRow` type for database session records
  - Better IDE support and runtime validation throughout the codebase

- **Plugin Hooks Configuration**: Automatic hooks setup via plugin system
  - New `hooks/hooks.json` defining all hook events for plugin mode
  - Uses `${CLAUDE_PLUGIN_ROOT}` variable for path-independent hook commands
  - Covers all 8 hook events (SessionStart, SessionEnd, PreToolUse, PostToolUse, etc.)
  - No manual `~/.claude/settings.json` editing required for plugin users
  - Automatic registration during plugin installation

- **Configuration Management**: Streamlined `.env.example` for plugin users
  - Removed `.env.example` entirely (replaced by YAML config and shell environment)
  - API keys now only in shell environment (safer for plugin mode - updates delete `.env`)
  - Configuration examples moved to config.yaml generator and documentation
  - Clear separation: API keys in shell env, preferences in config.yaml
  - Smart API key resolution priority: shell env > config.yaml (for non-secret settings)
  - Better user experience with explicit guidance on where each setting belongs

- **Project Structure Organization**: Enhanced asset and documentation organization
  - Moved documentation images and assets to cleaner structure
  - Better separation between user-facing and developer-facing documentation
  - Enhanced `.gitignore` with logs directory and legacy instance tracking entries
  - Removed legacy `db_cleanup.sh` (functionality replaced by better database management)
  - Cleaner repository structure for plugin distribution

- **Documentation Updates**: Comprehensive updates across all documentation files
  - `README.md` enhanced with plugin installation instructions
  - `CLAUDE.md` updated with plugin development guidelines
  - Better quick start examples with common configuration patterns
  - Enhanced audio system documentation with clearer provider explanations
  - Improved silent mode documentation with use case examples

### Changed

- **Audio Mappings Modularization**: Extracted audio configurations to dedicated utility module
  - New `utils/audio_mappings.py` centralizing all audio event configurations
  - `AudioConfig` dataclass for type-safe audio configuration management
  - `HOOK_AUDIO_MAPPINGS` dictionary defining sound effects and announcement settings
  - Moved audio mapping logic from event processor to dedicated module
  - Better separation of concerns between event processing and audio configuration
  - Easier maintenance and extension of audio event mappings

- **Installation Mode Detection**: Smart detection system for plugin vs standalone installation
  - Two-step detection: Plugin mode first (hooks.json), then standalone (settings.json)
  - Handles edge cases where hooks might be commented out (`#hooks_disabled`)
  - Used by `/cc-hooks-plugin:update` command for correct update workflow
  - Programmatic detection via Python script for reliable automation
  - Supports diagnostic tools showing current installation configuration

- **Sound Effects Enhancements**: Improved audio quality and file organization
  - Updated 4 core sound effect files (tek, cetek, klek, tung) with better quality recordings
  - Consistent audio levels and clearer sound signatures across all effects
  - Better distinction between different event types through improved sound design
  - Maintained file naming convention for backward compatibility

- **Version Management**: Release version 1.0.0 marking production-ready milestone
  - Bumped version across all metadata files (plugin.json, marketplace.json, package.json)
  - Stable API interface with comprehensive documentation
  - Production-ready error handling and logging
  - Complete feature set for core functionality
  - Full documentation coverage for users and developers

### Documentation

- **Dual Installation Mode Documentation**: Clear separation between plugin and standalone modes
  - `README.md` focuses on plugin mode (recommended for users)
  - `STANDALONE_README.md` focuses on standalone mode (for developers/contributors)
  - Both documents cross-reference each other for clarity
  - Installation path differences clearly documented
  - Update workflows documented for each mode

- **Migration Documentation**: Comprehensive guide for switching between modes
  - `MIGRATION.md` provides step-by-step migration from standalone to plugin
  - Pre-migration checklist covering API keys, aliases, status line config
  - Data preservation guarantees (shared `~/.claude/.cc-hooks/` directory)
  - Rollback instructions for reverting to standalone if needed
  - Edge cases covered (custom sounds, code modifications, multiple installations)

- **Plugin Architecture Documentation**: Complete plugin system documentation
  - Plugin metadata structure and requirements
  - Marketplace submission process and guidelines
  - Plugin discovery and installation workflows
  - Best practices for plugin development and distribution
  - Slash commands usage and customization

- **Hooks System Documentation**: Enhanced hooks documentation structure
  - User-facing `docs/hooks.md` with practical usage examples
  - Technical `docs/hooks-reference.md` with implementation details
  - Event reference table with all supported hook events
  - Custom hook creation guidelines and examples

- **Installation Guides**: Streamlined installation documentation
  - Plugin marketplace installation as primary method (3 commands)
  - Standalone manual installation as alternative method (developers)
  - Prerequisites and system requirements clearly documented
  - Step-by-step setup verification process with `/cc-hooks-plugin:setup check`
  - Shell alias setup (cld) with automatic detection
  - Config file creation with example generator

- **Configuration Documentation**: Comprehensive configuration layer documentation
  - YAML config file structure and usage examples
  - Layered configuration priority explanation
  - API key management best practices (shell env for plugin mode)
  - Per-session CLI flag overrides
  - Editor vs terminal usage patterns

### Technical

- **Metadata Architecture**: Plugin system metadata management
  - JSON schema for plugin and marketplace metadata
  - Version synchronization across multiple metadata files (plugin.json, marketplace.json,
    package.json)
  - Category and tag system for plugin classification
  - Author information and contact details standardization

- **Shared Data Directory**: Unified data storage for both installation modes
  - All runtime data in `~/.claude/.cc-hooks/` (database, logs, cache)
  - Enables seamless migration between plugin and standalone modes
  - Config file persists across updates and mode switches
  - Session logs organized by Claude PID for debugging

- **Session Management Enhancements**: Improved session lifecycle and configuration
  - Session-specific settings stored in sessions table (language, providers, AI features)
  - Silent modes tracked per session (announcements vs effects)
  - OpenRouter contextual features configurable per session
  - TTS provider chain and cache settings per session

- **Development Workflow**: Enhanced development tools and utilities
  - PEP 723 script dependencies for all utilities
  - Config loader utility with example generator
  - Editor detector for intelligent behavior
  - Installation mode detection script

## [0.17.1] - 2025-10-10

### Fixed

- **Status Line Dependencies**: Added missing `python-dotenv` dependency to status line script
  - Added `python-dotenv>=1.1.1,<2` to `status-lines/status_line.py` PEP 723 dependencies
  - Ensures consistency with other Python scripts in the project (server.py, hooks.py,
    tts_announcer.py)
  - Prevents import errors when status line tries to use config module that depends on dotenv

## [0.17.0] - 2025-10-09

### Added

- **Granular Silent Mode Control**: Advanced audio control with three independent modes
  - New `--silent` parameter with optional value support (announcements, sound-effects, all)
  - `--silent=announcements` disables TTS only while keeping sound effects enabled
  - `--silent=sound-effects` disables sound effects only while keeping TTS enabled
  - `--silent=all` or `--silent` (no value) disables both announcements and sound effects
  - Per-session environment variables: `CC_SILENT_ANNOUNCEMENTS` and `CC_SILENT_EFFECTS`
  - Backward compatible - `--silent` defaults to disabling both audio types

### Enhanced

- **Audio Processing Logic**: Independent control over TTS announcements and sound effects
  - Event processor now checks granular flags (`CC_SILENT_ANNOUNCEMENTS`, `CC_SILENT_EFFECTS`)
  - Clear logging when audio is skipped due to silent mode settings
  - Maintained parallel audio processing while respecting silent mode preferences
  - Better user feedback with mode-specific console messages

- **Session Configuration System**: Extended per-session override capabilities
  - Console feedback shows active silent mode: "all", "announcements only", or "sound effects only"
  - Environment variable propagation through server and hooks for consistent behavior
  - Support for combining silent modes with other session overrides (language, voice ID, providers)
  - Multiple concurrent sessions with different silent mode configurations

### Changed

- **Documentation Updates**: Comprehensive documentation for granular silent mode
  - CLAUDE.md updated with all silent mode options and combination examples
  - README.md enhanced with use case descriptions (meetings vs focused work)
  - Configuration precedence documentation updated to include silent mode parameters
  - Added 5 concurrent session examples demonstrating different audio configurations

## [0.16.5] - 2025-10-06

### Fixed

- **Update Script**: Removed incorrect `uv sync` dependency update step
  - Removed `uv sync` call that was incompatible with PEP 723 architecture
  - Project uses inline script dependencies (PEP 723), not `pyproject.toml`
  - Changed to verify `uv` installation instead (dependencies auto-managed via PEP 723)
  - Updated documentation to reflect correct dependency management approach
  - Eliminates "No pyproject.toml found" error during updates

## [0.16.4] - 2025-10-06

### Changed

- **Development Tools Rollback**: Reverted uv package manager to stable version
  - Rolled back from `uv@0.8.23` to `uv@0.5.29` in `.tool-versions`
  - Restored to previously stable version for better compatibility
  - Ensures consistent development environment across all contributors

## [0.16.3] - 2025-10-06

### Enhanced

- **Setup Validation System**: Improved `uv` package manager global accessibility validation
  - Added explicit test to verify `uv` works from any directory (runs test from `/tmp`)
  - Validates `uv` is installed in standard global locations (`~/.local/bin/`, `/bin/`,
    `~/.cargo/bin/`)
  - Detects and warns if `uv` is project-local instead of globally installed
  - Enhanced error messages with post-installation instructions (restart shell or source config)
  - Clearer success messages: "uv is globally accessible from any directory"

- **Documentation Improvements**: Enhanced README.md with `uv` installation clarity
  - Added post-installation step: restart shell or `source ~/.bashrc` (or `~/.zshrc`)
  - Added verification command: `uv --version` with note "should work from any directory"
  - Clarified that `uv` must be globally accessible, not project-local

### Technical

- **Global Accessibility Testing**: Multi-layered validation approach
  - `command -v uv` check for PATH availability
  - Directory-independent execution test (subshell cd to `/tmp`)
  - Installation path validation against known global locations
  - Project-local installation detection and warning system

## [0.16.2] - 2025-10-06

### Enhanced

- **WSL Shutdown Performance**: Optimized graceful shutdown timeouts for WSL environments
  - Automatic WSL environment detection via `/proc/version` checking
  - Reduced curl timeout from 2s to 1s for faster localhost API calls in WSL
  - Reduced max event wait timeout from 10s to 5s for faster shutdown (50% improvement)
  - Reduced server shutdown wait from 3s to 2s for more responsive cleanup
  - Max total shutdown time reduced from 15s to 8s in WSL environments
  - Native Linux/macOS environments maintain original timeout values for stability
  - Visual feedback: displays "WSL environment detected - using optimized timeouts" on startup

### Technical

- **Conditional Timeout Configuration**: Platform-aware timeout management system
  - `IS_WSL` flag for environment-specific optimizations
  - `CURL_TIMEOUT`, `MAX_EVENT_WAIT`, `SERVER_SHUTDOWN_WAIT` variables for dynamic timeout
    configuration
  - All timeout-dependent functions updated to use configurable timeout variables
  - Graceful degradation maintains safety while improving WSL user experience

## [0.16.1] - 2025-10-06

### Fixed

- **Instance Management Path Resolution**: Fixed critical bug with relative path handling in
  `claude.sh`
  - `INSTANCES_DIR` now uses absolute path based on script location instead of current working
    directory
  - `.env` file loading now resolves to script directory for consistent configuration access
  - `SERVER_SCRIPT` path now absolute, preventing startup failures when running from different
    directories
  - Prevents stale PID files when `claude.sh` is executed from directories other than cc-hooks root
  - Ensures proper cleanup during graceful shutdown regardless of working directory changes
  - Instance tracking files now always created in `<script-dir>/.claude-instances/` directory

### Technical

- **Path Resolution Architecture**: Enhanced wrapper script with `SCRIPT_DIR` variable
  - Uses `$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)` for reliable script location detection
  - All relative paths converted to absolute paths anchored to script directory
  - Better cross-directory execution support without breaking instance management
  - Improved reliability when running via absolute path or from different directories

## [0.16.0] - 2025-10-06

### Added

- **Automated Update System**: Comprehensive version management and update workflow
  - New `update.sh` script with smart uncommitted changes handling (auto-stash/restore)
  - Git-based version checking via `utils/version_checker.py` with 1-hour cache duration
  - Background version checks on server startup with SQLite persistence
  - Results cached in new `version_checks` table (migration v6)
  - Simple update workflow: `npm run update` or `./update.sh`
  - Version check command: `npm run version:check` for CLI-based status checking
  - Auto-fetch from origin/main with commits-behind tracking
  - Automatic dependency sync with `uv sync` after pull
  - Smart network connectivity checking before update attempts

- **Update Status API**: Real-time update information via REST endpoints
  - `/version/status` endpoint exposing version information and update availability
  - Force refresh support via `?force=true` query parameter to skip cache
  - Returns current version, latest version, commits behind, and update availability status
  - Integration with version checker's caching system for minimal network overhead

- **Status Line Update Notifications**: Visual update alerts in three-line status display
  - Third line notification shows when updates are available
  - Yellow-colored warning message with commits-behind count
  - Displays full update command: `cd <repo_root> && npm run update`
  - Update checks performed on status line render with cached results
  - Non-intrusive notification only appears when updates actually available

### Enhanced

- **Database Schema**: New migration for version tracking persistence
  - Migration v6 creates `version_checks` table with comprehensive fields
  - Stores current_version, latest_version, commits_behind, update_available, last_checked, error
  - Single-row table design (id=1) for current version status
  - Automatic cleanup and replacement on each check for fresh data

- **Version Checker Architecture**: Robust git-based version management
  - `VersionCheckResult` class for structured version information
  - In-memory caching with configurable expiration (1 hour default)
  - Database persistence for cross-session cache sharing
  - Git fetch with 10-second timeout to prevent hanging
  - Graceful error handling with detailed error messages
  - CLI interface for manual testing: `uv run utils/version_checker.py [--force]`

- **Update Script Features**: Production-ready update workflow
  - Detects uncommitted changes and offers interactive stash
  - Validates network connectivity before attempting fetch
  - Shows git status and confirms before stashing changes
  - Automatic stash restore after successful update
  - Comprehensive error handling with rollback on failure
  - Color-coded terminal output for better readability
  - Displays current version after successful update

### Changed

- **Documentation Updates**: Comprehensive version management documentation
  - CLAUDE.md enhanced with "Version Management" section and update workflow guide
  - Added API endpoint examples for `/version/status` with force refresh
  - Updated development commands section with `npm run update` and `npm run version:check`
  - README.md updated with prerequisites section including mise installation hint
  - Enhanced testing section with version check API examples

- **Development Workflow**: Streamlined update and version checking
  - New NPM scripts for simplified update management
  - `npm run update` provides one-command update workflow
  - `npm run version:check` enables quick CLI-based version status
  - Better integration with existing development tools and scripts

- **Gitignore Enhancement**: IDE-specific directories excluded
  - Added `.vscode/` and `.idea/` to .gitignore
  - Prevents IDE configuration pollution in version control

### Technical

- **API Integration**: Version checker integrated into FastAPI lifecycle
  - Server creates `VersionChecker` instance with configured database path
  - Async git operations with proper timeout handling
  - Background version checks don't block server startup
  - Graceful degradation when git commands fail

- **Status Line Architecture**: Extended to support three-line layout
  - Line 1: Main context (project, directory, git, model, cc-hooks, TTS, OpenRouter)
  - Line 2: Usage metrics (session stats, cost tracking)
  - Line 3: Update notifications (conditional, only when updates available)
  - Yellow color coding for update warnings using `\033[1;33m` ANSI codes

## [0.15.0] - 2025-10-05

### Added

- **Enhanced Status Line Display**: Two-line layout with improved information architecture
  - Line 1: Main context and features (project, directory, git, model, cc-hooks, TTS, OpenRouter)
  - Line 2: Dedicated usage and cost information (session stats, cost tracking)
  - Better visual separation between contextual info and resource usage metrics
  - Improved readability for complex configurations with multiple active features

- **OpenRouter Status Integration**: Real-time OpenRouter service monitoring in status line
  - New OpenRouter status indicator with emoji and model display (🔀)
  - Shows active model name and enabled contextual features (Stop, PreTool)
  - Connection status checking with color-coded indicators (🟢 online, 🔴 offline, ❌ error)
  - Automatic feature flag display for enabled contextual services
  - Format: `🔀 🟢 gpt-4o-mini (Stop, PreTool)` or `🔀 🟢 gpt-4o-mini` when no features enabled

### Changed

- **Status Line Architecture**: Restructured layout for better scalability
  - Split single-line display into two dedicated lines for better organization
  - Line 1 focuses on execution context: project, directory, git branch, model, hooks status
  - Line 2 reserved for ccusage metrics: session progress, cost tracking, hourly burn rate
  - Improved emoji consistency (💥 for model, 🎧 for cc-hooks, 🟢 for online status)
  - Better color coding with new OpenRouter cyan color (`openrouter_color()`)

- **Dependency Version Strictness**: Updated all PEP 723 script dependencies with version ranges
  - All Python dependencies now use strict version ranges (e.g., `>=2.32.5,<3`)
  - Affects: `hooks.py`, `server.py`, `status-lines/status_line.py`, `utils/sound_player.py`,
    `utils/tts_announcer.py`
  - Better dependency management and conflict resolution with explicit version boundaries
  - Prevents unintended breaking changes from major version updates

- **ccusage Dependency Update**: Bumped to latest version
  - Updated from `ccusage@16.2.4` to `ccusage@16.2.5`
  - Updated in both `package.json` and `package-lock.json`

- **Development Tools Update**: Updated uv package manager to latest version
  - Updated from `uv@0.5.29` to `uv@0.8.23` in `.tool-versions`
  - Major version bump with improved performance and stability
  - Updated README prerequisites with explicit uv installation instructions
  - Added Node.js prerequisite mention for ccusage dependency

## [0.14.2] - 2025-09-18

### Added

- **Database Cleanup System**: Streamlined SQLite database maintenance tools
  - New `db_cleanup.sh` script focused on essential operations: truncate and statistics
  - Single-purpose design: complete database reset (truncate) or statistics display only
  - Strong safety features: requires typing "TRUNCATE" for confirmation, dry-run mode support
  - Color-coded terminal output with detailed database statistics and file size reporting
  - Simplified NPM script integration: `npm run db:cleanup` (truncate), `npm run db:stats`
    (statistics)
  - Cross-platform sqlite3 installation guidance with automatic availability detection
  - Database optimization with VACUUM operation after truncate for optimal performance

## [0.14.1] - 2025-09-17

### Fixed

- **OpenRouter Response Lag**: Improved prompt structure to reduce AI processing time and response
  lag
  - Moved language instruction to beginning of prompt for better model attention and faster
    processing
  - Language directive now appears at start of context rather than end, reducing parsing overhead
  - Optimization applies to both contextual completion messages and PreToolUse message generation
  - Should result in more responsive contextual AI features with reduced latency

## [0.14.0] - 2025-09-15

### Added

- **ccusage Dependency Integration**: Added ccusage package for enhanced Claude Code usage tracking
  - New production dependency `ccusage@^16.2.4` for cost and usage monitoring
  - Enhanced status line integration with local-first ccusage detection
  - Comprehensive npm script integration: `npm run check` and `npm run check:verbose`
  - Improved project setup verification workflow

### Enhanced

- **Status Line ccusage Detection**: Smart ccusage binary resolution with local-first priority
  - Checks project `node_modules/.bin/ccusage` before falling back to global installation
  - Better debug logging for ccusage path resolution and availability
  - Improved reliability for projects with local ccusage installations
  - Maintains backward compatibility with global ccusage installations

- **Project Structure Organization**: Cleaner asset organization and documentation flow
  - Moved `banner.png` and `thumbnail.png` to `public/` directory for better organization
  - Updated README.md asset references to reflect new public directory structure
  - Enhanced installation workflow with separate dependency installation and verification steps
  - Restructured installation guide from 4 to 6 clear steps for better user experience

### Changed

- **Installation Documentation**: Streamlined setup process with clearer step separation
  - Split dependency installation from setup verification for better workflow
  - Added optional mise support for automatic Python, uv, and Node.js installation
  - Enhanced troubleshooting section with new npm script commands
  - Better structured installation steps with numbered progression

- **Package Management**: Simplified package configuration
  - Removed `packageManager` field from package.json for broader compatibility
  - Updated formatting scripts to use `uvx black` for better uv integration
  - Enhanced npm scripts for setup checking and validation workflows

## [0.13.0] - 2025-09-15

### Added

- **CamelCase-to-Readable Text Conversion**: Enhanced TTS system with intelligent programming
  identifier conversion
  - Converts camelCase variables to readable text: `getUserName` → `"get user name"`
  - Smart pattern detection for camelCase, PascalCase, and mixed alphanumeric identifiers
  - Preserves common brand names (JavaScript, React, GitHub, etc.) to avoid unwanted splitting
  - Multi-level fallback protection: returns original text if any conversion step fails
  - Lowercase normalization for consistent TTS pronunciation across all providers
  - Integrated into existing TTS text cleaning pipeline for seamless operation

- **TTS Providers Override Parameter**: New `--tts-providers` command-line parameter for per-session
  provider configuration
  - Override TTS provider chain per session: `./claude.sh --tts-providers=gtts,prerecorded`
  - Support for `CC_TTS_PROVIDERS` environment variable override in config system
  - Enable multiple concurrent Claude Code sessions with different TTS configurations
  - Comprehensive examples added to `.env.example` with usage patterns
  - Compatible with existing `--language` and `--elevenlabs-voice-id` parameters

- **Enhanced Status Line TTS Provider Display**: Unified status line system for all TTS providers
  - Generic TTS provider status display replacing ElevenLabs-specific implementation
  - Shows active provider name, voice information, and connection status for all providers
  - Language display consistency: ElevenLabs voices now show language like Google TTS
    (`"Cahaya (ID)"`)
  - Provider-specific information display based on available capabilities
  - Backward compatibility maintained with existing `elevenlabs_color()` method

### Changed

- **TTS Text Processing Pipeline**: Enhanced text cleaning with programming-aware conversions
  - Added camelCase conversion step after markdown cleanup, before lowercase normalization
  - Improved None/empty input handling with explicit empty string returns
  - Robust error handling with detailed logging for debugging conversion issues

### Technical

- **Status Line Architecture**: Refactored from provider-specific to generic TTS provider system
- **Documentation Updates**: Added `--tts-providers` parameter examples and environment variable
  documentation
- **Package Configuration**: Added `packageManager` field specifying pnpm version requirement

## [0.12.1] - 2025-09-12

### Fixed

- **OpenRouter Language Response**: Fixed issue where model was not returning responses in the
  target language
  - Removed conditional language instruction that only applied when target language was not English
  - Language instruction now always included regardless of target language (English, Indonesian,
    etc.)
  - Moved language instruction to end of prompt for better model attention and compliance
  - Ensures consistent language output across all OpenRouter-powered features (translation,
    contextual messages)

## [0.12.0] - 2025-09-12

### Added

- **Database Performance Optimization**: Added critical indexes for query performance
  - Composite index `idx_events_processing` on `(instance_id, status, created_at, id)` for event
    processing optimization
  - Session index `idx_events_session` on `session_id` for debugging and analytics support
  - Automatic migration system applies indexes on server startup
  - Significant performance improvement for `get_next_pending_event()` queries as database grows

### Changed

- **Migration System Enhancement**: Split multi-statement migrations to handle SQLite limitations
  - Fixed "You can only execute one statement at a time" error by separating index creation
  - Migration v4: Primary composite index for critical event processing queries
  - Migration v5: Secondary session index for debugging capabilities
  - Improved database query performance and scalability

## [0.11.0] - 2025-09-11

### Added

- **Per-Session Language & Voice Overrides**: New command-line parameters for dynamic TTS
  configuration
  - `--language=LANG` parameter to override TTS language per session (e.g.,
    `./claude.sh --language=id`)
  - `--elevenlabs-voice-id=ID` parameter to override ElevenLabs voice ID per session
  - Automatic environment variable setup: `CC_TTS_LANGUAGE` and `CC_ELEVENLABS_VOICE_ID`
  - Support for multiple concurrent Claude Code sessions with different voice configurations
  - Configuration precedence: session parameters → environment variables → default values
  - Comprehensive testing examples with per-session override environment variables

### Changed

- **Configuration System Enhancement**: Updated config loading to prioritize per-session overrides
  - Modified `config.py` to check `CC_TTS_LANGUAGE` and `CC_ELEVENLABS_VOICE_ID` first
  - Enhanced `claude.sh` argument parsing to extract cc-hooks specific parameters
  - Updated documentation with detailed usage examples and configuration precedence

### Fixed

- **Server Startup Environment Variables**: Fixed timing issue where server started before
  per-session overrides were set
  - Moved argument parsing to occur before server startup instead of after
  - Environment variables now properly propagated to server process at startup time
  - Per-session overrides now correctly override .env configuration
- **Multi-Session Voice Isolation**: Resolved potential voice configuration conflicts between
  concurrent sessions
  - Each session now maintains independent TTS configuration without affecting others
  - Clean separation between global `.env` configuration and per-session overrides

## [0.10.0] - 2025-09-11

### Changed

- **Documentation Streamlining**: Major CLAUDE.md refactoring for better maintainability and clarity
  - Simplified documentation from 774 to 229 lines, focusing on essential information
  - Removed verbose architectural explanations, emphasized practical development workflows
  - Enhanced testing command examples with clear environment variable usage
  - Better organized component testing sections with comprehensive examples
  - Improved development experience documentation with more concise, actionable guidance

### Fixed

- **Constants Management**: Comprehensive refactoring to centralize magic numbers and improve
  maintainability
  - Extracted all magic numbers from `hooks.py` to centralized constants in `utils/constants.py`
  - Added consistent constants imports across all components: `app/api.py`, `app/event_db.py`
  - Centralized HTTP timeout configuration in `utils/openrouter_service.py`
  - Improved TTS provider consistency with shared timeout constants in `elevenlabs_provider.py` and
    `gtts_provider.py`
  - Enhanced error code management with centralized exit codes (CONNECTION_ERROR_EXIT_CODE,
    INVALID_EVENT_EXIT_CODE)
  - Better port management with DEFAULT_PORT_START, MAX_PORT_ATTEMPTS constants
  - Improved instance management with INSTANCE_SHUTDOWN_TIMEOUT, INSTANCE_CLEANUP_DELAY constants
- **Setup Script Improvements**: Enhanced `check_setup.sh` reliability and consistency
  - Fixed port detection logic to match claude.sh behavior for better consistency
  - Improved instance ID handling and structural fixes
  - Added proper dynamic port assignment support
  - Better integration with existing Claude Code instance management system

## [0.9.0] - 2025-09-10

### Added

- **Dedicated Server Per Instance Architecture**: Complete architectural overhaul for better
  isolation and performance
  - Each Claude Code instance now runs its own dedicated server on a unique port
  - Automatic port discovery starting from 12222, incrementing as needed for multiple instances
  - New `/shutdown` API endpoint for graceful server termination via API calls
  - Enhanced instance tracking with port information stored in `.claude-instances/` directory
- **New Environment Variables**: Introduction of `CC_HOOKS_PORT` alongside existing `CC_INSTANCE_ID`
  - `CC_HOOKS_PORT` communicates assigned port from wrapper to hook scripts
  - Automatic port assignment eliminates manual configuration requirements
  - Environment variables properly propagated through entire event processing pipeline
- **Enhanced Status Line Integration**: Status line now displays instance-specific port information
  - Real-time port display format: `🔗 ✅ cc-hooks:12222` (shows actual assigned port)
  - Port-aware health checks use correct instance-specific endpoints
  - Dynamic port detection from environment for accurate status reporting

### Changed

- **Server Lifecycle Management**: Complete redesign from shared to dedicated server model
  - Eliminated shared server approach in favor of per-instance dedicated servers
  - Each instance manages its own server lifecycle independently
  - Improved startup process with dedicated server configuration per instance
  - Enhanced shutdown process stops only the instance-specific server
- **Instance Event Processing**: Enhanced event filtering with strict instance isolation
  - Event processor now requires instance ID for proper event filtering
  - Database queries filter events by both temporal (server start time) and instance criteria
  - Exit with error code if server start time or instance ID missing (prevents processing stale
    events)
- **Configuration Simplification**: Removed manual host/port configuration requirements
  - `HOST` and `PORT` environment variables no longer required in `.env`
  - Automatic port management eliminates configuration complexity
  - Updated `.env.example` to reflect streamlined configuration approach
- **Improved Logging Levels**: Optimized logging verbosity for production use
  - Database initialization and TTS provider setup now use debug level instead of info
  - Reduced log noise while maintaining comprehensive debug capabilities
  - Better distinction between operational info and debug messages

### Fixed

- **Port Conflict Resolution**: Automatic port discovery prevents conflicts between instances
  - Robust port availability checking before server startup
  - Graceful handling of port conflicts with automatic increment
  - Safety limits prevent infinite loops in port discovery
- **Instance Isolation**: Complete separation of event processing between Claude Code instances
  - No cross-contamination of events between different sessions
  - Instance-specific event queues and processing
  - Proper cleanup of instance-specific resources during shutdown

## [0.8.0] - 2025-09-10

### Added

- **Centralized Colored Logging System**: Introduced comprehensive logging system with per-component
  colored output
  - New `utils/colored_logger.py` module provides consistent logging configuration across all
    components
  - Each component gets distinctively colored log messages for easier debugging and log
    identification
  - Centralized root logging configuration prevents duplicate log handlers
  - Uses `coloredlogs` library for professional, readable log output

### Changed

- **Enhanced Logging Infrastructure**: Migrated all components from standard logging to new colored
  logging system
  - Updated `app/api.py`, `app/event_db.py`, `app/event_processor.py`, `app/migrations.py`
  - Updated `hooks.py`, `server.py`, and all utility modules
  - Improved debug logging with better context information throughout the system
- **Audio Processing Order**: Reordered audio task processing to prioritize TTS announcements over
  sound effects
  - TTS announcements now processed before sound effects for better user experience
  - Maintains parallel execution for optimal performance
- **Enhanced Error Handling**: Improved error messages and debug logging across multiple components
  - Better context logging in `transcript_parser.py` and `openrouter_service.py`
  - More descriptive error messages with reduced verbosity in API components
  - Enhanced debugging capabilities with full context preservation

### Fixed

- **Logging Consistency**: Resolved logging inconsistencies and duplicate handler issues
  - Prevents log message duplication through centralized configuration
  - Ensures all components use consistent logging format and colors
- **Context Preservation**: Enhanced context logging in transcript parsing and OpenRouter
  integration
  - Full user prompts and Claude responses preserved in debug logs
  - Better error context for troubleshooting complex conversation flows

## [0.7.2] - 2025-09-09

### Fixed

- **Instance PID Extraction**: Fixed bug in `claude.sh` where PID was incorrectly read from file
  contents instead of filename
  - Changed PID extraction logic to use `basename "$pidfile" .pid` to extract PID from filename
  - Resolves stale process cleanup issues where UUID content was being treated as PID

## [0.7.1] - 2025-09-07

### Changed

- **Default Port Configuration**: Updated default server port from 12345 to 12222 across all
  components
  - Updated default port in `config.py` and `.env.example`
  - Enhanced `claude.sh` wrapper with dynamic port loading from environment
  - Improved port configuration with .env file integration and fallback handling
- **Enhanced Wrapper Script**: Improved `claude.sh` with better configuration management
  - Added CC_ORIGINAL_DIR support for directory context preservation
  - Enhanced status messages to display actual port being used
  - Better environment variable loading from .env files
- **Dependency Management**: Added python-dotenv to hooks.py script dependencies for better
  environment handling

### Fixed

- **Port Consistency**: Ensured all components use the same configurable port instead of hardcoded
  values
- **Environment Loading**: Improved environment variable handling in wrapper script

## [0.7.0] - 2025-09-07

### Added

- **Contextual PreToolUse Messages**: AI-powered action-oriented messages for enhanced tool
  execution awareness
  - New `generate_pre_tool_message()` function in `OpenRouterService` for dynamic PreToolUse message
    generation
  - Dedicated system prompt optimized for action descriptions rather than tool announcements
  - Context-first approach describing what Claude will do based on user's request
  - Natural conversational messages like "Installing the dependencies you requested" instead of
    "Running Bash tool"
  - Separate configuration control via `OPENROUTER_CONTEXTUAL_PRETOOLUSE` environment variable
  - `generate_pre_tool_message_if_available()` convenience function with graceful fallbacks
- **Enhanced Session Management**: Improved memory management for transcript parsing
  - Session cleanup logic in `handle_session_end()` and `handle_stop()` event handlers
  - `clear_last_processed_message()` function for removing session-specific tracking data
  - `cleanup_old_processed_files()` function for automatic cleanup of old processed files (24
    hours+)
  - Better memory management preventing accumulation of tracking files across sessions
- **Cost Control Configuration**: Granular control over contextual message features
  - `OPENROUTER_CONTEXTUAL_STOP` and `OPENROUTER_CONTEXTUAL_PRETOOLUSE` environment variables
  - Both contextual features disabled by default to prevent unexpected API costs
  - Independent control allowing users to enable only desired contextual features
  - Translation services remain available regardless of contextual message settings

### Enhanced

- **OpenRouter Service Architecture**: Extended service capabilities beyond completion messages
  - Enhanced constructor with `contextual_stop` and `contextual_pretooluse` parameters
  - Feature-specific enablement checking preventing unnecessary API calls when disabled
  - Improved prompt engineering with action-oriented system prompts for PreToolUse messages
  - Better separation between translation, completion, and PreToolUse message generation services
- **Transcript Parser Integration**: Better handling of conversation context extraction
  - Enhanced logic for Stop event processing in transcript parsing
  - Improved message hash tracking system for preventing duplicate processing
  - Better error handling and graceful fallbacks when transcript parsing fails
- **Configuration Management**: Extended configuration system for contextual features
  - New configuration fields in root `config.py` for contextual message control
  - Proper service initialization with contextual feature flags
  - Complete `.env.example` updates with contextual message configuration examples

### Changed

- **OpenRouter Service Initialization**: Updated service creation with contextual feature parameters
  - Modified `initialize_openrouter_service()` function signature to include contextual flags
  - Updated service instantiation in `config.py` to pass contextual configuration
  - Better service lifecycle management with feature-specific initialization
- **Event Processing Cleanup**: Enhanced session lifecycle management
  - Proactive cleanup in Stop and SessionEnd event handlers
  - Automatic removal of stale tracking files during session transitions
  - Improved error handling for cleanup operations with warning-level logging

### Documentation

- **CLAUDE.md Comprehensive Updates**: Complete documentation for contextual PreToolUse messages
  - New "Contextual PreToolUse Messages" architectural pattern section
  - Enhanced OpenRouter configuration documentation covering all three service types
  - Updated testing examples for contextual PreToolUse message generation
  - Expanded cost control documentation with selective enablement examples
  - Additional troubleshooting scenarios for contextual message features
- **Configuration Examples**: Real-world usage scenarios for contextual features
  - Complete `.env.example` updates with contextual message configuration examples
  - Multiple configuration scenarios showing different feature combinations
  - Cost-effective model recommendations for contextual message generation
  - Testing commands for validating contextual PreToolUse functionality

## [0.6.0] - 2025-09-07

### Added

- **Contextual Completion Messages**: AI-powered dynamic completion messages for enhanced user
  experience
  - `utils/transcript_parser.py` for extracting conversation context from Claude Code JSONL
    transcripts
  - Intelligent parsing of user prompts and Claude responses from conversation history
  - `ConversationContext` class for structured context management with validation
  - Support for both string and array content formats from Claude Code transcripts
- **Enhanced OpenRouter Integration**: Extended AI services beyond translation
  - New `generate_completion_message_if_available()` function for contextual message generation
  - Separate system prompts for translation vs completion message tasks
  - Session-aware completion message generation with conversation context
  - Multi-language support for completion messages respecting `TTS_LANGUAGE` configuration
- **Smart TTS Text Preparation**: Centralized text processing for all TTS providers
  - `_prepare_text_for_event()` function consolidating text determination logic
  - Special Stop event handling using transcript parser + OpenRouter for dynamic messages
  - Consistent translation workflow across all TTS providers
  - Graceful fallback to default messages when context unavailable

### Enhanced

- **TTS Providers Architecture**: Simplified and more efficient text processing
  - Removed duplicated translation logic from individual providers (`GTTSProvider`,
    `ElevenLabsProvider`)
  - Providers now use prepared text from `tts_announcer.py` via `_prepared_text` event data field
  - Better separation of concerns between text preparation and audio generation
- **Advanced Caching Strategy**: Context-aware caching for optimal performance
  - `_no_cache` flag support for dynamic content (contextual completion messages)
  - Static content cached for performance, dynamic content generates fresh for relevance
  - Per-event caching control ensuring contextual messages remain current
- **Stop Event Intelligence**: Context-aware completion announcements
  - Integration with Claude Code transcript files for real conversation context
  - Dynamic completion messages based on actual user interactions
  - Falls back to standard completion messages when transcript unavailable
  - No-cache strategy ensures completion messages reflect current session context

### Changed

- **OpenRouter Service Architecture**: Improved prompt engineering and service separation
  - Moved Claude Code context from user prompts to dedicated system prompts
  - Separate system prompts optimized for translation vs completion message generation
  - Cleaner prompt templates with better context separation
  - Enhanced completion message prompts with conversation context formatting
- **TTS Text Processing Flow**: Streamlined text preparation workflow
  - Centralized text preparation in `tts_announcer.py` before provider calls
  - Enhanced event data with `_prepared_text` field for provider consumption
  - Removed translation logic duplication across multiple provider files
  - Better error handling and fallback chain for text preparation failures

### Documentation

- **CLAUDE.md Enhancements**: Comprehensive documentation updates for new features
  - New "Contextual Completion Messages" architectural pattern section
  - Enhanced OpenRouter configuration documentation covering both translation and completion
    services
  - Updated TTS system documentation with contextual completion capabilities
  - Added practical implementation guide for contextual completion messages
  - Enhanced testing examples for transcript parser and OpenRouter completion generation
  - Updated important gotchas with TTS caching strategy and transcript parser limitations

## [0.5.0] - 2025-09-07

### Added

- **OpenRouter API Integration**: AI-powered translation services for multilingual TTS support
  - `utils/openrouter_service.py` providing generic OpenRouter API interface
  - Support for multiple LLM providers through OpenRouter (Google Gemini, OpenAI GPT, Claude, etc.)
  - Automatic translation of TTS text when `TTS_LANGUAGE` is not "en"
  - Configurable model selection with sensible defaults (`openai/gpt-4o-mini`)
  - Graceful fallback to original English text if translation fails
  - Generic service architecture for future AI-powered features beyond translation

### Enhanced

- **TTS Providers with Translation**: Automatic text translation before speech generation
  - `GTTSProvider` and `ElevenLabsProvider` now support OpenRouter translation integration
  - Smart language detection - only translates when target language differs from English
  - Maintains existing functionality when OpenRouter is disabled or unavailable
  - Seamless fallback chain: AI translation → TTS generation → audio playback
- **Configuration System**: Extended with OpenRouter settings
  - New environment variables: `OPENROUTER_ENABLED`, `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`
  - Centralized service initialization in root-level `config.py`
  - Complete configuration examples in `.env.example` with multiple scenarios
- **Parallel Audio Processing**: Concurrent execution of audio tasks for improved performance
  - Sound effects and TTS announcements now run in parallel using `asyncio.gather()`
  - Significantly reduced audio processing latency for events with multiple audio tasks
  - Maintains individual provider error handling while improving overall responsiveness
  - Graceful handling of mixed success/failure scenarios across concurrent audio tasks
- **PrerecordedProvider Enforcement**: Stricter validation for sound file existence
  - Only plays sounds that actually exist on disk
  - Better fallback to TTS providers when prerecorded sounds unavailable
  - Improved logging for missing sound file scenarios

### Documentation

- **OpenRouter Integration Guide**: Complete setup and configuration documentation
  - API key setup instructions with links to OpenRouter dashboard
  - Model selection guide with recommendations for different use cases
  - Translation workflow examples for Indonesian, Spanish, and other languages
  - Testing commands for validating OpenRouter integration
- **Configuration Examples**: Real-world configuration scenarios
  - Multi-language TTS with AI translation examples
  - Provider priority configuration for different language combinations
  - Troubleshooting guide for translation failures and fallbacks

### Dependencies

- **OpenAI SDK**: Added for OpenRouter API communication
  - Lazy-loaded dependency - system works without OpenAI SDK installed
  - Proper error handling when dependencies unavailable
  - Added to server.py PEP 723 script dependencies

## [0.4.0] - 2025-09-07

### Added

- **Advanced TTS Provider System**: Comprehensive text-to-speech architecture with provider chain
  pattern
  - Abstract base class `TTSProvider` for extensible TTS implementations
  - Factory pattern for provider registration and parameter filtering in
    `utils/tts_providers/factory.py`
  - Three built-in providers: `prerecorded`, `gtts` (Google TTS), and `elevenlabs` (ElevenLabs API)
  - Smart parameter filtering - providers only receive supported parameters
  - Context-aware event mapping system analyzing event data beyond just event names
  - Intelligent fallback chain with configurable priority order (leftmost = highest priority)
- **TTS Provider Implementations**:
  - `PrerecordedProvider`: Uses existing sound files from `sound/` directory
  - `GTTSProvider`: Google Text-to-Speech integration with caching support
  - `ElevenLabsProvider`: Advanced voice cloning with API integration and rate limit handling
  - Event-to-text mapping system with 19+ comprehensive event contexts
- **Enhanced Configuration System**: Root-level configuration management
  - Moved configuration from `app/config.py` to root-level `config.py` for better organization
  - Comprehensive `.env.example` with all TTS configuration options and examples
  - TTS provider priority configuration via `TTS_PROVIDERS` comma-separated list
  - ElevenLabs-specific settings: API key, voice ID, model selection
  - Language and caching configuration for TTS generation
- **Type-Safe Event System**: Enum-based event validation and constants
  - `utils/hooks_constants.py` with `HookEvent` enum for all supported events
  - `is_valid_hook_event()` validation function preventing invalid event names
  - Type-safe event status constants with literal types in `event_db.py`
  - API integration with automatic event name validation (warning for unknown events)

### Enhanced

- **TTS Manager Integration**: Orchestrated multi-provider TTS system
  - `utils/tts_manager.py` managing provider chain with automatic fallbacks
  - Server initialization includes TTS system setup with configured providers
  - Graceful cleanup during server shutdown to prevent resource leaks
  - Integration with existing announcement system via `utils/tts_announcer.py`
- **Event Processing Architecture**: Improved processing with type safety
  - Event processor uses enum constants instead of string literals
  - Enhanced validation with graceful handling of unknown events
  - Better error handling and logging for invalid event types
  - Maintained backwards compatibility while improving type safety
- **Cross-Platform Audio System**: Improved sound playback reliability
  - Enhanced `utils/sound_player.py` with better error handling
  - Consistent audio backend usage across all TTS providers
  - Synchronous playback maintained to prevent audio overlap
- **Documentation**: Comprehensive architectural and development documentation
  - Major CLAUDE.md updates with architectural patterns and dependencies
  - TTS provider development guide with examples
  - Enhanced troubleshooting sections for TTS system
  - Complete API documentation with TTS configuration examples

### Changed

- **Configuration Architecture**: Centralized configuration management
  - All components now import from root-level `config.py` instead of `app/config.py`
  - TTS-related configuration integrated into main config class
  - Environment variable parsing improved with type safety
- **Import Structure**: Updated import paths across entire codebase
  - All `from app.config import config` changed to `from config import config`
  - Consistent import structure throughout all modules
  - Better separation of concerns between app logic and configuration

### Documentation

- **Architectural Patterns**: Detailed documentation of key design patterns
  - Multi-instance server sharing pattern explanation
  - Provider chain pattern for TTS system architecture
  - Async/sync bridge pattern for handling different execution contexts
  - Type-safe event handling pattern with enum usage
- **Development Workflows**: Enhanced development and testing documentation
  - TTS provider testing commands and examples
  - Provider availability checking and debugging
  - Event-specific testing with different TTS configurations
  - Step-by-step provider development guide
- **Configuration Guide**: Complete configuration documentation
  - All environment variables documented with examples
  - TTS provider priority configuration explained
  - ElevenLabs setup guide with API key requirements
  - Multiple configuration scenarios for different use cases

## [0.3.2] - 2025-09-06

### Added

- **Instance Tracking System**: Comprehensive tracking and identification of Claude Code instances
  - `CC_INSTANCE_ID` environment variable automatically set by wrapper script
  - UUID-based instance identification for better session management
  - Instance-specific event filtering and status tracking
  - New API endpoint `/instances/{instance_id}/last-event` for per-instance event monitoring
- **Server Lifecycle Management**: Enhanced startup/shutdown coordination
  - Server start time tracking for event filtering and session management
  - Improved instance cleanup during wrapper script shutdown
  - Better pending event detection before server shutdown
  - UUID generation and management for unique instance identification

### Enhanced

- **Database Operations**: Added server start time tracking and instance-based event filtering
  - `set_server_start_time()` and `get_server_start_time()` functions for session boundaries
  - `get_last_event_status_for_instance()` for instance-specific event monitoring
  - Improved event queries with server start time filtering
- **API Endpoints**: Instance-aware event processing and status monitoring
  - Optional `instance_id` field in event submission model
  - Enhanced event queuing with automatic instance ID extraction from environment
  - New instance status endpoint for better session coordination
- **Wrapper Script**: More robust instance lifecycle management
  - Automatic UUID generation for unique instance identification
  - `check_last_event_pending()` function for graceful shutdown coordination
  - Improved error handling and cleanup during startup/shutdown sequences
- **Hook Integration**: Automatic instance tracking without user configuration
  - Environment variable detection for seamless instance identification
  - Backwards compatible - works with or without instance tracking

### Documentation

- **CLAUDE.md Updates**: Enhanced development workflow and API documentation
  - Updated API examples with instance tracking usage
  - Improved server lifecycle troubleshooting section
  - Better structured development testing commands

## [0.3.1] - 2025-09-06

### Added

- **Development Server Hot Reload**: Enhanced development workflow with automatic code reloading
  - `npm run dev` now starts server with `--dev` flag (includes hot reload)
  - `npm run dev:reload` provides explicit hot reload command
  - `uv run server.py --dev` and `uv run server.py --reload` support for direct server usage
  - Watch directories configured for `app/`, `utils/`, and root directory
  - Excludes databases, instances, and sound files from reload watching

### Enhanced

- **Server Configuration**: Improved development experience with conditional reload logic
  - Automatic detection of `--reload` and `--dev` command line arguments
  - Production mode preserved for normal server operations
  - Better separation between development and production server startup

### Documentation

- **CLAUDE.md Improvements**: Updated development workflow documentation
  - Clarified development testing commands with hot reload examples
  - Enhanced formatting and structure for better readability
  - Improved changelog workflow documentation formatting

## [0.3.0] - 2025-09-06

### Added

- **TTS Announcement System**: Intelligent context-aware voice announcements
  - Smart event-to-sound mapping based on hook event names and context
  - 19 comprehensive sound effects covering all Claude Code hook events
  - `utils/tts_announcer.py` utility with command-line interface
  - `--announce` argument support with configurable volume levels
  - Context extraction from event data for precise sound selection
- **Enhanced Sound Processing**: Improved audio handling for sequential events
  - Changed from asynchronous to synchronous sound playback
  - Prevents sound overlap during rapid event sequences
  - Better error handling and logging for audio operations

### Changed

- **Event Processing Performance**: Reduced NO_EVENTS_WAIT_SECONDS from 1s to 0.1s
  - Significantly improved system responsiveness
  - Better user experience with faster event processing
- **Sound API Consistency**: Renamed `play_sound_effect()` to `play_sound()`
  - Unified function naming across sound utilities
  - Backwards compatible argument processing

## [0.2.0] - 2025-09-06

### Added

- **Sound Effects Support**: Built-in audio feedback system with synchronous playback
  - Sound files can be placed in `sound/` directory
  - Cross-platform audio playback via `utils/sound_player.py`
  - Graceful error handling when sound files or audio system unavailable
- **Hook Arguments System**: Dynamic command-line argument support for hooks
  - `--sound_effect=filename.wav` for audio feedback
  - `--debug=true` for enhanced logging
  - `--key=value` and `--flag` format support for extensibility
- **Database Schema Enhancement**: Added `arguments` column to events table
  - Migration system automatically applies schema updates
  - Arguments stored as JSON for flexible parameter passing
- **Enhanced API Model**: Optional `arguments` field in event submission
  - Backwards compatible with existing hook configurations
  - Support for complex argument structures

### Enhanced

- **Event Processing**: Arguments passed to event handlers for custom processing
- **Hook Script**: Dynamic argument parsing instead of hardcoded parameters
- **Database Operations**: Updated queries to handle arguments column
- **API Endpoints**: Enhanced event submission with optional arguments support

### Documentation

- Updated CLAUDE.md with comprehensive feature documentation
- Added API usage examples with argument examples
- Enhanced database management commands
- Documented migration system and versioning

## [0.1.0] - 2025-09-06

### Added

- **Initial Project Setup**: Basic Claude Code hooks processing system
- **Core Architecture**:
  - Hook script (`hooks.py`) for receiving Claude Code events
  - FastAPI server (`server.py`) with background event processing
  - Wrapper script (`claude.sh`) for server lifecycle management
- **Database System**: SQLite-based event queue with retry logic
  - Events table with session tracking and status management
  - Automatic retry mechanism for failed events (max 3 attempts)
- **Server Lifecycle Management**: Sophisticated multi-instance support
  - Instance tracking via `.claude-instances/` directory
  - Graceful startup/shutdown with health checks
  - Shared server across multiple Claude Code sessions
- **Configuration System**: Environment-based configuration with defaults
- **API Endpoints**:
  - `/health` - Server health check
  - `/events` - Event submission endpoint
  - `/events/status` - Queue status monitoring
- **Migration System**: Automatic database schema management
- **Development Tools**:
  - Package management via uv with PEP 723 inline dependencies
  - Code formatting with Black and Prettier
  - Development and production run scripts

### Documentation

- Comprehensive CLAUDE.md with architecture overview
- Development commands and troubleshooting guides
- Server lifecycle management documentation

---

## Version Strategy

This project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html):

- **0.x.x**: Pre-release development versions
- **Major (x.0.0)**: Breaking changes or significant feature milestones
- **Minor (0.x.0)**: New features, enhancements, backwards-compatible changes
- **Patch (0.0.x)**: Bug fixes, small improvements, documentation updates

**Version 1.0.0** will be released when the system is considered production-ready with:

- Stable API interface
- Comprehensive error handling
- Performance optimization
- Production deployment guides
- Full test coverage
