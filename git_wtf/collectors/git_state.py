"""
Runs git commands and collects repo state.
Everything git knows, we know.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from typing import Optional


def _run(cmd: list[str], cwd: Optional[str] = None) -> str:
    """Run a git command, return stdout. Empty string on failure."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd,
        )
        if result.returncode != 0:
            return ""
        return result.stdout.strip()
    except Exception:
        return ""


def _run_lines(cmd: list[str], cwd: Optional[str] = None) -> list[str]:
    out = _run(cmd, cwd)
    return [l for l in out.splitlines() if l.strip()] if out else []


@dataclass
class BranchInfo:
    current: str
    tracking: Optional[str]
    ahead: int
    behind: int
    is_detached: bool


@dataclass
class MergeInfo:
    in_progress: bool
    merge_head: Optional[str]          # SHA of MERGE_HEAD
    merge_head_branch: Optional[str]   # human name if resolvable
    our_branch: Optional[str]
    our_commits: list[str] = field(default_factory=list)   # commit summaries unique to ours
    their_commits: list[str] = field(default_factory=list) # commit summaries unique to theirs


@dataclass
class RepoState:
    branch: BranchInfo
    merge: MergeInfo
    status_porcelain: str          # raw `git status --porcelain`
    conflicted_files: list[str]
    recent_log: list[str]          # last 10 commit onelines
    has_staged: bool
    has_unstaged: bool
    has_untracked: bool
    rebase_in_progress: bool
    cherry_pick_in_progress: bool


def collect(cwd: Optional[str] = None) -> RepoState:
    """Collect full repo state. This is the single source of truth."""

    # ── branch ──────────────────────────────────────────────────────────────
    head_ref = _run(["git", "symbolic-ref", "--short", "HEAD"], cwd)
    is_detached = head_ref == ""
    if is_detached:
        head_ref = _run(["git", "rev-parse", "--short", "HEAD"], cwd) + " (detached)"

    tracking = _run(
        ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], cwd
    ) or None

    ahead = behind = 0
    if tracking:
        counts = _run(["git", "rev-list", "--left-right", "--count", "HEAD...@{u}"], cwd)
        if counts:
            parts = counts.split()
            if len(parts) == 2:
                ahead, behind = int(parts[0]), int(parts[1])

    branch = BranchInfo(
        current=head_ref,
        tracking=tracking,
        ahead=ahead,
        behind=behind,
        is_detached=is_detached,
    )

    # ── merge state ──────────────────────────────────────────────────────────
    merge_head_sha = _run(["git", "rev-parse", "MERGE_HEAD"], cwd)
    in_merge = bool(merge_head_sha)

    merge_head_branch = None
    our_commits: list[str] = []
    their_commits: list[str] = []

    if in_merge:
        # Try to get a human-readable name for MERGE_HEAD
        merge_head_branch = _run(
            ["git", "name-rev", "--name-only", merge_head_sha], cwd
        ) or merge_head_sha[:8]

        our_commits = _run_lines(
            ["git", "log", "HEAD", "--not", "MERGE_HEAD", "--oneline", "--max-count=10"], cwd
        )
        their_commits = _run_lines(
            ["git", "log", "MERGE_HEAD", "--not", "HEAD", "--oneline", "--max-count=10"], cwd
        )

    merge = MergeInfo(
        in_progress=in_merge,
        merge_head=merge_head_sha or None,
        merge_head_branch=merge_head_branch,
        our_branch=head_ref if not is_detached else None,
        our_commits=our_commits,
        their_commits=their_commits,
    )

    # ── status ───────────────────────────────────────────────────────────────
    status_porcelain = _run(["git", "status", "--porcelain=v1"], cwd)
    lines = status_porcelain.splitlines()

    conflicted_files = []
    has_staged = False
    has_unstaged = False
    has_untracked = False

    for line in lines:
        if len(line) < 2:
            continue
        xy = line[:2]
        fname = line[3:]
        x, y = xy[0], xy[1]

        # conflict codes
        if xy in ("DD", "AU", "UD", "UA", "DU", "AA", "UU"):
            conflicted_files.append(fname.strip())
        elif x != " " and x != "?" and x != "!":
            has_staged = True
        elif y != " " and y != "?" and y != "!":
            has_unstaged = True

        if xy.startswith("??"):
            has_untracked = True

    # ── recent log ───────────────────────────────────────────────────────────
    recent_log = _run_lines(
        ["git", "log", "--oneline", "--max-count=10"], cwd
    )

    # ── special states ───────────────────────────────────────────────────────
    rebase_in_progress = bool(
        _run(["git", "rev-parse", "--git-dir"], cwd)
        and _run(["git", "rev-parse", "--verify", "REBASE_HEAD"], cwd)
    )
    cherry_pick_in_progress = bool(
        _run(["git", "rev-parse", "--verify", "CHERRY_PICK_HEAD"], cwd)
    )

    return RepoState(
        branch=branch,
        merge=merge,
        status_porcelain=status_porcelain,
        conflicted_files=conflicted_files,
        recent_log=recent_log,
        has_staged=has_staged,
        has_unstaged=has_unstaged,
        has_untracked=has_untracked,
        rebase_in_progress=rebase_in_progress,
        cherry_pick_in_progress=cherry_pick_in_progress,
    )
