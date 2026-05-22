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

- [ ] `biome/biome.json` — when ≥2 repos want identical Biome config
- [ ] `tsconfig/base.json` — shared tsconfig base
- [ ] `commitlint/index.js` — shared commitlint config (currently
      smrt has its own enforced; if other repos adopt, lift here)
- [ ] `editorconfig` — shared `.editorconfig`

Consumption mechanism is TBD per config. Likely either:
- Publish as npm packages (`@happyvertical/biome-config`, etc.), each
  repo depends via package.json; or
- Bootstrap script that copies/symlinks at repo init.

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
