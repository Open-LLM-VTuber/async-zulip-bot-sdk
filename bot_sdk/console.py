from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Optional, TYPE_CHECKING
import sys
from collections import deque

from loguru import logger

from .config import AppConfig, load_config
from .loader import BotSpec, discover_bot_factories
from .runner import BotRunner
from .db.cli import make_bot_migrations, run_bot_migrations

try:  # Optional rich-based UI
    from rich.console import Console
    from rich.layout import Layout
    from rich.live import Live
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    _RICH_AVAILABLE = True
except Exception:  # pragma: no cover - rich is optional
    _RICH_AVAILABLE = False

try:  # Optional prompt_toolkit-based input for non-Windows platforms
    from prompt_toolkit import PromptSession
    from prompt_toolkit.completion import WordCompleter

    _PROMPT_TOOLKIT_AVAILABLE = True
except Exception:  # pragma: no cover - prompt_toolkit is optional
    _PROMPT_TOOLKIT_AVAILABLE = False


COMMAND_LIST = [
    "run",
    "stop",
    "reload",
    "status",
    "bots",
    "help",
    "exit",
    "quit",
    "makemigrations",
    "migrate",
]


COMMAND_LIST = [
    "run",
    "stop",
    "reload",
    "status",
    "bots",
    "help",
    "exit",
    "quit",
    "makemigrations",
    "migrate",
]


@dataclass
class ManagedBot:
    spec: BotSpec
    runner: BotRunner
    task: Optional[asyncio.Task[None]] = None


class BotManager:
    def __init__(self, specs: Iterable[BotSpec]) -> None:
        self._specs = {spec.name: spec for spec in specs}
        self._running: dict[str, ManagedBot] = {}
        self._lock = asyncio.Lock()

    @property
    def available_bots(self) -> list[str]:
        return sorted(self._specs.keys())

    @property
    def running_bots(self) -> list[str]:
        return sorted(self._running.keys())

    def set_spec(self, spec: BotSpec) -> None:
        self._specs[spec.name] = spec

    async def start_all(self) -> list[str]:
        tasks = [self.start_bot(name) for name in self.available_bots]
        results = await asyncio.gather(*tasks)
        return results


    async def start_bot(self, name: str) -> str:
        async with self._lock:
            if name in self._running:
                return f"Bot '{name}' is already running"
            spec = self._specs.get(name)
        if not spec:
            return f"Bot '{name}' is not configured or disabled"

        runner = BotRunner(
            spec.factory,
            client_kwargs={"config_file": spec.zuliprc},
            event_types=spec.event_types,
        )
        managed = ManagedBot(spec=spec, runner=runner)
        task = asyncio.create_task(self._run_runner(name, managed))
        managed.task = task

        async with self._lock:
            self._running[name] = managed
        return f"Starting bot '{name}'"

    async def _run_runner(self, name: str, managed: ManagedBot) -> None:
        try:
            async with managed.runner:
                await managed.runner.run_forever()
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # pragma: no cover - runtime safety
            logger.exception("Bot '{}' exited with error: {}", name, exc)
        finally:
            async with self._lock:
                self._running.pop(name, None)

    async def stop_bot(self, name: str, *, reason: str = "") -> str:
        async with self._lock:
            managed = self._running.get(name)
        if not managed:
            return f"Bot '{name}' is not running"

        managed.runner.request_stop(reason=reason or "stop requested")
        if managed.task:
            try:
                await asyncio.wait_for(managed.task, timeout=20)
            except asyncio.TimeoutError:
                managed.task.cancel()
                await asyncio.gather(managed.task, return_exceptions=True)

        async with self._lock:
            self._running.pop(name, None)
        return f"Stopped bot '{name}'"

    async def reload_bot(self, spec: BotSpec) -> str:
        self.set_spec(spec)
        await self.stop_bot(spec.name, reason="reload")
        return await self.start_bot(spec.name)

    async def stop_all(self) -> None:
        running = self.running_bots
        for name in running:
            await self.stop_bot(name, reason="shutdown")


class LogBuffer:
    def __init__(self, max_lines: int = 400) -> None:
        self._lines = deque(maxlen=max_lines)

    def append(self, message: str) -> None:
        # Sink for loguru: receives formatted string messages.
        self._lines.extend(message.rstrip("\n").splitlines())

    @property
    def lines(self) -> list[str]:
        return list(self._lines)


