"""
Prompt templates.

Tone: like your most competent dev friend who also spends way too much
time on reels. Knows everything, explains it like you're both in on the joke.
No corporate speak. No "certainly!". Just vibes + clarity.
"""
from __future__ import annotations

from git_wtf.collectors.conflict import ConflictFile
from git_wtf.collectors.context import ProjectContext
from git_wtf.collectors.git_state import RepoState


# ── Shared system prompt ─────────────────────────────────────────────────────

SYSTEM_BASE = """\
You are git-wtf — an AI git assistant built for vibe coders who are moving fast, \
using AI tools to build, and genuinely do not have time to read 400 lines of merge conflict \
on code they didn't write.

Your tone: you're the dev friend who actually knows git inside out, \
but you explain it like you're both scrolling reels between builds. \
Casual, clear, a little funny — but never at the expense of accuracy. \
No "certainly!", no "great question!", no corporate filler. \
Short sentences. Get to the point fast. \
Use phrases like "ok so basically", "ngl", "no cap", "it's giving", \
"bro", "lowkey", "the move here is", "slay" (sparingly) — \
but ONLY when it doesn't make the explanation harder to follow. \
Accuracy is non-negotiable. Vibes are the bonus.
"""


# ── DIAGNOSE prompt ──────────────────────────────────────────────────────────

def build_diagnose_prompt(state: RepoState, ctx: ProjectContext) -> tuple[str, str]:
    """Returns (system, user) tuple for the diagnose command."""

    system = SYSTEM_BASE + """
For this task you are diagnosing the current git state. Your job:
1. Explain in plain English what state the repo is in right now
2. Explain how it got there (likely cause, based on the evidence)
3. Give the exact commands to get out of it, in order
4. Flag anything the user should be careful about

Format your response as:
## what happened
[explanation]

## how to fix it
[numbered list of exact commands with one-line explanations]

## heads up
[any warnings, edge cases, or things they might lose — or omit this section if there's nothing scary]

Keep it tight. The dev is probably mid-task.
"""

    project_block = _project_context_block(ctx)
    status_block = f"```\n{state.status_porcelain or '(clean)'}\n```"
    log_block = "\n".join(state.recent_log) or "(no commits yet)"

    flags: list[str] = []
    if state.branch.is_detached:
        flags.append("DETACHED HEAD")
    if state.merge.in_progress:
        flags.append(f"MID-MERGE (merging {state.merge.merge_head_branch})")
    if state.rebase_in_progress:
        flags.append("REBASE IN PROGRESS")
    if state.cherry_pick_in_progress:
        flags.append("CHERRY-PICK IN PROGRESS")
    if state.branch.behind > 0:
        flags.append(f"BEHIND REMOTE by {state.branch.behind} commits")
    if state.branch.ahead > 0:
        flags.append(f"AHEAD of remote by {state.branch.ahead} commits")
    if state.conflicted_files:
        files_list = "\n".join(f"  - {f}" for f in state.conflicted_files)
        flags.append(f"CONFLICTED FILES:\n{files_list}")

    flags_block = "\n".join(flags) if flags else "None detected — might actually be fine"

    user = f"""\
{project_block}

## current branch
{state.branch.current}{"  ← detached HEAD!" if state.branch.is_detached else ""}
tracking: {state.branch.tracking or "none"}

## detected states
{flags_block}

## git status
{status_block}

## recent commits
{log_block}

Diagnose this and tell me what's going on + exactly what to do.
"""
    return system, user


# ── MERGE / per-file resolution prompt ───────────────────────────────────────

def build_merge_file_prompt(
    conflict_file: ConflictFile,
    state: RepoState,
    ctx: ProjectContext,
) -> tuple[str, str]:
    """
    Returns (system, user) for resolving one conflicted file.

    The LLM must return:
      - For each hunk: a ```resolved``` block with the merged code
      - An ```intent``` block summarising what this file now does
      - A ```confidence``` block: HIGH / MEDIUM / LOW + one-line reason
    """

    system = SYSTEM_BASE + """
For this task you are resolving merge conflicts in a single file.

Rules (non-negotiable):
1. Your goal is to preserve BOTH intents — not pick a winner.
2. If the two sides are truly incompatible and you cannot keep both, say so \
explicitly in the confidence block. Do NOT silently drop one intent.
3. Return one ```resolved``` fenced block per conflict hunk, IN ORDER.
4. Return one ```intent``` block describing what this file does after the merge \
in plain English — what does it DO, not what code changed.
5. Return one ```confidence``` block: HIGH, MEDIUM, or LOW, and a one-sentence reason.

CRITICAL — what goes inside each ```resolved``` block:
- The resolved block replaces EXACTLY the content between (and including) the \
<<<<<<< and >>>>>>> markers in the working tree.
- Do NOT include lines from "context before" or "context after" in the resolved block. \
Those lines already exist in the file and will NOT be replaced.
- Only include the lines that should appear in place of the entire conflict region \
(from <<<<<<< to >>>>>>> inclusive).

If confidence is LOW, add a ```warning``` block explaining what the human \
should double-check manually.

Do not explain your reasoning outside of these blocks — \
the output is parsed programmatically. \
Put any human-readable commentary INSIDE the intent block.
"""

    project_block = _project_context_block(ctx)

    our_branch   = state.merge.our_branch or "HEAD"
    their_branch = state.merge.merge_head_branch or "MERGE_HEAD"

    our_commits_block = "\n".join(
        f"  {c}" for c in (state.merge.our_commits or ["(no commits found)"])
    )
    their_commits_block = "\n".join(
        f"  {c}" for c in (state.merge.their_commits or ["(no commits found)"])
    )

    hunks_block = _format_hunks(conflict_file)

    user = f"""\
{project_block}

## what's being merged
YOUR branch ({our_branch}) recent commits:
{our_commits_block}

THEIR branch ({their_branch}) recent commits:
{their_commits_block}

## file being resolved
{conflict_file.path}

## conflict hunks ({len(conflict_file.hunks)} total)
{hunks_block}

## full file — your version (HEAD / :2:)
```
{conflict_file.ours_content or "(empty)"}
```

## full file — their version (MERGE_HEAD / :3:)
```
{conflict_file.theirs_content or "(empty)"}
```

## common ancestor (:1:)
```
{conflict_file.ancestor_content or "(empty or new file)"}
```

Resolve every conflict hunk. Return one ```resolved``` block per hunk (in order), \
one ```intent``` block, one ```confidence``` block, \
and a ```warning``` block only if confidence is LOW.
"""
    return system, user


