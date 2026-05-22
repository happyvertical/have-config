# @happyvertical/prettier-config

Shared Prettier configuration for HappyVertical projects.

## Install

```bash
pnpm add -D @happyvertical/prettier-config prettier
```

## Usage

Reference from `package.json`:

```json
{
  "prettier": "@happyvertical/prettier-config"
}
```

Or import in a `.prettierrc.js` if you need to override:

```js
// .prettierrc.js
import config from '@happyvertical/prettier-config';

export default {
  ...config,
  // local overrides (rare — please contribute upstream if generally useful)
};
```

## What's enforced

- 2-space indentation
- Single quotes (double quotes in YAML)
- 80-char line width
- Trailing comma `all` (none in JSON to avoid spec violations)
- LF line endings
- Semicolons
- `arrowParens: always`

## License

MIT.