class ConsoleUI:
    """Builds the Rich layout: logs at top, status in middle, prompt panel at bottom.

    The actual user input is still read via input()/console.input(); this
    class is only responsible for rendering the static chrome so that Live
    can refresh it without touching the editing line.
    """

    def __init__(self, manager: BotManager, log_buffer: LogBuffer, console: Console) -> None:
        self.manager = manager
        self.log_buffer = log_buffer
        self.console = console
        self.scroll_offset = 0

    def render(self, command_buffer: str = ""):
        if not _RICH_AVAILABLE:
            return ""  # Safety: only used when rich is present

        layout = Layout()
        layout.split_column(
            Layout(name="logs", ratio=3),
            Layout(name="status", size=5),
            Layout(name="prompt", size=3),
        )

        # Calculate visible log lines based on console height
        # Approx height available for logs = total - status(5) - prompt(2) - borders(~7)
        log_height = max(8, self.console.height - 9)
        
        lines = self.log_buffer.lines
        total_lines = len(lines)
        
        # Calculate slice
        if self.scroll_offset > total_lines - log_height:
             self.scroll_offset = max(0, total_lines - log_height)
        
        start_idx = max(0, total_lines - log_height - self.scroll_offset)
        end_idx = total_lines - self.scroll_offset if self.scroll_offset > 0 else None
        
        visible_chunk = lines[start_idx:end_idx]
        log_content = Text.from_ansi("\n".join(visible_chunk))
        
        title = f"Logs ({self.scroll_offset})" if self.scroll_offset > 0 else "Logs"
        layout["logs"].update(Panel(log_content, title=title, border_style="cyan", padding=(0, 1)))

        status_table = Table.grid(expand=True, padding=(0, 10))
        status_table.add_column(justify="left", no_wrap=True, style="bold")
        status_table.add_column(justify="left", ratio=1, no_wrap=False)
        status_table.add_row("Running", ", ".join(self.manager.running_bots) or "none", style="green")
        status_table.add_row("Available", ", ".join(self.manager.available_bots) or "none", style="cyan")
        help_text = _command_help_suggestions(command_buffer, self.manager.available_bots)
        help_state = _command_help_state(command_buffer, self.manager.available_bots)
        help_cell = _render_help_cell(help_text, help_state)
        status_table.add_row("Command Help", help_cell, style="magenta")
        layout["status"].update(Panel(status_table, title="Status", border_style="magenta", padding=(0, 1)))

        # Add cursor effect
        prompt_content = Text("bot-console> ", style="bold yellow")
        prompt_content.append(command_buffer)
        prompt_content.append("█", style="blink")
        layout["prompt"].update(Panel(prompt_content, title="Command", border_style="green", padding=(0, 1)))

        return layout


def _print_help(output_func: Callable[[str], None], manager: BotManager) -> None:
    help_lines = [
        "\nCommands:",
        "  run <bot|all>   - start a bot or all bots",
        "  stop <bot|all>  - stop a bot or all running bots",
        "  reload <bot>    - stop then start a bot (reload module)",
        "  status        - show running bots",
        "  bots          - list available bots",
        "  help          - show this help",
        "  exit/quit     - stop all and exit",
        "  makemigrations <bot> [msg] - create migrations",
        "  migrate <bot> [rev]      - apply migrations",
        "",
        f"Available bots: {', '.join(manager.available_bots) if manager.available_bots else 'none'}",
    ]
    output_func("\n".join(help_lines))


def _complete_command(command_buffer: str, manager: BotManager) -> str:
    # Simple tab completion for commands and bot names.
    commands = COMMAND_LIST
    bots = manager.available_bots

    parts = command_buffer.split()
    if not parts:
        # Complete to the first command
        return commands[0] + " "

    # Determine candidate list based on position
    if len(parts) == 1 and not command_buffer.endswith(" "):
        # Completing command name
        prefix = parts[0]
        candidates = [c for c in commands if c.startswith(prefix)]
    elif len(parts) == 1 and command_buffer.endswith(" "):
        # Command chosen, completing first argument
        cmd = parts[0]
        choices = _choices_for_command(cmd, bots)
        candidates = choices
        prefix = ""
    else:
        prefix = parts[-1]
        cmd = parts[0]
        choices = _choices_for_command(cmd, bots)
        candidates = [c for c in choices if c.startswith(prefix)]

    if not candidates:
        return command_buffer

    if len(candidates) == 1:
        # If we're completing an argument right after a space, append; otherwise replace token.
        if len(parts) == 1 and command_buffer.endswith(" "):
            return command_buffer + candidates[0] + " "
        parts[-1] = candidates[0]
        suffix = " " if command_buffer and not command_buffer.endswith(" ") else ""
        return " ".join(parts) + suffix

    # Multiple candidates: use longest common prefix.
    if prefix == "" and len(candidates) > 0:
        # No prefix typed; insert the first candidate.
        return command_buffer + candidates[0] + " "

    common_prefix = candidates[0]
    for cand in candidates[1:]:
        i = 0
        while i < min(len(common_prefix), len(cand)) and common_prefix[i] == cand[i]:
            i += 1
        common_prefix = common_prefix[:i]
    if common_prefix and common_prefix != prefix:
        parts[-1] = common_prefix
        return " ".join(parts)

    return command_buffer


