# git-wtf

Understands what both sides of a merge conflict were trying to do. Resolves them. Explains its reasoning. Asks before touching anything.

```
git wtf merge    # resolve merge conflicts — semantically, not just line-by-line
git wtf          # diagnose whatever broken state you're in
```

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

Don't have a merge conflict handy? Run `git wtf --demo` to see it in action.

---

## setup

Run `git wtf setup` to configure your LLM provider (~30 seconds).

> Full setup docs — API keys, proxy config, SSL, env var overrides — are in [SETUP.md](SETUP.md).

---

## usage

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

### `git wtf`

Diagnoses whatever state your repo is in. Detached HEAD, mid-merge, diverged from remote, unresolved conflicts — it reads the git state, figures out what happened, and tells you exactly what to run.

---

## how it works

- Reads git state and parses conflict markers — extracts all three blob versions (ancestor, yours, theirs) plus full file context
- Reads project context — `README.md`, `package.json`, `CLAUDE.md` / `.cursorrules` — so the LLM knows what you're building
- One LLM call per conflicted file, with both branch commit histories and full file versions
- Shows you everything it's about to do, asks for confirmation, then writes and `git add`s

---

## what it doesn't do (yet)

- Rebase conflict resolution
- Multi-file semantic understanding (e.g. a type changed in one file and needs updating in five others)
- Auto-commit after merge

---

## license

MIT
