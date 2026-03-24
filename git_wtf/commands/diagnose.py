"""
git wtf  — diagnose the current repo state.
"""
from __future__ import annotations

import subprocess

from git_wtf import ui
from git_wtf.collectors import context, git_state
from git_wtf.llm.client import LLMClient, NotConfiguredError
from git_wtf.llm.prompts import build_diagnose_prompt

console = ui.console


# ── chaos level (feat/chaos-level) ───────────────────────────────────────────

def _chaos_level(state) -> tuple[int, str]:
    """Score how bad the repo state is. 0 = clean, higher = worse."""
    score = 0
    if state.branch.is_detached:       score += 3
    if state.merge.in_progress:        score += 2
    if state.rebase_in_progress:       score += 2
    if state.cherry_pick_in_progress:  score += 1
    score += len(state.conflicted_files) * 2
    score += min(state.branch.behind, 10)
    if state.has_staged:               score += 1
    if state.has_unstaged:             score += 1

    if score == 0:   return 0, "all good"
    if score <= 2:   return score, "minor chaos"
    if score <= 5:   return score, "it's giving problems"
    if score <= 9:   return score, "bro what did you do"
    if score <= 14:  return score, "this is a lot"
    return score,    "legendary disaster"


# ── blame info (feat/blame) ───────────────────────────────────────────────────

def _get_blame_info(state) -> list[str]:
    """Who last touched the conflicted files + who initiated the merge."""
    lines = []

    if state.merge.in_progress and state.merge.merge_head:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%an <%ae> — %s", state.merge.merge_head],
            capture_output=True, text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            lines.append(f"merge initiated by: {result.stdout.strip()}")

    for filepath in state.conflicted_files[:5]:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%an — %ar", "--", filepath],
            capture_output=True, text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            lines.append(f"{filepath}: last touched by {result.stdout.strip()}")

    return lines


# ── main ──────────────────────────────────────────────────────────────────────

def run(
    cwd: str | None = None,
    show_chaos: bool = False,
    show_blame: bool = False,
) -> int:
    """Entry point for `git wtf`. Returns exit code."""

    with ui.spinner("reading your git state..."):
        try:
            state = git_state.collect(cwd)
        except Exception as e:
            ui.error_msg(f"couldn't read git state: {e}")
            return 1
        ctx = context.collect(cwd)

    ui.print_logo()

    console.print(
        f"  [bold cyan]{state.branch.current}[/bold cyan]"
        + (f"  [dim]→  {state.branch.tracking}[/dim]"
           if state.branch.tracking else "  [dim](no remote)[/dim]")
    )
    console.print()
    ui.print_state_bar(state)

    # chaos level
    score, label = _chaos_level(state)
    if show_chaos or score > 0:
        color = "green" if score == 0 else "yellow" if score <= 5 else "red"
        console.print(
            f"  chaos level  [bold {color}]{score}/10[/bold {color}]"
            f"  [dim]— {label}[/dim]\n"
        )

    # blame
    if show_blame and (state.merge.in_progress or state.conflicted_files):
        blame_lines = _get_blame_info(state)
        if blame_lines:
            console.print("  [bold]who did this:[/bold]")
            for line in blame_lines:
                console.print(f"  [dim]→[/dim]  [yellow]{line}[/yellow]")
            console.print()

    # clean?
    no_issues = score == 0
    if no_issues:
        ui.success_msg("repo is clean. nothing to diagnose. go ship something.")
        console.print()
        return 0

    try:
        client = LLMClient()
    except NotConfiguredError:
        ui.error_msg("not configured. run: [bold]git wtf setup[/bold]")
        return 1

    ui.rule("diagnosis")
    system, user = build_diagnose_prompt(state, ctx)

    try:
        ui.stream_llm(client, system, user, spinner_msg="figuring out what happened...")
    except Exception as e:
        ui.error_msg(f"LLM call failed: {e}")
        return 1

    return 0
