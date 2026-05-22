# have-config

HappyVertical shared cross-repo configuration for agent-assisted development.

This repo is the umbrella for configuration that ≥2 HappyVertical projects
consume. Today that's slash commands for Claude Code and Codex. Other
shared config (MCP servers, agent hooks, lint/format/tsconfig bases) will
land here as second consumers appear.

## What lives here

**In scope:**

- Slash commands for Claude Code and Codex (`claude/`, `codex/`)
- Shared lint / format / tsconfig configs as published npm packages
  (`packages/eslint-config`, `packages/prettier-config`,
  `packages/tsconfig-base`)
- MCP server configs consumed by ≥2 projects (planned — `TODO.md`)
- Agent hook scripts (planned — `TODO.md`)
- CLAUDE.md / AGENTS.md template sections that should be identical across
  repos (planned — `TODO.md`)

**Out of scope:**

- Runnable tools — these get their own repos (see
  [`happyvertical/pr-review`](https://github.com/happyvertical/pr-review))
- Per-repo specifics (e.g. anytown's
  `apps/dashboard/docs/ad-network.md`)
- Anything used by exactly one project
- Project source code

The scope rule exists to prevent kitchen-sink rot. If you're tempted to
add something used by only one repo, put it in that repo.

## Layout

```
have-config/
├── README.md
├── LICENSE
├── install.sh                       # one-line setup (agents)
├── TODO.md                          # planned additions, with consumer count
├── package.json                     # pnpm workspace root
├── pnpm-workspace.yaml
├── .changeset/                      # versioning + publish manifests
│   └── config.json
├── claude/                          # Claude Code marketplace
│   ├── .claude-plugin/
│   │   └── marketplace.json
│   └── have/                        # the `have` plugin
│       ├── .claude-plugin/
│       │   └── plugin.json
│       └── commands/
│           ├── ship.md              # /have:ship
│           └── review-cycle.md      # /have:review-cycle
├── codex/                           # Codex marketplace
│   └── plugins/
│       └── have/                    # the `have` plugin
│           ├── .codex-plugin/
│           │   └── plugin.json
│           └── commands/
│               ├── ship.md          # /have:ship
│               └── review-cycle.md  # /have:review-cycle
└── packages/                        # published npm configs
    ├── eslint-config/               # @happyvertical/eslint-config
    ├── prettier-config/             # @happyvertical/prettier-config
    └── tsconfig-base/               # @happyvertical/tsconfig-base
```

## Published packages

The `@happyvertical/*` scope publishes to **GitHub Packages**, not
npmjs.org (matching the org standard used by smrt, sdk, etc.). To install
from a consuming repo, you need an `.npmrc` that routes the scope to GH
Packages and provides auth:

```ini
# .npmrc in the consuming repo (and/or ~/.npmrc for local dev)
@happyvertical:registry=https://npm.pkg.github.com
//npm.pkg.github.com/:_authToken=${NODE_AUTH_TOKEN}
```

Set `NODE_AUTH_TOKEN` to:
- **In CI**: `${{ secrets.GITHUB_TOKEN }}` (or a token from the
  `HAVE_RELEASE` GitHub App for cross-repo installs)
- **Locally**: a personal access token with `read:packages` scope

Then install:

```bash
pnpm add -D \
  @happyvertical/eslint-config \
  @happyvertical/prettier-config \
  @happyvertical/tsconfig-base \
  eslint prettier typescript
```

See each package's README for usage details:

| Package | Purpose |
|---|---|
| [`@happyvertical/eslint-config`](packages/eslint-config) | Type-aware ESLint flat config with optional Svelte 5 preset |
| [`@happyvertical/prettier-config`](packages/prettier-config) | Org-wide Prettier rules |
| [`@happyvertical/tsconfig-base`](packages/tsconfig-base) | Strict TypeScript baselines (app, lib, test variants) |

Configs are versioned via Changesets and published on merge to `main`.

## Plugin install (slash commands)

```bash
git clone https://github.com/happyvertical/have-config.git ~/Work/happyvertical/repos/have-config
cd ~/Work/happyvertical/repos/have-config
./install.sh
```

`install.sh` does:

1. Clones [`happyvertical/pr-review`](https://github.com/happyvertical/pr-review)
   if missing, adds `pr-review/bin` to a shell-rc snippet.
2. Registers this repo as a marketplace for both Claude Code and Codex.
3. Installs the `have` plugin in both agents.
4. Optionally symlinks the cached plugin install back to the live repo
   path for in-place editing (`./install.sh --live`).

After install, both agents have:

- `/have:ship` — end-to-end shipping pipeline
- `/have:review-cycle` — multi-tool review/fix/retest loop

## Editing

The repo is the source of truth. Edits to `claude/have/commands/*.md` or
`codex/plugins/have/commands/*.md` are picked up:

- **Live mode** (`install.sh --live`): edits are immediately visible to
  running sessions via symlink. May need re-linking after
  `claude plugin update` rewrites the cache.
- **Standard mode**: edits require `claude plugin update have@have-config`
  (and the codex equivalent) to refresh the installed copy.

## Companion tool

The shipping/review commands generate review prompts via
[`pr-review`](https://github.com/happyvertical/pr-review). pr-review stays
a standalone tool because it has a broader audience (anyone running
pre-PR review with any LLM, regardless of harness). have-config wraps
pr-review in opinionated workflow commands; pr-review itself is unopinionated.

## License

MIT.
