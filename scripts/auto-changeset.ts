/**
 * Auto-generate Changesets from conventional commits.
 *
 * Runs in CI on every push to main. Scans commits since the last
 * package release tag and writes a single changeset bumping all
 * packages together (version-locked behaviour matching smrt's pattern).
 *
 * Defers to manual changesets — if any non-auto changeset file exists
 * under `.changeset/`, this script does nothing so the maintainer's
 * explicit notes win. This is the documented escape hatch when the
 * commit history alone doesn't capture what you want consumers to
 * see in the changelog.
 *
 * Bump rules for 0.x.x releases (everything stays pre-1.0):
 * - Any commit with `!` after type/scope, or `BREAKING CHANGE` /
 *   `BREAKING-CHANGE` in the subject OR body → minor bump
 * - All other commits (including `docs:`, `chore:`, `ci:`) → patch bump
 *
 * Body inspection matters: the Conventional Commits spec puts breaking
 * markers in a footer, e.g.
 *
 *   feat: change config shape
 *
 *   BREAKING CHANGE: consumers must update their extends path
 *
 * Subject-only inspection would classify this as a patch and ship a
 * breaking change under a patch version. We scan the body too.
 *
 * `chore(release):` commits are filtered out — they're the workflow's
 * own version-bump commits and including them would re-bump on the
 * next run.
 */

import { execFileSync } from 'node:child_process';
import { randomBytes } from 'node:crypto';
import { existsSync, readdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const PACKAGES = [
  '@happyvertical/eslint-config',
  '@happyvertical/prettier-config',
  '@happyvertical/tsconfig-base',
] as const;

interface Commit {
  hash: string;
  subject: string;
  body: string;
}

// Field/record separators for parsing `git log` output. We need bytes
// that won't appear in commit subjects or bodies and that don't break
// Node's child_process argv handling. Git's `%x<hex>` pretty-format
// escape emits the byte in the OUTPUT without requiring us to put it
// in the argv (which would fail — Node rejects NUL bytes in args, and
// even non-NUL control bytes in argv are awkward). We use ASCII 31
// (Unit Separator) between fields and ASCII 30 (Record Separator)
// between commits — neither appears in real commit text.
const FIELD_SEP_OUT = '\x1f';
const COMMIT_SEP_OUT = '\x1e';
const GIT_PRETTY_FORMAT = `%H%x1f%s%x1f%b%x1e`;

/**
 * Run a git subcommand with args passed positionally. Uses execFileSync
 * so no shell parsing occurs. Returns trimmed stdout, or empty string
 * when git itself exits non-zero (e.g. `git describe` with no tags).
 *
 * Surfaces non-git errors (invalid argv, missing binary, etc.) by
 * logging to stderr and returning empty — we don't want a typo in our
 * own format string to look like "no commits" and silently skip a
 * release. Caller should treat empty as "no output" but log if needed.
 */
function git(...args: string[]): string {
  try {
    return execFileSync('git', args, {
      encoding: 'utf-8',
      stdio: ['pipe', 'pipe', 'pipe'],
    }).trim();
  } catch (err) {
    // Git returning non-zero is expected for some calls (describe with
    // no tags). But Node-level errors (NUL in args, binary not found,
    // etc.) indicate our bug, not git's — surface them.
    const e = err as { status?: number | null; code?: string; message?: string };
    if (e.status === undefined || e.status === null) {
      console.error(`auto-changeset: git ${args.join(' ')} failed: ${e.code ?? e.message ?? err}`);
    }
    return '';
  }
}

function getLastReleaseTag(): string | null {
  // Prefer per-package tags created by `changeset publish`
  // (e.g. `@happyvertical/eslint-config@0.2.0`).
  const perPackage = git(
    'tag',
    '--list',
    '@happyvertical/*@*',
    '--sort=-creatordate',
  )
    .split('\n')
    .filter(Boolean)[0];
  if (perPackage) return perPackage;

  // Fallback to the most recent tag of any shape.
  const any = git('describe', '--tags', '--abbrev=0');
  return any || null;
}

function getCommitsSinceLastRelease(): Commit[] {
  const lastTag = getLastReleaseTag();
  const range = lastTag ? `${lastTag}..HEAD` : 'HEAD';
  // %x1f / %x1e are git pretty-format escapes that emit ASCII 31 / 30
  // in the OUTPUT. We don't put those bytes in argv (Node rejects NUL
  // bytes there, and embedding raw control bytes is brittle); git
  // expands them when generating the log.
  const log = git('log', range, `--pretty=format:${GIT_PRETTY_FORMAT}`, '--no-merges');
  if (!log) return [];
  return log
    .split(COMMIT_SEP_OUT)
    .map((entry) => entry.trim())
    .filter(Boolean)
    .map((entry) => {
      const [hash = '', subject = '', body = ''] = entry.split(FIELD_SEP_OUT);
      return { hash, subject, body };
    });
}

function hasManualChangesets(): boolean {
  const dir = '.changeset';
  if (!existsSync(dir)) return false;
  return readdirSync(dir).some(
    (f) =>
      f.endsWith('.md') &&
      !f.startsWith('auto-') &&
      f.toLowerCase() !== 'readme.md',
  );
}

function isBreaking(commit: Commit): boolean {
  // `type!: ...` or `type(scope)!: ...`
  if (/^[a-z]+(\([^)]+\))?!:/.test(commit.subject)) return true;
  // Per Conventional Commits spec, `BREAKING CHANGE:` (or
  // `BREAKING-CHANGE:`) is a footer line — at the start of its own
  // line in the body, followed by `: `. Anchoring with `^…: `
  // (multiline) avoids false positives from narrative or docstring
  // mentions. Without this anchor, a body that SHOWS a
  // `BREAKING CHANGE:` example (like this script's own top-of-file
  // JSDoc, or any commit explaining what a breaking-change footer is)
  // would silently force a minor bump.
  if (/^BREAKING[- ]CHANGE: /m.test(commit.body)) return true;
  // Subject: looser anchor — require the `: ` separator (so narrative
  // phrasing like "fix: avoid BREAKING CHANGE false positives" stays
  // out) but allow the marker anywhere within the subject. Catches
  // both the bare form (`BREAKING CHANGE: …`) and the inline form
  // (`feat: BREAKING CHANGE: …`). Subjects are short and single-line
  // so line-anchoring would be unnecessarily strict.
  if (/\bBREAKING[- ]CHANGE: /.test(commit.subject)) return true;
  return false;
}

function main(): void {
  if (hasManualChangesets()) {
    console.log(
      'auto-changeset: manual changeset(s) present in .changeset/ — deferring.',
    );
    return;
  }

  const all = getCommitsSinceLastRelease();
  const real = all.filter((c) => !c.subject.startsWith('chore(release)'));

  if (real.length === 0) {
    console.log(
      `auto-changeset: no releasable commits since last release (skipped ${all.length} chore(release) commits).`,
    );
    return;
  }

  const bump: 'minor' | 'patch' = real.some(isBreaking) ? 'minor' : 'patch';

  const frontmatter = PACKAGES.map((p) => `'${p}': ${bump}`).join('\n');
  const summary = real
    .map((c) => `- ${c.subject} (${c.hash.slice(0, 7)})`)
    .join('\n');

  const id = randomBytes(8).toString('hex');
  const file = join('.changeset', `auto-${id}.md`);
  writeFileSync(file, `---\n${frontmatter}\n---\n\n${summary}\n`);

  console.log(
    `auto-changeset: wrote ${file} — ${bump} bump for ${PACKAGES.length} packages from ${real.length} commits.`,
  );
}

main();
