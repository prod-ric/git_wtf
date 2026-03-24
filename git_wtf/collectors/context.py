"""
Reads project context files so the LLM understands what you're building.
README, package.json, pyproject.toml, CLAUDE.md — whatever's there.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Optional

MAX_README_CHARS = 3000   # truncate if massive
MAX_CONTEXT_CHARS = 1500  # for CLAUDE.md / agent context files

CONTEXT_FILE_CANDIDATES = [
    "CLAUDE.md",
    "AGENTS.md",
    "CONTEXT.md",
    ".cursorrules",
    "GEMINI.md",
]

README_CANDIDATES = [
    "README.md",
    "README.txt",
    "README.rst",
    "README",
]


@dataclass
class ProjectContext:
    project_name: Optional[str]
    project_description: Optional[str]
    tech_stack: list[str] = field(default_factory=list)
    readme_excerpt: Optional[str] = None
    agent_context: Optional[str] = None   # CLAUDE.md etc
    raw_files_found: list[str] = field(default_factory=list)


def _read_truncated(path: str, max_chars: int) -> Optional[str]:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(max_chars)
            if os.path.getsize(path) > max_chars:
                content += "\n\n[... truncated ...]"
            return content
    except OSError:
        return None


def _parse_package_json(root: str) -> tuple[Optional[str], Optional[str], list[str]]:
    path = os.path.join(root, "package.json")
    if not os.path.exists(path):
        return None, None, []
    try:
        with open(path) as f:
            data = json.load(f)
        name = data.get("name")
        description = data.get("description")
        deps = list(data.get("dependencies", {}).keys())
        dev_deps = list(data.get("devDependencies", {}).keys())
        # Surface notable frameworks
        all_deps = deps + dev_deps
        stack = [d for d in all_deps if d in {
            "react", "next", "vue", "nuxt", "svelte", "angular",
            "express", "fastapi", "django", "flask", "nestjs",
            "prisma", "drizzle-orm", "supabase", "firebase",
            "tailwindcss", "shadcn-ui",
            "typescript", "vite", "webpack",
            "openai", "anthropic", "@anthropic-ai/sdk",
        }]
        return name, description, stack
    except Exception:
        return None, None, []


def _parse_pyproject(root: str) -> tuple[Optional[str], Optional[str], list[str]]:
    path = os.path.join(root, "pyproject.toml")
    if not os.path.exists(path):
        return None, None, []
    try:
        # Basic parsing without tomllib dependency
        name = description = None
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("name ="):
                    name = line.split("=", 1)[1].strip().strip('"').strip("'")
                elif line.startswith("description ="):
                    description = line.split("=", 1)[1].strip().strip('"').strip("'")
        return name, description, []
    except Exception:
        return None, None, []


def collect(root: Optional[str] = None) -> ProjectContext:
    """Collect project context from the repo root."""
    root = root or os.getcwd()

    name: Optional[str] = None
    description: Optional[str] = None
    tech_stack: list[str] = []
    files_found: list[str] = []

    # Try package.json first (JS/TS projects)
    pkg_name, pkg_desc, pkg_stack = _parse_package_json(root)
    if pkg_name:
        name, description, tech_stack = pkg_name, pkg_desc, pkg_stack
        files_found.append("package.json")

    # Try pyproject.toml
    if not name:
        py_name, py_desc, _ = _parse_pyproject(root)
        if py_name:
            name, description = py_name, py_desc
            files_found.append("pyproject.toml")

    # README
    readme_excerpt: Optional[str] = None
    for candidate in README_CANDIDATES:
        path = os.path.join(root, candidate)
        if os.path.exists(path):
            readme_excerpt = _read_truncated(path, MAX_README_CHARS)
            files_found.append(candidate)
            break

    # Agent context files (CLAUDE.md etc)
    agent_context: Optional[str] = None
    for candidate in CONTEXT_FILE_CANDIDATES:
        path = os.path.join(root, candidate)
        if os.path.exists(path):
            agent_context = _read_truncated(path, MAX_CONTEXT_CHARS)
            files_found.append(candidate)
            break

    return ProjectContext(
        project_name=name,
        project_description=description,
        tech_stack=tech_stack,
        readme_excerpt=readme_excerpt,
        agent_context=agent_context,
        raw_files_found=files_found,
    )
