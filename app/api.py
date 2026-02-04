from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import os
import signal
from app.event_db import (
    queue_event,
    query_events,
    store_session,
    get_session_by_id,
    get_session_by_pid,
    delete_session,
    cleanup_orphaned_sessions,
    get_active_session_count,
    get_last_event_status_for_instance,
)
from app.migrations import get_migration_status
from utils.hooks_constants import is_valid_hook_event
from utils.colored_logger import setup_logger, configure_root_logging
from utils.constants import EventStatus, HTTPStatusConstants, NetworkConstants
from utils.version_checker import VersionChecker
from config import config

configure_root_logging()
logger = setup_logger(__name__)


class Event(BaseModel):
    """Pydantic model for incoming events."""

    data: Dict[str, Any] = Field(..., description="Event payload from Claude Code")
    instance_id: Optional[str] = Field(
        None,
        description='Instance identifier in format "claude_pid:server_port" (e.g., "12345:12222")',
    )


class SessionInfo(BaseModel):
    """Pydantic model for session info with settings."""

    session_id: str = Field(..., description="Claude session UUID")
    claude_pid: int = Field(..., description="Claude process ID", gt=0)
    server_port: int = Field(..., description="Server port number", ge=12222, le=12271)
    tts_language: Optional[str] = Field(None, description="TTS language code")
    tts_providers: Optional[str] = Field(
        None, description="Comma-separated TTS provider chain"
    )
    tts_cache_enabled: bool = Field(True, description="Enable TTS caching")
    elevenlabs_voice_id: Optional[str] = Field(None, description="ElevenLabs voice ID")
    elevenlabs_model_id: Optional[str] = Field(None, description="ElevenLabs model ID")
    silent_announcements: bool = Field(False, description="Disable TTS announcements")
    silent_effects: bool = Field(False, description="Disable sound effects")
    openrouter_enabled: bool = Field(False, description="Enable OpenRouter features")
    openrouter_model: Optional[str] = Field(None, description="OpenRouter model name")
    openrouter_contextual_stop: bool = Field(
        False, description="Enable contextual Stop messages"
    )
    openrouter_contextual_pretooluse: bool = Field(
        False, description="Enable contextual PreToolUse messages"
    )


class EventResponse(BaseModel):
    """Response for event submission."""

    status: str = Field(..., description="Status of the request")
    message: str = Field(..., description="Human-readable message")
    event_id: int = Field(..., description="Database ID of queued event")


class SessionResponse(BaseModel):
    """Response for session operations."""

    status: str = Field(..., description="Status of the request")
    message: str = Field(..., description="Human-readable message")
    session_id: str = Field(..., description="Session UUID")
    claude_pid: Optional[int] = Field(None, description="Claude process ID")


class SessionCountResponse(BaseModel):
    """Response for session count query."""

    count: int = Field(..., description="Number of active sessions")
    server_port: Optional[int] = Field(
        None, description="Server port filter (if specified)"
    )


class HealthResponse(BaseModel):
    """Response for health check."""

    status: str = Field(..., description="Health status")


class VersionResponse(BaseModel):
    """Response for version check."""

    current_version: str = Field(..., description="Current installed version")
    latest_version: str = Field(..., description="Latest available version")
    commits_behind: int = Field(..., description="Number of commits behind latest")
    update_available: bool = Field(..., description="Whether update is available")
    last_checked: str = Field(..., description="ISO timestamp of last check")
    error: Optional[str] = Field(None, description="Error message if check failed")


class EventQueryItem(BaseModel):
    """Single event item returned by GET /events."""

    id: int = Field(..., description="Event database ID")
    session_id: str = Field(..., description="Claude session UUID")
    hook_event_name: str = Field(..., description="Hook event type")
    status: str = Field(
        ..., description="Event status (pending/processing/completed/failed)"
    )
    created_at: Optional[str] = Field(
        None, description="ISO timestamp when event was created"
    )
    processed_at: Optional[str] = Field(
        None, description="ISO timestamp when event was processed"
    )
    error_message: Optional[str] = Field(
        None, description="Error message if event failed"
    )


class InstanceStatusResponse(BaseModel):
    """Response for instance status query."""

    instance_id: str = Field(..., description="Instance identifier")
    last_event_status: Optional[str] = Field(
        None, description="Status of last event or None"
    )
    has_pending: bool = Field(
        False, description="True if last event is pending/processing"
    )


