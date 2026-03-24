"""
LLM client — OpenAI-compatible interface.

Uses the OpenAI SDK against any OpenAI-compatible endpoint, including:
  - api.anthropic.com/v1  (Anthropic's OpenAI-compatible layer)
  - api.openai.com/v1     (OpenAI direct)
  - Any corporate / LiteLLM proxy

All config comes from git_wtf.config — this module just makes the calls.
"""
from __future__ import annotations

import re
from typing import Callable, Optional

import httpx
import openai

from git_wtf import config as cfg_module
from git_wtf.config import Config

MAX_TOKENS = 8096


class NotConfiguredError(Exception):
    pass


class LLMClient:
    def __init__(self) -> None:
        cfg = cfg_module.load()
        if cfg is None:
            raise NotConfiguredError(
                "git-wtf is not configured yet.\n"
                "Run:  git wtf setup"
            )
        self._cfg = cfg
        self._client = _build_client(cfg)

    def debug_info(self) -> str:
        return (
            f"provider={self._cfg.provider}  "
            f"base_url={self._cfg.base_url or 'sdk default'}  "
            f"model={self._cfg.model}  "
            f"verify_ssl={self._cfg.verify_ssl}"
        )

    def stream(
        self,
        system: str,
        user: str,
        on_token: Optional[Callable[[str], None]] = None,
    ) -> str:
        """Stream a completion. Calls on_token(chunk) for each text chunk."""
        full_text = ""
        with self._client.chat.completions.create(
            model=self._cfg.model,
            max_tokens=MAX_TOKENS,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
            stream=True,
        ) as stream:
            for chunk in stream:
                delta = chunk.choices[0].delta.content or ""
                if delta:
                    full_text += delta
                    if on_token:
                        on_token(delta)
        return full_text

    def complete(self, system: str, user: str) -> str:
        """Non-streaming completion. For structured output that needs parsing."""
        response = self._client.chat.completions.create(
            model=self._cfg.model,
            max_tokens=MAX_TOKENS,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
        )
        return response.choices[0].message.content or ""


def _build_client(cfg: Config) -> openai.OpenAI:
    kwargs: dict = {"api_key": cfg.api_key}

    if cfg.base_url:
        kwargs["base_url"] = cfg.base_url

    if not cfg.verify_ssl:
        kwargs["http_client"] = httpx.Client(verify=False)

    return openai.OpenAI(**kwargs)


# ── response parsing ─────────────────────────────────────────────────────────

def extract_block(text: str, tag: str) -> Optional[str]:
    """Extract first occurrence of a tagged block. Supports ``` and <tag>."""
    m = re.search(rf"```{re.escape(tag)}\n(.*?)```", text, re.DOTALL)
    if m:
        return m.group(1)
    m = re.search(rf"<{re.escape(tag)}>(.*?)</{re.escape(tag)}>", text, re.DOTALL)
    if m:
        return m.group(1)
    return None


def extract_all_blocks(text: str, tag: str) -> list[str]:
    """Extract all occurrences of a tagged block, in order."""
    results = [
        m.group(1)
        for m in re.finditer(rf"```{re.escape(tag)}\n(.*?)```", text, re.DOTALL)
    ]
    if not results:
        results = [
            m.group(1)
            for m in re.finditer(
                rf"<{re.escape(tag)}>(.*?)</{re.escape(tag)}>", text, re.DOTALL
            )
        ]
    return results
