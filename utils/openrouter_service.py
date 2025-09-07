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

    # System prompt for translation with Claude Code context (static)
    _TRANSLATION_SYSTEM_PROMPT = (
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

    # System prompt for completion message generation (static)
    _COMPLETION_SYSTEM_PROMPT = (
        "You are Claude. You will be given context from your conversation with the user.\n\n"
        "Your response was a long text.\n\n"
        "From your response, you must create a short single sentence that you will speak "
        "to replace your previous response.\n\n"
        "RULES:\n"
        "1. ONLY 1 SHORT SENTENCE (maximum 10-12 words)\n"
        "2. Don't be identical to the original response - change the wording but keep the same meaning\n"
        "3. DO NOT use emojis, symbols, or backticks at all\n"
        "4. Avoid commas after names (e.g., 'Hello Hus' not 'Hello, Hus!') - TTS friendly\n"
        "5. Plain text format only\n"
        "6. Focus on the main point of your response\n"
        "7. If too long for 1 sentence, pick the most important part\n\n"
        "Generate ONLY the spoken text, nothing else."
    )

    # System prompt for PreToolUse message generation (static)
    _PRE_TOOL_SYSTEM_PROMPT = (
        "You are Claude. You will be given context from your conversation with the user "
        "and information about a programming tool you're about to use.\n\n"
        "Create a short single sentence that describes what you're about to do based on "
        "the user's request and your planned response.\n\n"
        "RULES:\n"
        "1. ONLY 1 SHORT SENTENCE (maximum 10-12 words)\n"
        "2. Focus on the USER'S REQUEST and what you're doing to fulfill it\n"
        "3. Make it sound natural, like you're explaining your next action\n"
        "4. Tool name is supplementary context - don't always mention it explicitly\n"
        "5. DO NOT use emojis, symbols, or backticks at all\n"
        "6. Avoid commas after names (e.g., 'Let me check the file' not 'Let me check the file, Hus') - TTS friendly\n"
        "7. Plain text format only\n"
        "8. Be action-oriented and conversational\n\n"
        "Examples of good messages:\n"
        "- 'Installing the dependencies you requested'\n"
        "- 'Checking the configuration file you mentioned'\n"
        "- 'Creating the component you asked for'\n"
        "- 'Running the build process now'\n"
        "- 'Let me examine that error for you'\n\n"
        "Generate ONLY the spoken text, nothing else."
    )

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
        self.api_key = api_key
        self.model = model
        self.enabled = enabled
        self.contextual_stop = contextual_stop
        self.contextual_pretooluse = contextual_pretooluse
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

            # Make API call with system prompt
            messages = [
                {"role": "system", "content": self._TRANSLATION_SYSTEM_PROMPT},
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

    def generate_completion_message(
        self,
        session_id: str,
        user_prompt: Optional[str] = None,
        claude_response: Optional[str] = None,
        target_language: str = "en",
    ) -> Optional[str]:
        """
        Generate a contextual completion message based on conversation context.

        Args:
            session_id (str): Claude Code session ID
            user_prompt (str, optional): Last user prompt from conversation
            claude_response (str, optional): Last Claude response from conversation
            target_language (str): Target language for the message (default: "en")

        Returns:
            str or None: Generated completion message if successful, None if failed
        """
        if not self.contextual_stop:
            logger.debug("Contextual Stop messages are disabled")
            return None

        if not self.is_available():
            logger.debug("OpenRouter not available for completion message generation")
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

            # Make API call with system prompt
            messages = [
                {"role": "system", "content": self._COMPLETION_SYSTEM_PROMPT},
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
                logger.error("Empty response from OpenRouter for completion message")
                return None

            completion_message = response.choices[0].message.content.strip()

            # Remove surrounding quotes that the LLM might add
            if completion_message.startswith('"') and completion_message.endswith('"'):
                completion_message = completion_message[1:-1]
            elif completion_message.startswith("'") and completion_message.endswith(
                "'"
            ):
                completion_message = completion_message[1:-1]

            logger.info(f"Completion message generated: '{completion_message}'")
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
    ) -> Optional[str]:
        """
        Generate a contextual PreToolUse message based on conversation context and tool info.

        Args:
            session_id (str): Claude Code session ID
            tool_name (str): Name of the tool about to be used
            user_prompt (str, optional): Last user prompt from conversation
            claude_response (str, optional): Last Claude response from conversation
            target_language (str): Target language for the message (default: "en")

        Returns:
            str or None: Generated PreToolUse message if successful, None if failed
        """
        if not self.contextual_pretooluse:
            logger.debug("Contextual PreToolUse messages are disabled")
            return None

        if not self.is_available():
            logger.debug("OpenRouter not available for PreToolUse message generation")
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

            # Make API call with system prompt
            messages = [
                {"role": "system", "content": self._PRE_TOOL_SYSTEM_PROMPT},
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
                logger.error("Empty response from OpenRouter for PreToolUse message")
                return None

            pre_tool_message = response.choices[0].message.content.strip()

            # Remove surrounding quotes that the LLM might add
            if pre_tool_message.startswith('"') and pre_tool_message.endswith('"'):
                pre_tool_message = pre_tool_message[1:-1]
            elif pre_tool_message.startswith("'") and pre_tool_message.endswith("'"):
                pre_tool_message = pre_tool_message[1:-1]

            logger.info(f"PreToolUse message generated: '{pre_tool_message}'")
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

        # Format final prompt (without base claude context - now in system prompt)
        return f'{event_data}{task_instruction}"{text}"'

    def _create_completion_message_prompt(
        self,
        user_prompt: Optional[str] = None,
        claude_response: Optional[str] = None,
        target_language: str = "en",
    ) -> str:
        """Create a prompt for generating contextual completion messages."""
        context_lines = []

        if target_language != "en":
            context_lines.append(
                f"Generate the your response in language code '{target_language}' (ISO 639-1/639-2 format)."
            )
            context_lines.append("")

        # Add conversation context
        context_lines.append("Conversation context:")
        if user_prompt:
            # Truncate very long prompts
            prompt_preview = (
                user_prompt[:200] + "..." if len(user_prompt) > 200 else user_prompt
            )
            context_lines.append(f"User said: {prompt_preview}")

        if claude_response:
            # Truncate very long responses
            response_preview = (
                claude_response[:300] + "..."
                if len(claude_response) > 300
                else claude_response
            )
            context_lines.append(f"You said: {response_preview}")

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

        if target_language != "en":
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
            # Truncate very long prompts
            prompt_preview = (
                user_prompt[:200] + "..." if len(user_prompt) > 200 else user_prompt
            )
            context_lines.append(f"User requested: {prompt_preview}")

        if claude_response:
            # Truncate very long responses
            response_preview = (
                claude_response[:300] + "..."
                if len(claude_response) > 300
                else claude_response
            )
            context_lines.append(f"You are about to: {response_preview}")

        if not user_prompt and not claude_response:
            context_lines.append("No specific context available.")

        return "\n".join(context_lines)


# Global instance that will be initialized by config
_openrouter_service: Optional[OpenRouterService] = None


def get_openrouter_service() -> Optional[OpenRouterService]:
    """Get the global OpenRouter service instance."""
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


def generate_completion_message_if_available(
    session_id: str,
    user_prompt: Optional[str] = None,
    claude_response: Optional[str] = None,
    target_language: str = "en",
    fallback_message: str = "Task completed successfully",
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

    Returns:
        str: Generated contextual completion message or fallback message
    """
    service = get_openrouter_service()
    if not service:
        logger.debug("OpenRouter not available, using fallback completion message")
        return fallback_message

    completion_message = service.generate_completion_message(
        session_id=session_id,
        user_prompt=user_prompt,
        claude_response=claude_response,
        target_language=target_language,
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
        logger.debug("OpenRouter not available, using fallback PreToolUse message")
        return fallback_message

    pre_tool_message = service.generate_pre_tool_message(
        session_id=session_id,
        tool_name=tool_name,
        user_prompt=user_prompt,
        claude_response=claude_response,
        target_language=target_language,
    )

    if pre_tool_message:
        return pre_tool_message
    else:
        if fallback_message is None:
            fallback_message = f"Running {short_tool_name} tool"
        logger.debug("Failed to generate PreToolUse message, using fallback")
        return fallback_message
