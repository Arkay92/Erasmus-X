# -*- coding: utf-8 -*-
"""Erasmus X terminal assistant UI.

Install dependencies:
    python -m pip install -r requirements.txt

Run:
    python erasmus_cli.py

This file is intentionally self-contained. It renders a polished Rich-based
terminal dashboard and command loop without calling external services or APIs.
"""

from __future__ import annotations

import os
import platform
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

try:
    from rich import box
    from rich.align import Align
    from rich.console import Console, Group
    from rich.live import Live
    from rich.panel import Panel
    from rich.progress import BarColumn, Progress, TextColumn
    from rich.prompt import Prompt
    from rich.rule import Rule
    from rich.table import Table
    from rich.text import Text
except ImportError:  # pragma: no cover - helpful runtime message for new installs.
    print("Rich is required to run the Erasmus X CLI.")
    print("Install it with: python -m pip install rich")
    raise SystemExit(1)


PROJECT_ROOT = Path(__file__).resolve().parent

LOGO = r"""
   ███████╗██╗  ██╗
   ██╔════╝╚██╗██╔╝
   █████╗   ╚███╔╝
   ██╔══╝   ██╔██╗
   ███████╗██╔╝ ██╗
   ╚══════╝╚═╝  ╚═╝

      Erasmus X
"""


@dataclass
class AgentState:
    """Mutable state for the terminal session."""

    project_name: str = "Erasmus X"
    subtitle: str = "Agentic OS"
    model: str = "local-orchestrator"
    mode: str = "architect"
    accent: str = "#00bcd4"
    panel_border: str = "#252a33"
    command_border: str = "#526170"
    header_border: str = "#00bcd4"
    live_status: str = "offline"
    index_status: str = "indexing"
    latency_ms: int = 0
    tokens: str = "0"
    total_tokens_count: int = 0
    agents: int = 1
    memory_state: str = "stable"
    recent_tasks: list[str] = field(
        default_factory=lambda: [
            "Initializing Agentic OS...",
            "Checking workspace integrity...",
        ]
    )
    active_modules: list[str] = field(default_factory=list)
    commands_run: int = 0
    session_started: datetime = field(default_factory=datetime.now)

    def remember(self, message: str) -> None:
        self.recent_tasks.insert(0, message)
        self.recent_tasks = self.recent_tasks[:6]


