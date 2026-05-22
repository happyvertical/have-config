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
 * - Any commit with `!` after type/scope, or `BREAKING CHANGE` in the
 *   subject → minor bump
 * - All other commits (including `docs:`, `chore:`, `ci:`) → patch bump
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

/**
 * Run a git subcommand with args passed positionally. Uses execFileSync
 * so no shell parsing occurs. Returns trimmed stdout, or empty string on
 * non-zero exit (e.g. `git describe` with no tags yet).
 */
function git(...args: string[]): string {
  try {
    return execFileSync('git', args, {
      encoding: 'utf-8',
      stdio: ['pipe', 'pipe', 'pipe'],
    }).trim();
  } catch {
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
  const log = git(
    'log',
    range,
    '--pretty=format:%H|||%s',
    '--no-merges',
  );
  if (!log) return [];
  return log.split('\n').map((line) => {
    const [hash, ...subjectParts] = line.split('|||');
    return { hash: hash ?? '', subject: subjectParts.join('|||') };
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
  // `BREAKING CHANGE:` in subject. Body inspection would be more
  // complete but `git log --format=%s` only gives subjects; relying on
  // the convention of putting BREAKING CHANGE in the subject when
  // authors mean it.
  if (/\bBREAKING CHANGE\b/.test(commit.subject)) return true;
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
