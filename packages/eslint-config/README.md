# @happyvertical/eslint-config

Type-aware ESLint flat config for HappyVertical projects. ESLint 9+.

## Install

```bash
pnpm add -D @happyvertical/eslint-config eslint typescript
```

## Usage

### TypeScript projects (the common case)

```js
// eslint.config.js
import base from '@happyvertical/eslint-config/base';

export default [
  ...base,
  // project overrides
];
```

### Svelte 5 projects

Install the optional peers:

```bash
pnpm add -D eslint-plugin-svelte svelte-eslint-parser svelte
```

Then:

```js
// eslint.config.js
import base from '@happyvertical/eslint-config/base';
import svelte from '@happyvertical/eslint-config/svelte';

export default [
  ...base,
  ...svelte,
  // project overrides
];
```

## What's in `base`

- `@eslint/js/recommended`
- `typescript-eslint`'s `strictTypeChecked` + `stylisticTypeChecked` (type-aware)
- `eslint-config-prettier` (disables stylistic rules Prettier handles)
- HappyVertical overrides:
  - `consistent-type-imports` (separate type imports)
  - `no-unused-vars` (allow `_`-prefixed)
  - `no-console: warn` (allow `console.warn` / `console.error`)
- Test files relax unsafe-* rules
- Common ignores: `node_modules/`, `dist/`, `build/`, `coverage/`, `.turbo/`, `.svelte-kit/`, `.vite/`, `*.d.ts`

## What's in `svelte`

- `eslint-plugin-svelte`'s `flat/recommended`
- Svelte file parser config (with `experimentalGenerics`)
- Disables type-aware unsafe-* rules inside `.svelte` files where type info isn't reliable

## Type-aware setup

The config sets `parserOptions.projectService: true`, which makes
typescript-eslint discover each file's owning tsconfig automatically.
Most projects need no further setup. If you have a non-standard tsconfig
layout, override:

```js
export default [
  ...base,
  {
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
    },
  },
];
```

## Companion configs

Use alongside:

- [`@happyvertical/tsconfig-base`](../tsconfig-base) — strict TS baseline
- [`@happyvertical/prettier-config`](../prettier-config) — formatting

## License

MIT.
