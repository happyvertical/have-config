#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

DOTFILES_DIR="$TMP_DIR/dotfiles"
HAVE_CONFIG_DIR="$TMP_DIR/have-config"
CONTEXTFORGE_DIR="$TMP_DIR/contextforge"
LOCAL_DIR="$TMP_DIR/local"
HOME_DIR="$TMP_DIR/home"
OUTPUT_DIR="$TMP_DIR/generated"
LOCK_PATH="$TMP_DIR/agent-lock.json"
REPORT_PATH="$TMP_DIR/install-report.md"

mkdir -p "$DOTFILES_DIR/agent" "$DOTFILES_DIR/.agents/commands/codex" \
    "$DOTFILES_DIR/.agents/commands/claude" "$DOTFILES_DIR/.agents/skills/ship" \
    "$DOTFILES_DIR/.agents/skills/review-cycle" "$HAVE_CONFIG_DIR/hv" "$HAVE_CONFIG_DIR/profiles/hermes/commands/codex" \
    "$HAVE_CONFIG_DIR/profiles/hermes/skills/check-setup" "$HAVE_CONFIG_DIR/services" "$CONTEXTFORGE_DIR" \
    "$LOCAL_DIR/commands/codex" "$LOCAL_DIR/skills/codex/ship" "$HOME_DIR"
mkdir -p "$HOME_DIR/.claude"

cat > "$DOTFILES_DIR/agent/manifest.json" <<'JSON'
{
  "schema": "https://example.test/agent-manifest/v1",
  "layer": "dotfiles",
  "priority": 10,
  "commands": [
    {
      "agent": "codex",
      "name": "review-cycle",
      "path": ".agents/commands/codex/review-cycle.md"
    },
    {
      "agent": "claude",
      "name": "review-cycle",
      "path": ".agents/commands/claude/review-cycle.md"
    }
  ],
  "skills": [
    {
      "agent": "codex",
      "name": "ship",
      "path": ".agents/skills/ship"
    },
    {
      "agent": "codex",
      "name": "review-cycle",
      "path": ".agents/skills/review-cycle"
    }
  ],
  "agent_docs": [
    {
      "id": "dotfiles.test",
      "targets": ["agents"],
      "content": "Agents may use dotfiles-baseline."
    }
  ]
}
JSON

cat > "$DOTFILES_DIR/.agents/commands/codex/review-cycle.md" <<'EOF'
dotfiles codex review-cycle
EOF

cat > "$DOTFILES_DIR/.agents/commands/claude/review-cycle.md" <<'EOF'
dotfiles claude review-cycle
EOF

cat > "$DOTFILES_DIR/.agents/skills/ship/SKILL.md" <<'EOF'
dotfiles ship
EOF

cat > "$DOTFILES_DIR/.agents/skills/review-cycle/SKILL.md" <<'EOF'
dotfiles review-cycle skill
EOF

cat > "$HAVE_CONFIG_DIR/hv/manifest.json" <<'JSON'
{
  "schema": "https://happyvertical.com/hv-agent-manifest/v1",
  "layer": "have-config",
  "priority": 20,
  "commands": [],
  "skills": [],
  "agent_docs": [
    {
      "id": "have-config.test",
      "targets": ["agents"],
      "content": "Agents must use fixture-order."
    }
  ],
  "env_requirements": [
    {
      "capability": "identity",
      "vars": ["HV_AGENT_EMAIL"],
      "default_enabled": false
    }
  ]
}
JSON

cat > "$HAVE_CONFIG_DIR/profiles/hermes/manifest.json" <<'JSON'
{
  "schema": "https://happyvertical.com/hv-agent-manifest/v1",
  "layer": "profile:hermes",
  "priority": 25,
  "commands": [
    {
      "agent": "codex",
      "name": "check-setup",
      "path": "commands/codex/check-setup.md"
    }
  ],
  "skills": [
    {
      "agent": "codex",
      "name": "check-setup",
      "path": "skills/check-setup"
    }
  ]
}
JSON

cat > "$HAVE_CONFIG_DIR/profiles/hermes/commands/codex/check-setup.md" <<'EOF'
hermes check setup
EOF

cat > "$HAVE_CONFIG_DIR/profiles/hermes/skills/check-setup/SKILL.md" <<'EOF'
hermes check setup skill
EOF

cat > "$HAVE_CONFIG_DIR/services/services.json" <<'JSON'
{
  "schema": "https://happyvertical.com/service-registry/v1",
  "services": [
    {
      "id": "fixture-service",
      "name": "Fixture Service",
      "url": "https://fixture.example.test",
      "cli": {
        "status": "test-only"
      }
    }
  ]
}
JSON

