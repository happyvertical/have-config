# have-config — planned additions

Things that *could* live here when a second consumer emerges. Listed so
contributors don't add them prematurely (kitchen-sink rot) but know where
to put them when the time comes.

Admission rule: a config goes in have-config when **≥2 repos** in the
HappyVertical org would consume it. Until then, keep it in the one repo
that needs it.

## Slash commands and agent surfaces

- [x] `claude/` — Claude Code `have` plugin
- [x] `codex/plugins/have/` — Codex `have` plugin
- [ ] `cursor/` — Cursor commands, when there's a second project using
      Cursor as the primary IDE

## Shared MCP server configs

- [ ] `mcp/` — server configs consumed by ≥2 repos. Candidates:
      `playwright`, `chrome-devtools`, project-specific MCPs.

## Agent hooks

- [ ] `hooks/` — pre-/post-tool-use hooks consumed by ≥2 repos.

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

- [ ] `agent-doc-snippets/` — durable policy text that should be
      identical across repos:
      - No Workarounds Policy
      - No Private API Reach-Ins
      - Git Workflow SOPs
      - Git And PR SOP
      - Review Readiness
      
      Today every repo carries its own copy and drift is a recurring
      problem. Lifting these into snippets would require a
      consumption mechanism (probably a generator script that
      assembles each repo's CLAUDE.md from snippets + repo-specific
      sections).