def _choices_for_command(cmd: str, bots: list[str]) -> list[str]:
    if cmd in {"run", "stop"}:
        return ["all"] + bots
    if cmd in {"reload", "makemigrations", "migrate"}:
        return bots
    return []


def _command_help_suggestions(command_buffer: str, bots: list[str]) -> str:
    """Display filtered commands/arguments in the Status panel based on current input."""
    buf = (command_buffer or "").lstrip()
    if not buf:
        return "/".join(COMMAND_LIST)

    parts = buf.split()
    cmd_prefix = parts[0]

    # Still typing the command name (no space yet)
    if len(parts) == 1 and not buf.endswith(" "):
        matches = [c for c in COMMAND_LIST if c.startswith(cmd_prefix)]
        return "/".join(matches) if matches else ""

    # Command selected; suggest arguments
    cmd = cmd_prefix
    arg_prefix = parts[1] if len(parts) > 1 else ""
    choices = _choices_for_command(cmd, bots)
    if not choices:
        return ""

    if arg_prefix:
        matches = [c for c in choices if c.startswith(arg_prefix)]
    else:
        matches = choices

    if len(matches) == 1 and matches[0] == arg_prefix:
        return ""

    return "/".join(matches) if matches else ""


def _command_help_state(command_buffer: str, bots: list[str]) -> str:
    """Return Do it! when the current buffer is runnable, Error! when invalid."""
    buf = (command_buffer or "").strip()
    if not buf:
        return ""

    parts = buf.split()
    cmd = parts[0]
    if cmd not in COMMAND_LIST:
        return "Error!"

    # Commands with no args required
    if cmd in {"status", "bots", "help", "exit", "quit"}:
        return "Do it!"

    # Commands requiring one argument
    if len(parts) < 2:
        return "Error!"

    target = parts[1]

    # Commands requiring a target bot/all
    if cmd in {"run", "stop"}:
        return "Do it!" if (target == "all" or target in bots) else "Error!"

    # Commands requiring a bot name
    if cmd in {"reload", "makemigrations", "migrate"}:
        return "Do it!" if target in bots else "Error!"

    return ""


def _render_help_cell(help_text: str, help_state: str):
    """Render the status Help cell with simple precedence to stay readable."""
    if help_state == "Do it!":
        return Text(help_state, style="bold green")

    if help_state == "Error!":
        if help_text:
            txt = Text(help_text)
            txt.append("  ")
            txt.append(help_state, style="bold red")
            return txt
        return Text(help_state, style="bold red")

    if help_text:
        return help_text

    return "-"


