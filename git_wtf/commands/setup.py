"""
git wtf setup — interactive first-run configuration.

Two paths:
  1. Direct  — paste an Anthropic or OpenAI key, done.
  2. Proxy   — custom base URL + key (corporate / LiteLLM / etc.)

Saves to ~/.config/git-wtf/config.json
"""
from __future__ import annotations

from typing import Optional

import httpx
from rich.padding import Padding
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

from git_wtf import ui
from git_wtf import config as cfg_module
from git_wtf.config import ANTHROPIC_BASE_URL, Config, DEFAULT_MODELS, save

console = ui.console

PRESET_MODELS = {
    "anthropic": ["claude-sonnet-4-6", "claude-opus-4-6", "claude-haiku-4-5-20251001"],
    "openai":    ["gpt-4o", "gpt-4.1", "gpt-4o-mini"],
    "proxy":     [],
}


def run() -> int:
    ui.print_logo()
    ui.rule("setup")
    console.print()
    console.print("  let's get you configured. takes like 30 seconds.\n")

    # ── already configured? ───────────────────────────────────────────────────
    existing = cfg_module.load()
    if existing:
        _print_current_config(existing)
        console.print()
        if not Confirm.ask("  reconfigure?", default=False):
            ui.info_msg("nothing changed.")
            console.print()
            return 0
        console.print()

    # ── choose setup type ─────────────────────────────────────────────────────
    table = Table.grid(padding=(0, 3))
    table.add_column(style="bold cyan")
    table.add_column()
    table.add_column(style="dim")
    table.add_row("1", "Anthropic", "api.anthropic.com  →  Claude")
    table.add_row("2", "OpenAI",    "api.openai.com  →  GPT-4o, o3, ...")
    table.add_row("3", "Proxy",     "corporate / LiteLLM / custom endpoint")

    console.print(Padding(table, (0, 2)))
    console.print()

    choice = Prompt.ask("  which setup", choices=["1", "2", "3"], default="1")
    console.print()

    if choice == "1":
        cfg = _setup_anthropic()
    elif choice == "2":
        cfg = _setup_openai()
    else:
        cfg = _setup_proxy()

    if cfg is None:
        return 1

    # ── test connection ───────────────────────────────────────────────────────
    console.print()
    with ui.spinner("testing connection..."):
        ok, err = _test_connection(cfg)

    if not ok:
        ui.error_msg(f"connection test failed: {err}")
        console.print("  config was [bold]not[/bold] saved. fix the issue and run setup again.\n")
        return 1

    ui.success_msg("connection works.")

    # ── save ──────────────────────────────────────────────────────────────────
    save(cfg)
    console.print()
    _print_current_config(cfg, title="saved")
    console.print()
    console.print("  now try:  [bold cyan]git wtf[/bold cyan]  or  [bold cyan]git wtf merge[/bold cyan]\n")
    return 0


# ── setup flows ───────────────────────────────────────────────────────────────

def _setup_anthropic() -> Optional[Config]:
    console.print("  [bold]Anthropic[/bold]  [dim]→  console.anthropic.com[/dim]\n")
    api_key = _prompt_key("sk-ant-")
    if not api_key:
        return None
    model = _pick_model(PRESET_MODELS["anthropic"], DEFAULT_MODELS["anthropic"])
    return Config(provider="anthropic", api_key=api_key,
                  base_url=ANTHROPIC_BASE_URL, model=model, verify_ssl=True)


def _setup_openai() -> Optional[Config]:
    console.print("  [bold]OpenAI[/bold]  [dim]→  platform.openai.com[/dim]\n")
    api_key = _prompt_key("sk-")
    if not api_key:
        return None
    model = _pick_model(PRESET_MODELS["openai"], DEFAULT_MODELS["openai"])
    return Config(provider="openai", api_key=api_key,
                  base_url=None, model=model, verify_ssl=True)


