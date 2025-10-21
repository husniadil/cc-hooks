"""
Generic OpenRouter service for Claude Code hooks system.

This service provides a unified interface to OpenRouter's LLM API,
supporting translation and other text generation tasks for future extensibility.
"""

from typing import Optional, Dict, Any
from utils.colored_logger import setup_logger, configure_root_logging
from utils.openrouter_prompts import (
    TRANSLATION_SYSTEM_PROMPT,
    COMPLETION_SYSTEM_PROMPT,
    PRE_TOOL_SYSTEM_PROMPT,
)

configure_root_logging()
logger = setup_logger(__name__)

try:
    from openai import OpenAI

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

    # Define a dummy OpenAI class for type hints when not available
    class OpenAI:
        pass

    logger.warning("OpenAI SDK not available. Install with: uv add openai")


class OpenRouterService:
    """Generic service for interacting with OpenRouter API."""

    def __init__(
        self,
        api_key: str,
        model: str = "openai/gpt-4o-mini",
        enabled: bool = True,
        contextual_stop: bool = False,
        contextual_pretooluse: bool = False,
    ):
        """
        Initialize OpenRouter service.

        Args:
            api_key (str): OpenRouter API key
            model (str): Default model to use
            enabled (bool): Whether the service is enabled
            contextual_stop (bool): Whether contextual Stop messages are enabled
            contextual_pretooluse (bool): Whether contextual PreToolUse messages are enabled
        """
        # Strip and validate API key (empty or whitespace-only strings become empty)
        self.api_key = api_key.strip() if api_key else ""
        self.model = model
        self.enabled = enabled
        self.contextual_stop = contextual_stop
        self.contextual_pretooluse = contextual_pretooluse
        self._client = None
        self._is_available = None

    @property
    def client(self) -> Optional[OpenAI]:
        """Lazy-load OpenAI client configured for OpenRouter."""
        # Initialize client if we have valid API key and SDK, regardless of enabled flag
        # (to support session-specific usage even when globally disabled)
        if (
            not self._client
            and self._is_valid_api_key(self.api_key)
            and OPENAI_AVAILABLE
        ):
            try:
                self._client = OpenAI(
                    api_key=self.api_key,
                    base_url="https://openrouter.ai/api/v1",
                )
                logger.debug(f"Client initialized with model: {self.model}")
            except Exception as e:
                logger.error(f"Failed to initialize client: {e}")
                self._client = None
        return self._client

    def _is_valid_api_key(self, api_key: str) -> bool:
        """Check if API key is valid (non-empty, not placeholder, reasonable length)"""
        if not api_key or not api_key.strip():
            return False
        # Check for common placeholder values
        placeholders = ["your_key_here", "your_api_key", "null", "none", "undefined"]
        if api_key.lower() in placeholders:
            return False
        # OpenRouter keys should be at least 20 characters (reasonable minimum)
        if len(api_key) < 20:
            return False
        return True

    def is_available(self, for_translation: bool = False) -> bool:
        """
        Check if OpenRouter service is available and properly configured.

        Args:
            for_translation (bool): If True, only checks API key availability (ignores enabled flag)
                                   This allows translation to work even when enabled=False globally
        """
        if self._is_available is not None and not for_translation:
            return self._is_available

        # For translation, only require API key (ignore enabled flag)
        if for_translation:
            is_ready = self._is_valid_api_key(self.api_key) and OPENAI_AVAILABLE
            if not is_ready:
                if not self._is_valid_api_key(self.api_key):
                    logger.debug(
                        "API key not valid for translation (empty, placeholder, or too short)"
                    )
                elif not OPENAI_AVAILABLE:
                    logger.debug("OpenAI SDK not available for translation")
            return is_ready

        # For other features (contextual messages), check enabled flag
        self._is_available = (
            self.enabled and self._is_valid_api_key(self.api_key) and OPENAI_AVAILABLE
        )

        if not self._is_available:
            if not self.enabled:
                logger.debug("Service is disabled")
            elif not self._is_valid_api_key(self.api_key):
                logger.warning("API key not valid (empty, placeholder, or too short)")
            elif not OPENAI_AVAILABLE:
                logger.warning("OpenAI SDK not available")

        return self._is_available

    def translate_text(
        self,
        text: str,
        target_language: str,
        source_language: str = "en",
        hook_event_name: Optional[str] = None,
        event_data: Optional[dict] = None,
    ) -> Optional[str]:
        """
        Translate text from source language to target language with Claude Code context.

        Args:
            text (str): Text to translate
            target_language (str): Target language code (e.g., "id", "es", "fr")
            source_language (str): Source language code (default: "en")
            hook_event_name (str, optional): Claude Code hook event name for context
            event_data (dict, optional): Event data for additional context

        Returns:
            str or None: Translated text if successful, None if failed
        """
        if not self.is_available(for_translation=True):
            logger.debug("Service not available for translation")
            return None

        if not text or not text.strip():
            logger.warning("Empty text provided for translation")
            return None

        # Allow English-to-English processing for context enhancement
        if source_language == target_language and not (hook_event_name or event_data):
            logger.debug(
                f"Source and target languages are the same ({target_language}) with no context, returning original text"
            )
            return text

        try:
            # Create context-aware translation prompt
            prompt = self._create_context_aware_translation_prompt(
                text, source_language, target_language, hook_event_name, event_data
            )

            logger.info(
                f"Translating from {source_language} to {target_language}: '{text}'"
                + (f" (event: {hook_event_name})" if hook_event_name else "")
            )

            # Make API call with system prompt
            messages = [
                {"role": "system", "content": TRANSLATION_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=150,  # Allow more tokens for context-aware translations
                temperature=0.3,  # Slightly creative but consistent
                extra_headers={
                    "HTTP-Referer": "https://github.com/husniadil/cc-hooks",
                    "X-Title": "Claude Code Hooks",
                },
            )

            if not response.choices or not response.choices[0].message.content:
                logger.error("Empty response from API")
                return None

            translated_text = response.choices[0].message.content.strip()

            # Remove surrounding quotes that the LLM might add
            if translated_text.startswith('"') and translated_text.endswith('"'):
                translated_text = translated_text[1:-1]
            elif translated_text.startswith("'") and translated_text.endswith("'"):
                translated_text = translated_text[1:-1]

            logger.info(f"Translation successful: '{text}' → '{translated_text}'")
            return translated_text

        except Exception as e:
            logger.error(f"Translation failed: {e}")
            return None

    def generate_completion_message(
        self,
        session_id: str,
        user_prompt: Optional[str] = None,
        claude_response: Optional[str] = None,
        target_language: str = "en",
        override_contextual_stop: Optional[bool] = None,
    ) -> Optional[str]:
        """
        Generate a contextual completion message based on conversation context.

        Args:
            session_id (str): Claude Code session ID
            user_prompt (str, optional): Last user prompt from conversation
            claude_response (str, optional): Last Claude response from conversation
            target_language (str): Target language for the message (default: "en")
            override_contextual_stop (bool, optional): Override contextual_stop setting (for session-specific config)

        Returns:
            str or None: Generated completion message if successful, None if failed
        """
        # Use override if provided, otherwise use instance setting
        contextual_stop_enabled = (
            override_contextual_stop
            if override_contextual_stop is not None
            else self.contextual_stop
        )

        if not contextual_stop_enabled:
            logger.debug("Contextual completion messages are disabled")
            return None

        # When using session-specific override, skip the global enabled check
        # Only check API key availability
        if override_contextual_stop is not None:
            # Session-specific mode: only check API key and SDK availability
            if not (bool(self.api_key) and OPENAI_AVAILABLE):
                logger.debug("Service not available (missing API key or SDK)")
                return None
        else:
            # Global mode: check full availability including enabled flag
            if not self.is_available():
                logger.debug("Service not available for completion message generation")
                return None

        if not user_prompt and not claude_response:
            logger.debug("No conversation context available for completion message")
            return None

        try:
            # Create context-aware completion message prompt
            prompt = self._create_completion_message_prompt(
                user_prompt, claude_response, target_language
            )

            logger.info(
                f"Generating completion message for session {session_id} in {target_language}"
            )
            # Debug logging for input context
            logger.debug(f"User Prompt: {user_prompt}")
            logger.debug(f"Claude Response: {claude_response}")

            # Make API call with system prompt
            messages = [
                {"role": "system", "content": COMPLETION_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=50,  # Short completion messages
                temperature=0.3,  # Consistent but natural
                extra_headers={
                    "HTTP-Referer": "https://github.com/husniadil/cc-hooks",
                    "X-Title": "Claude Code Hooks",
                },
            )

            if not response.choices or not response.choices[0].message.content:
                logger.error("Empty response from API for completion message")
                return None

            completion_message = response.choices[0].message.content.strip()

            # Remove surrounding quotes that the LLM might add
            if completion_message.startswith('"') and completion_message.endswith('"'):
                completion_message = completion_message[1:-1]
            elif completion_message.startswith("'") and completion_message.endswith(
                "'"
            ):
                completion_message = completion_message[1:-1]

            logger.info(f"Generated completion message: '{completion_message}'")
            return completion_message

        except Exception as e:
            logger.error(f"Completion message generation failed: {e}")
            return None

    def generate_pre_tool_message(
        self,
        session_id: str,
        tool_name: str,
        user_prompt: Optional[str] = None,
        claude_response: Optional[str] = None,
        target_language: str = "en",
        override_contextual_pretooluse: Optional[bool] = None,
    ) -> Optional[str]:
        """
        Generate a contextual PreToolUse message based on conversation context and tool info.

        Args:
            session_id (str): Claude Code session ID
            tool_name (str): Name of the tool about to be used
            user_prompt (str, optional): Last user prompt from conversation
            claude_response (str, optional): Last Claude response from conversation
            target_language (str): Target language for the message (default: "en")
            override_contextual_pretooluse (bool, optional): Override contextual_pretooluse setting (for session-specific config)

        Returns:
            str or None: Generated PreToolUse message if successful, None if failed
        """
        # Use override if provided, otherwise use instance setting
        contextual_pretooluse_enabled = (
            override_contextual_pretooluse
            if override_contextual_pretooluse is not None
            else self.contextual_pretooluse
        )

        if not contextual_pretooluse_enabled:
            logger.debug("Contextual PreToolUse messages are disabled")
            return None

        # When using session-specific override, skip the global enabled check
        # Only check API key availability
        if override_contextual_pretooluse is not None:
            # Session-specific mode: only check API key and SDK availability
            if not (bool(self.api_key) and OPENAI_AVAILABLE):
                logger.debug("Service not available (missing API key or SDK)")
                return None
        else:
            # Global mode: check full availability including enabled flag
            if not self.is_available():
                logger.debug("Service not available for PreToolUse message generation")
                return None

        if not user_prompt and not claude_response:
            logger.debug("No conversation context available for PreToolUse message")
            return None

        try:
            # Create context-aware PreToolUse message prompt
            prompt = self._create_pre_tool_message_prompt(
                tool_name, user_prompt, claude_response, target_language
            )

            logger.info(
                f"Generating PreToolUse message for session {session_id} using {tool_name} in {target_language}"
            )
            # Debug logging for input context
            logger.debug(f"Tool Name: {tool_name}")
            logger.debug(f"User Prompt: {user_prompt}")
            logger.debug(f"Claude Response: {claude_response}")

            # Make API call with system prompt
            messages = [
                {"role": "system", "content": PRE_TOOL_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=50,  # Short action messages
                temperature=0.3,  # Consistent but natural
                extra_headers={
                    "HTTP-Referer": "https://github.com/husniadil/cc-hooks",
                    "X-Title": "Claude Code Hooks",
                },
            )

            if not response.choices or not response.choices[0].message.content:
                logger.error("Empty response from API for PreToolUse message")
                return None

            pre_tool_message = response.choices[0].message.content.strip()

            # Remove surrounding quotes that the LLM might add
            if pre_tool_message.startswith('"') and pre_tool_message.endswith('"'):
                pre_tool_message = pre_tool_message[1:-1]
            elif pre_tool_message.startswith("'") and pre_tool_message.endswith("'"):
                pre_tool_message = pre_tool_message[1:-1]

            logger.info(f"Generated PreToolUse message: '{pre_tool_message}'")
            return pre_tool_message

        except Exception as e:
            logger.error(f"PreToolUse message generation failed: {e}")
            return None

    def _build_translation_instruction(
        self, source_lang: str, target_lang: str, is_enhancement: bool = False
    ) -> str:
        """Build task-specific translation instruction."""
        if source_lang == target_lang == "en" or is_enhancement:
            # English-to-English context enhancement
            return (
                "Improve this English text to be more contextually appropriate for Claude Code users. "
                "Make it more specific and user-friendly while maintaining the technical accuracy. "
                "Return only the improved text, no explanations:\n\n"
            )
        else:
            # Regular translation with context enhancement
            return (
                f"Translate this text from language code '{source_lang}' to language code '{target_lang}'. "
                f"Language codes follow standard ISO 639-1/639-2 format (e.g., 'en' for English, 'id' for Indonesian). "
                f"Use the event context information above to make the translation more specific and accurate. "
                f"If specific tool names or details are mentioned in the context, incorporate them into your translation. "
                f"Maintain the technical context and user-friendly tone. Return only the translation, no explanations:\n\n"
            )

    def _create_context_aware_translation_prompt(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        hook_event_name: Optional[str] = None,
        event_data: Optional[dict] = None,
    ) -> str:
        """Create a context-aware translation prompt for Claude Code events."""
        # Build translation instruction
        is_enhancement = source_lang == target_lang == "en"
        task_instruction = self._build_translation_instruction(
            source_lang, target_lang, is_enhancement
        )

        # Format final prompt (base claude context is in system prompt)
        return f'{event_data}{task_instruction}"{text}"'

    def _create_completion_message_prompt(
        self,
        user_prompt: Optional[str] = None,
        claude_response: Optional[str] = None,
        target_language: str = "en",
    ) -> str:
        """Create a prompt for generating contextual completion messages."""
        context_lines = []

        context_lines.append(
            f"Generate the your response in language code '{target_language}' (ISO 639-1/639-2 format)."
        )
        context_lines.append("")

        # Add conversation context
        context_lines.append("Conversation context:")
        if user_prompt:
            context_lines.append(f"User said: {user_prompt}")

        if claude_response:
            context_lines.append(f"You said: {claude_response}")

        if not user_prompt and not claude_response:
            context_lines.append("No specific context available.")

        return "\n".join(context_lines)

    def _create_pre_tool_message_prompt(
        self,
        tool_name: str,
        user_prompt: Optional[str] = None,
        claude_response: Optional[str] = None,
        target_language: str = "en",
    ) -> str:
        """Create a prompt for generating contextual PreToolUse messages."""
        context_lines = []

        context_lines.append(
            f"Generate your response in language code '{target_language}' (ISO 639-1/639-2 format)."
        )
        context_lines.append("")

        # Add tool context
        context_lines.append(f"Tool to be used: {tool_name}")
        context_lines.append("")

        # Add conversation context
        context_lines.append("Conversation context:")
        if user_prompt:
            context_lines.append(f"User requested: {user_prompt}")

        if claude_response:
            context_lines.append(f"You are about to: {claude_response}")

        if not user_prompt and not claude_response:
            context_lines.append("No specific context available.")

        return "\n".join(context_lines)


# Global instance that will be initialized by config
_openrouter_service: Optional[OpenRouterService] = None


def get_openrouter_service() -> Optional[OpenRouterService]:
    """Get the global OpenRouter service instance, initializing if needed."""
    global _openrouter_service
    if _openrouter_service is None:
        # Try lazy initialization
        try:
            from config import initialize_openrouter_service_lazy

            initialize_openrouter_service_lazy()
        except ImportError:
            # Config not available, service remains None
            pass
    return _openrouter_service


def initialize_openrouter_service(
    api_key: str,
    model: str,
    enabled: bool,
    contextual_stop: bool = False,
    contextual_pretooluse: bool = False,
) -> None:
    """Initialize the global OpenRouter service instance."""
    global _openrouter_service
    _openrouter_service = OpenRouterService(
        api_key=api_key,
        model=model,
        enabled=enabled,
        contextual_stop=contextual_stop,
        contextual_pretooluse=contextual_pretooluse,
    )
    logger.debug("Service initialized")


def translate_text_if_available(
    text: str,
    target_language: str,
    hook_event_name: Optional[str] = None,
    event_data: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Convenience function to translate text if OpenRouter is available.
    The LLM handles both text enhancement and translation via system prompt rules.
    Falls back to original text if translation fails or service unavailable.

    Args:
        text (str): Base text to translate and enhance
        target_language (str): Target language code
        hook_event_name (str, optional): Claude Code hook event name for context
        event_data (dict, optional): Event data for additional context

    Returns:
        str: Context-enhanced and translated text if successful, original text as fallback
    """
    service = get_openrouter_service()
    if not service:
        return text

    # Let the LLM handle both enhancement and translation via system prompt
    translated = service.translate_text(
        text,
        target_language,
        hook_event_name=hook_event_name,
        event_data=event_data,
    )
    return translated if translated else text


def generate_completion_message_if_available(
    session_id: str,
    user_prompt: Optional[str] = None,
    claude_response: Optional[str] = None,
    target_language: str = "en",
    fallback_message: str = "Task completed successfully",
    override_contextual_stop: Optional[bool] = None,
) -> str:
    """
    Convenience function to generate completion message if OpenRouter is available.
    Falls back to default message if generation fails or service unavailable.

    Args:
        session_id (str): Claude Code session ID
        user_prompt (str, optional): Last user prompt from conversation
        claude_response (str, optional): Last Claude response from conversation
        target_language (str): Target language for the message (default: "en")
        fallback_message (str): Default message if generation fails
        override_contextual_stop (bool, optional): Override contextual_stop setting (for session-specific config)

    Returns:
        str: Generated contextual completion message or fallback message
    """
    service = get_openrouter_service()
    if not service:
        logger.debug("Service not available, using fallback completion message")
        return fallback_message

    completion_message = service.generate_completion_message(
        session_id=session_id,
        user_prompt=user_prompt,
        claude_response=claude_response,
        target_language=target_language,
        override_contextual_stop=override_contextual_stop,
    )

    if completion_message:
        return completion_message
    else:
        logger.debug("Failed to generate completion message, using fallback")
        return fallback_message


def generate_pre_tool_message_if_available(
    session_id: str,
    tool_name: str,
    user_prompt: Optional[str] = None,
    claude_response: Optional[str] = None,
    target_language: str = "en",
    fallback_message: Optional[str] = None,
    override_contextual_pretooluse: Optional[bool] = None,
) -> str:
    """
    Convenience function to generate PreToolUse message if OpenRouter is available.
    Falls back to default message if generation fails or service unavailable.

    Args:
        session_id (str): Claude Code session ID
        tool_name (str): Name of the tool about to be used
        user_prompt (str, optional): Last user prompt from conversation
        claude_response (str, optional): Last Claude response from conversation
        target_language (str): Target language for the message (default: "en")
        fallback_message (str, optional): Default message if generation fails (auto-generated if None)
        override_contextual_pretooluse (bool, optional): Override contextual_pretooluse setting (for session-specific config)

    Returns:
        str: Generated contextual PreToolUse message or fallback message
    """
    # Import the tool name shortening function
    try:
        from utils.tts_announcer import _shorten_tool_name_for_tts

        short_tool_name = _shorten_tool_name_for_tts(tool_name)
    except ImportError:
        short_tool_name = tool_name

    service = get_openrouter_service()
    if not service:
        if fallback_message is None:
            fallback_message = f"Running {short_tool_name} tool"
        logger.debug("Service not available, using fallback PreToolUse message")
        return fallback_message

    pre_tool_message = service.generate_pre_tool_message(
        session_id=session_id,
        tool_name=tool_name,
        user_prompt=user_prompt,
        claude_response=claude_response,
        target_language=target_language,
        override_contextual_pretooluse=override_contextual_pretooluse,
    )

    if pre_tool_message:
        return pre_tool_message
    else:
        if fallback_message is None:
            fallback_message = f"Running {short_tool_name} tool"
        logger.debug("Failed to generate PreToolUse message, using fallback")
        return fallback_message