async def _handle_command(
    raw: str,
    manager: BotManager,
    cfg_path: Path,
    bots_dir: str,
    output_func: Callable[[str], None] = print,
) -> bool:
    """Process a single console command. Returns True to exit."""

    command_line = raw.strip()
    if not command_line:
        return False

    parts = command_line.split()
    cmd = parts[0].lower()
    args = parts[1:]

    if cmd in {"exit", "quit"}:
        return True
    if cmd == "help":
        _print_help(output_func, manager)
        return False
    if cmd == "bots":
        output_func(f"Configured bots: {', '.join(manager.available_bots) if manager.available_bots else 'none'}")
        return False
    if cmd == "status":
        running = manager.running_bots
        output_func(f"Running bots: {', '.join(running) if running else 'none'}")
        return False

    if cmd == "start":
        cmd = "run"  # backward compatibility

    if cmd == "run":
        if not args:
            output_func("Usage: run <bot|all>")
            return False
        bot_name = args[0]
        if bot_name == "all":
            results = await manager.start_all()
            for line in results:
                output_func(line)
            return False
        if bot_name not in manager.available_bots:
            spec = await _load_spec(bot_name, cfg_path, bots_dir, reload_modules=False)
            if spec:
                manager.set_spec(spec)
        result = await manager.start_bot(bot_name)
        output_func(result)
        return False

    if cmd == "stop":
        if not args:
            output_func("Usage: stop <bot|all>")
            return False
        bot_name = args[0]
        if bot_name == "all":
            results = await manager.stop_all()
            if results:
                for line in results:
                    output_func(line)
            else:
                output_func("No running bots to stop.")
            return False

        result = await manager.stop_bot(bot_name)
        output_func(result)
        return False

    if cmd == "reload":
        if not args:
            output_func("Usage: reload <bot>")
            return False
        bot_name = args[0]
        spec = await _load_spec(bot_name, cfg_path, bots_dir, reload_modules=True)
        if not spec:
            output_func(f"Bot '{bot_name}' is not configured or disabled")
            return False
        # Stop bot if running to release file locks (important for migrations/reloads)
        if bot_name in manager.running_bots:
            await manager.stop_bot(bot_name, reason="reload")
            
        result = await manager.reload_bot(spec)
        output_func(result)
        return False

    if cmd == "makemigrations":
        if not args:
            output_func("Usage: makemigrations <bot> [message]")
            return False
        bot_name = args[0]
        message = " ".join(args[1:]) if len(args) > 1 else None
        try:
            output_func(f"Creating migrations for {bot_name}...")
            # Run in thread to allow UI updates
            await asyncio.to_thread(make_bot_migrations, bot_name, message)
            output_func(f"Migrations created successfully for {bot_name}")
        except Exception as e:
            output_func(f"Error creating migrations: {e}")
        return False

    if cmd == "migrate":
        if not args:
            output_func("Usage: migrate <bot> [revision]")
            return False
        bot_name = args[0]
        revision = args[1] if len(args) > 1 else "head"
        try:
            output_func(f"Applying migrations for {bot_name}...")
            await asyncio.to_thread(run_bot_migrations, bot_name, revision)
            output_func(f"Migrations applied successfully for {bot_name}")
        except Exception as e:
            output_func(f"Error applying migrations: {e}")
        return False

    output_func(f"Unknown command: {cmd}. Type 'help' for list of commands.")
    return False


async def _load_spec(bot_name: str, config_path: Path, bots_dir: str, reload_modules: bool) -> Optional[BotSpec]:
    app_config = load_config(str(config_path), AppConfig)
    specs = discover_bot_factories(app_config, bots_dir, reload_modules=reload_modules)
    for spec in specs:
        if spec.name == bot_name:
            return spec
    return None