def _setup_proxy() -> Optional[Config]:
    console.print("  [bold]Proxy / corporate setup[/bold]\n")

    base_url = Prompt.ask(
        "  base URL",
        default="https://your-proxy.company.com/v1",
    ).strip()

    if not base_url or base_url == "https://your-proxy.company.com/v1":
        ui.error_msg("base URL is required.")
        return None

    if not base_url.endswith("/v1"):
        if Confirm.ask("  url doesn't end with /v1 — add it?", default=True):
            base_url = base_url.rstrip("/") + "/v1"

    console.print()
    api_key = Prompt.ask(
        "  API key [dim](enter to skip if not required)[/dim]",
        default="placeholder",
    ).strip() or "placeholder"

    # Fetch model list from proxy
    console.print()
    with ui.spinner("fetching available models from proxy..."):
        available_models = _fetch_proxy_models(base_url, api_key)

    if available_models:
        ui.success_msg(f"found {len(available_models)} model(s)")
        console.print()
        model = _pick_model(available_models[:12], available_models[0])
    else:
        ui.warn_msg("couldn't fetch models — enter manually")
        model = Prompt.ask("  model name", default=DEFAULT_MODELS["proxy"]).strip()

    return Config(provider="proxy", api_key=api_key,
                  base_url=base_url, model=model, verify_ssl=False)


# ── helpers ───────────────────────────────────────────────────────────────────

def _prompt_key(prefix_hint: str = "") -> Optional[str]:
    hint = f"[dim](starts with {prefix_hint}...)[/dim]" if prefix_hint else ""
    key = Prompt.ask(f"  paste your API key {hint}").strip()
    if not key:
        ui.error_msg("no key entered.")
        return None
    return key


def _pick_model(options: list[str], default: str) -> str:
    if not options:
        return Prompt.ask("  model name", default=default).strip()

    console.print()
    table = Table.grid(padding=(0, 3))
    table.add_column(style="bold cyan", width=3)
    table.add_column()
    table.add_column(style="dim green")

    for i, m in enumerate(options, 1):
        rec = "← recommended" if i == 1 else ""
        table.add_row(str(i), m, rec)

    console.print(Padding(table, (0, 4)))
    console.print()

    choices = [str(i) for i in range(1, len(options) + 1)]
    choice = Prompt.ask("  which model", choices=choices, default="1")
    return options[int(choice) - 1]


def _fetch_proxy_models(base_url: str, api_key: str) -> list[str]:
    try:
        r = httpx.get(
            base_url.rstrip("/") + "/models",
            headers={"Authorization": f"Bearer {api_key}"},
            verify=False,
            timeout=8,
        )
        if r.status_code != 200:
            return []
        ids = [m["id"] for m in r.json().get("data", []) if isinstance(m.get("id"), str)]
        claude = [m for m in ids if "claude" in m.lower()]
        gpt    = [m for m in ids if "gpt" in m.lower() and m not in claude]
        rest   = [m for m in ids if m not in claude and m not in gpt]
        return claude + gpt + rest
    except Exception:
        return []


def _test_connection(cfg: Config) -> tuple[bool, str]:
    from git_wtf.llm.client import _build_client
    try:
        client = _build_client(cfg)
        client.chat.completions.create(
            model=cfg.model,
            max_tokens=8,
            messages=[{"role": "user", "content": "hi"}],
        )
        return True, ""
    except Exception as e:
        return False, str(e)


def _print_current_config(cfg: Config, title: str = "current config") -> None:
    table = Table.grid(padding=(0, 2))
    table.add_column(style="dim", width=12)
    table.add_column(style="bold")

    table.add_row("provider", cfg.provider)
    table.add_row("model", cfg.model)
    table.add_row("base_url", cfg.base_url or "sdk default")
    table.add_row("config file", str(cfg_module.CONFIG_FILE))

    console.print(Panel(
        Padding(table, (0, 1)),
        title=Text(f" {title} ", style="bold green"),
        border_style="green",
        padding=(1, 2),
    ))
