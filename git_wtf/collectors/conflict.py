"""
Parses conflict markers and extracts the three versions of each hunk.

Git stores three blob stages in the index during a merge:
  :1:<file>  → common ancestor
  :2:<file>  → ours (HEAD)
  :3:<file>  → theirs (MERGE_HEAD)

We use those for full-file context and parse the working-tree file
for the individual conflict hunks + surrounding lines.
"""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from typing import Optional


CONFLICT_START = re.compile(r"^<{7}(?:\s+(.+))?$")
CONFLICT_SEP   = re.compile(r"^={7}$")
CONFLICT_END   = re.compile(r"^>{7}(?:\s+(.+))?$")
CONTEXT_LINES  = 20  # lines of surrounding context to include per hunk


def _git_blob(stage: int, filepath: str, cwd: Optional[str] = None) -> str:
    """Read a file at a given merge stage (1=ancestor, 2=ours, 3=theirs)."""
    try:
        result = subprocess.run(
            ["git", "show", f":{stage}:{filepath}"],
            capture_output=True,
            text=True,
            cwd=cwd,
        )
        return result.stdout if result.returncode == 0 else ""
    except Exception:
        return ""


@dataclass
class ConflictHunk:
    index: int                  # 1-based hunk number within the file
    ours_label: str             # branch label from <<<<<<< line
    theirs_label: str           # branch label from >>>>>>> line
    ours_lines: list[str]       # lines from HEAD side
    theirs_lines: list[str]     # lines from MERGE_HEAD side
    context_before: list[str]   # lines before conflict marker
    context_after: list[str]    # lines after conflict end marker
    start_line: int             # line number in working tree file (1-based)


@dataclass
class ConflictFile:
    path: str
    hunks: list[ConflictHunk]
    ancestor_content: str       # :1: blob (common ancestor)
    ours_content: str           # :2: blob (our full version)
    theirs_content: str         # :3: blob (their full version)
    working_tree_content: str   # current file with conflict markers


def parse_file(filepath: str, cwd: Optional[str] = None) -> ConflictFile:
    """Parse a conflicted file and return all hunks with context."""
    # Read working tree version with conflict markers
    try:
        abs_path = filepath if cwd is None else f"{cwd}/{filepath}"
        with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
            working_content = f.read()
    except OSError:
        working_content = ""

    lines = working_content.splitlines()
    hunks: list[ConflictHunk] = []

    i = 0
    hunk_index = 1

    while i < len(lines):
        m_start = CONFLICT_START.match(lines[i])
        if not m_start:
            i += 1
            continue

        ours_label = m_start.group(1) or "HEAD"
        start_line = i + 1  # 1-based

        # Collect context before
        ctx_start = max(0, i - CONTEXT_LINES)
        context_before = lines[ctx_start:i]

        # Collect ours lines
        ours_lines: list[str] = []
        i += 1
        while i < len(lines) and not CONFLICT_SEP.match(lines[i]):
            ours_lines.append(lines[i])
            i += 1

        # Skip separator
        if i < len(lines):
            i += 1

        # Collect theirs lines
        theirs_lines: list[str] = []
        theirs_label = "MERGE_HEAD"
        while i < len(lines):
            m_end = CONFLICT_END.match(lines[i])
            if m_end:
                theirs_label = m_end.group(1) or "MERGE_HEAD"
                i += 1
                break
            theirs_lines.append(lines[i])
            i += 1

        # Collect context after
        ctx_end = min(len(lines), i + CONTEXT_LINES)
        context_after = lines[i:ctx_end]

        hunks.append(ConflictHunk(
            index=hunk_index,
            ours_label=ours_label,
            theirs_label=theirs_label,
            ours_lines=ours_lines,
            theirs_lines=theirs_lines,
            context_before=context_before,
            context_after=context_after,
            start_line=start_line,
        ))
        hunk_index += 1

    # Fetch the three blob versions
    ancestor = _git_blob(1, filepath, cwd)
    ours     = _git_blob(2, filepath, cwd)
    theirs   = _git_blob(3, filepath, cwd)

    return ConflictFile(
        path=filepath,
        hunks=hunks,
        ancestor_content=ancestor,
        ours_content=ours,
        theirs_content=theirs,
        working_tree_content=working_content,
    )


def parse_all(conflicted_files: list[str], cwd: Optional[str] = None) -> list[ConflictFile]:
    """Parse all conflicted files. Returns list in same order."""
    return [parse_file(f, cwd) for f in conflicted_files]
