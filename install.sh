#!/usr/bin/env bash
#
# install.sh - one-line setup for have-config.
#
# Does:
#   1. Clones/updates dotfiles and runs dotfiles/install.sh for base tooling.
#   2. Ensures pr-review is cloned and on $PATH.
#   3. Registers this repo as a marketplace for Claude Code.
#   4. Installs the `have` plugin in Claude Code.
#   5. Registers this repo as a marketplace for Codex.
#   6. Enables and syncs the `have` plugin cache in Codex.
#   7. Resolves org/profile/Context Forge/local agent material.
#   8. With --live, symlinks the cached plugin installs back to this repo
#      so edits are immediately visible to running sessions.
#
# Usage:
#   ./install.sh              # standard install (use `plugin update` after fallback edits)
#   ./install.sh --live       # live mode (cache symlinked to repo)
#   ./install.sh --dry-run    # audit without changing plugin installs
#   ./install.sh --skip-dotfiles
#   ./install.sh --uninstall  # remove marketplaces + plugins
#   ./install.sh -h           # help
#
set -euo pipefail

LIVE=0
UNINSTALL=0
DRY_RUN=0
SKIP_DOTFILES="${HAVE_CONFIG_SKIP_DOTFILES:-0}"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --live) LIVE=1; shift ;;
    --dry-run|--audit) DRY_RUN=1; shift ;;
    --skip-dotfiles) SKIP_DOTFILES=1; shift ;;
    --uninstall) UNINSTALL=1; shift ;;
    -h|--help)
      sed -n '2,/^set -euo/p' "$0" | sed -e '$d' -e 's/^# \{0,1\}//'
      exit 0 ;;
    *) echo "install.sh: unknown option: $1" >&2; exit 2 ;;
  esac
done

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PR_REVIEW_DIR="${PR_REVIEW_DIR:-$HOME/Work/happyvertical/repos/pr-review}"
DOTFILES_DIR="${DOTFILES_DIR:-$HOME/Work/willgriffin/repos/dotfiles}"
DOTFILES_REPO_URL="${DOTFILES_REPO_URL:-git@github.com:willgriffin/dotfiles.git}"
DOTFILES_FALLBACK_REPO_URL="https://github.com/willgriffin/dotfiles.git"
HAVE_PLUGIN_VERSION="0.1.1"

if [[ -d "$PR_REVIEW_DIR/bin" && ":$PATH:" != *":$PR_REVIEW_DIR/bin:"* ]]; then
  export PATH="$PR_REVIEW_DIR/bin:$PATH"
fi

cyan() { printf "\033[36m%s\033[0m\n" "$*"; }
green() { printf "\033[32m%s\033[0m\n" "$*"; }
red() { printf "\033[31m%s\033[0m\n" "$*" >&2; }

bootstrap_dotfiles() {
  cyan "Step 1/6: dotfiles baseline"

  if [[ "$SKIP_DOTFILES" == "1" || "${HAVE_CONFIG_BOOTSTRAPPING_DOTFILES:-0}" == "1" ]]; then
    cyan "  Skipping dotfiles baseline."
    return 0
  fi

  if [[ "$DRY_RUN" -eq 1 ]]; then
    if [[ -e "$DOTFILES_DIR/.git" ]]; then
      cyan "  Dry-run: dotfiles exists at $DOTFILES_DIR"
    else
      cyan "  Dry-run: would clone dotfiles to $DOTFILES_DIR"
    fi
    cyan "  Dry-run: would run dotfiles/install.sh for base tooling."
    return 0
  fi

  if [[ -e "$DOTFILES_DIR/.git" ]]; then
    cyan "  Updating dotfiles at $DOTFILES_DIR..."
    if ! git -C "$DOTFILES_DIR" pull --ff-only --quiet; then
      red "  Could not fast-forward dotfiles; using existing checkout."
    fi
  else
    cyan "  Cloning dotfiles to $DOTFILES_DIR..."
    mkdir -p "$(dirname "$DOTFILES_DIR")"
    if ! git clone --quiet "$DOTFILES_REPO_URL" "$DOTFILES_DIR"; then
      if [[ "$DOTFILES_REPO_URL" != "$DOTFILES_FALLBACK_REPO_URL" ]]; then
        red "  SSH clone failed, trying HTTPS..."
        git clone --quiet "$DOTFILES_FALLBACK_REPO_URL" "$DOTFILES_DIR"
      else
        return 1
      fi
    fi
  fi

  if [[ ! -x "$DOTFILES_DIR/install.sh" ]]; then
    red "  dotfiles installer not executable at $DOTFILES_DIR/install.sh"
    return 1
  fi

  (cd "$DOTFILES_DIR" && HAVE_CONFIG_BOOTSTRAPPING_DOTFILES=1 ./install.sh)
}

if [[ "$UNINSTALL" -eq 1 ]]; then
  if [[ "$DRY_RUN" -eq 1 ]]; then
    cyan "Dry-run: would uninstall have plugins and remove Codex cache."
    exit 0
  fi
  cyan "Uninstalling have plugins..."
  command -v claude >/dev/null 2>&1 && claude plugin uninstall have@have-config 2>/dev/null || true
  command -v claude >/dev/null 2>&1 && claude plugin marketplace remove have-config 2>/dev/null || true
  command -v codex >/dev/null 2>&1 && codex plugin marketplace remove have-config 2>/dev/null || true
  rm -rf "$HOME/.codex/plugins/cache/have-config"
  green "Uninstalled."
  exit 0
