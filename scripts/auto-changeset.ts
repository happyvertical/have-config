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
 * - Any commit with `!` after type/scope (e.g. `feat!:` or
 *   `feat(scope)!:`) → minor bump
 * - All other commits (including `docs:`, `chore:`, `ci:`) → patch bump
 *
 * We deliberately do NOT scan for `BREAKING CHANGE:` / `BREAKING-CHANGE:`
 * footers. The org's convention is `!`, and footer scanning is a
 * regex-tuning trap (narrative mentions, docstring examples, and inline
 * subject forms each need bespoke handling). If a footer-marked commit
 * ever lands here, the maintainer can drop a manual changeset to force
 * the right bump — the deferral path is the documented escape hatch.
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
}

// Subject-only output: hash + space + subject + newline per commit.
// We don't fetch the body (we don't scan footers — see top-of-file
// JSDoc), so newlines are safe as record separators: git commit
// subjects can't contain newlines.
const GIT_PRETTY_FORMAT = `%H %s`;

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
  const log = git('log', range, `--pretty=format:${GIT_PRETTY_FORMAT}`, '--no-merges');
  if (!log) return [];
  // Split on newlines — git subjects can't contain newlines, so
  // there's no ambiguity. First space splits hash from subject.
  return log
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const spaceIdx = line.indexOf(' ');
      if (spaceIdx === -1) return { hash: line, subject: '' };
      return {
        hash: line.slice(0, spaceIdx),
        subject: line.slice(spaceIdx + 1),
      };
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
  // `type!: ...` or `type(scope)!: ...` — the only breaking marker
  // we recognize. See top-of-file JSDoc for why we don't scan footers.
  return /^[a-z]+(\([^)]+\))?!:/.test(commit.subject);
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
