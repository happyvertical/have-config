# have-config

HappyVertical shared cross-repo configuration for agent-assisted development.

This repo is the umbrella for configuration that ≥2 HappyVertical projects
consume. Today that's slash commands for Claude Code and Codex. Other
shared config (MCP servers, agent hooks, lint/format/tsconfig bases) will
land here as second consumers appear.

## What lives here

**In scope:**

- Slash commands for Claude Code and Codex (`claude/`, `codex/`)
- MCP server configs consumed by ≥2 projects (planned)
- Agent hook scripts (planned)
- Shared lint / format / tsconfig bases (planned, when a second consumer
  emerges — until then each repo keeps its own)
- CLAUDE.md / AGENTS.md template sections that should be identical across
  repos (planned — currently each repo carries its own copy)

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
├── install.sh                       # one-line setup
├── TODO.md                          # planned additions, with consumer count
├── claude/                          # Claude Code marketplace
│   ├── .claude-plugin/
│   │   └── marketplace.json
│   └── have/                        # the `have` plugin
│       ├── .claude-plugin/
│       │   └── plugin.json
│       └── commands/
│           ├── ship.md              # /have:ship
│           └── review-cycle.md      # /have:review-cycle
└── codex/                           # Codex marketplace
    └── plugins/
        └── have/                    # the `have` plugin
            ├── .codex-plugin/
            │   └── plugin.json
            └── commands/
                ├── ship.md          # /have:ship
                └── review-cycle.md  # /have:review-cycle
```

## Install

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
