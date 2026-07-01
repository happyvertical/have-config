# have-config — planned additions

Things that *could* live here when a second consumer emerges. Listed so
contributors don't add them prematurely (kitchen-sink rot) but know where
to put them when the time comes.

Admission rule: a config goes in have-config when **≥2 repos** in the
HappyVertical org would consume it. Until then, keep it in the one repo
that needs it.

## Slash commands and agent surfaces

- [x] `hv/manifest.json` — org-owned agent docs, env requirements, and service
      metadata consumed by the resolver
- [x] `profiles/hermes/` — Hermes-only commands and skills such as
      `check-setup`
- [x] `reusable-scripts/hermes/no-agent/` — reusable notification scripts for
      Hermes Vikunja task updates and GitHub `cricket`-labeled issue updates
- [ ] `claude/` / `codex/` packaged surfaces, only if a future second
      consumer needs marketplace/plugin distribution instead of generated local
      files
- [ ] `cursor/` — Cursor commands, when there's a second project using
      Cursor as the primary IDE

## Shared MCP server configs

- [ ] `mcp/` — server configs consumed by ≥2 repos. Candidates:
      `playwright`, `chrome-devtools`, project-specific MCPs.

## Agent hooks

- [ ] `hooks/` — pre-/post-tool-use hooks consumed by ≥2 repos.
- [x] `scripts` manifest entries — reusable operational scripts materialized
      by the resolver and linked into `~/.local/bin` when executable

## Lint / format / build bases

- [x] `packages/eslint-config/` — ESLint flat config (type-aware) +
      optional Svelte 5 preset
- [x] `packages/prettier-config/` — org-wide Prettier rules
- [x] `packages/tsconfig-base/` — strict TS baseline (app + lib + test
      variants)
- [ ] `packages/tsconfig-base/tsconfig.browser.json` — variant with
      `lib: ["ES2022", "DOM", "DOM.Iterable"]` and
      `moduleResolution: "Bundler"`, intended for SvelteKit / Vite /
      other browser projects. Add when there's a second browser
      consumer (right now anytown is the main one; smrt-svelte will be
      the second). Currently consumers extend `tsconfig.base.json` and
      override `lib` in their own tsconfig — see tsconfig-base/README.
- [ ] `packages/commitlint-config/` — shared commitlint config (currently
      smrt has its own; lift here if other repos adopt)
- [ ] `packages/editorconfig/` or `templates/.editorconfig` —
      shared `.editorconfig` template

Consumption mechanism for shared configs: **published as npm packages**
to GitHub Packages (`npm.pkg.github.com`) under the `@happyvertical`
scope. Renovate keeps consumers current.

Pick when the first consumer pair exists, not before.

## CLAUDE.md / AGENTS.md template sections

- [x] `agent-doc-snippets/` — durable policy text that should be
      identical across repos:
      - HappyVertical source layering
      - runtime behavior
      - identity and secrets
      - service map

      The have-config resolver assembles these snippets with active profiles,
      Context Forge snapshots, and local overrides.

## Service registry and infrastructure docs

- [x] `docs/infrastructure.md` — HappyVertical service map for humans and agents
- [x] `docs/agent-playbook.md` — agent-facing guide for which service to use
      for identity, secrets, files, tasks, chat, gateway access, and memory
- [x] `services/services.json` — machine-readable service registry consumed by
      have-config reports

## Context Forge snapshots

- [x] `hv/manifest.json` — source manifest consumed by have-config
- [x] `profiles/hermes/manifest.json` — Hermes-only defaults such as
      `check-setup`
- [x] Hermes `hermes-ops` skill — scheduled Vikunja pickup state,
      blocked-task recovery, and watcher setup
- [x] Hermes `hermes-manager` skill — Dev Team Mode manager behavior for
      local worker dispatch, board state, and live integration
- [x] Hermes `hermes-board` skill — GitHub Projects board #7 pickup and
      lane-lifecycle procedure (`docs/hermes-github-project-board.md`)
- [x] `hv-hermes-dev-team-manager` — Dev Team Mode sidecar for Vikunja board
      provisioning, worker dispatch, and worker process status
- [ ] Publish an exporter from Context Forge into the manifest shape expected by
      have-config (`manifest.json` with `skills`, `commands`, and `agent_docs`).
