#!/usr/bin/env bash
#
# install.sh - one-line setup for have-config.
#
# Does:
#   1. Clones/updates dotfiles and runs dotfiles/install.sh for base tooling.
#   2. Ensures pr-review is cloned and on $PATH.
#   3. Resolves dotfiles/org/profile/Context Forge/local agent material.
#
# Usage:
#   ./install.sh              # standard install
#   ./install.sh --dry-run    # audit without changing generated files
#   ./install.sh --skip-dotfiles
#   ./install.sh -h           # help
#
set -euo pipefail

DRY_RUN=0
SKIP_DOTFILES="${HAVE_CONFIG_SKIP_DOTFILES:-0}"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run|--audit) DRY_RUN=1; shift ;;
    --skip-dotfiles) SKIP_DOTFILES=1; shift ;;
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

if [[ -d "$PR_REVIEW_DIR/bin" && ":$PATH:" != *":$PR_REVIEW_DIR/bin:"* ]]; then
  export PATH="$PR_REVIEW_DIR/bin:$PATH"
fi

cyan() { printf "\033[36m%s\033[0m\n" "$*"; }
green() { printf "\033[32m%s\033[0m\n" "$*"; }
red() { printf "\033[31m%s\033[0m\n" "$*" >&2; }

bootstrap_dotfiles() {
  cyan "Step 1/3: dotfiles baseline"

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

bootstrap_dotfiles

cyan "Step 2/3: pr-review"
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

run_agent_resolver() {
  cyan "Step 3/3: agent materialization"

  if ! command -v python3 >/dev/null 2>&1; then
    red "  python3 not found; cannot resolve HappyVertical agent configuration."
    return 1
  fi

  local args=(--dotfiles-dir "$DOTFILES_DIR" --have-config-dir "$REPO_ROOT")
  if [[ "$DRY_RUN" -eq 1 ]]; then
    args+=(--dry-run)
  fi

  python3 "$REPO_ROOT/scripts/hv-agent-resolver.py" "${args[@]}"
}

run_agent_resolver

green ""
green "Done. Restart Claude / Codex sessions to pick up generated commands and skills."