cat > "$CONTEXTFORGE_DIR/manifest.json" <<'JSON'
{
  "schema": "https://happyvertical.com/hv-agent-manifest/v1",
  "layer": "contextforge",
  "priority": "dynamic",
  "commands": [
    {
      "agent": "codex",
      "name": "review-cycle",
      "content": "contextforge review-cycle"
    }
  ],
  "skills": [
    {
      "agent": "codex",
      "name": "ship",
      "content": "contextforge ship"
    }
  ],
  "agent_docs": [
    {
      "id": "contextforge.test",
      "targets": ["codex"],
      "content": "Agents must not use fixture-order."
    }
  ]
}
JSON

cat > "$LOCAL_DIR/commands/codex/review.md" <<'EOF'
local review
EOF

cat > "$LOCAL_DIR/commands/codex/review-cycle.md" <<'EOF'
local review-cycle
EOF

cat > "$LOCAL_DIR/skills/codex/ship/SKILL.md" <<'EOF'
local ship
EOF

cat > "$HOME_DIR/.claude/CLAUDE.md" <<'EOF'
local claude note
EOF

HV_AGENT_PROFILE=hermes python3 "$ROOT_DIR/scripts/hv-agent-resolver.py" \
    --dotfiles-dir "$DOTFILES_DIR" \
    --have-config-dir "$HAVE_CONFIG_DIR" \
    --contextforge-dir "$CONTEXTFORGE_DIR" \
    --local-overrides-dir "$LOCAL_DIR" \
    --output-dir "$OUTPUT_DIR" \
    --home-dir "$HOME_DIR" \
    --lock-path "$LOCK_PATH" \
    --report-path "$REPORT_PATH" >/dev/null

grep -q "local review-cycle" "$HOME_DIR/.codex/commands/review-cycle.md"
grep -q "dotfiles claude review-cycle" "$HOME_DIR/.claude/commands/review-cycle.md"
grep -q "local ship" "$HOME_DIR/.agents/skills/ship/SKILL.md"
grep -q "dotfiles review-cycle skill" "$HOME_DIR/.agents/skills/review-cycle/SKILL.md"
grep -q "hermes check setup" "$HOME_DIR/.codex/commands/check-setup.md"
grep -q "hermes check setup skill" "$HOME_DIR/.agents/skills/check-setup/SKILL.md"
grep -q "local claude note" "$LOCAL_DIR/agent-docs/CLAUDE.md"
grep -q "local claude note" "$HOME_DIR/.claude/CLAUDE.md"
grep -q "potential must/must-not conflict" "$REPORT_PATH"
grep -q '"key": "codex:command:review-cycle"' "$LOCK_PATH"
grep -q '`dotfiles` priority 10: available' "$REPORT_PATH"
grep -q "invalid declared priority 'dynamic' ignored; using fixed 30" "$REPORT_PATH"
grep -q '`fixture-service` https://fixture.example.test CLI: test-only (source: services/services.json)' "$REPORT_PATH"
grep -q '"id": "fixture-service"' "$LOCK_PATH"
grep -q 'skills/codex/<name>/SKILL.md' "$LOCAL_DIR/README.md"

if HV_ENABLED_CAPABILITIES=identity python3 "$ROOT_DIR/scripts/hv-agent-resolver.py" \
    --dotfiles-dir "$DOTFILES_DIR" \
    --have-config-dir "$HAVE_CONFIG_DIR" \
    --contextforge-dir "$CONTEXTFORGE_DIR" \
    --local-overrides-dir "$LOCAL_DIR" \
    --output-dir "$TMP_DIR/generated-env-failure" \
    --home-dir "$TMP_DIR/home-env-failure" \
    --lock-path "$TMP_DIR/env-failure-lock.json" \
    --report-path "$TMP_DIR/env-failure-report.md" >/dev/null 2>&1; then
    echo "Expected missing HV_AGENT_EMAIL to fail when identity capability is enabled" >&2
    exit 1
fi

EXPLICIT_HOME="$TMP_DIR/explicit-home"
mkdir -p "$EXPLICIT_HOME"
EXPLICIT_HOME="$(cd "$EXPLICIT_HOME" && pwd -P)"
HOME="$EXPLICIT_HOME" python3 "$ROOT_DIR/scripts/hv-agent-resolver.py" \
    --profiles hermes \
    --dotfiles-dir "$DOTFILES_DIR" \
    --have-config-dir "$HAVE_CONFIG_DIR" \
    --contextforge-dir "$CONTEXTFORGE_DIR" \
    --dry-run >/dev/null

grep -q '`profile:hermes` priority 25: available' "$EXPLICIT_HOME/.hermes/install-report.md"
grep -q "would ensure local override directories under \`$EXPLICIT_HOME/.hermes/overrides\`" "$EXPLICIT_HOME/.hermes/install-report.md"

echo "hv-agent-resolver tests passed"
