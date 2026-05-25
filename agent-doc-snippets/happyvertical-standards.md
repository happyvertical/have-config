# HappyVertical Organization Standards

## Source Layers
- Treat `dotfiles` as the personal baseline for workstation and agent bootstrap.
- Treat `have-config` as the HappyVertical organization standard for shared agent behavior, infrastructure docs, and reusable development config.
- Treat Context Forge snapshots as dynamic organization policy materialized during install/update.
- Treat machine-local overrides as explicit exceptions that must be visible in install reports.

## Runtime Behavior
- Agents must use local installed command, skill, and instruction files at runtime.
- Agents should not depend on live Context Forge access during normal task execution.
- When command or skill definitions conflict, use this order: local override, Context Forge snapshot, `have-config`, then `dotfiles`.
- AGENTS and CLAUDE instructions are cumulative; do not discard lower-layer instructions unless a higher layer explicitly supersedes them.

## Identity And Secrets
- Account identity is per user or per agent. Do not commit account-specific addresses, tokens, or passwords.
- Use `idp.happyvertical.com` for HappyVertical identity and SSO.
- Use Warden for password sharing and retrieval.
- Use SOPS only for machine-provided encrypted environment material and templates; do not place real user-specific values in this repo.

## HappyVertical Services
- Use `warden.happyvertical.com` for approved password and shared secret access.
- Use `drive.happyvertical.com` for OxiCloud file sharing.
- Use `todo.happyvertical.com` for Vikunja project management.
- Use `chat.happyvertical.com` (Zulip) for primary chat and collaboration; Hermes agents should enable `platforms.zulip.enabled: true`, use per-agent Zulip account API credentials, and long-poll events when chat response is enabled.
- Treat `stoat.happyvertical.com` as legacy/superseded chat unless a task explicitly asks for Stoat.
- Use `bifrost.happyvertical.com` as the gateway.
- Use `context.happyvertical.com` for prompts, resources, and memory snapshots.
- Hermes agents run `check-setup` after bootstrap or account changes to verify service access.