def create_app(lifespan=None) -> FastAPI:
    """Create FastAPI application with configured endpoints."""
    app = FastAPI(lifespan=lifespan)

    # Initialize version checker instance
    version_checker = VersionChecker(db_path=config.db_path)

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        """Health check endpoint."""
        return HealthResponse(status="ok")

    @app.post("/events", response_model=EventResponse)
    async def create_event(event: Event) -> EventResponse:
        """Queue an event for async processing. Returns immediately."""
        try:
            session_id = event.data.get("session_id")
            hook_event_name = event.data.get("hook_event_name")

            if not session_id or not hook_event_name:
                raise HTTPException(
                    status_code=HTTPStatusConstants.BAD_REQUEST,
                    detail="Both session_id and hook_event_name are required",
                )

            if not is_valid_hook_event(hook_event_name):
                logger.warning(
                    f"Unknown hook event: {hook_event_name} (session: {session_id})"
                )

            event_id = await queue_event(
                session_id,
                hook_event_name,
                event.data,
                event.instance_id,
            )

            return EventResponse(
                status="ok",
                message="Event queued for processing",
                event_id=event_id,
            )

        except Exception as e:
            logger.error(f"Error queuing event: {e}", exc_info=True)
            raise HTTPException(
                status_code=HTTPStatusConstants.INTERNAL_SERVER_ERROR,
                detail="Failed to queue event",
            )

    @app.get("/events", response_model=List[EventQueryItem])
    async def get_events(
        hook_event_name: Optional[str] = None,
        session_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 10,
    ) -> List[EventQueryItem]:
        """Query events with optional filters."""
        try:
            limit = min(limit, 100)
            return await query_events(
                hook_event_name=hook_event_name,
                session_id=session_id,
                status=status,
                limit=limit,
            )
        except Exception as e:
            logger.error(f"Error querying events: {e}", exc_info=True)
            raise HTTPException(
                status_code=HTTPStatusConstants.INTERNAL_SERVER_ERROR,
                detail="Failed to query events",
            )

    @app.get("/migrations/status")
    async def get_migrations_status():
        """Get current database migration status."""
        try:
            return await get_migration_status()
        except Exception as e:
            logger.error(f"Error getting migration status: {e}", exc_info=True)
            raise HTTPException(
                status_code=HTTPStatusConstants.INTERNAL_SERVER_ERROR,
                detail="Failed to get migration status",
            )

    @app.get("/version/status")
    async def get_version_status(force: bool = False):
        """Get version status and check for updates."""
        try:
            result = await version_checker.check_for_updates(force=force)

            if not result:
                raise HTTPException(
                    status_code=HTTPStatusConstants.INTERNAL_SERVER_ERROR,
                    detail="Version check failed",
                )

            return result.to_dict()

        except Exception as e:
            logger.error(f"Error checking version status: {e}", exc_info=True)
            raise HTTPException(
                status_code=HTTPStatusConstants.INTERNAL_SERVER_ERROR,
                detail="Failed to check version status",
            )

    @app.post("/sessions")
    async def register_session(
        session: SessionInfo, cleanup: bool = False, cleanup_pid: int | None = None
    ):
        """Register session with settings. Optionally cleans up orphaned entries."""
        try:
            import uuid

            try:
                uuid.UUID(session.session_id)
            except ValueError:
                raise HTTPException(
                    status_code=HTTPStatusConstants.BAD_REQUEST,
                    detail=f"Invalid session_id format: {session.session_id} (must be UUID)",
                )

            if session.claude_pid <= 0:
                raise HTTPException(
                    status_code=HTTPStatusConstants.BAD_REQUEST,
                    detail=f"Invalid claude_pid: {session.claude_pid} (must be positive)",
                )

            if not (
                NetworkConstants.PORT_RANGE_MIN
                <= session.server_port
                <= NetworkConstants.PORT_RANGE_MAX
            ):
                raise HTTPException(
                    status_code=HTTPStatusConstants.BAD_REQUEST,
                    detail=f"Invalid server_port: {session.server_port} "
                    f"(must be {NetworkConstants.PORT_RANGE_MIN}-{NetworkConstants.PORT_RANGE_MAX})",
                )

            if cleanup:
                try:
                    cleaned_count = await cleanup_orphaned_sessions()
                    logger.info(f"Cleaned up {cleaned_count} orphaned session(s)")
                except Exception as e:
                    logger.warning(f"Cleanup failed (non-fatal): {e}")

            if cleanup_pid:
                try:
                    from app.event_db import delete_session_by_pid

                    deleted = await delete_session_by_pid(cleanup_pid)
                    if deleted:
                        logger.info(f"Cleaned up sessions for claude_pid {cleanup_pid}")
                except Exception as e:
                    logger.warning(f"PID cleanup failed (non-fatal): {e}")

            success = await store_session(
                session_id=session.session_id,
                claude_pid=session.claude_pid,
                server_port=session.server_port,
                tts_language=session.tts_language,
                tts_providers=session.tts_providers,
                tts_cache_enabled=session.tts_cache_enabled,
                elevenlabs_voice_id=session.elevenlabs_voice_id,
                elevenlabs_model_id=session.elevenlabs_model_id,
                silent_announcements=session.silent_announcements,
                silent_effects=session.silent_effects,
                openrouter_enabled=session.openrouter_enabled,
                openrouter_model=session.openrouter_model,
                openrouter_contextual_stop=session.openrouter_contextual_stop,
                openrouter_contextual_pretooluse=session.openrouter_contextual_pretooluse,
            )

            if not success:
                raise HTTPException(
                    status_code=HTTPStatusConstants.INTERNAL_SERVER_ERROR,
                    detail="Failed to store session",
                )

            return {
                "status": "ok",
                "message": "Session registered",
                "session_id": session.session_id,
                "claude_pid": session.claude_pid,
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                f"Error registering session {session.session_id}: {e}", exc_info=True
            )
            raise HTTPException(
                status_code=HTTPStatusConstants.INTERNAL_SERVER_ERROR,
                detail="Failed to register session",
            )

    @app.get("/sessions/count", response_model=SessionCountResponse)
    async def get_session_count(
        server_port: Optional[int] = None,
    ) -> SessionCountResponse:
        """Get count of active sessions. Must be defined before /sessions/{session_id}."""
        try:
            count = await get_active_session_count(server_port)
            return SessionCountResponse(count=count, server_port=server_port)
        except Exception as e:
            logger.error(f"Error getting session count: {e}", exc_info=True)
            raise HTTPException(
                status_code=HTTPStatusConstants.INTERNAL_SERVER_ERROR,
                detail="Failed to get session count",
            )

    @app.get("/sessions/{session_id}")
    async def get_session(session_id: str):
        """Get session by session_id. Returns 404 if not found."""
        try:
            session = await get_session_by_id(session_id)
            if not session:
                raise HTTPException(
                    status_code=HTTPStatusConstants.NOT_FOUND,
                    detail=f"Session {session_id} not found",
                )

            return session

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting session {session_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=HTTPStatusConstants.INTERNAL_SERVER_ERROR,
                detail="Failed to get session",
            )

    @app.delete("/sessions/{session_id}")
    async def remove_session(session_id: str):
        """Delete session from database."""
        try:
            success = await delete_session(session_id)
            if not success:
                raise HTTPException(
                    status_code=HTTPStatusConstants.INTERNAL_SERVER_ERROR,
                    detail="Failed to delete session",
                )

            return {
                "status": "ok",
                "message": "Session deleted",
                "session_id": session_id,
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting session {session_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=HTTPStatusConstants.INTERNAL_SERVER_ERROR,
                detail="Failed to delete session",
            )

    @app.get(
        "/instances/{instance_id}/last-event", response_model=InstanceStatusResponse
    )
    async def get_instance_last_event_status(
        instance_id: str,
    ) -> InstanceStatusResponse:
        """Get status of last event for a specific instance."""
        try:
            status = await get_last_event_status_for_instance(instance_id)
            has_pending = (
                status in (EventStatus.PENDING.value, EventStatus.PROCESSING.value)
                if status
                else False
            )

            return InstanceStatusResponse(
                instance_id=instance_id,
                last_event_status=status,
                has_pending=has_pending,
            )
        except Exception as e:
            logger.error(
                f"Error getting last event status for instance {instance_id}: {e}"
            )
            raise HTTPException(
                status_code=HTTPStatusConstants.INTERNAL_SERVER_ERROR,
                detail="Failed to get last event status for instance",
            )

    @app.get("/instances/{claude_pid}/settings")
    async def get_instance_settings(claude_pid: int):
        """Get session settings by claude_pid. Returns 404 if not found."""
        try:
            session = await get_session_by_pid(claude_pid)
            if not session:
                raise HTTPException(
                    status_code=HTTPStatusConstants.NOT_FOUND,
                    detail=f"Session not found for claude_pid {claude_pid}",
                )

            return session

        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                f"Error getting session for PID {claude_pid}: {e}", exc_info=True
            )
            raise HTTPException(
                status_code=HTTPStatusConstants.INTERNAL_SERVER_ERROR,
                detail="Failed to get session",
            )

    @app.post("/shutdown")
    async def shutdown_server():
        """Shutdown the server gracefully via SIGTERM."""
        logger.info("Shutdown requested via API endpoint")
        try:
            os.kill(os.getpid(), signal.SIGTERM)

            return {"status": "ok", "message": "Server shutdown initiated"}
        except Exception as e:
            logger.error(f"Error during shutdown: {e}", exc_info=True)
            raise HTTPException(
                status_code=HTTPStatusConstants.INTERNAL_SERVER_ERROR,
                detail="Failed to shutdown server",
            )

    return app
