# git-wtf setup

```bash
git wtf setup
```

Interactive. Takes ~30 seconds. Three options:

```
  1   Anthropic   api.anthropic.com  →  Claude
  2   OpenAI      api.openai.com  →  GPT-4o, o3, ...
  3   Proxy       corporate / LiteLLM / custom endpoint
```

**Option 1 — Anthropic (direct)**

Get your key at [console.anthropic.com](https://console.anthropic.com), paste it in, pick a model. Done.

**Option 2 — OpenAI (direct)**

Get your key at [platform.openai.com](https://platform.openai.com), paste it in. Done.

**Option 3 — Proxy / corporate**

Paste your proxy base URL (e.g. `https://llm-proxy.yourcompany.com/v1`), paste the key if required. The tool fetches the available model list from the proxy and lets you pick. SSL verification is automatically disabled for corporate MITM setups.

Config is saved to `~/.config/git-wtf/config.json`.

---

## env vars (override config file)

```bash
GITWFT_API_KEY=...          # API key
GITWFT_BASE_URL=...         # custom base URL
GITWFT_MODEL=...            # model override
GITWFT_VERIFY_SSL=false     # disable SSL verification
```

Standard `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` are also picked up automatically.

---

## opencode users

If you use [opencode](https://opencode.ai), git-wtf reads your `~/.config/opencode/opencode.json` automatically and routes through the same proxy. Zero extra config.
