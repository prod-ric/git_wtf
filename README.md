# git-wtf

> AI-powered git assistant. For when git is being git.

Two commands that cover 90% of the pain:

```
git wtf          # diagnose whatever broken state you're in
git wtf merge    # resolve merge conflicts — semantically, not just line-by-line
```

Built for vibe coders who are moving fast with AI tools. When you hit a merge conflict on code you didn't write and don't have time to read, `git wtf merge` reads both sides, understands what each branch was *trying to do*, merges them properly, explains what it did in plain English, and asks you to confirm before touching a single file.

---

## install

**macOS (Homebrew)**

```bash
brew tap git-wtf/tap
brew install git-wtf
```

**Any OS (pipx — recommended)**

```bash
pipx install git-wtf
```

Git automatically picks up `git-wtf` as a subcommand. No PATH tricks, no aliases required.

---

## setup

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

### env vars (override config file)

```bash
GITWFT_API_KEY=...          # API key
GITWFT_BASE_URL=...         # custom base URL
GITWFT_MODEL=...            # model override
GITWFT_VERIFY_SSL=false     # disable SSL verification
```

Standard `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` are also picked up automatically.

### opencode users

If you use [opencode](https://opencode.ai), git-wtf reads your `~/.config/opencode/opencode.json` automatically and routes through the same proxy. Zero extra config.

---

## usage

### `git wtf`

Diagnoses whatever state your repo is in. Detached HEAD, mid-merge, diverged from remote, unresolved conflicts — it reads the git state, figures out what happened, and tells you exactly what to run.

```
 __ _(_) |_  __ _____ __
/ _` | |  _| \ V V / '_ \
\__, |_|\__|  \_/\_/ | .__/
|___/               |_|

  feat/onboarding  →  origin/feat/onboarding

  ↓ 3 behind    MID-MERGE    2 CONFLICTS

──────────────────────────── diagnosis ────────────────────────────

## what happened
ok so basically you're in the middle of a merge that hit conflicts.
git is frozen waiting for you to resolve them...

## how to fix it
1. run `git wtf merge` to resolve conflicts automatically
2. run `git merge --continue` to finish the merge
...
```

### `git wtf merge`

The main thing. Reads both sides of every conflict, understands the intent behind each, and produces a resolution that keeps both features intact — not just picking a winner.

**The trust flow (this is the important part):**

After resolving all conflicts, before writing a single file, it shows you:

1. A per-file panel — what each file does now, confidence rating (HIGH / MEDIUM / LOW), and any warnings about things it wasn't sure about
2. A plain-English summary of the entire merge — what the app will *do* after this, what trade-offs were made, anything that needs manual review
3. A single `apply this merge? [Y/n]` prompt

Nothing is written to disk until you say Y.

```
  feat/chat-agent  +  feat/onboarding  →  3 conflicted files

  (1/3)  src/auth.ts        2 hunks    MEDIUM
  (2/3)  src/api/client.ts  1 hunk     HIGH
  (3/3)  src/user.ts        3 hunks    HIGH

────────────────────── what i'm about to change ───────────────────

╭──────  src/auth.ts    MEDIUM   2 hunks  ─────────────────────────╮
│                                                                   │
│  fetchUser now uses the shared httpClient AND sends the auth      │
│  token as a Bearer header. logout clears localStorage, the        │
│  httpClient cache, AND sessionStorage — all three steps kept.     │
│                                                                   │
│  ⚠  verify httpClient.get() accepts a headers config object       │
│     before shipping                                               │
╰───────────────────────────────────────────────────────────────────╯

───────────────────────── the big picture ─────────────────────────

╭──────────────  what this merge will do  ─────────────────────────╮
│                                                                   │
│  • fetchUser now uses the shared HTTP client AND sends auth       │
│  • logout does a full triple cleanup — nothing left behind        │
│  • onboarding auth + chat-agent HTTP refactor coexist cleanly     │
│                                                                   │
│  ⚠  NEEDS MANUAL REVIEW: httpClient.get() headers assumption      │
│                                                                   │
│  vibe check: clean merge, one loose wire — verify before ship     │
╰───────────────────────────────────────────────────────────────────╯

  3 files resolved  ·  nothing written to disk yet

  apply this merge? [Y/n]
```

---

## how it works

1. **Reads git state** — `git status`, `git log`, branch info, merge state
2. **Parses conflict markers** — extracts the three blob versions (`:1:` ancestor, `:2:` yours, `:3:` theirs) for full file context
3. **Reads project context** — `README.md`, `package.json`, `CLAUDE.md` / `.cursorrules` so the LLM knows what you're building
4. **One LLM call per conflicted file** — sends both branch commit histories, both full file versions, and each conflict hunk with surrounding context
5. **Self-validates** — if hunk count doesn't match, skips the file and tells you to resolve manually
6. **Summary call** — a second LLM call synthesises all per-file resolutions into a plain-English "what this merge will do" summary
7. **You confirm** — one Y/n. Then it writes and `git add`s everything.

---

## confidence levels

Every resolved file gets a confidence rating:

| Level | Meaning |
|-------|---------|
| **HIGH** | both changes are in clearly different parts of the code, no semantic overlap |
| **MEDIUM** | changes interact — resolution is probably right but verify the integration |
| **LOW** | genuinely ambiguous — the LLM resolved it but you should read this one manually |

LOW confidence files always get a `⚠ heads up` block in the panel explaining exactly what to check.

---

## what it doesn't do (yet)

- Rebase conflict resolution
- Multi-file semantic understanding (e.g. a type changed in one file and needs updating in five others)
- Auto-commit after merge

---

## license

MIT
