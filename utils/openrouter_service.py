#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "openai",
#   "requests",
# ]
# ///
"""
Generic OpenRouter service for Claude Code hooks system.

This service provides a unified interface to OpenRouter's LLM API,
supporting translation and other text generation tasks for future extensibility.
"""

import logging
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)

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

    # Base Claude Code context (static)
    _BASE_CLAUDE_CONTEXT = (
        "You are translating user interface text for Claude Code, an AI-powered coding assistant.\n\n"
        "Claude Code context:\n"
        "- Claude Code is an AI assistant that helps users with programming and development tasks\n"
        "- It uses 'tools' like Bash (running terminal commands), Read (reading files), "
        "Write (creating files), Edit (modifying files), Grep (searching content)\n"
        "- A 'session' is a conversation/interaction between the user and Claude Code\n"
        "- 'Agents' or 'subagents' are specialized sub-tasks that Claude Code creates to handle complex operations\n"
        "- 'Hooks' are automated responses to Claude Code events (like tool usage, session start/end)\n\n"
        "Claude Code Event Types:\n"
        "- SessionStart: when Claude Code begins or resumes a coding session (session = interactive coding conversation)\n"
        "- SessionEnd: when the Claude Code session is ending (conversation concluding)\n"
        "- PreToolUse: before Claude Code executes a programming tool (right before development task)\n"
        "- PostToolUse: after Claude Code completes a programming tool (right after development task)\n"
        "- Notification: from Claude Code requiring user attention (permission requests, waiting status)\n"
        "- Stop: when Claude Code completes its current task (finished processing, ready for next input)\n"
        "- SubagentStop: when a Claude Code sub-task completes (specialized sub-tasks finish)\n"
        "- UserPromptSubmit: when the user sends input to Claude Code (user interaction/input submission)\n"
        "- PreCompact: before Claude Code optimizes conversation history (conversation optimization)\n\n"
        "Text Enhancement Rules:\n"
        "When translating, also enhance the text based on available context:\n"
        "- For 'Running tool' text with PreToolUse events: Include specific tool name if available (e.g., 'Running Bash tool')\n"
        "- For 'Tool completed' text with PostToolUse events: Include tool name and status (e.g., 'Bash tool completed' or 'Read tool failed')\n"
        "- For 'Claude Code ready' text with SessionStart events, consider the session context:\n"
        "  * source='resume': User is continuing a previous coding session\n"
        "  * source='clear': User started fresh after clearing conversation history\n"
        "  * source='compact': User restarted after conversation was optimized for efficiency\n"
        "- For SessionEnd events, consider the session end context:\n"
        "  * reason='clear': User is ending session to start fresh (session termination)\n"
        "  * reason='logout': User is logging out (proper session closure)\n"
        "- Consider additional context fields when available:\n"
        "  * trigger: What triggered the event (user action, system action, etc.)\n"
        "  * action: Specific action being taken (e.g., 'compact', 'save', 'reload')\n"
        "  * type: Event type classification for more specific translation\n"
        "- Always prioritize user-friendly, contextual text over generic messages\n"
        "- Maintain technical accuracy while being specific and informative\n\n"
    )

    def __init__(
        self,
        api_key: str,
        model: str = "openai/gpt-4o-mini",
        enabled: bool = True,
    ):
        """
        Initialize OpenRouter service.

        Args:
            api_key (str): OpenRouter API key
            model (str): Default model to use
            enabled (bool): Whether the service is enabled
        """
        self.api_key = api_key
        self.model = model
        self.enabled = enabled
        self._client = None
        self._is_available = None

    @property
    def client(self) -> Optional[OpenAI]:
        """Lazy-load OpenAI client configured for OpenRouter."""
        if not self._client and self.is_available():
            try:
                self._client = OpenAI(
                    api_key=self.api_key,
                    base_url="https://openrouter.ai/api/v1",
                )
                logger.info(f"OpenRouter client initialized with model: {self.model}")
            except Exception as e:
                logger.error(f"Failed to initialize OpenRouter client: {e}")
                self._client = None
        return self._client

    def is_available(self) -> bool:
        """Check if OpenRouter service is available and properly configured."""
        if self._is_available is not None:
            return self._is_available

        self._is_available = self.enabled and bool(self.api_key) and OPENAI_AVAILABLE

        if not self._is_available:
            if not self.enabled:
                logger.debug("OpenRouter service is disabled")
            elif not self.api_key:
                logger.warning("OpenRouter API key not provided")
            elif not OPENAI_AVAILABLE:
                logger.warning("OpenAI SDK not available for OpenRouter")

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
        if not self.is_available():
            logger.debug("OpenRouter not available for translation")
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
                f"Translating text from {source_language} to {target_language}: '{text}'"
                + (f" (event: {hook_event_name})" if hook_event_name else "")
            )

            # Make API call
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,  # Allow more tokens for context-aware translations
                temperature=0.3,  # Slightly creative but consistent
                extra_headers={
                    "HTTP-Referer": "https://github.com/husniadil/cc-hooks",
                    "X-Title": "Claude Code Hooks",
                },
            )

            if not response.choices or not response.choices[0].message.content:
                logger.error("Empty response from OpenRouter")
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

    def generate_text(self, prompt: str, **kwargs) -> Optional[str]:
        """
        Generate text using OpenRouter (for future extensibility).

        Args:
            prompt (str): Input prompt
            **kwargs: Additional parameters for the API call

        Returns:
            str or None: Generated text if successful, None if failed
        """
        if not self.is_available():
            logger.debug("OpenRouter not available for text generation")
            return None

        try:
            # Set default parameters
            params = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": kwargs.get("max_tokens", 150),
                "temperature": kwargs.get("temperature", 0.7),
                "extra_headers": {
                    "HTTP-Referer": "https://github.com/husniadil/cc-hooks",
                    "X-Title": "Claude Code Hooks",
                },
            }

            # Override with any additional kwargs
            params.update(kwargs)

            logger.info(f"Generating text with model: {self.model}")
            response = self.client.chat.completions.create(**params)

            if not response.choices or not response.choices[0].message.content:
                logger.error("Empty response from OpenRouter")
                return None

            generated_text = response.choices[0].message.content.strip()

            # Remove surrounding quotes that the LLM might add
            if generated_text.startswith('"') and generated_text.endswith('"'):
                generated_text = generated_text[1:-1]
            elif generated_text.startswith("'") and generated_text.endswith("'"):
                generated_text = generated_text[1:-1]

            logger.info("Text generation successful")
            return generated_text

        except Exception as e:
            logger.error(f"Text generation failed: {e}")
            return None

    def _get_base_claude_context(self) -> str:
        """Get the base Claude Code context for translation prompts."""
        return self._BASE_CLAUDE_CONTEXT

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

    def _format_prompt_template(
        self, context: str, event_context: str, instruction: str, text: str
    ) -> str:
        """Format the final translation prompt template."""
        return f'{context}{event_context}{instruction}"{text}"'

    def _create_context_aware_translation_prompt(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        hook_event_name: Optional[str] = None,
        event_data: Optional[dict] = None,
    ) -> str:
        """Create a context-aware translation prompt for Claude Code events."""
        # Get base context
        claude_context = self._get_base_claude_context()

        # Get event-specific context if available
        event_context = ""
        if hook_event_name and event_data:
            event_context = self._get_event_context(hook_event_name, event_data)

        # Build translation instruction
        is_enhancement = source_lang == target_lang == "en"
        task_instruction = self._build_translation_instruction(
            source_lang, target_lang, is_enhancement
        )

        # Format final prompt
        return self._format_prompt_template(
            claude_context, event_context, task_instruction, text
        )

    def _get_event_context(self, hook_event_name: str, event_data: dict) -> str:
        """Get simplified event context for translation prompt."""
        if not hook_event_name:
            return ""

        context_lines = [f"Current event: {hook_event_name}"]

        # Add specific event data if available
        if event_data:
            # Tool information
            if "tool_name" in event_data:
                context_lines.append(f"Tool: {event_data['tool_name']}")

            # Common context fields from Claude Code hook data (matches mappings.py source_fields)
            if "source" in event_data:
                context_lines.append(f"Source: {event_data['source']}")
            if "reason" in event_data:
                context_lines.append(f"Reason: {event_data['reason']}")
            if "trigger" in event_data:
                context_lines.append(f"Trigger: {event_data['trigger']}")
            if "action" in event_data:
                context_lines.append(f"Action: {event_data['action']}")
            if "type" in event_data:
                context_lines.append(f"Type: {event_data['type']}")

            # Error and notification information
            if "error" in event_data:
                context_lines.append(f"Error: {event_data['error']}")
            if "message" in event_data:
                context_lines.append(f"Message: {event_data['message']}")

        return "\n".join(context_lines) + "\n\n" if context_lines else ""


# Global instance that will be initialized by config
_openrouter_service: Optional[OpenRouterService] = None


def get_openrouter_service() -> Optional[OpenRouterService]:
    """Get the global OpenRouter service instance."""
    return _openrouter_service


def initialize_openrouter_service(api_key: str, model: str, enabled: bool) -> None:
    """Initialize the global OpenRouter service instance."""
    global _openrouter_service
    _openrouter_service = OpenRouterService(
        api_key=api_key, model=model, enabled=enabled
    )
    logger.info("OpenRouter service initialized")


def translate_text_if_available(
    text: str,
    target_language: str,
    hook_event_name: Optional[str] = None,
    event_data: Optional[dict] = None,
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
