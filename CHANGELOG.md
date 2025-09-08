# Changelog

All notable changes to the Claude Code hooks processing system will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
