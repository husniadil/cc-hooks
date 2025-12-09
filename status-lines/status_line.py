#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "requests>=2.32.5,<3",
#     "elevenlabs>=2.16.0,<3",
#     "openai>=2.1.0,<3",
#     "python-dotenv>=1.1.1,<2",
#     "psutil>=6.1.1,<7",
# ]
# ///
"""
Claude Code statusline
Theme: detailed | Colors: true | Features: directory, git, model, output_style, usage, session
Cross-platform compatible (macOS/Linux/WSL)
"""

import sys
import json
import os
import subprocess
import shutil
from pathlib import Path
from datetime import datetime
import re

# Add imports for constants (at the beginning after standard imports)
try:
    from utils.constants import NetworkConstants, get_server_url
except ImportError:
    # Fallback for when running as standalone script
    class NetworkConstants:
        DEFAULT_PORT = 12222
        LOCALHOST = "localhost"

    def get_server_url(
        port: int = NetworkConstants.DEFAULT_PORT, endpoint: str = ""
    ) -> str:
        return f"http://{NetworkConstants.LOCALHOST}:{port}{endpoint}"


# Add parent directory to path for config import
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

try:
    from config import config
except ImportError:
    # Fallback if config module still can't be imported
    print("Warning: Could not import config module", file=sys.stderr)
    config = None