# ── MERGE SUMMARY prompt ─────────────────────────────────────────────────────

def build_merge_summary_prompt(
    file_summaries: list[dict],   # [{path, intent, confidence, warning?}]
    state: RepoState,
    ctx: ProjectContext,
) -> tuple[str, str]:
    """
    Final confirmation prompt. Returns a human-readable summary of
    what the entire merge will do so the user can say Y/n.

    LLM returns a single ```summary``` block.
    """

    system = SYSTEM_BASE + """
For this task you are writing the final human-readable summary of a merge \
that is about to be applied. The user will read this and decide Y/n.

Rules:
- Write for someone who didn't write the code and may not know it well
- Focus on BEHAVIOR and FEATURES, not code structure
- Lead with what the app/system will DO after this merge
- Bullet-point format, max 6 bullets
- Flag any trade-offs or things that were dropped (be honest — this is critical)
- Flag any LOW confidence resolutions that need manual review
- End with a one-line "vibe check" — is this merge clean or sketchy?

Return your answer in a single ```summary``` block. Nothing outside it.
"""

    our_branch   = state.merge.our_branch or "HEAD"
    their_branch = state.merge.merge_head_branch or "MERGE_HEAD"
    project_block = _project_context_block(ctx)

    files_block = ""
    for f in file_summaries:
        confidence = f.get("confidence", "UNKNOWN")
        warning    = f.get("warning", "")
        files_block += f"\n### {f['path']} (confidence: {confidence})\n"
        files_block += f"{f['intent']}\n"
        if warning:
            files_block += f"⚠️  {warning}\n"

    user = f"""\
{project_block}

## merge being applied
YOUR branch: {our_branch}
THEIR branch: {their_branch}

YOUR branch commits:
{chr(10).join("  " + c for c in (state.merge.our_commits or ["(none)"]))}

THEIR branch commits:
{chr(10).join("  " + c for c in (state.merge.their_commits or ["(none)"]))}

## per-file resolution summaries
{files_block}

Write the final summary for the human to confirm.
"""
    return system, user


# ── helpers ──────────────────────────────────────────────────────────────────

def _project_context_block(ctx: ProjectContext) -> str:
    parts: list[str] = ["## project context"]

    if ctx.project_name:
        parts.append(f"name: {ctx.project_name}")
    if ctx.project_description:
        parts.append(f"description: {ctx.project_description}")
    if ctx.tech_stack:
        parts.append(f"stack: {', '.join(ctx.tech_stack)}")
    if ctx.agent_context:
        parts.append(f"\nagent context (CLAUDE.md / .cursorrules):\n{ctx.agent_context}")
    elif ctx.readme_excerpt:
        parts.append(f"\nREADME excerpt:\n{ctx.readme_excerpt}")

    if len(parts) == 1:
        parts.append("(no project context files found)")

    return "\n".join(parts)


def _format_hunks(conflict_file: ConflictFile) -> str:
    parts: list[str] = []

    for hunk in conflict_file.hunks:
        ctx_before = "\n".join(hunk.context_before) if hunk.context_before else ""
        ctx_after  = "\n".join(hunk.context_after)  if hunk.context_after  else ""
        ours       = "\n".join(hunk.ours_lines)
        theirs     = "\n".join(hunk.theirs_lines)

        parts.append(f"""\
### hunk {hunk.index} (line {hunk.start_line} in working tree)

[context before — NOT part of the conflict, do NOT include in resolved block]
```
{ctx_before or "(start of file)"}
```

[CONFLICT REGION STARTS HERE — this is what your resolved block must replace]
YOUR version ({hunk.ours_label}):
```
{ours or "(empty — this was deleted on your side)"}
```

THEIR version ({hunk.theirs_label}):
```
{theirs or "(empty — this was deleted on their side)"}
```
[CONFLICT REGION ENDS HERE]

[context after — NOT part of the conflict, do NOT include in resolved block]
```
{ctx_after or "(end of file)"}
```
""")

    return "\n".join(parts)