async def run_console(config_path: str = "bots.yaml", bots_dir: str = "bots", log_level: str = "INFO") -> None:
    cfg_path = Path(config_path)
    if not cfg_path.exists():
        raise FileNotFoundError("bots.yaml not found; please create it to list bots to launch")

    app_config = load_config(str(cfg_path), AppConfig)
    specs = discover_bot_factories(app_config, bots_dir)
    manager: BotManager = BotManager(specs)

    # Windows: keep Rich-based full-screen console with msvcrt key handling.
    use_rich_windows = _RICH_AVAILABLE and sys.platform.startswith("win")
    if use_rich_windows:
        try:
            import msvcrt  # type: ignore[import]
        except ImportError:
            use_rich_windows = False
        else:
            console = Console()
            log_buffer = LogBuffer(max_lines=1000)
            ui = ConsoleUI(manager, log_buffer, console)

            # Log updates to the buffer will direct here, which goes to the logs panel
            def log_sink(message: str) -> None:
                log_buffer.append(message)

            logger.remove()
            # Restore styling and ensure ANSI codes are preserved for Text.from_ansi
            timefmt = "%Y-%m-%d %H:%M:%S"
            fmt = "<green>{time:"+ timefmt +"}</green> |[<level>{level}</level>]| <cyan>{name} | line: {line}</cyan> | <level>{message}</level>"
            logger.add(log_sink, format=fmt, level=log_level, enqueue=False, colorize=True)

            def output_to_logs(msg: str) -> None:
                logger.info(msg)

            command_buffer: str = ""
            command_history: list[str] = []
            history_idx: int = 0  # 0 means "newest+1", 1 means last command

            with Live(
                ui.render(command_buffer),
                console=console,
                refresh_per_second=10,
                auto_refresh=False,
                screen=True,  # Use full screen to prevent scroll artifacts
            ) as live:
                # Initial render
                live.update(ui.render(command_buffer), refresh=True)

                while True:
                    # Poll for input
                    while msvcrt.kbhit():
                        # We use getch() (bytes) instead of getwch() (unicode) to robustly parse
                        # scan codes (e.g. arrows) which come as 0xE0 + code.
                        ch = msvcrt.getch()

                        if ch == b"\x03":  # Ctrl+C
                            await manager.stop_all()
                            return
                        elif ch in {b"\r", b"\n"}:  # Enter
                            cmd = command_buffer
                            command_buffer = ""
                            history_idx = 0
                            if cmd.strip():
                                # Prevent duplicates in history
                                if not command_history or command_history[0] != cmd:
                                    command_history.insert(0, cmd)
                                live.update(ui.render(command_buffer), refresh=True)
                                logger.info(f"> {cmd}")  # Echo command to logs
                                should_exit = await _handle_command(cmd, manager, cfg_path, bots_dir, output_to_logs)
                                if should_exit:
                                    await manager.stop_all()
                                    return
                            else:
                                live.update(ui.render(command_buffer), refresh=True)

                        elif ch == b"\x08":  # Backspace
                            command_buffer = command_buffer[:-1]

                        elif ch == b"\t":  # Tab completion
                            command_buffer = _complete_command(command_buffer, manager)

                        elif ch in {b"\xe0", b"\x00"}:  # Arrow keys prefix
                            sc = msvcrt.getch()
                            if sc == b"H":  # Up
                                if history_idx < len(command_history):
                                    if history_idx == 0:
                                        # (Optional) could save current draft
                                        pass
                                    command_buffer = command_history[history_idx]
                                    history_idx += 1
                            elif sc == b"P":  # Down
                                if history_idx > 0:
                                    history_idx -= 1
                                    if history_idx == 0:
                                        command_buffer = ""
                                    else:
                                        command_buffer = command_history[history_idx - 1]
                                else:
                                    command_buffer = ""
                                    history_idx = 0
                            elif sc == b"I":  # Page Up
                                ui.scroll_offset += 5
                            elif sc == b"Q":  # Page Down
                                ui.scroll_offset = max(0, ui.scroll_offset - 5)

                        else:
                            try:
                                # Normal char decoding
                                char_str = ch.decode("utf-8", "ignore")
                                if char_str and ord(char_str) >= 32:
                                    command_buffer += char_str
                            except Exception as e:
                                logger.debug("Failed to decode character: {}", e)

                    # Update UI
                    # We always refresh to animate the cursor blink or show new logs
                    live.update(ui.render(command_buffer), refresh=True)

                    # Yield to event loop
                    await asyncio.sleep(0.05)

            await manager.stop_all()
            return

    # Non-Windows or when Rich fullscreen is unavailable: prefer prompt_toolkit if installed.
    if _PROMPT_TOOLKIT_AVAILABLE:
        # Basic word completer: commands + bot names + 'all'
        words = set(COMMAND_LIST)
        words.update(manager.available_bots)
        words.add("all")
        completer = WordCompleter(sorted(words), ignore_case=True)
        session = PromptSession(completer=completer)

        print("Async Zulip Bot Console (prompt_toolkit). Type 'help' for commands.")
        _print_help(print, manager)
        while True:
            try:
                raw = await session.prompt_async("bot-console> ")
            except (EOFError, KeyboardInterrupt):
                print("Exiting console...")
                break
            if not raw.strip():
                continue
            should_exit = await _handle_command(raw, manager, cfg_path, bots_dir, print)
            if should_exit:
                break
        await manager.stop_all()
        return

    # Final fallback when neither Rich+msvcrt nor prompt_toolkit are available.
    print("Async Zulip Bot Console (basic). Type 'help' for commands.")
    _print_help(print, manager)
    while True:
        try:
            raw = await asyncio.to_thread(input, "bot-console> ")
        except (EOFError, KeyboardInterrupt):
            print("Exiting console...")
            break
        if not raw.strip():
            continue
        should_exit = await _handle_command(raw, manager, cfg_path, bots_dir, print)
        if should_exit:
            break
    await manager.stop_all()
