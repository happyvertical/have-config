#!/usr/bin/env bash
#
# install.sh — one-line setup for have-config.
#
# Does:
#   1. Ensures pr-review is cloned and on $PATH.
#   2. Registers this repo as a marketplace for Claude Code.
#   3. Installs the `have` plugin in Claude Code.
#   4. Registers this repo as a marketplace for Codex.
#   5. (Codex auto-enables installed plugins via marketplace add.)
#   6. With --live, symlinks the cached plugin installs back to this repo
#      so edits are immediately visible to running sessions.
#
# Usage:
#   ./install.sh              # standard install (use `plugin update` after edits)
#   ./install.sh --live       # live mode (cache symlinked to repo)
#   ./install.sh --uninstall  # remove marketplaces + plugins
#   ./install.sh -h           # help
#
set -euo pipefail

LIVE=0
UNINSTALL=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --live) LIVE=1; shift ;;
    --uninstall) UNINSTALL=1; shift ;;
    -h|--help)
      sed -n '2,/^set -euo/p' "$0" | sed -e '$d' -e 's/^# \{0,1\}//'
      exit 0 ;;
    *) echo "install.sh: unknown option: $1" >&2; exit 2 ;;
  esac
done

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PR_REVIEW_DIR="${PR_REVIEW_DIR:-$HOME/Work/happyvertical/repos/pr-review}"

cyan() { printf "\033[36m%s\033[0m\n" "$*"; }
green() { printf "\033[32m%s\033[0m\n" "$*"; }
red() { printf "\033[31m%s\033[0m\n" "$*" >&2; }

if [[ "$UNINSTALL" -eq 1 ]]; then
  cyan "Uninstalling have plugins…"
  command -v claude >/dev/null 2>&1 && claude plugin uninstall have@have-config 2>/dev/null || true
  command -v claude >/dev/null 2>&1 && claude plugin marketplace remove have-config 2>/dev/null || true
  command -v codex >/dev/null 2>&1 && codex plugin marketplace remove have-config 2>/dev/null || true
  green "Uninstalled."
  exit 0
fi

# 1. pr-review
cyan "→ Step 1/4: pr-review"
if [[ ! -d "$PR_REVIEW_DIR" ]]; then
  cyan "  Cloning pr-review to $PR_REVIEW_DIR…"
  mkdir -p "$(dirname "$PR_REVIEW_DIR")"
  git clone https://github.com/happyvertical/pr-review.git "$PR_REVIEW_DIR"
else
  cyan "  Already cloned at $PR_REVIEW_DIR (skipping)."
fi

if ! command -v pr-review >/dev/null 2>&1; then
  red "  pr-review not on \$PATH. Add this to your shell rc:"
  red "    export PATH=\"$PR_REVIEW_DIR/bin:\$PATH\""
else
  green "  pr-review on PATH ($(command -v pr-review))"
fi

# 2. Claude marketplace + plugin
cyan "→ Step 2/4: Claude Code marketplace + have plugin"
if command -v claude >/dev/null 2>&1; then
  if ! claude plugin marketplace list 2>/dev/null | grep -q "have-config"; then
    claude plugin marketplace add "$REPO_ROOT/claude"
  else
    cyan "  marketplace 'have-config' already registered."
  fi
  if ! claude plugin list 2>/dev/null | grep -q "have@have-config"; then
    claude plugin install have@have-config
  else
    cyan "  have@have-config already installed."
  fi
  green "  Claude: /have:ship and /have:review-cycle ready."
else
  red "  claude CLI not found; skipping Claude install."
fi

# 3. Codex marketplace
cyan "→ Step 3/4: Codex marketplace + have plugin"
if command -v codex >/dev/null 2>&1; then
  # Codex marketplace add registers the marketplace; plugin enablement is
  # config-driven (codex has no `plugin install/enable` CLI). We add the
  # enabled=true entry to ~/.codex/config.toml directly.
  codex plugin marketplace add "$REPO_ROOT/codex" 2>&1 | head -3 || true

  # Idempotently enable have@have-config
  python3 - <<'PY' || red "  Could not auto-enable plugin in ~/.codex/config.toml; add this manually:
  [plugins.\"have@have-config\"]
  enabled = true"
import os
path = os.path.expanduser("~/.codex/config.toml")
content = open(path).read() if os.path.exists(path) else ""
if 'plugins."have@have-config"' in content:
    print("  have@have-config already enabled in codex config.")
else:
    with open(path, "a") as f:
        f.write('\n[plugins."have@have-config"]\nenabled = true\n')
    print("  Enabled have@have-config in ~/.codex/config.toml.")
PY

  green "  Codex: /have:ship and /have:review-cycle ready (after restart)."
else
  red "  codex CLI not found; skipping Codex install."
fi

# 4. Live mode (optional)
if [[ "$LIVE" -eq 1 ]]; then
  cyan "→ Step 4/4: --live mode — symlinking caches to repo"

  # Claude cache path: ~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/
  CLAUDE_CACHE="$HOME/.claude/plugins/cache/have-config/have/0.1.0"
  CLAUDE_SOURCE="$REPO_ROOT/claude/have"
  if [[ -d "$(dirname "$CLAUDE_CACHE")" ]]; then
    rm -rf "$CLAUDE_CACHE"
    ln -s "$CLAUDE_SOURCE" "$CLAUDE_CACHE"
    green "  Claude cache symlinked: $CLAUDE_CACHE -> $CLAUDE_SOURCE"
    cyan "  (Edits to $CLAUDE_SOURCE are now live. Re-run --live after 'claude plugin update' which re-clones the cache.)"
  else
    red "  Claude cache dir not found at $(dirname "$CLAUDE_CACHE"); install may have failed."
  fi

  # Codex doesn't expose its cache layout the same way; skip symlink for now.
  cyan "  Codex: --live not implemented (codex marketplace add appears to read directly from source; edits propagate naturally)."
else
  cyan "→ Step 4/4: skipping --live (pass --live to enable live edits)"
fi

green ""
green "Done. Restart Claude / Codex sessions to pick up the new commands."
green "Try:  /have:review-cycle"
green "      /have:ship"
