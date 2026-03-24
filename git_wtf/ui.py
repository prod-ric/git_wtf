"""
Shared UI helpers — all Rich styling lives here.
One import gives you everything you need for consistent output.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Optional

from rich.columns import Columns
from rich.console import Console
from rich.markdown import Markdown
from rich.padding import Padding
from rich.panel import Panel
from rich.rule import Rule
from rich.spinner import Spinner
from rich.style import Style
from rich.text import Text
from rich.theme import Theme

# ── colour palette ────────────────────────────────────────────────────────────
# Keep it tight — four semantic colours + accent.
BRAND   = "bold cyan"          # git-wtf identity
SUCCESS = "bold green"
WARN    = "bold yellow"
ERROR   = "bold red"
MUTED   = "dim"
ACCENT  = "cyan"               # highlights, branch names, file paths

CONFIDENCE_COLOR = {
    "HIGH":   "green",
    "MEDIUM": "yellow",
    "LOW":    "red",
}

# ── singleton console ─────────────────────────────────────────────────────────
console = Console(
    theme=Theme({
        "info":    "cyan",
        "success": "bold green",
        "warn":    "bold yellow",
        "error":   "bold red",
        "muted":   "dim",
        "brand":   "bold cyan",
        "accent":  "cyan",
    }),
    highlight=False,   # don't auto-highlight numbers, strings, etc.
)


# ── logo ──────────────────────────────────────────────────────────────────────

LOGO = """\
 __ _(_) |_  __ _____ __
/ _` | |  _| \\ V V / '_ \\
\\__, |_|\\__|  \\_/\\_/ | .__/
|___/               |_|"""


def print_logo() -> None:
    console.print(Text(LOGO, style="bold cyan"))
    console.print()


# ── section rules ─────────────────────────────────────────────────────────────

def rule(title: str = "", style: str = "cyan") -> None:
    if title:
        console.print(Rule(f"[{style}]{title}[/{style}]", style="dim"))
    else:
        console.print(Rule(style="dim"))


# ── badges ────────────────────────────────────────────────────────────────────

def badge(text: str, color: str) -> Text:
    """Inline coloured badge."""
    t = Text()
    t.append(f" {text} ", style=f"bold {color} on {color}4" )
    return t


def confidence_badge(level: str) -> Text:
    """Styled confidence badge — HIGH / MEDIUM / LOW."""
    color = CONFIDENCE_COLOR.get(level.upper(), "white")
    styles = {
        "HIGH":   Style(color="black", bgcolor="green",  bold=True),
        "MEDIUM": Style(color="black", bgcolor="yellow", bold=True),
        "LOW":    Style(color="white", bgcolor="red",    bold=True),
    }
    t = Text()
    t.append(f" {level.upper()} ", style=styles.get(level.upper(), Style(bold=True)))
    return t


def file_badge(path: str) -> Text:
    t = Text()
    t.append("  ")
    t.append(path, style="bold cyan")
    return t


# ── status spinner ────────────────────────────────────────────────────────────

@contextmanager
def spinner(msg: str):
    with console.status(f"[dim]{msg}[/dim]", spinner="dots"):
        yield


# ── LLM output rendering ──────────────────────────────────────────────────────

def stream_llm(client, system: str, user: str, spinner_msg: str = "thinking...") -> str:
    """
    Collect the full LLM response with a spinner, then render as Markdown.
    Looks much better than raw token streaming.
    """
    buffer = ""
    with console.status(f"[dim]{spinner_msg}[/dim]", spinner="dots"):
        buffer = client.stream(system, user)

    console.print()
    console.print(Markdown(buffer))
    console.print()
    return buffer


# ── panels ────────────────────────────────────────────────────────────────────

def intent_panel(
    path: str,
    intent: str,
    confidence: str,
    n_hunks: int,
    warning: Optional[str] = None,
) -> None:
    color = CONFIDENCE_COLOR.get(confidence.upper(), "white")

    title = Text()
    title.append(f" {path} ", style=f"bold")
    title.append("  ")
    cb = confidence_badge(confidence)
    title.append_text(cb)
    title.append(f"  {n_hunks} hunk{'s' if n_hunks != 1 else ''}", style="dim")

    body = Text.from_markup(intent)
    if warning:
        body.append("\n\n")
        body.append("⚠  ", style="bold yellow")
        body.append(warning, style="yellow")

    console.print(Panel(
        body,
        title=title,
        border_style=color,
        padding=(1, 2),
    ))


def summary_panel(summary: str) -> None:
    console.print(Panel(
        Markdown(summary.strip()),
        title=Text(" what this merge will do ", style="bold white on blue"),
        border_style="blue",
        padding=(1, 2),
    ))


def success_panel(msg: str) -> None:
    console.print(Panel(
        Text(msg, style="bold green"),
        border_style="green",
        padding=(0, 2),
    ))


def error_msg(msg: str) -> None:
    console.print(f"\n[bold red]✗[/bold red]  {msg}\n")


def warn_msg(msg: str) -> None:
    console.print(f"[bold yellow]⚠[/bold yellow]  {msg}")


def success_msg(msg: str) -> None:
    console.print(f"[bold green]✓[/bold green]  {msg}")


def info_msg(msg: str) -> None:
    console.print(f"[dim]→[/dim]  {msg}")


# ── state badges (for diagnose header) ───────────────────────────────────────

def state_pill(label: str, color: str) -> Text:
    t = Text()
    t.append(f" {label} ", style=f"bold {color} reverse")
    return t


def print_state_bar(state) -> None:
    """Print a row of coloured state pills based on repo state."""
    pills: list[Text] = []

    if state.branch.is_detached:
        pills.append(state_pill("DETACHED HEAD", "red"))
    if state.merge.in_progress:
        pills.append(state_pill("MID-MERGE", "yellow"))
    if state.rebase_in_progress:
        pills.append(state_pill("REBASE", "yellow"))
    if state.cherry_pick_in_progress:
        pills.append(state_pill("CHERRY-PICK", "yellow"))
    if state.conflicted_files:
        pills.append(state_pill(f"{len(state.conflicted_files)} CONFLICTS", "red"))
    if state.branch.behind > 0:
        pills.append(state_pill(f"↓ {state.branch.behind} behind", "yellow"))
    if state.branch.ahead > 0:
        pills.append(state_pill(f"↑ {state.branch.ahead} ahead", "cyan"))
    if state.has_staged:
        pills.append(state_pill("staged changes", "cyan"))
    if state.has_unstaged:
        pills.append(state_pill("unstaged changes", "dim"))

    if not pills:
        return

    row = Text("  ")
    for i, p in enumerate(pills):
        if i > 0:
            row.append("  ")
        row.append_text(p)

    console.print(row)
    console.print()
