# git-wtf demo tape
# Records git wtf merge resolving a realistic 2-file, 4-hunk conflict.
#
# Usage:
#   bash demo/setup-conflict.sh        # creates /tmp/git-wtf-demo
#   vhs demo/demo.tape                 # renders demo/demo.gif
#
# Tune SLEEP_LLM if your LLM is faster/slower (default 60s covers most models).
# Output is demo/demo.gif — swap to .mp4 if you prefer video.

Output demo/demo.gif

Set Shell "bash"
Set FontSize 14
Set Width 1200
Set Height 800
Set Theme "Catppuccin Mocha"
Set Padding 24
Set TypingSpeed 40ms
Set CursorBlink false

# ── silent setup ──────────────────────────────────────────────────────────────
# Run the conflict setup in the background — not part of the recording.
Hide
Type "bash /Users/ric/code/git_wtf/demo/setup-conflict.sh 2>&1 | tail -1"
Enter
Wait
Type "cd /tmp/git-wtf-demo"
Enter
Wait
Show

# ── show the mid-merge state ───────────────────────────────────────────────────
Sleep 600ms
Type "git status"
Enter
Wait
Sleep 2s

# ── the main event ─────────────────────────────────────────────────────────────
Type "git wtf merge"
Enter

# LLM resolves 2 files + writes a summary — give it time.
# Increase if your model is slow; decrease for fast local models.
Sleep 60s

# ── confirm ────────────────────────────────────────────────────────────────────
Type "Y"
Enter
Sleep 3s
