"""
Applies resolved conflict content back to disk and stages the files.
Safety-critical — never writes without user confirmation.
"""
from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from typing import Optional

from rich.text import Text

from git_wtf import ui
from git_wtf.collectors.conflict import ConflictFile

console = ui.console


@dataclass
class FileResolution:
    """Holds the resolved content for one file, ready to be written."""
    conflict_file: ConflictFile
    resolved_hunks: list[str]
    intent: str
    confidence: str
    warning: Optional[str]


def build_resolved_content(
    conflict_file: ConflictFile,
    resolved_hunks: list[str],
) -> str:
    """
    Reconstructs the full file by replacing each conflict region with its
    resolved hunk. Replaces from last to first so line indices stay valid.
    """
    n_conflicts = len(conflict_file.hunks)
    n_resolved  = len(resolved_hunks)

    if n_resolved != n_conflicts:
        raise ValueError(
            f"{conflict_file.path}: got {n_resolved} resolved hunks "
            f"but file has {n_conflicts} conflict(s)"
        )

    lines = conflict_file.working_tree_content.splitlines(keepends=True)
    regions: list[tuple[int, int, str]] = []

    CONFLICT_START = re.compile(r"^<{7}")
    CONFLICT_END   = re.compile(r"^>{7}")

    i = hunk_idx = 0
    while i < len(lines):
        if CONFLICT_START.match(lines[i]):
            start = i
            while i < len(lines) and not CONFLICT_END.match(lines[i]):
                i += 1
            end = i
            resolved_text = resolved_hunks[hunk_idx].rstrip("\n") + "\n"
            regions.append((start, end, resolved_text))
            hunk_idx += 1
        i += 1

    for start, end, resolved_text in reversed(regions):
        lines[start : end + 1] = [resolved_text]

    return "".join(lines)


def apply_resolutions(
    resolutions: list[FileResolution],
    cwd: Optional[str] = None,
) -> bool:
    """Write resolved files to disk and `git add` them. Returns True on success."""
    success = True

    for res in resolutions:
        filepath = res.conflict_file.path
        abs_path = os.path.join(cwd, filepath) if cwd else filepath

        try:
            resolved_content = build_resolved_content(
                res.conflict_file,
                res.resolved_hunks,
            )
        except ValueError as e:
            ui.error_msg(str(e))
            success = False
            continue

        try:
            with open(abs_path, "w", encoding="utf-8") as f:
                f.write(resolved_content)
        except OSError as e:
            ui.error_msg(f"write failed for {filepath}: {e}")
            success = False
            continue

        result = subprocess.run(
            ["git", "add", filepath],
            capture_output=True, text=True, cwd=cwd,
        )
        if result.returncode != 0:
            ui.error_msg(f"git add failed for {filepath}: {result.stderr.strip()}")
            success = False
        else:
            row = Text()
            row.append("  ✓  ", style="bold green")
            row.append(filepath, style="bold cyan")
            row.append("  staged", style="dim")
            console.print(row)

    return success


def show_diff_preview(
    resolutions: list[FileResolution],
    cwd: Optional[str] = None,
) -> None:
    """Show intent + confidence panel per file. No raw diffs — readable for everyone."""
    for res in resolutions:
        ui.intent_panel(
            path=res.conflict_file.path,
            intent=res.intent,
            confidence=res.confidence,
            n_hunks=len(res.conflict_file.hunks),
            warning=res.warning,
        )
    console.print()