class ErasmusTerminalUI:
    """Rich-powered command surface for the Erasmus X project."""

    def __init__(self, root: Path = PROJECT_ROOT) -> None:
        self.root = root
        self.console = Console(style="white on #05060a")
        self.state = AgentState()
        self.commands: dict[str, Callable[[list[str]], None]] = {
            "/help": self.command_help,
            "/status": self.command_status,
            "/run": self.command_run,
            "/files": self.command_files,
            "/chat": self.command_chat,
            "/clear": self.command_clear,
            "/exit": self.command_exit,
        }
        self.agent = None
        self.brain = None
        self.running = True

    def _ensure_agent(self) -> None:
        if self.agent is not None:
            return
            
        from main import build_agent
        with self.console.status("[bold cyan]Connecting to the Neurosymbolic Agent Pipeline...", spinner="dots"):
            try:
                self.agent, self.brain = build_agent()
                self.state.live_status = "online"
                self.state.index_status = "ready"
                self.state.remember("Connected to Neurosymbolic Pipeline")
                self.state.remember("Vector store synchronized")
            except Exception as e:
                self.state.live_status = "error"
                self.state.index_status = "failed"
                self.console.print(f"[bold red]Failed to load Agent Brain:[/bold red] {e}")

    def run(self) -> None:
        """Start the dashboard and command loop."""
        self.refresh_active_modules()
        self._ensure_agent()
        self.command_clear([])
        self.render_dashboard()

        while self.running:
            try:
                prompt = Text("erasmus-x", style=f"bold {self.state.accent}")
                prompt.append(" /", style="dim")
                raw = Prompt.ask(
                    prompt,
                    console=self.console,
                ).strip()
            except (EOFError, KeyboardInterrupt):
                self.console.print()
                self.command_exit([])
                break

            if not raw:
                continue

            self.handle_command(raw)

    def handle_command(self, raw: str) -> None:
        self.state.commands_run += 1

        if not raw.startswith("/"):
            self.state.remember(f"Chat request: {raw[:30]}...")
            self._ensure_agent()
            if self.agent:
                try:
                    streamed_text = Text("", style="green")
                    panel = Panel(streamed_text, title="Erasmus X (thinking...)", box=box.ROUNDED, border_style=self.state.command_border, padding=(1, 2))
                    
                    with Live(panel, console=self.console, refresh_per_second=15, transient=True) as live:
                        def live_update_callback(chunk: str):
                            streamed_text.append(chunk)
                            live.update(Panel(streamed_text, title="Erasmus X (thinking...)", box=box.ROUNDED, border_style=self.state.command_border, padding=(1, 2)))

                        start_time = time.perf_counter()
                        result = self.agent.chat(raw, stream_callback=live_update_callback)

                    raw_response, clean_ans = result
                    duration = time.perf_counter() - start_time
                    self.state.latency_ms = int(duration * 1000)
                    from utils.text_utils import count_tokens
                    response_text = clean_ans if clean_ans else raw_response
                    input_tokens = count_tokens(raw)
                    output_tokens = count_tokens(response_text)
                    self.state.total_tokens_count += (input_tokens + output_tokens)
                    if self.state.total_tokens_count > 1000:
                        self.state.tokens = f"{self.state.total_tokens_count / 1000:.1f}k"
                    else:
                        self.state.tokens = str(self.state.total_tokens_count)
                    self.print_response("Erasmus X", response_text, style="green")
                    
                    if self.state.commands_run % 3 == 0 and self.brain:
                        self.brain.save()
                except Exception as e:
                    self.print_response("Error", str(e), style="red")
            return

        command, *args = raw.split()
        handler = self.commands.get(command.lower())
        if handler is None:
            suggestions = self.command_suggestions(raw)
            if suggestions:
                self.print_suggestions(raw, suggestions)
                return
            self.print_response(
                "Unknown command",
                f"`{command}` is not registered. Run `/help` to see available commands.",
                style="yellow",
            )
            return

        handler(args)

    def render_dashboard(self) -> None:
        self.console.print(self.header_panel())
        self.console.print()

        grid = Table.grid(expand=True)
        grid.add_column(ratio=1)
        grid.add_column(ratio=1)
        grid.add_row(self.recent_tasks_panel(), self.status_panel())
        grid.add_row(self.active_files_panel(), self.actions_panel())
        self.console.print(grid)
        self.console.print()
        self.console.print(self.command_bar())
        self.console.print(self.telemetry_footer())

    def header_panel(self) -> Panel:
        logo_lines = LOGO.strip("\n").splitlines()
        compact_logo = "\n".join(line[3:] if line.startswith("   ") else line for line in logo_lines)
        logo = Text(compact_logo, style=f"bold {self.state.accent}", justify="center")

        title = Text(self.state.project_name, style=f"bold {self.state.accent}")
        title.append("  ", style="default")
        title.append(self.state.subtitle, style="#aab2c0")

        meta = Text()
        meta.append("mode ", style="dim")
        meta.append(self.state.mode, style="bold violet")
        meta.append("  model ", style="dim")
        meta.append(self.state.model, style="bold cyan")
        meta.append("  status ", style="dim")
        status_color = "green" if self.state.live_status == "online" else "dim"
        meta.append("● ", style=status_color)
        meta.append(self.state.live_status, style=status_color)
        meta.append("  workspace ", style="dim")
        meta.append(self.root.name, style="white")

        rule = Text("─" * 38, style="#27303a")
        content = Group(Align.center(logo), Align.center(rule), Align.center(title), Align.center(meta))
        return Panel(content, box=box.ROUNDED, border_style=self.state.header_border, padding=(1, 2))

    def recent_tasks_panel(self) -> Panel:
        table = Table.grid(padding=(0, 1))
        table.add_column("indicator", width=3)
        table.add_column("task")
        for index, task in enumerate(self.state.recent_tasks[:5]):
            indicator = "[+]" if index == 0 else "[ ]"
            color = self.state.accent if index == 0 else "dim"
            table.add_row(Text(indicator, style=color), Text(task, style="white" if index == 0 else "dim"))
        return Panel(table, title="Recent Activity", box=box.ROUNDED, border_style=self.state.panel_border, padding=(1, 2))

    def active_files_panel(self) -> Panel:
        table = Table.grid(padding=(0, 1))
        table.add_column("file", ratio=2)
        table.add_column("state", ratio=1)
        for index, module in enumerate(self.state.active_modules[:6]):
            # Use real modification times to determine "active" status
            mtime = os.path.getmtime(self.root / module)
            is_recent = (time.time() - mtime) < 3600 # modified in last hour
            status = "active" if is_recent else "idle"
            color = self.state.accent if is_recent else "blue"
            table.add_row(self.module_text(module), self.status_text(status, color))
        if not self.state.active_modules:
            table.add_row(Text("No Python modules found", style="yellow"), self.status_text("idle", "dim"))
        return Panel(table, title="Active Files / Modules", box=box.ROUNDED, border_style=self.state.panel_border, padding=(1, 2))

    def status_panel(self) -> Panel:
        py_files = len(list(self.root.rglob("*.py")))
        test_files = len(list((self.root / "test").rglob("test_*.py"))) if (self.root / "test").exists() else 0
        uptime = datetime.now() - self.state.session_started

        table = Table.grid(padding=(0, 1))
        table.add_column("label", style="dim")
        table.add_column("value")
        table.add_row("Runtime", f"Python {platform.python_version()}")
        table.add_row("Platform", platform.system())
        table.add_row("Source files", str(py_files))
        table.add_row("Tests", str(test_files))
        
        index_color = "green" if self.state.index_status == "ready" else "yellow"
        table.add_row("Index", self.status_text(self.state.index_status, index_color))
        
        status_color = "green" if self.state.live_status == "online" else "dim"
        if self.state.live_status == "error":
            status_color = "red"
            
        table.add_row("Agent", self.status_text(self.state.live_status, status_color))
        table.add_row("Session", f"{int(uptime.total_seconds())}s")

        progress = Progress(
            TextColumn("[dim]system coherence[/]"),
            BarColumn(bar_width=None, style="bright_black", complete_style=self.state.accent),
            TextColumn("[green]stable[/]"),
            expand=True,
        )
        progress.add_task("coherence", total=100, completed=86)

        return Panel(Group(table, Rule(style="#27303a"), progress), title="System Status", box=box.ROUNDED, border_style=self.state.panel_border, padding=(1, 2))

    def actions_panel(self) -> Panel:
        actions = Table.grid(padding=(0, 1))
        actions.add_column("command", style=f"bold {self.state.accent}", width=12)
        actions.add_column("description", style="white")
        actions.add_row("/status", "Inspect local workspace health")
        actions.add_row("/files", "List core modules and tools")
        actions.add_row("/run tests", "Run the project test harness")
        actions.add_row("/run agent", "Preview agent orchestration")
        actions.add_row("/run boot", "Stream workspace activity")
        actions.add_row("/run scan", "Refresh project module index")
        actions.add_row("/help", "Show all command verbs")
        return Panel(actions, title="Suggested Next Actions", box=box.ROUNDED, border_style=self.state.panel_border, padding=(1, 2))

    def command_bar(self) -> Panel:
        commands = "  ".join(self.commands.keys())
        text = Text("Command surface: ", style="dim")
        text.append(commands, style=f"bold {self.state.accent}")
        return Panel(text, box=box.ROUNDED, border_style=self.state.command_border, padding=(0, 2))

    def telemetry_footer(self) -> Panel:
        text = Text()
        text.append("tokens ", style="dim")
        text.append(self.state.tokens, style="white")
        text.append("  |  latency ", style="dim")
        text.append(f"{self.state.latency_ms}ms", style="white")
        text.append("  |  agents ", style="dim")
        text.append(str(self.state.agents), style="white")
        text.append("  |  memory ", style="dim")
        text.append(self.state.memory_state, style="green")
        return Panel(Align.center(text), box=box.ROUNDED, border_style="#1c222b", padding=(0, 1))

    def refresh_active_modules(self) -> None:
        candidates = [
            "main.py",
            "api_server.py",
            "core/agent.py",
            "core/model_router.py",
            "core/context_manager.py",
            "core/task_queue.py",
            "tools/project_scanner.py",
            "utils/brain_sync.py",
        ]
        self.state.active_modules = [path for path in candidates if (self.root / path).exists()]

    def status_text(self, label: str, color: str) -> Text:
        status = Text("● ", style=color)
        status.append(label, style=color)
        return status

    def module_text(self, module: str) -> Text:
        path = Path(module)
        text = Text()
        parent = path.parent.as_posix()
        if parent != ".":
            text.append(f"{parent}/", style="dim")
        text.append(path.name, style="white")
        return text

    def command_help(self, _: list[str]) -> None:
        table = Table(title="Erasmus X Commands", box=box.ROUNDED, border_style=self.state.accent)
        table.add_column("Command", style=f"bold {self.state.accent}", no_wrap=True)
        table.add_column("Purpose", style="white")
        table.add_row("/help", "Show this command reference")
        table.add_row("/status", "Render system status and workspace metrics")
        table.add_row("/run tests", "Run test/run_all_tests.py locally")
        table.add_row("/run scan", "Refresh active module index")
        table.add_row("/run agent", "Stream a local agent orchestration trace")
        table.add_row("/run boot", "Stream a staged workspace activity trace")
        table.add_row("/files", "Show active project modules")
        table.add_row("/chat", "Open a dedicated full-screen chat session")
        table.add_row("/clear", "Clear the terminal and redraw the dashboard")
        table.add_row("/exit", "Leave the Erasmus X terminal UI")
        self.console.print(table)

    def command_status(self, _: list[str]) -> None:
        self.state.remember("Rendered workspace status")
        self.console.print(self.status_panel())

    def command_files(self, _: list[str]) -> None:
        self.refresh_active_modules()
        self.state.remember("Refreshed active module map")
        self.console.print(self.active_files_panel())

    def command_run(self, args: list[str]) -> None:
        target = args[0].lower() if args else "demo"

        if target == "scan":
            self.refresh_active_modules()
            self.state.remember("Scanned project modules")
            self.print_response("Scan complete", f"{len(self.state.active_modules)} active modules are tracked.")
            return

        if target == "boot":
            py_files = len(list(self.root.rglob("*.py")))
            self.state.remember("Streamed workspace boot activity")
            self.stream_activity(
                [
                    f"[+] Loaded neurosymbolic agent workspace ({py_files} modules)...",
                    "    indexing embeddings...",
                    "    syncing orchestration graph...",
                    "    mapping active tools...",
                ]
            )
            self._ensure_agent()
            self.console.print("[green]    Erasmus X control surface ready.[/green]")
            return

        if target == "agent":
            self._ensure_agent()
            self.state.remember("Streamed agent orchestration trace")
            self.stream_activity(
                [
                    f"[+] Spawning local planning agent (status: {self.state.live_status})...",
                    "    reading active module graph...",
                    "    selecting implementation path...",
                    "    preparing verification loop...",
                    "    agent handoff complete.",
                ]
            )
            return

            return

        if target == "tests":
            self.run_tests()
            return

        run_prefix = f"/run {target}"
        suggestions = self.command_suggestions(run_prefix)
        if suggestions:
            self.print_suggestions(run_prefix, suggestions)
            return

        self.print_response("Run target unavailable", "Use `/run agent`, `/run demo`, `/run scan`, `/run boot`, `/run pulse`, or `/run tests`.", style="yellow")

    def run_tests(self) -> None:
        test_runner = self.root / "test" / "run_all_tests.py"
        if not test_runner.exists():
            self.print_response("Tests unavailable", "Could not find test/run_all_tests.py.", style="yellow")
            return

        self.console.print(Panel(self.status_text("indexing", "yellow"), title="Running local test harness", box=box.ROUNDED, border_style=self.state.command_border))
        completed = subprocess.run(
            [sys.executable, str(test_runner)],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=False,
        )
        output = (completed.stdout or completed.stderr or "No output captured.").strip()
        style = "green" if completed.returncode == 0 else "red"
        self.state.remember(f"Test harness exited with code {completed.returncode}")
        self.print_response(f"Test result: {completed.returncode}", output[-3000:], style=style)

    def command_clear(self, _: list[str]) -> None:
        os.system("cls" if os.name == "nt" else "clear")
        if self.state.commands_run:
            self.render_dashboard()

    def command_chat(self, _: list[str]) -> None:
        self.state.remember("Opened dedicated chat session")
        self._ensure_agent()
        os.system("cls" if os.name == "nt" else "clear")
        
        self.console.print(self.header_panel())
        self.console.print()
        self.console.print("[dim]Type your message below. Type [bold]/exit[/bold] to return to the dashboard.[/dim]\n")
        
        while self.running:
            try:
                prompt = Text("chat", style=f"bold {self.state.accent}")
                prompt.append(" > ", style="dim")
                raw = Prompt.ask(prompt, console=self.console).strip()
            except (EOFError, KeyboardInterrupt):
                break
                
            if not raw:
                continue
            if raw.lower() in ["/exit", "/quit"]:
                break
                
            if self.agent:
                try:
                    streamed_text = Text("", style="green")
                    panel = Panel(streamed_text, title="Erasmus X (thinking...)", box=box.ROUNDED, border_style=self.state.command_border, padding=(1, 2))
                    
                    with Live(panel, console=self.console, refresh_per_second=15, transient=True) as live:
                        def live_update_callback(chunk: str):
                            streamed_text.append(chunk)
                            live.update(Panel(streamed_text, title="Erasmus X (thinking...)", box=box.ROUNDED, border_style=self.state.command_border, padding=(1, 2)))

                        result = self.agent.chat(raw, stream_callback=live_update_callback)

                    raw_response, clean_ans = result
                    response_text = clean_ans if clean_ans else raw_response
                    self.print_response("Erasmus X", response_text, style="green")
                    
                    self.state.commands_run += 1
                    if self.state.commands_run % 3 == 0 and self.brain:
                        self.brain.save()
                except Exception as e:
                    self.print_response("Error", str(e), style="red")
            else:
                self.console.print("[red]Agent is not connected.[/red]")
                
        # Return to main dashboard
        self.command_clear([])

    def command_exit(self, _: list[str]) -> None:
        self.running = False
        if self.brain:
            with self.console.status("Persisting Brain before exit..."):
                self.brain.save()
        self.console.print(Panel("Session closed. Erasmus X control surface offline.", box=box.ROUNDED, border_style=self.state.panel_border))

    def print_response(self, title: str, message: str, style: str = "white", stream: bool = False) -> None:
        if stream:
            self.stream_response(title, message, style)
            return
        body = Text(message, style=style)
        border = self.state.command_border if style == "white" else style
        self.console.print(Panel(body, title=title, box=box.ROUNDED, border_style=border, padding=(1, 2)))

    def stream_response(self, title: str, message: str, style: str = "white") -> None:
        streamed = Text("", style=style)
        panel = Panel(streamed, title=title, box=box.ROUNDED, border_style=self.state.command_border, padding=(1, 2))
        with Live(panel, console=self.console, refresh_per_second=30, transient=False) as live:
            for character in message:
                streamed.append(character)
                live.update(Panel(streamed, title=title, box=box.ROUNDED, border_style=self.state.command_border, padding=(1, 2)))
                time.sleep(0.008)

    def stream_activity(self, lines: list[str]) -> None:
        streamed = Text()
        panel = Panel(streamed, title="Streaming Activity", box=box.ROUNDED, border_style=self.state.command_border, padding=(1, 2))
        with Live(panel, console=self.console, refresh_per_second=30, transient=False) as live:
            for line in lines:
                line_style = self.state.accent if line.startswith("[+]") else "dim"
                for character in line:
                    streamed.append(character, style=line_style)
                    live.update(Panel(streamed, title="Streaming Activity", box=box.ROUNDED, border_style=self.state.command_border, padding=(1, 2)))
                    time.sleep(0.006)
                streamed.append("\n")
                time.sleep(0.16)

    def command_suggestions(self, raw: str) -> list[str]:
        options = [
            "/help",
            "/status",
            "/run tests",
            "/run scan",
            "/run agent",
            "/run boot",
            "/run pulse",
            "/files",
            "/chat",
            "/clear",
            "/exit",
        ]
        return [option for option in options if option.startswith(raw.lower())][:5]

    def print_suggestions(self, raw: str, suggestions: list[str]) -> None:
        table = Table.grid(padding=(0, 1))
        table.add_column("hint", style="dim")
        table.add_column("command", style=f"bold {self.state.accent}")
        for suggestion in suggestions:
            table.add_row("suggestion", suggestion)
        self.console.print(Panel(table, title=f"Autocomplete: {raw}", box=box.ROUNDED, border_style=self.state.command_border, padding=(1, 2)))

    def pulse_status(self) -> None:
        frames = [
            ("● online", "dim green"),
            ("● online", "green"),
            ("● online", "bold green"),
            ("● online", "green"),
        ]
        with Live(console=self.console, refresh_per_second=8, transient=False) as live:
            for index in range(16):
                label, style = frames[index % len(frames)]
                live.update(Panel(Text(label, style=style), title="Status Pulse", box=box.ROUNDED, border_style=self.state.command_border, padding=(1, 2)))
                time.sleep(0.12)


def main() -> None:
    ErasmusTerminalUI().run()


if __name__ == "__main__":
    main()