fi

bootstrap_dotfiles

# 1. pr-review
cyan "Step 2/6: pr-review"
if [[ "$DRY_RUN" -eq 1 ]]; then
  if [[ -d "$PR_REVIEW_DIR" ]]; then
    cyan "  Dry-run: pr-review exists at $PR_REVIEW_DIR"
  else
    cyan "  Dry-run: would clone pr-review to $PR_REVIEW_DIR"
  fi
else
if [[ ! -d "$PR_REVIEW_DIR" ]]; then
  cyan "  Cloning pr-review to ${PR_REVIEW_DIR}..."
  mkdir -p "$(dirname "$PR_REVIEW_DIR")"
  git clone https://github.com/happyvertical/pr-review.git "$PR_REVIEW_DIR"
else
  cyan "  Already cloned at $PR_REVIEW_DIR (skipping)."
fi
fi

if ! command -v pr-review >/dev/null 2>&1; then
  red "  pr-review not on \$PATH. Add this to your shell rc:"
  red "    export PATH=\"$PR_REVIEW_DIR/bin:\$PATH\""
else
  green "  pr-review on PATH ($(command -v pr-review))"
fi

# 3. Claude marketplace + plugin
cyan "Step 3/6: Claude Code marketplace + have plugin"
if command -v claude >/dev/null 2>&1; then
  if [[ "$DRY_RUN" -eq 1 ]]; then
    cyan "  Dry-run: would ensure Claude marketplace and have@have-config plugin."
  else
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
  fi
  green "  Claude: /have:ship and /have:review-cycle ready."
else
  red "  claude CLI not found; skipping Claude install."
fi

# 4. Codex marketplace
cyan "Step 4/6: Codex marketplace + have plugin"
if command -v codex >/dev/null 2>&1; then
  if [[ "$DRY_RUN" -eq 1 ]]; then
    cyan "  Dry-run: would ensure Codex marketplace and sync have plugin cache."
  else
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

  CODEX_CACHE="$HOME/.codex/plugins/cache/have-config/have/$HAVE_PLUGIN_VERSION"
  CODEX_SOURCE="$REPO_ROOT/codex/plugins/have"
  mkdir -p "$(dirname "$CODEX_CACHE")"
  rm -rf "$CODEX_CACHE"
  cp -R "$CODEX_SOURCE" "$CODEX_CACHE"
  green "  Codex cache synced: $CODEX_CACHE"
  fi

  green "  Codex: have:ship and have:review-cycle skills ready (after restart)."
else
  red "  codex CLI not found; skipping Codex install."
fi

run_agent_resolver() {
  cyan "Step 5/6: agent materialization"

  if ! command -v python3 >/dev/null 2>&1; then
    red "  python3 not found; cannot resolve HappyVertical agent configuration."
    return 1
  fi

  local args=(--have-config-dir "$REPO_ROOT")
  if [[ "$DRY_RUN" -eq 1 ]]; then
    args+=(--dry-run)
  fi

  python3 "$REPO_ROOT/scripts/hv-agent-resolver.py" "${args[@]}"
}

run_agent_resolver

# 6. Live mode (optional)
if [[ "$LIVE" -eq 1 ]]; then
  cyan "Step 6/6: --live mode - symlinking caches to repo"

  if [[ "$DRY_RUN" -eq 1 ]]; then
    cyan "  Dry-run: would symlink Claude and Codex plugin caches to this repo."
    green ""
    green "Dry-run complete."
    exit 0
  fi

  # Claude cache path: ~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/
  CLAUDE_CACHE="$HOME/.claude/plugins/cache/have-config/have/$HAVE_PLUGIN_VERSION"
  CLAUDE_SOURCE="$REPO_ROOT/claude/have"
  if [[ -d "$(dirname "$CLAUDE_CACHE")" ]]; then
    rm -rf "$CLAUDE_CACHE"
    ln -s "$CLAUDE_SOURCE" "$CLAUDE_CACHE"
    green "  Claude cache symlinked: $CLAUDE_CACHE -> $CLAUDE_SOURCE"
    cyan "  (Org fallback edits to $CLAUDE_SOURCE are now live. Context Forge snapshots are resolved by have-config.)"
  else
    red "  Claude cache dir not found at $(dirname "$CLAUDE_CACHE"); install may have failed."
  fi

  CODEX_CACHE="$HOME/.codex/plugins/cache/have-config/have/$HAVE_PLUGIN_VERSION"
  CODEX_SOURCE="$REPO_ROOT/codex/plugins/have"
  if [[ -d "$(dirname "$CODEX_CACHE")" ]]; then
    rm -rf "$CODEX_CACHE"
    ln -s "$CODEX_SOURCE" "$CODEX_CACHE"
    green "  Codex cache symlinked: $CODEX_CACHE -> $CODEX_SOURCE"
  else
    red "  Codex cache dir not found at $(dirname "$CODEX_CACHE"); install may have failed."
  fi
else
  if [[ "$DRY_RUN" -eq 1 ]]; then
    cyan "Step 6/6: dry-run; no live symlinks changed"
  else
    cyan "Step 6/6: skipping --live (pass --live to enable live edits)"
  fi
fi

green ""
green "Done. Restart Claude / Codex sessions to pick up the workflows."
green "Claude: /have:review-cycle"
green "        /have:ship"
green "Codex:  have:review-cycle"
green "        have:ship"
