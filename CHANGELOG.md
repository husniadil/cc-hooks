# Changelog

All notable changes to the Claude Code hooks processing system will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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