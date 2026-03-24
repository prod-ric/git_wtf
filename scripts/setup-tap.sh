#!/usr/bin/env bash
# Bootstrap github.com/git-wtf/homebrew-tap
# Run once before the first release: make setup-tap
set -euo pipefail

ORG="git-wtf"
TAP_REPO="homebrew-tap"
FORMULA_SRC="Formula/git-wtf.rb"
WORK_DIR="$(mktemp -d)"

echo "▸ checking prerequisites..."
command -v gh  >/dev/null 2>&1 || { echo "error: gh CLI not found — brew install gh"; exit 1; }
command -v git >/dev/null 2>&1 || { echo "error: git not found"; exit 1; }

echo "▸ creating github.com/$ORG/$TAP_REPO..."
gh repo create "$ORG/$TAP_REPO" \
  --public \
  --description "Homebrew tap for git-wtf" \
  --homepage "https://github.com/$ORG/git-wtf" \
  2>/dev/null || echo "  (repo already exists, continuing)"

echo "▸ cloning tap repo..."
gh repo clone "$ORG/$TAP_REPO" "$WORK_DIR/$TAP_REPO"

echo "▸ seeding formula..."
mkdir -p "$WORK_DIR/$TAP_REPO/Formula"
cp "$FORMULA_SRC" "$WORK_DIR/$TAP_REPO/Formula/git-wtf.rb"

echo "▸ pushing initial formula..."
cd "$WORK_DIR/$TAP_REPO"
git add Formula/git-wtf.rb
git diff --cached --quiet && echo "  (no changes to push)" && exit 0
git commit -m "add git-wtf formula (placeholder — sha256 updated on first release)"
git push

cd - >/dev/null
rm -rf "$WORK_DIR"

echo ""
echo "✓ tap live at github.com/$ORG/$TAP_REPO"
echo ""
echo "  brew install git-wtf/tap/git-wtf   ← works after first 'make release v=x.y.z'"
echo ""
echo "next steps:"
echo "  1. add BREW_TAP_TOKEN secret to github.com/$ORG/git-wtf (Settings → Secrets)"
echo "     — a PAT with 'repo' scope on $ORG/$TAP_REPO"
echo "  2. make release v=0.1.0"
