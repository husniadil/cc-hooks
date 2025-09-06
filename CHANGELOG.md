# Changelog

All notable changes to the Claude Code hooks processing system will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
