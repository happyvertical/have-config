#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

HAVE_CONFIG_DIR="$TMP_DIR/have-config"
CONTEXTFORGE_DIR="$TMP_DIR/contextforge"
LOCAL_DIR="$TMP_DIR/local"
HOME_DIR="$TMP_DIR/home"
OUTPUT_DIR="$TMP_DIR/generated"
LOCK_PATH="$TMP_DIR/agent-lock.json"
REPORT_PATH="$TMP_DIR/install-report.md"

mkdir -p "$HAVE_CONFIG_DIR/hv" "$HAVE_CONFIG_DIR/profiles/hermes/commands/codex" \
    "$HAVE_CONFIG_DIR/profiles/hermes/skills/check-setup" "$CONTEXTFORGE_DIR" \
    "$LOCAL_DIR/commands/codex" "$LOCAL_DIR/skills/codex/ship" "$HOME_DIR"

cat > "$HAVE_CONFIG_DIR/hv/manifest.json" <<'JSON'
{
  "schema": "https://happyvertical.com/hv-agent-manifest/v1",
  "layer": "have-config",
  "priority": 20,
  "commands": [
    {
      "agent": "all",
      "name": "review",
      "content": "have-config review"
    }
  ],
  "skills": [
    {
      "agent": "codex",
      "name": "ship",
      "content": "have-config ship"
    }
  ],
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

cat > "$CONTEXTFORGE_DIR/manifest.json" <<'JSON'
{
  "schema": "https://happyvertical.com/hv-agent-manifest/v1",
  "layer": "contextforge",
  "priority": 30,
  "commands": [
    {
      "agent": "codex",
      "name": "review",
      "content": "contextforge review"
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

cat > "$LOCAL_DIR/skills/codex/ship/SKILL.md" <<'EOF'
local ship
EOF

HV_AGENT_PROFILE=hermes python3 "$ROOT_DIR/scripts/hv-agent-resolver.py" \
    --have-config-dir "$HAVE_CONFIG_DIR" \
    --contextforge-dir "$CONTEXTFORGE_DIR" \
    --local-overrides-dir "$LOCAL_DIR" \
    --output-dir "$OUTPUT_DIR" \
    --home-dir "$HOME_DIR" \
    --lock-path "$LOCK_PATH" \
    --report-path "$REPORT_PATH" >/dev/null

grep -q "local review" "$HOME_DIR/.codex/commands/review.md"
grep -q "have-config review" "$HOME_DIR/.claude/commands/review.md"
grep -q "local ship" "$HOME_DIR/.agents/skills/ship/SKILL.md"
grep -q "hermes check setup" "$HOME_DIR/.codex/commands/check-setup.md"
grep -q "hermes check setup skill" "$HOME_DIR/.agents/skills/check-setup/SKILL.md"
grep -q "potential must/must-not conflict" "$REPORT_PATH"
grep -q '"key": "codex:command:review"' "$LOCK_PATH"

if HV_ENABLED_CAPABILITIES=identity python3 "$ROOT_DIR/scripts/hv-agent-resolver.py" \
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

echo "hv-agent-resolver tests passed"