class StatusLine:
    def __init__(self, debug=False, no_color=False):
        self.debug = debug
        self.no_color = no_color
        self.use_color = self._should_use_color()
        if self.debug:
            self._debug_log(
                f"StatusLine initialized with debug={debug}, no_color={no_color}, use_color={self.use_color}"
            )

    def _should_use_color(self):
        """Determine if colors should be used (TTY-aware, respect no_color flag)"""
        if self.no_color:
            return False
        return sys.stdout.isatty()

    def _debug_log(self, message):
        """Debug logging helper"""
        if self.debug:
            debug_msg = f"[DEBUG StatusLine] {message}"
            print(debug_msg, file=sys.stderr, flush=True)

    def _color(self, code):
        """Apply ANSI color code if colors enabled"""
        return f"\033[{code}m" if self.use_color else ""

    def _reset(self):
        """Reset ANSI colors"""
        return "\033[0m" if self.use_color else ""

    # Color helpers
    def dir_color(self):
        return self._color("1;36")  # cyan

    def model_color(self):
        return self._color("1;35")  # magenta

    def version_color(self):
        return self._color("1;33")  # yellow

    def style_color(self):
        return self._color("1;34")  # blue

    def project_color(self):
        return self._color("1;37")  # white

    def git_color(self):
        return self._color("1;32")  # green

    def usage_color(self):
        return self._color("1;35")  # magenta

    def cost_color(self):
        return self._color("1;36")  # cyan

    def tts_color(self):
        return self._color("1;33")  # yellow

    def elevenlabs_color(self):
        return self.tts_color()  # backward compatibility

    def openrouter_color(self):
        return self._color("1;36")  # cyan

    def session_color(self, session_pct):
        """Dynamic session color based on remaining percentage"""
        rem_pct = 100 - session_pct
        if rem_pct <= 10:
            return self._color("1;31")  # red
        elif rem_pct <= 25:
            return self._color("1;33")  # yellow
        else:
            return self._color("1;32")  # green

    def _run_command(self, cmd, shell=False, capture_output=True, text=True):
        """Run shell command safely"""
        try:
            if isinstance(cmd, str) and not shell:
                cmd = cmd.split()
            result = subprocess.run(
                cmd, shell=shell, capture_output=capture_output, text=text, timeout=10
            )
            return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return False, "", ""

    def _to_epoch(self, timestamp_str):
        """Convert ISO timestamp to epoch seconds (cross-platform)"""
        try:
            # Try Python datetime parsing first
            import datetime

            # Handle 'Z' suffix and various formats
            ts = timestamp_str.replace("Z", "+00:00")
            dt = datetime.datetime.fromisoformat(ts)
            return int(dt.timestamp())
        except:
            # Fallback to date commands
            # Try GNU date first
            success, output, _ = self._run_command(
                f'date -d "{timestamp_str}" +%s', shell=True
            )
            if success and output.isdigit():
                return int(output)

            # Try BSD date (macOS)
            bsd_ts = timestamp_str.replace("Z", "+0000")
            success, output, _ = self._run_command(
                f'date -u -j -f "%Y-%m-%dT%H:%M:%S%z" "{bsd_ts}" +%s', shell=True
            )
            if success and output.isdigit():
                return int(output)

            return None

    def _format_time_hm(self, epoch_seconds):
        """Format epoch seconds to HH:MM"""
        try:
            dt = datetime.fromtimestamp(epoch_seconds)
            return dt.strftime("%H:%M")
        except:
            return ""

    def _progress_bar(self, pct, width=10):
        """Generate ASCII progress bar"""
        pct = max(0, min(100, int(pct) if str(pct).isdigit() else 0))
        filled = pct * width // 100
        empty = width - filled
        return "=" * filled + "-" * empty

    def _detect_claude_pid(self):
        """Detect Claude binary PID by walking up the process tree.
        Returns the PID of the Claude process or None if not found.
        """
        try:
            import psutil

            current_process = psutil.Process(os.getpid())

            while current_process:
                cmdline_list = current_process.cmdline()
                cmdline = " ".join(cmdline_list).lower()
                name = current_process.name().lower()

                # Detection strategies for Claude binary:
                # 1. Name-based: process name is exactly "claude"
                # 2. Cmdline-based: cmdline starts with "claude " or equals "claude"
                # 3. Path-based: first cmdline arg ends with "/claude" (for Bun-compiled binary
                #    where process name might be version number like "2.0.59")
                is_claude_binary = (
                    name == "claude"
                    or cmdline.startswith("claude ")
                    or cmdline == "claude"
                    or (len(cmdline_list) > 0 and cmdline_list[0].endswith("/claude"))
                )

                if is_claude_binary:
                    claude_pid = current_process.pid
                    self._debug_log(f"Found Claude PID: {claude_pid}")
                    return claude_pid

                if current_process.parent():
                    current_process = current_process.parent()
                else:
                    break

            self._debug_log("Could not detect Claude PID")
            return None

        except ImportError:
            self._debug_log("psutil package not available")
            return None
        except Exception as e:
            self._debug_log(f"Error detecting Claude PID: {e}")
            return None

    def _find_server_port_for_pid(self, claude_pid):
        """Find server port for a given Claude PID.
        Returns port number or None if not found.
        """
        if not claude_pid:
            return None

        try:
            import requests

            # Query each potential server port to find our instance settings
            # Use shorter timeout and check fewer ports for faster failure
            for port_offset in range(3):  # Reduced from 10 to 3
                test_port = NetworkConstants.DEFAULT_PORT + port_offset
                try:
                    url = get_server_url(test_port, f"/instances/{claude_pid}/settings")
                    response = requests.get(
                        url, timeout=0.1
                    )  # Reduced from 0.5s to 0.1s
                    if response.status_code == 200:
                        settings = response.json()
                        port = settings.get("server_port")
                        self._debug_log(
                            f"Found server port {port} for PID {claude_pid}"
                        )
                        return port
                except:
                    continue

            # No server found - this is normal for status_line processes
            # Don't log as it creates noise
            return None

        except ImportError:
            self._debug_log("requests package not available")
            return None
        except Exception as e:
            self._debug_log(f"Error finding server port: {e}")
            return None

    def _get_git_info(self):
        """Get git branch and status information"""
        git_branch = ""
        git_status = ""

        # Check if we're in a git repo
        success, _, _ = self._run_command(["git", "rev-parse", "--git-dir"])
        if not success:
            return git_branch, git_status

        # Get current branch or short hash
        success, output, _ = self._run_command(["git", "branch", "--show-current"])
        if success and output:
            git_branch = output
        else:
            success, output, _ = self._run_command(
                ["git", "rev-parse", "--short", "HEAD"]
            )
            if success:
                git_branch = output

        # Get git status indicators
        success, _, _ = self._run_command(
            ["git", "diff-index", "--quiet", "HEAD", "--"]
        )
        if success:
            git_status = "✓"  # clean
        else:
            changes = ""

            # Check staged changes
            success, _, _ = self._run_command(["git", "diff", "--cached", "--quiet"])
            if not success:
                changes += "●"  # staged

            # Check unstaged changes
            success, _, _ = self._run_command(["git", "diff", "--quiet"])
            if not success:
                changes += "◐"  # modified

            # Check untracked files
            success, output, _ = self._run_command(
                ["git", "ls-files", "--others", "--exclude-standard"]
            )
            if success and output:
                changes += "?"  # untracked

            git_status = changes

        return git_branch, git_status

    def _get_cc_hooks_health(self):
        """Get cc-hooks server health status"""
        # Detect Claude PID and find its server port
        claude_pid = self._detect_claude_pid()
        port = self._find_server_port_for_pid(claude_pid)

        # Fallback to env var or default port if detection failed
        if not port:
            port = int(os.getenv("CC_HOOKS_PORT", str(NetworkConstants.DEFAULT_PORT)))

        # Check health on detected port
        try:
            import requests

            response = requests.get(get_server_url(port, "/health"), timeout=2)
            if response.status_code == 200:
                return True, "🟢", "online", port
            else:
                return False, "❌", "error", port

        except ImportError:
            self._debug_log("requests package not available")
            return False, "❓", "no-deps", port
        except requests.exceptions.RequestException:
            return False, "🔴", "offline", port
        except Exception as e:
            self._debug_log(f"Unexpected error in health check: {e}")
            return False, "⚠️", "unknown", port

    def _get_cc_hooks_update_status(self):
        """Check if cc-hooks update is available"""
        update_available = False
        update_msg = ""

        # Detect Claude PID and find its server port (reuse same helper functions)
        claude_pid = self._detect_claude_pid()
        port = self._find_server_port_for_pid(claude_pid)

        # Fallback to env var or default port if detection failed
        if not port:
            port = int(os.getenv("CC_HOOKS_PORT", str(NetworkConstants.DEFAULT_PORT)))

        try:
            import requests

            response = requests.get(get_server_url(port, "/version/status"), timeout=2)
            if response.status_code == 200:
                version_data = response.json()
                update_available = version_data.get("update_available", False)
                if update_available:
                    commits_behind = version_data.get("commits_behind", 0)
                    commits_msg = f"{commits_behind} commit" + (
                        "s" if commits_behind > 1 else ""
                    )
                    # Get repo root path and detect installation mode
                    repo_root = Path(__file__).parent.parent.resolve()
                    repo_root_str = str(repo_root)

                    # Check if installed as plugin (path contains .claude/plugins/marketplaces/)
                    if ".claude/plugins/marketplaces/" in repo_root_str:
                        # Plugin mode - use marketplace update command
                        update_msg = f"⚠ cc-hooks: update available ({commits_msg} behind) - run: claude plugin marketplace update cc-hooks-plugin"
                    else:
                        # Standalone mode - use npm update command
                        update_msg = f"⚠ cc-hooks: update available ({commits_msg} behind) - run: cd {repo_root} && npm run update"
        except ImportError:
            self._debug_log("requests package not available for update check")
        except Exception as e:
            self._debug_log(f"Error checking for cc-hooks updates: {e}")

        return update_available, update_msg

    def _get_ccusage_info(self):
        """Get usage information from ccusage command"""
        self._debug_log("_get_ccusage_info() called")
        session_txt = ""
        session_pct = 0
        session_bar = ""
        cost_usd = ""
        cost_per_hour = ""

        # Try local ccusage first (from project node_modules), then global
        project_root = Path(__file__).parent.parent
        local_ccusage = project_root / "node_modules" / ".bin" / "ccusage"

        if local_ccusage.exists():
            ccusage_path = str(local_ccusage)
            self._debug_log(f"Using local ccusage: {ccusage_path}")
        else:
            # Fallback to global ccusage
            ccusage_path = shutil.which("ccusage")
            if not ccusage_path:
                self._debug_log("ccusage command not found locally or in PATH")
                return session_txt, session_pct, session_bar, cost_usd, cost_per_hour
            self._debug_log(f"Using global ccusage: {ccusage_path}")

        # Get blocks output
        success, output, error = self._run_command([ccusage_path, "blocks", "--json"])
        if not success or not output:
            self._debug_log(f"ccusage failed or no output: {error}")
            return session_txt, session_pct, session_bar, cost_usd, cost_per_hour

        self._debug_log(f"ccusage output length: {len(output)}")

        try:
            blocks_data = json.loads(output)
            active_blocks = [
                b for b in blocks_data.get("blocks", []) if b.get("isActive")
            ]

            if not active_blocks:
                return session_txt, session_pct, session_bar, cost_usd, cost_per_hour

            active_block = active_blocks[0]

            # Get cost information
            cost_usd = active_block.get("costUSD", "")
            burn_rate = active_block.get("burnRate") or {}
            cost_per_hour = (
                burn_rate.get("costPerHour", "") if isinstance(burn_rate, dict) else ""
            )

            # Session time calculation
            reset_time_str = active_block.get(
                "usageLimitResetTime"
            ) or active_block.get("endTime")
            start_time_str = active_block.get("startTime")

            if reset_time_str and start_time_str:
                start_sec = self._to_epoch(start_time_str)
                end_sec = self._to_epoch(reset_time_str)
                now_sec = int(datetime.now().timestamp())

                if start_sec and end_sec:
                    total = max(1, end_sec - start_sec)
                    elapsed = max(0, min(total, now_sec - start_sec))
                    session_pct = elapsed * 100 // total

                    remaining = max(0, end_sec - now_sec)
                    rh = remaining // 3600
                    rm = (remaining % 3600) // 60
                    end_hm = self._format_time_hm(end_sec)

                    session_txt = (
                        f"{rh}h {rm}m until reset at {end_hm} ({session_pct}%)"
                    )
                    session_bar = self._progress_bar(session_pct, 10)

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            self._debug_log(f"Error parsing ccusage output: {e}")

        return session_txt, session_pct, session_bar, cost_usd, cost_per_hour

    def _get_session_settings(self):
        """Get session settings from database for current Claude instance"""
        # Detect Claude PID and find its server port
        claude_pid = self._detect_claude_pid()
        if not claude_pid:
            # No Claude PID detected - likely status_line running standalone
            return None

        port = self._find_server_port_for_pid(claude_pid)

        # If no server found for this PID, don't try to fetch settings
        # This avoids unnecessary 404 requests in logs
        if not port:
            return None

        try:
            import requests

            url = get_server_url(port, f"/instances/{claude_pid}/settings")
            response = requests.get(url, timeout=0.5)  # Reduced from 2s to 0.5s
            if response.status_code == 200:
                settings = response.json()
                self._debug_log(f"Fetched session settings from server: {settings}")
                return settings
            else:
                # Server exists but no session for this PID - normal for --resume
                return None

        except ImportError:
            self._debug_log("requests package not available")
            return None
        except Exception as e:
            # Connection failed - server likely not running
            return None

    def _get_tts_info(self):
        """Get TTS provider information from session settings"""
        tts_info = ""
        tts_enabled = False
        voice_name = ""

        try:
            # Get session-specific settings from database
            session_settings = self._get_session_settings()
            if not session_settings:
                self._debug_log("No session settings available, using config defaults")
                # Fallback to config defaults
                if config is None:
                    return tts_info, tts_enabled, voice_name
                tts_providers_str = config.tts_providers
                tts_language = config.tts_language
                silent_announcements = False
            else:
                tts_providers_str = (
                    session_settings.get("tts_providers") or config.tts_providers
                )
                tts_language = (
                    session_settings.get("tts_language") or config.tts_language
                )
                silent_announcements = session_settings.get(
                    "silent_announcements", False
                )

            # If announcements are silenced, show muted indicator
            if silent_announcements:
                self._debug_log("Silent announcements mode - showing muted indicator")
                tts_info = "Muted"
                tts_enabled = True
                voice_name = ""
                return tts_info, tts_enabled, voice_name

            # Parse TTS providers string
            tts_providers_list = (
                [p.strip() for p in tts_providers_str.split(",") if p.strip()]
                if tts_providers_str
                else ["prerecorded"]
            )
            self._debug_log(f"TTS providers list: {tts_providers_list}")

            if not tts_providers_list:
                return tts_info, tts_enabled, voice_name

            # Find the first available provider
            active_provider = None
            for provider in tts_providers_list:
                if provider == "elevenlabs":
                    api_key = config.elevenlabs_api_key if config else None
                    if api_key:
                        active_provider = "elevenlabs"
                        break
                elif provider == "gtts":
                    # GTTS is always available if specified
                    active_provider = "gtts"
                    break
                elif provider == "prerecorded":
                    # Prerecorded is always available if specified
                    active_provider = "prerecorded"
                    break

            if not active_provider:
                self._debug_log("No active TTS provider found")
                return tts_info, tts_enabled, voice_name

            self._debug_log(f"Active TTS provider: {active_provider}")
            tts_enabled = True

            # Get provider-specific information
            if active_provider == "elevenlabs":
                tts_info, voice_name = self._get_elevenlabs_details(session_settings)
            elif active_provider == "gtts":
                tts_info = f"Google TTS ({tts_language.upper()})"
                voice_name = "Google TTS"
            elif active_provider == "prerecorded":
                tts_info = "Prerecorded Audio"
                voice_name = "Prerecorded"

        except Exception as e:
            self._debug_log(f"Error getting TTS info: {e}")
            return tts_info, tts_enabled, voice_name

        return tts_info, tts_enabled, voice_name

    def _get_elevenlabs_details(self, session_settings=None):
        """Get detailed ElevenLabs information"""
        elevenlabs_info = ""
        voice_name = ""

        try:
            api_key = config.elevenlabs_api_key if config else None
            if not api_key:
                return "ElevenLabs: No API key", ""

            from elevenlabs.client import ElevenLabs

            client = ElevenLabs(api_key=api_key)
            subscription = client.user.subscription.get()

            self._debug_log(f"ElevenLabs subscription: {subscription}")

            # Extract subscription info
            char_limit = getattr(subscription, "character_limit", 0)
            char_used = getattr(subscription, "character_count", 0)
            can_do_tts = char_used < char_limit if char_limit > 0 else True

            # Get language for display from session settings or config
            if session_settings:
                language = session_settings.get("tts_language") or (
                    config.tts_language if config else "en"
                )
            else:
                language = config.tts_language if config else "en"
            language_display = f" ({language.upper()})"

            # Fetch voice name from session settings or config
            try:
                if session_settings:
                    voice_id = session_settings.get("elevenlabs_voice_id") or (
                        config.elevenlabs_voice_id if config else None
                    )
                else:
                    voice_id = config.elevenlabs_voice_id if config else None

                if voice_id:
                    voice = client.voices.get(voice_id)
                    base_voice_name = getattr(voice, "name", "ElevenLabs")
                    voice_name = f"{base_voice_name}{language_display}"
                    self._debug_log(
                        f"ElevenLabs voice name with language: {voice_name}"
                    )
                else:
                    voice_name = f"ElevenLabs{language_display}"
            except Exception as e:
                self._debug_log(f"Error fetching voice name: {e}")
                voice_name = f"ElevenLabs{language_display}"

            # Format the usage info
            if char_limit > 0:
                usage_pct = (char_used * 100) // char_limit
                elevenlabs_info = f"{char_used:,}/{char_limit:,} chars ({usage_pct}%)"
                if not can_do_tts:
                    elevenlabs_info += " [LIMIT REACHED]"
            else:
                elevenlabs_info = (
                    f"{char_used:,} chars used" if char_used > 0 else "Connected"
                )

        except ImportError:
            self._debug_log("elevenlabs package not available")
            elevenlabs_info = "Not installed"
            if session_settings:
                language = session_settings.get("tts_language") or (
                    config.tts_language if config else "en"
                )
            else:
                language = config.tts_language if config else "en"
            voice_name = f"ElevenLabs ({language.upper()})"
        except Exception as e:
            self._debug_log(f"Error fetching ElevenLabs details: {e}")
            elevenlabs_info = f"Error: {type(e).__name__}"
            if session_settings:
                language = session_settings.get("tts_language") or (
                    config.tts_language if config else "en"
                )
            else:
                language = config.tts_language if config else "en"
            voice_name = f"ElevenLabs ({language.upper()})"

        return elevenlabs_info, voice_name

    def _get_openrouter_info(self):
        """Get OpenRouter status and model information from session settings"""
        openrouter_info = ""
        openrouter_enabled = False
        openrouter_model = ""

        try:
            # Get session-specific settings from database
            session_settings = self._get_session_settings()
            if not session_settings:
                self._debug_log("No session settings available, using config defaults")
                if config is None:
                    return openrouter_info, openrouter_enabled, openrouter_model
                # Fallback to config defaults
                openrouter_enabled = config.openrouter_enabled
                openrouter_model = config.openrouter_model
                contextual_stop = config.openrouter_contextual_stop
                contextual_pretooluse = config.openrouter_contextual_pretooluse
                silent_announcements = False
            else:
                openrouter_enabled = session_settings.get("openrouter_enabled", False)
                openrouter_model = session_settings.get("openrouter_model") or (
                    config.openrouter_model if config else "openai/gpt-4o-mini"
                )
                contextual_stop = session_settings.get(
                    "openrouter_contextual_stop", False
                )
                contextual_pretooluse = session_settings.get(
                    "openrouter_contextual_pretooluse", False
                )
                silent_announcements = session_settings.get(
                    "silent_announcements", False
                )

            self._debug_log(f"OpenRouter enabled: {openrouter_enabled}")

            # If silent announcements mode is active, show disabled status
            # (OpenRouter calls are skipped to save costs)
            if silent_announcements:
                self._debug_log(
                    "Silent announcements mode - OpenRouter disabled to save costs"
                )
                openrouter_info = "Disabled (silent mode)"
                openrouter_enabled = True  # Show in status line
                return openrouter_info, openrouter_enabled, openrouter_model

            if not openrouter_enabled:
                return openrouter_info, openrouter_enabled, openrouter_model

            # Get API key to verify configuration
            api_key = config.openrouter_api_key if config else None
            if not api_key:
                openrouter_info = "No API key"
                return openrouter_info, openrouter_enabled, openrouter_model

            # Get model name
            model_display = openrouter_model.split("/")[-1]  # Get just the model name

            # Build feature flags display
            features = []
            if contextual_stop:
                features.append("Stop")
            if contextual_pretooluse:
                features.append("PreTool")

            if features:
                openrouter_info = f"{model_display} ({', '.join(features)})"
            else:
                openrouter_info = f"{model_display}"

            # Try to verify connection with a simple API check
            status_emoji = ""
            try:
                import requests

                response = requests.get(
                    "https://openrouter.ai/api/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=2,
                )
                if response.status_code == 200:
                    status_emoji = "🟢"  # online
                else:
                    status_emoji = "❌"  # error
            except ImportError:
                self._debug_log("requests package not available for OpenRouter check")
                status_emoji = "❓"  # no-requests
            except requests.exceptions.RequestException:
                status_emoji = "🔴"  # offline
            except Exception as e:
                self._debug_log(f"Unexpected error in OpenRouter check: {e}")
                status_emoji = "⚠️"  # unknown

            # Format: emoji model (features)
            if status_emoji:
                openrouter_info = f"{status_emoji} {openrouter_info}"

        except Exception as e:
            self._debug_log(f"Error getting OpenRouter info: {e}")
            return openrouter_info, openrouter_enabled, openrouter_model

        return openrouter_info, openrouter_enabled, openrouter_model

    def _get_sound_effects_info(self):
        """Get sound effects status from session settings.

        Returns tuple of (effects_info, effects_muted):
        - effects_info: Display string (empty if not muted, "Effects" if muted)
        - effects_muted: Boolean indicating if effects are muted
        """
        effects_info = ""
        effects_muted = False

        try:
            # Get session-specific settings from database
            session_settings = self._get_session_settings()
            if not session_settings:
                self._debug_log("No session settings available for sound effects check")
                return effects_info, effects_muted

            # Check if sound effects are muted
            effects_muted = session_settings.get("silent_effects", False)

            if effects_muted:
                self._debug_log("Silent effects mode - showing muted indicator")
                effects_info = "Effects"
            else:
                self._debug_log("Sound effects active - no indicator needed")

        except Exception as e:
            self._debug_log(f"Error getting sound effects info: {e}")
            return effects_info, effects_muted

        return effects_info, effects_muted

    def render(self, input_data=None):
        """Render the complete status line"""
        self._debug_log("render() method called")

        if input_data is None:
            input_data = sys.stdin.read()

        # Parse input JSON
        try:
            data = json.loads(input_data) if input_data.strip() else {}
            self._debug_log(f"Parsed JSON data keys: {list(data.keys())}")
        except json.JSONDecodeError as e:
            self._debug_log(f"JSON decode error: {e}")
            data = {}

        # Extract basic information
        workspace = data.get("workspace", {})
        current_dir = workspace.get("current_dir") or workspace.get("cwd", "unknown")
        project_dir = workspace.get("project_dir", "")

        model = data.get("model", {})
        model_name = model.get("display_name", "Claude")
        model_version = model.get("version", "")

        output_style = data.get("output_style", {}).get("name", "")

        # Replace home directory with ~
        home = os.path.expanduser("~")
        if current_dir.startswith(home):
            current_dir = current_dir.replace(home, "~", 1)
        if project_dir.startswith(home):
            project_dir = project_dir.replace(home, "~", 1)

        # Fallback to PWD if current_dir is unknown
        if current_dir == "unknown" and "PWD" in os.environ:
            pwd = os.environ["PWD"]
            current_dir = pwd.replace(home, "~", 1) if pwd.startswith(home) else pwd

        self._debug_log(f"Rendering statusline with current_dir='{current_dir}'")

        # Project context
        project_name = ""
        if project_dir and project_dir != current_dir and project_dir != "null":
            project_name = os.path.basename(project_dir)

        # Git information
        git_branch, git_status = self._get_git_info()

        # CC-Hooks health check
        _, cc_hooks_emoji, _, cc_hooks_port = self._get_cc_hooks_health()

        # CC-Hooks update check
        update_available, update_msg = self._get_cc_hooks_update_status()

        # Usage information
        session_txt, session_pct, session_bar, cost_usd, cost_per_hour = (
            self._get_ccusage_info()
        )

        # TTS information
        tts_info, tts_enabled, voice_name = self._get_tts_info()

        # OpenRouter information
        openrouter_info, openrouter_enabled, openrouter_model = (
            self._get_openrouter_info()
        )

        # Sound effects information
        effects_info, effects_muted = self._get_sound_effects_info()

        # Build line 1: Main context + cc-hooks features
        line1_parts = []

        # Project context (if different from current dir)
        if project_name:
            line1_parts.append(
                f"📦 {self.project_color()}{project_name}{self._reset()}"
            )

        # Current directory
        line1_parts.append(f"📁 {self.dir_color()}{current_dir}{self._reset()}")

        # Git information
        if git_branch:
            git_part = f"🌿 {self.git_color()}{git_branch}"
            if git_status:
                git_part += f" {git_status}"
            git_part += self._reset()
            line1_parts.append(git_part)

        # Model information
        line1_parts.append(f"💥 {self.model_color()}{model_name}{self._reset()}")

        # Output style (persona)
        if output_style and output_style != "null":
            line1_parts.append(f"🎨 {self.style_color()}{output_style}{self._reset()}")

        # Model version
        if model_version and model_version != "null":
            line1_parts.append(
                f"🏷️ {self.version_color()}{model_version}{self._reset()}"
            )

        # Build line 2: CC-Hooks features
        line2_parts = []

        # CC-Hooks health status
        line2_parts.append(f"🎧 {cc_hooks_emoji} cc-hooks:{cc_hooks_port}")

        # TTS information
        if tts_enabled and tts_info:
            tts_display = tts_info
            if (
                voice_name
                and voice_name != tts_info
                and not tts_info.startswith(voice_name)
            ):
                tts_display = f"{voice_name}: {tts_info}"
            # Use muted icon for muted state, speaker icon otherwise
            tts_icon = "🔇" if tts_info == "Muted" else "🔊"
            line2_parts.append(
                f"{tts_icon} {self.tts_color()}{tts_display}{self._reset()}"
            )

        # Sound effects information (only show when muted)
        if effects_muted and effects_info:
            line2_parts.append(f"🔕 {effects_info}")

        # OpenRouter information
        if openrouter_enabled and openrouter_info:
            line2_parts.append(
                f"🔀 {self.openrouter_color()}{openrouter_info}{self._reset()}"
            )

        # Build line 3: Usage & Cost (ccusage dedicated)
        line3_parts = []

        # Session information
        if session_txt:
            session_col = self.session_color(session_pct)
            line3_parts.append(f"⌛ {session_col}{session_txt}{self._reset()}")
            line3_parts.append(f"{session_col}[{session_bar}]{self._reset()}")

        # Cost information
        if cost_usd and re.match(r"^[\d.]+$", str(cost_usd)):
            cost_part = f"💵 {self.cost_color()}${float(cost_usd):.2f}"
            if cost_per_hour and re.match(r"^[\d.]+$", str(cost_per_hour)):
                cost_part += f" (${float(cost_per_hour):.2f}/h)"
            cost_part += self._reset()
            line3_parts.append(cost_part)

        # Print the final status line (2-4 lines)
        print("  ".join(line1_parts))
        if line2_parts:  # Only print line 2 if there's cc-hooks info
            print("  ".join(line2_parts))
        if line3_parts:  # Only print line 3 if there's usage info
            print("  ".join(line3_parts))
        if update_available and update_msg:  # Print update notification on line 4
            # Add yellow color to warning message
            yellow = self._color("1;33")
            reset = self._reset()
            colored_msg = f"{yellow}{update_msg}{reset}"
            print(colored_msg)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Claude Code statusline")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    parser.add_argument("--no-color", action="store_true", help="Disable color output")
    args = parser.parse_args()

    debug = args.debug
    no_color = args.no_color

    # Initialize with debug info
    if debug:
        print(
            f"[DEBUG StatusLine] Debug mode enabled via command line, no_color={no_color}",
            file=sys.stderr,
            flush=True,
        )

    status_line = StatusLine(debug=debug, no_color=no_color)

    # Read input from stdin
    input_data = sys.stdin.read() if not sys.stdin.isatty() else ""
    if debug:
        print(
            f"[DEBUG StatusLine] Input data length: {len(input_data)}",
            file=sys.stderr,
            flush=True,
        )

    status_line.render(input_data)


if __name__ == "__main__":
    main()
