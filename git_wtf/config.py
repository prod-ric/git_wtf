"""
Config management for git-wtf.

Stored at: ~/.config/git-wtf/config.json

Resolution order for each setting (first match wins):
  env var  →  config file  →  opencode auto-detect  →  None

Supported setups:
  - "anthropic"  : direct to api.anthropic.com via Anthropic-compatible OpenAI endpoint
  - "openai"     : direct to api.openai.com
  - "proxy"      : any OpenAI-compatible proxy (corporate, LiteLLM, etc.)
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

CONFIG_DIR  = Path.home() / ".config" / "git-wtf"
CONFIG_FILE = CONFIG_DIR / "config.json"

ANTHROPIC_BASE_URL = "https://api.anthropic.com/v1"
OPENAI_BASE_URL    = "https://api.openai.com/v1"

DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-4-6",
    "openai":    "gpt-4o",
    "proxy":     "claude-sonnet-4-6",
}


@dataclass
class Config:
    provider: str          # "anthropic" | "openai" | "proxy"
    api_key: str
    base_url: Optional[str]  # None = use provider default
    model: str
    verify_ssl: bool = True  # set False for MITM-proxy corporate environments


def _load_file() -> dict:
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text())
        except Exception:
            pass
    return {}


def _opencode_base_url() -> Optional[str]:
    """Auto-detect proxy URL from opencode config if present."""
    p = Path.home() / ".config" / "opencode" / "opencode.json"
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text())
        return (
            data
            .get("provider", {})
            .get("anthropic", {})
            .get("options", {})
            .get("baseURL")
        )
    except Exception:
        return None


def load() -> Optional[Config]:
    """
    Load resolved config. Returns None if not configured at all.
    Env vars always win over the config file.
    """
    file_cfg = _load_file()

    # API key
    api_key = (
        os.environ.get("GITWFT_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or os.environ.get("ANTHROPIC_API_KEY")
        or file_cfg.get("api_key")
    )

    # Base URL
    base_url = (
        os.environ.get("GITWFT_BASE_URL")
        or os.environ.get("OPENAI_BASE_URL")
        or file_cfg.get("base_url")
        or _opencode_base_url()   # auto-detect opencode proxy
    )

    # Provider
    provider = (
        os.environ.get("GITWFT_PROVIDER")
        or file_cfg.get("provider")
    )
    if not provider:
        # Infer from what we have
        if base_url and base_url != ANTHROPIC_BASE_URL and base_url != OPENAI_BASE_URL:
            provider = "proxy"
        elif api_key and api_key.startswith("sk-ant"):
            provider = "anthropic"
        else:
            provider = "openai"

    # Model
    model = (
        os.environ.get("GITWFT_MODEL")
        or file_cfg.get("model")
        or DEFAULT_MODELS.get(provider, "gpt-4o")
    )

    # SSL verification — proxies often need this off
    verify_ssl_env = os.environ.get("GITWFT_VERIFY_SSL", "").lower()
    if verify_ssl_env in ("0", "false", "no"):
        verify_ssl = False
    elif verify_ssl_env in ("1", "true", "yes"):
        verify_ssl = True
    else:
        verify_ssl = file_cfg.get("verify_ssl", True)
        # Auto-disable for known-proxy setups
        if provider == "proxy":
            verify_ssl = file_cfg.get("verify_ssl", False)

    if not api_key:
        return None

    # Resolve base_url to concrete URL
    if base_url is None:
        if provider == "anthropic":
            base_url = ANTHROPIC_BASE_URL
        # openai: leave as None (SDK default)

    return Config(
        provider=provider,
        api_key=api_key,
        base_url=base_url,
        model=model,
        verify_ssl=verify_ssl,
    )


def save(cfg: Config) -> None:
    """Write config to disk."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(asdict(cfg), indent=2))


def is_configured() -> bool:
    return load() is not None
