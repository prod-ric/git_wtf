"""
git wtf merge  — semantic merge conflict resolution.

Flow:
  1. Collect git state + conflicted files
  2. For each file: ask LLM to resolve + explain intent
  3. Show per-file confidence panels
  4. Generate a high-level plain-English summary of the full merge
  5. Ask the user Y/n — nothing touches disk before this
  6. Apply on Y, bail on N
"""
from __future__ import annotations

from typing import Optional

from rich.text import Text

from git_wtf import ui
from git_wtf.collectors import conflict as conflict_collector
from git_wtf.collectors import context, git_state
from git_wtf.llm.client import LLMClient, NotConfiguredError, extract_all_blocks, extract_block
from git_wtf.llm.prompts import build_merge_file_prompt, build_merge_summary_prompt
from git_wtf.resolver import FileResolution, apply_resolutions, show_diff_preview

console = ui.console


def run(cwd: Optional[str] = None) -> int:
    """Entry point for `git wtf merge`. Returns exit code."""

    # ── collect ──────────────────────────────────────────────────────────────
    with ui.spinner("reading your git state..."):
        try:
            state = git_state.collect(cwd)
        except Exception as e:
            ui.error_msg(f"couldn't read git state: {e}")
            return 1
        ctx = context.collect(cwd)

    # ── guards ────────────────────────────────────────────────────────────────
    if not state.merge.in_progress and not state.conflicted_files:
        ui.print_logo()
        ui.warn_msg(
            "no merge in progress and no conflicts found.\n"
            "   run [bold]git merge <branch>[/bold] first, then come back."
        )
        console.print()
        return 1

    if not state.conflicted_files:
        ui.print_logo()
        ui.success_msg(
            "merge is in progress but there are no conflicts.\n"
            "   run [bold]git merge --continue[/bold] or [bold]git commit[/bold] to finish."
        )
        console.print()
        return 0

    # ── header ────────────────────────────────────────────────────────────────
    their_branch = state.merge.merge_head_branch or "MERGE_HEAD"
    our_branch   = state.merge.our_branch or "HEAD"
    n_files      = len(state.conflicted_files)

    ui.print_logo()
    ui.rule("merge conflict")
    console.print()
    console.print(
        f"  [bold cyan]{our_branch}[/bold cyan]"
        f"  [dim]+[/dim]  "
        f"[bold cyan]{their_branch}[/bold cyan]"
        f"  [dim]→[/dim]  "
        f"[bold]{n_files} conflicted file{'s' if n_files != 1 else ''}[/bold]"
    )
    console.print()

    # ── init LLM ─────────────────────────────────────────────────────────────
    try:
        client = LLMClient()
    except NotConfiguredError:
        ui.error_msg("not configured. run: [bold]git wtf setup[/bold]")
        return 1

    # ── parse conflict files ──────────────────────────────────────────────────
    with ui.spinner("parsing conflict markers..."):
        conflict_files = conflict_collector.parse_all(state.conflicted_files, cwd)

    # ── resolve each file ─────────────────────────────────────────────────────
    resolutions: list[FileResolution] = []
    file_summaries: list[dict] = []

    for i, cf in enumerate(conflict_files, 1):
        n_hunks = len(cf.hunks)

        console.print(
            f"  [dim]({i}/{n_files})[/dim]  "
            f"[bold cyan]{cf.path}[/bold cyan]  "
            f"[dim]{n_hunks} hunk{'s' if n_hunks != 1 else ''}[/dim]"
        )

        system, user = build_merge_file_prompt(cf, state, ctx)

        try:
            with ui.spinner(f"reading both sides of {cf.path}..."):
                response = client.complete(system, user)
        except Exception as e:
            ui.warn_msg(f"LLM failed on {cf.path} — skipping, resolve manually")
            ui.info_msg(str(e))
            continue

        # Parse blocks
        resolved_hunks = extract_all_blocks(response, "resolved")
        intent         = extract_block(response, "intent") or "(no intent summary returned)"
        confidence_raw = extract_block(response, "confidence") or "MEDIUM"
        warning        = extract_block(response, "warning")
        confidence     = _parse_confidence(confidence_raw)

        # Hunk count must match
        if len(resolved_hunks) != n_hunks:
            ui.warn_msg(
                f"got {len(resolved_hunks)} resolved hunks, expected {n_hunks} — "
                f"skipping {cf.path}, resolve manually"
            )
            continue

        resolution = FileResolution(
            conflict_file=cf,
            resolved_hunks=resolved_hunks,
            intent=intent.strip(),
            confidence=confidence,
            warning=warning.strip() if warning else None,
        )
        resolutions.append(resolution)
        file_summaries.append({
            "path":       cf.path,
            "intent":     intent.strip(),
            "confidence": confidence,
            "warning":    warning.strip() if warning else None,
        })

        conf_badge = ui.confidence_badge(confidence)
        row = Text("       ")
        row.append_text(conf_badge)
        console.print(row)

    console.print()

    if not resolutions:
        ui.error_msg("couldn't resolve any files automatically — all need manual resolution.")
        return 1

    # ── per-file intent panels ────────────────────────────────────────────────
    ui.rule("what i'm about to change")
    console.print()
    show_diff_preview(resolutions, cwd)

    # ── full-merge summary ────────────────────────────────────────────────────
    ui.rule("the big picture")
    console.print()

    system_s, user_s = build_merge_summary_prompt(file_summaries, state, ctx)
    try:
        with ui.spinner("writing merge summary..."):
            summary_response = client.complete(system_s, user_s)
        summary = extract_block(summary_response, "summary") or summary_response
    except Exception:
        summary = "_(summary generation failed — review the per-file panels above)_"

    ui.summary_panel(summary)
    console.print()

    # ── low-confidence warning ────────────────────────────────────────────────
    low_confidence = [r for r in resolutions if r.confidence == "LOW"]
    if low_confidence:
        ui.warn_msg(
            f"{len(low_confidence)} file(s) have [bold]LOW[/bold] confidence. "
            f"seriously review those before confirming."
        )
        console.print()

    # ── stats line ───────────────────────────────────────────────────────────
    n_resolved = len(resolutions)
    n_skipped  = len(conflict_files) - n_resolved

    resolved_txt = Text()
    resolved_txt.append(f"  {n_resolved} file{'s' if n_resolved != 1 else ''} resolved", style="bold green")
    if n_skipped:
        resolved_txt.append(f"  ·  {n_skipped} skipped", style="bold yellow")
    resolved_txt.append("  ·  nothing written to disk yet", style="dim")
    console.print(resolved_txt)
    console.print()

    # ── confirm ───────────────────────────────────────────────────────────────
    try:
        answer = console.input(
            "  [bold]apply this merge?[/bold] [dim][Y/n][/dim]  "
        ).strip().lower()
    except (KeyboardInterrupt, EOFError):
        console.print()
        ui.info_msg("bailed. nothing was touched.")
        console.print()
        return 0

    if answer not in ("", "y", "yes"):
        console.print()
        ui.info_msg("no worries. nothing was touched.")
        console.print()
        return 0

    # ── apply ─────────────────────────────────────────────────────────────────
    console.print()
    ui.rule("applying")
    console.print()

    ok = apply_resolutions(resolutions, cwd)

    console.print()
    if ok:
        if n_skipped:
            ui.success_msg(f"{n_resolved} file(s) resolved and staged.")
            ui.warn_msg(
                f"{n_skipped} file(s) still need manual resolution — "
                f"fix them, then [bold]git merge --continue[/bold]."
            )
        else:
            ui.success_msg(f"all {n_resolved} file(s) resolved and staged.")
            ui.info_msg("run [bold]git merge --continue[/bold] (or [bold]git commit[/bold]) to finish.")
        console.print()
        return 0
    else:
        ui.error_msg("something went wrong during apply. check git status.")
        return 1


def _parse_confidence(raw: str) -> str:
    raw = raw.strip().upper()
    for level in ("HIGH", "MEDIUM", "LOW"):
        if level in raw:
            return level
    return "MEDIUM"
