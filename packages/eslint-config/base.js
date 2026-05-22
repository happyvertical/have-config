/**
 * @happyvertical/eslint-config/base
 *
 * Type-aware TypeScript baseline for HappyVertical projects.
 *
 * Uses the flat config format (ESLint 9+). Consumers spread this into
 * their `eslint.config.js`:
 *
 *   import base from '@happyvertical/eslint-config/base';
 *   export default [...base, { files: ['src/**'], ... }];
 *
 * Type-aware rules require `parserOptions.projectService: true` so the
 * parser can locate each file's owning tsconfig. We default that on.
 */

import eslint from '@eslint/js';
import tseslint from 'typescript-eslint';
import prettier from 'eslint-config-prettier';
import globals from 'globals';

/** @type {import('eslint').Linter.Config[]} */
const config = [
  // Recommended JavaScript rules
  eslint.configs.recommended,

  // Type-aware TypeScript rules
  ...tseslint.configs.strictTypeChecked,
  ...tseslint.configs.stylisticTypeChecked,

  // Disable rules that conflict with Prettier (must come after typescript-eslint)
  prettier,

  // Project-wide defaults
  {
    languageOptions: {
      parserOptions: {
        projectService: true,
        tsconfigRootDir: process.cwd(),
      },
      globals: {
        ...globals.node,
        ...globals.es2022,
      },
    },
    rules: {
      // HappyVertical org conventions: tighten what tseslint defaults are too soft on
      '@typescript-eslint/consistent-type-imports': [
        'error',
        { prefer: 'type-imports', fixStyle: 'separate-type-imports' },
      ],
      '@typescript-eslint/no-unused-vars': [
        'error',
        {
          argsIgnorePattern: '^_',
          varsIgnorePattern: '^_',
          caughtErrorsIgnorePattern: '^_',
        },
      ],
      // Warn rather than error so debugging mid-development isn't blocked
      'no-console': ['warn', { allow: ['warn', 'error'] }],
    },
  },

  // Disable type-aware rules for files outside the TS project (configs, scripts)
  {
    files: ['**/*.{js,mjs,cjs}', '**/*.config.{ts,js,mjs,cjs}'],
    ...tseslint.configs.disableTypeChecked,
  },

  // Tests can be a bit looser
  {
    files: ['**/*.{test,spec}.{ts,tsx,js,jsx}', '**/__tests__/**'],
    rules: {
      '@typescript-eslint/no-explicit-any': 'off',
      '@typescript-eslint/no-non-null-assertion': 'off',
      '@typescript-eslint/no-unsafe-assignment': 'off',
      '@typescript-eslint/no-unsafe-member-access': 'off',
    },
  },

  // Common ignores
  {
    ignores: [
      'node_modules/**',
      'dist/**',
      'build/**',
      'coverage/**',
      '.turbo/**',
      '.svelte-kit/**',
      '.vite/**',
      '**/*.d.ts',
    ],
  },
];

export default config;
