# HappyVertical Infrastructure

This document is the organization-level map of services that agents and humans
should expect when working in HappyVertical environments. Account credentials are
per user or per agent and must stay out of git.

## Services

| Service | URL | Purpose | CLI status |
| --- | --- | --- | --- |
| Email | per-account | Human and agent identity | Account-specific |
| HappyVertical IDP | `https://idp.happyvertical.com` | Identity provider and SSO | Verify through browser/session or available connector |
| Warden | `https://warden.happyvertical.com` | Password and shared secret access | Credential source; never print secret values |
| OxiCloud | `https://drive.happyvertical.com` | File sharing | Use WebDAV-capable tooling such as `rclone` |
| Analytics | `https://matomo.happyvertical.com` / Plausible | Project analytics | Use per-agent API tokens only when enabled by contract |
| Storage | Garage/S3 | Scoped object storage | Use bucket-scoped S3 keys; never give agents Garage admin credentials |
| Vikunja | `https://todo.happyvertical.com` | Project management | Use `hv-services vikunja` or the HappyVertical API wrapper with `HV_VIKUNJA_TOKEN`; the official CLI is server/container admin focused |
| Zulip | `https://chat.happyvertical.com` | Primary team chat and agent-response channel | Hermes gateway long-poll adapter with per-agent Zulip account API credentials; use `/api/v1/typing` while processing |
| Stoat | `https://stoat.happyvertical.com` | Legacy chat and collaboration | Superseded by Zulip unless explicitly requested |
| Bifrost | `https://bifrost.happyvertical.com` | Gateway | No standard CLI selected yet |
| Context Forge | `https://context.happyvertical.com` | Prompts, resources, and memory | Export install-time snapshots |

## Secrets And Accounts

- Every workstation and Hermes agent has its own account identity.
- Passwords and shared credentials should be distributed through Warden.
- SOPS may be used for machine-local encrypted environment files, but committed
  repos should only contain templates and non-secret policy.
- Project Hermes identity, repo scope, permissions, Vikunja board, SOPS profile,
  and runtime expectations should be declared in a non-secret Hermes agent
  contract.
- Optional service credentials such as OxiCloud WebDAV, analytics API tokens,
  and Garage/S3 keys should be declared in contract `service_access`, stored as
  Warden/SOPS references, and scoped to the named project or bucket.
- Put only mandatory runtime names in `service_access.<service>.runtime_env`.
  Put aliases or convenience names such as alternate AWS region/profile/env
  variables in `optional_runtime_env` so setup checks do not block valid
  configurations.
- Installers may hard-fail missing environment variables only for capabilities
  explicitly enabled with `HV_ENABLED_CAPABILITIES`.

## Context Forge Snapshot Policy

Context Forge is the dynamic source for organization prompt and resource policy.
Installers should materialize snapshots into local generated files and record
the selected content hash in `agent-lock.json`. Runtime agent behavior should
not require live Context Forge access.

## Reusable Operational Scripts

have-config can materialize reusable operational scripts declared in
`hv/manifest.json`. Current Hermes no-agent scripts poll Vikunja task updates
and GitHub open issues labeled `cricket`; credentials must come from local
environment variables or approved secret tooling.
