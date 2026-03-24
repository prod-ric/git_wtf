"""
Entry point for the git-wtf CLI.

Registered as `git-wtf` binary via pyproject.toml [project.scripts].
Git picks it up automatically as a subcommand: `git wtf [subcommand]`
"""
from __future__ import annotations

import argparse
import sys

from rich.console import Console

console = Console()


def _not_configured_error() -> None:
    console.print(
        "\n[red]git-wtf is not configured.[/red]\n\n"
        "run this to get set up in ~30 seconds:\n\n"
        "  [bold]git wtf setup[/bold]\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="git-wtf",
        description="AI-powered git assistant. For when git is being git.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "commands:\n"
            "  git wtf              diagnose current repo state\n"
            "  git wtf merge        resolve merge conflicts with AI\n"
            "  git wtf setup        configure API key and provider\n"
        ),
    )

    parser.add_argument(
        "command",
        nargs="?",
        choices=["merge", "setup"],
        help="subcommand (omit to diagnose current state)",
    )

    parser.add_argument(
        "--version",
        action="version",
        version="git-wtf 0.1.0",
    )

    parser.add_argument(
        "--dir",
        metavar="PATH",
        default=None,
        help="run as if started in PATH (default: current directory)",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="print resolved config before running",
    )

    parser.add_argument(
        "--chaos",
        action="store_true",
        help="show chaos level score for the current repo state",
    )

    parser.add_argument(
        "--blame",
        action="store_true",
        help="show who last touched each conflicted file and who initiated the merge",
    )

    args = parser.parse_args()

    # ── setup is always available, no config required ────────────────────────
    if args.command == "setup":
        from git_wtf.commands.setup import run
        sys.exit(run())

    # ── debug: show resolved config ──────────────────────────────────────────
    if args.debug:
        from git_wtf import config as cfg_module
        cfg = cfg_module.load()
        if cfg:
            console.print(f"\n[dim]config:[/dim]")
            console.print(f"  provider  : {cfg.provider}")
            console.print(f"  model     : {cfg.model}")
            console.print(f"  base_url  : {cfg.base_url or 'sdk default'}")
            console.print(f"  verify_ssl: {cfg.verify_ssl}")
            console.print(f"  api_key   : {'set' if cfg.api_key else 'NOT SET'}\n")
        else:
            _not_configured_error()
            sys.exit(1)

    # ── guard: must be configured for all other commands ────────────────────
    from git_wtf import config as cfg_module
    if not cfg_module.is_configured():
        _not_configured_error()
        sys.exit(1)

    # ── dispatch ─────────────────────────────────────────────────────────────
    if args.command == "merge":
        from git_wtf.commands.merge import run
        sys.exit(run(cwd=args.dir))
    else:
        from git_wtf.commands.diagnose import run
        sys.exit(run(cwd=args.dir, show_chaos=args.chaos, show_blame=args.blame))


if __name__ == "__main__":
    main()
