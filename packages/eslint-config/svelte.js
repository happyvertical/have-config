/**
 * @happyvertical/eslint-config/svelte
 *
 * Extends `base` with Svelte 5 support. `eslint-plugin-svelte` and
 * `svelte-eslint-parser` ship as optionalDependencies of this package
 * and will be installed transitively under normal `pnpm install`. The
 * only true peer the consumer must install themselves is `svelte`.
 *
 * If your install uses `--no-optional` (or another package manager that
 * treats optionalDependencies differently), add the plugin + parser as
 * direct devDependencies.
 *
 * Usage:
 *   import base from '@happyvertical/eslint-config/base';
 *   import svelte from '@happyvertical/eslint-config/svelte';
 *   export default [...base, ...svelte, { ...project overrides }];
 *
 * Notes on Svelte 5 specifics (see anytown's .pr-review/extensions.md and
 * smrt's CLAUDE.md for the full discipline):
 *   - `$state` proxies break `===` equality with the original input
 *   - `$app/navigation` is client-only — guard with `if (browser)` in SSR
 *   - `$props()` with inline intersected generics triggers TS recursion;
 *     export an explicit interface instead
 *   - Avoid `<script>` inside JSDoc examples in .svelte files
 *
 * These are project-level review concerns, not lint rules — pr-review
 * catches them. This config handles the mechanical stuff.
 */

import svelteParser from 'svelte-eslint-parser';
import sveltePlugin from 'eslint-plugin-svelte';
import tseslint from 'typescript-eslint';

/** @type {import('eslint').Linter.Config[]} */
const config = [
  ...sveltePlugin.configs['flat/recommended'],

  {
    files: ['**/*.svelte', '**/*.svelte.ts', '**/*.svelte.js'],
    languageOptions: {
      parser: svelteParser,
      parserOptions: {
        parser: tseslint.parser,
        projectService: true,
        extraFileExtensions: ['.svelte'],
        svelteFeatures: {
          experimentalGenerics: true,
        },
      },
    },
    rules: {
      // Type-aware rules don't work inside .svelte files reliably; disable
      // the ones that produce noise without type info.
      '@typescript-eslint/no-unsafe-argument': 'off',
      '@typescript-eslint/no-unsafe-assignment': 'off',
      '@typescript-eslint/no-unsafe-call': 'off',
      '@typescript-eslint/no-unsafe-member-access': 'off',
      '@typescript-eslint/no-unsafe-return': 'off',
    },
  },
];

export default config;
