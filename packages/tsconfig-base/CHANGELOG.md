# @happyvertical/tsconfig-base

## 0.2.0

### Minor Changes

- 4026431: Initial release of HappyVertical shared configs.
  - **@happyvertical/tsconfig-base**: strict, type-aware, ESM-first TypeScript baselines. Variants for application (`tsconfig.base.json`), publishable library (`tsconfig.lib.json` with composite + declarations), and tests (`tsconfig.test.json` with vitest + node types).
  - **@happyvertical/prettier-config**: org-wide Prettier config. 2-space indent, single quotes, 80-char width, trailing commas, LF line endings. Overrides for JSON (no trailing commas), Markdown (preserve prose wrap), YAML (double quotes).
  - **@happyvertical/eslint-config**: ESLint 9+ flat config with type-aware TypeScript rules (`strictTypeChecked` + `stylisticTypeChecked`), prettier compatibility, and HappyVertical conventions (consistent-type-imports, `_`-prefixed unused vars). Optional Svelte 5 preset via `@happyvertical/eslint-config/svelte`.

  Consume independently or together. Type-aware linting requires `parserOptions.projectService: true` which the config sets by default.
