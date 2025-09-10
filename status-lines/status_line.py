#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "requests",
#     "elevenlabs",
#     "openai",
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

    def elevenlabs_color(self):
        return self._color("1;33")  # yellow

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
        # Get port from environment variable (set by claude.sh), fallback to default
        port = int(os.getenv("CC_HOOKS_PORT", "12222"))

        try:
            import requests

            response = requests.get(f"http://localhost:{port}/health", timeout=2)
            if response.status_code == 200:
                return True, "✅", "online", port
            else:
                return False, "❌", "error", port
        except ImportError:
            self._debug_log("requests package not available for health check")
            return False, "❓", "no-requests", port
        except requests.exceptions.RequestException:
            return False, "🔴", "offline", port
        except Exception as e:
            self._debug_log(f"Unexpected error in health check: {e}")
            return False, "⚠️", "unknown", port

    def _get_ccusage_info(self):
        """Get usage information from ccusage command"""
        self._debug_log("_get_ccusage_info() called")
        session_txt = ""
        session_pct = 0
        session_bar = ""
        cost_usd = ""
        cost_per_hour = ""

        # Check if ccusage is available
        ccusage_path = shutil.which("ccusage")
        if not ccusage_path:
            self._debug_log("ccusage command not found in PATH")
            return session_txt, session_pct, session_bar, cost_usd, cost_per_hour

        self._debug_log(f"ccusage found at: {ccusage_path}")

        # Get blocks output
        success, output, error = self._run_command(["ccusage", "blocks", "--json"])
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

    def _get_elevenlabs_info(self):
        """Get ElevenLabs usage information if available"""
        elevenlabs_info = ""
        elevenlabs_enabled = False

        # Check if ElevenLabs is configured by checking TTS providers and API key
        try:
            if config is None:
                self._debug_log("config module not available")
                return elevenlabs_info, elevenlabs_enabled

            # Check if elevenlabs is in TTS_PROVIDERS list
            tts_providers_list = config.get_tts_providers_list()
            has_elevenlabs_provider = "elevenlabs" in tts_providers_list

            # Check if API key is available
            api_key = config.elevenlabs_api_key
            has_api_key = bool(api_key)

            elevenlabs_enabled = has_elevenlabs_provider and has_api_key

            self._debug_log(f"ElevenLabs provider in list: {has_elevenlabs_provider}")
            self._debug_log(f"ElevenLabs API key available: {has_api_key}")
            self._debug_log(f"ElevenLabs enabled: {elevenlabs_enabled}")
        except ImportError:
            self._debug_log("python-dotenv not available for ElevenLabs check")
            return elevenlabs_info, elevenlabs_enabled
        except Exception as e:
            self._debug_log(f"Error accessing config: {e}")
            return elevenlabs_info, elevenlabs_enabled

        if not elevenlabs_enabled:
            self._debug_log("ElevenLabs not properly configured")
            return elevenlabs_info, elevenlabs_enabled

        if config is None:
            self._debug_log("config module not available for API key check")
            return elevenlabs_info, elevenlabs_enabled

        api_key = config.elevenlabs_api_key
        if not api_key:
            self._debug_log("ElevenLabs API key not found")
            return elevenlabs_info, elevenlabs_enabled

        try:
            from elevenlabs.client import ElevenLabs

            client = ElevenLabs(api_key=api_key)
            subscription = client.user.subscription.get()

            self._debug_log(f"ElevenLabs subscription type: {type(subscription)}")
            self._debug_log(f"ElevenLabs subscription: {subscription}")

            # Extract subscription info
            char_limit = getattr(subscription, "character_limit", 0)
            char_used = getattr(subscription, "character_count", 0)
            # For can_do_tts, we'll check if character_count < character_limit
            can_do_tts = char_used < char_limit if char_limit > 0 else True

            self._debug_log(
                f"ElevenLabs: limit={char_limit}, used={char_used}, can_tts={can_do_tts}"
            )

            # Format the usage info
            if char_limit > 0:
                usage_pct = (char_used * 100) // char_limit
                elevenlabs_info = f"{char_used:,}/{char_limit:,} chars ({usage_pct}%)"
                if not can_do_tts:
                    elevenlabs_info += " [LIMIT REACHED]"
            else:
                elevenlabs_info = (
                    f"{char_used:,} chars used"
                    if char_used > 0
                    else "ElevenLabs: Connected"
                )

        except ImportError:
            self._debug_log("elevenlabs package not available")
            elevenlabs_info = "ElevenLabs: Not installed"
        except Exception as e:
            self._debug_log(f"Error fetching ElevenLabs info: {e}")
            if self.debug:
                print(f"ELEVENLABS ERROR: {e}", file=sys.stderr)
            elevenlabs_info = f"ElevenLabs: {type(e).__name__}"

        return elevenlabs_info, elevenlabs_enabled

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

        # Usage information
        session_txt, session_pct, session_bar, cost_usd, cost_per_hour = (
            self._get_ccusage_info()
        )

        # ElevenLabs information
        elevenlabs_info, elevenlabs_enabled = self._get_elevenlabs_info()

        # Start building the status line
        parts = []

        # Project context (if different from current dir)
        if project_name:
            parts.append(f"📦 {self.project_color()}{project_name}{self._reset()}")

        # Current directory
        parts.append(f"📁 {self.dir_color()}{current_dir}{self._reset()}")

        # Git information
        if git_branch:
            git_part = f"🌿 {self.git_color()}{git_branch}"
            if git_status:
                git_part += f" {git_status}"
            git_part += self._reset()
            parts.append(git_part)

        # Model information
        parts.append(f"🤖 {self.model_color()}{model_name}{self._reset()}")

        # Output style
        if output_style and output_style != "null":
            parts.append(f"🎨 {self.style_color()}{output_style}{self._reset()}")

        # Model version
        if model_version and model_version != "null":
            parts.append(f"🏷️ {self.version_color()}{model_version}{self._reset()}")

        # CC-Hooks health status
        parts.append(f"🔗 {cc_hooks_emoji} cc-hooks:{cc_hooks_port}")

        # Session information
        if session_txt:
            session_col = self.session_color(session_pct)
            parts.append(f"⌛ {session_col}{session_txt}{self._reset()}")
            parts.append(f"{session_col}[{session_bar}]{self._reset()}")

        # Cost information
        if cost_usd and re.match(r"^[\d.]+$", str(cost_usd)):
            cost_part = f"💵 {self.cost_color()}${float(cost_usd):.2f}"
            if cost_per_hour and re.match(r"^[\d.]+$", str(cost_per_hour)):
                cost_part += f" (${float(cost_per_hour):.2f}/h)"
            cost_part += self._reset()
            parts.append(cost_part)

        # ElevenLabs information
        if elevenlabs_enabled and elevenlabs_info:
            parts.append(
                f"🔊 {self.elevenlabs_color()}{elevenlabs_info}{self._reset()}"
            )

        # Print the final status line
        print("  ".join(parts))


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
