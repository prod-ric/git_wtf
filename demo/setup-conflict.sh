#!/usr/bin/env bash
# Creates a realistic mid-merge git repo for demoing git wtf merge.
#
# Scenario: two AI-generated feature branches that both touched auth + http client.
#   feat/onboarding  — added Bearer token headers, session cleanup
#   feat/chat-agent  — introduced shared httpClient, response caching
#
# Usage:
#   bash demo/setup-conflict.sh            # creates /tmp/git-wtf-demo
#   bash demo/setup-conflict.sh ~/mydir    # creates at custom path
set -euo pipefail

DEMO_DIR="${1:-/tmp/git-wtf-demo}"

echo "▸ creating demo repo at $DEMO_DIR"
rm -rf "$DEMO_DIR"
mkdir -p "$DEMO_DIR"
cd "$DEMO_DIR"

git init -q -b main
git config user.email "demo@git-wtf.sh"
git config user.name "Demo"

# ── initial commit ─────────────────────────────────────────────────────────────
mkdir -p src/api

cat > README.md << 'EOF'
# myapp

A small web app. Users can log in, browse, chat.
EOF

cat > src/auth.ts << 'EOF'
import fetch from 'node-fetch';

let _userCache: Record<string, unknown> = {};

export async function getUser(id: string) {
  if (_userCache[id]) return _userCache[id];
  const res = await fetch(`/api/users/${id}`);
  const data = await res.json() as unknown;
  _userCache[id] = data;
  return data;
}

export function logout() {
  _userCache = {};
  localStorage.removeItem('token');
}
EOF

cat > src/api/client.ts << 'EOF'
export const httpClient = {
  async get(url: string) {
    const res = await fetch(url);
    return res.json();
  },

  async post(url: string, body: unknown) {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    return res.json();
  },
};
EOF

cat > src/session.ts << 'EOF'
export function getToken(): string {
  return localStorage.getItem('token') ?? '';
}

export function setToken(t: string) {
  localStorage.setItem('token', t);
}
EOF

git add .
git commit -q -m "initial: auth, http client, session helpers"

# ── feat/onboarding ────────────────────────────────────────────────────────────
# This branch was built with AI assistance for the onboarding flow.
# It adds auth headers to every API call and cleans up all session state on logout.
git checkout -q -b feat/onboarding

cat > src/auth.ts << 'EOF'
import fetch from 'node-fetch';
import { getToken } from './session';

let _userCache: Record<string, unknown> = {};

export async function getUser(id: string) {
  if (_userCache[id]) return _userCache[id];
  const res = await fetch(`/api/users/${id}`, {
    headers: { Authorization: `Bearer ${getToken()}` },
  });
  const data = await res.json() as unknown;
  _userCache[id] = data;
  return data;
}

export function logout() {
  _userCache = {};
  localStorage.removeItem('token');
  sessionStorage.clear();
}
EOF

cat > src/api/client.ts << 'EOF'
import { getToken } from '../session';

export const httpClient = {
  async get(url: string) {
    const res = await fetch(url, {
      headers: { Authorization: `Bearer ${getToken()}` },
    });
    return res.json();
  },

  async post(url: string, body: unknown) {
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${getToken()}`,
      },
      body: JSON.stringify(body),
    });
    return res.json();
  },
};
EOF

git add .
git commit -q -m "feat/onboarding: auth headers on every request, full session wipe on logout"

# ── feat/chat-agent ────────────────────────────────────────────────────────────
# This branch was built separately for the chat feature.
# It switches to a shared httpClient (no more raw fetch), adds response caching.
git checkout -q main

git checkout -q -b feat/chat-agent

cat > src/auth.ts << 'EOF'
import { httpClient } from './api/client';

let _userCache: Record<string, unknown> = {};

export async function getUser(id: string) {
  if (_userCache[id]) return _userCache[id];
  const data = await httpClient.get(`/api/users/${id}`);
  _userCache[id] = data;
  return data;
}

export function logout() {
  _userCache = {};
  localStorage.removeItem('token');
  httpClient.clearCache();
}
EOF

cat > src/api/client.ts << 'EOF'
const _cache = new Map<string, unknown>();

export const httpClient = {
  async get(url: string) {
    if (_cache.has(url)) return _cache.get(url);
    const res = await fetch(url);
    const data = await res.json();
    _cache.set(url, data);
    return data;
  },

  async post(url: string, body: unknown) {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    return res.json();
  },

  clearCache() {
    _cache.clear();
  },
};
EOF

git add .
git commit -q -m "feat/chat-agent: shared httpClient with response caching, clearCache on logout"

# ── merge onboarding into main (clean) ────────────────────────────────────────
git checkout -q main
git merge -q feat/onboarding -m "Merge branch 'feat/onboarding'"

# ── merge chat-agent — this is the one that conflicts ─────────────────────────
echo "▸ triggering merge conflict..."
git merge --no-edit feat/chat-agent 2>/dev/null || true

echo ""
echo "✓ done. repo is sitting in a mid-merge conflicted state."
echo ""
echo "  conflicted files:"
git diff --name-only --diff-filter=U | sed 's/^/    /'
echo ""
echo "  now run:"
echo "    cd $DEMO_DIR && git wtf merge"
echo ""
