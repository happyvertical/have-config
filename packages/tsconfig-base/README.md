# @happyvertical/tsconfig-base

Shared TypeScript configurations for HappyVertical projects: strict,
type-aware, ESM-first, opinionated.

## Install

```bash
pnpm add -D @happyvertical/tsconfig-base
```

## Usage

Pick the variant that matches what you're building.

### Application (Node service, internal tool)

```jsonc
// tsconfig.json
{
  "extends": "@happyvertical/tsconfig-base/tsconfig.base.json",
  "compilerOptions": {
    "outDir": "./dist",
    "rootDir": "./src"
  },
  "include": ["src/**/*"]
}
```

> **Browser / SvelteKit projects**: the base sets `lib: ["ES2022"]` only
> (no DOM types). For browser apps, add the browser libs in your project
> tsconfig:
>
> ```jsonc
> {
>   "extends": "@happyvertical/tsconfig-base/tsconfig.base.json",
>   "compilerOptions": {
>     "lib": ["ES2022", "DOM", "DOM.Iterable"],
>     "moduleResolution": "Bundler"
>   }
> }
> ```
>
> A dedicated `tsconfig.browser.json` variant is planned (see `TODO.md`
> in have-config) once a second browser/SvelteKit consumer emerges.

### Publishable library (npm package)

```jsonc
// tsconfig.json
{
  "extends": "@happyvertical/tsconfig-base/tsconfig.lib.json",
  "compilerOptions": {
    "outDir": "./dist",
    "rootDir": "./src",
    "types": ["node"]
  },
  "include": ["src/**/*"]
}
```

Adds `declaration`, `declarationMap`, `sourceMap`, `composite`, and
`noEmitOnError` on top of the base.

### Test files (vitest)

```jsonc
// tsconfig.test.json
{
  "extends": "@happyvertical/tsconfig-base/tsconfig.test.json"
}
```

Adds `vitest/globals` and `node` types, sets `noEmit`, includes `**/*.test.ts`
and `**/*.spec.ts` patterns.

## What's enforced

- `strict: true` — all strict checks on
- `noUncheckedIndexedAccess: true` — array/record access returns `T | undefined`
- `noImplicitOverride: true` — must mark `override` explicitly
- `noFallthroughCasesInSwitch: true`
- ESM-first: `module: ESNext`, `moduleResolution: Bundler`
- `target: ES2022` (Node 18+ baseline; org standard is Node 24)
- `isolatedModules: true` — required for tooling like esbuild, swc, ts-loader
- `forceConsistentCasingInFileNames: true`

## What's not opinionated here

Set in your project's `tsconfig.json`:

- `outDir` / `rootDir`
- `paths` aliases
- `types` (which @types packages to include)
- Framework-specific settings (Svelte, React, etc.)

## License

MIT.
