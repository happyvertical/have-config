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
  committer: string;
  subject: string;
}

// Three fields per line: hash, committer name, subject. Records are
// separated by newline (subjects can't contain newlines). Fields are
// separated by ASCII 31 (Unit Separator) emitted via git's `%x1f`
// pretty-format escape — neither committer names nor subjects contain
// that byte in practice, and emitting it via `%x<hex>` keeps the byte
// OUT of argv (Node rejects NUL in argv and is awkward with other
// control bytes).
//
// We need committer name to distinguish workflow-generated
// `chore(release): bump …` commits (always committed by
// `have-release-bot`) from identically-prefixed human commits like
// `chore(release): bump pnpm/action-setup` — a valid Conventional
// Commit that a human might write for a dependency bump. Filtering
// by subject alone would silently exclude that human commit from
// the auto-generated changelog.
const GIT_PRETTY_FORMAT = `%H%x1f%cn%x1f%s`;
const FIELD_SEP = '\x1f';
const RELEASE_BOT_NAME = 'have-release-bot';

/**
 * Run a git subcommand with args passed positionally. Uses execFileSync
 * so no shell parsing occurs. Returns trimmed stdout.
 *
 * Two failure modes are distinguished:
 * - Git exited non-zero (e.g. `describe --tags` with no tags exists).
 *   Returns empty string; callers treat empty as "no output".
 * - Node-level failure (invalid argv, binary missing, spawn error).
 *   This indicates a bug in OUR code, not git's expected behaviour,
 *   so we throw to fail the workflow loudly. The previous "log and
 *   return empty" path made a typo in our own format string look
 *   identical to "no commits since last release" — auto-changeset
 *   would silently skip the run and the workflow would go green
 *   without producing a release.
 */
function git(...args: string[]): string {
  try {
    return execFileSync('git', args, {
      encoding: 'utf-8',
      stdio: ['pipe', 'pipe', 'pipe'],
    }).trim();
  } catch (err) {
    const e = err as { status?: number | null; code?: string; message?: string };
    if (e.status === undefined || e.status === null) {
      // Node-level error — re-throw to fail loudly. We never want
      // this swallowed; an empty return here would let the caller
      // proceed as if git succeeded with no output.
      throw new Error(
        `auto-changeset: git ${args.join(' ')} failed at Node level: ${e.code ?? e.message ?? err}`,
      );
    }
    // Git's own non-zero exit — expected for `describe --tags`
    // when no tags exist, etc. Empty output signals that.
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
  // Split on newlines (subjects can't contain newlines), then split
  // each line on the field separator into hash, committer, subject.
  return log
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const [hash = '', committer = '', subject = ''] = line.split(FIELD_SEP);
      return { hash, committer, subject };
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
  // Filter out workflow-created release commits — but only when BOTH
  // subject and committer match the bot's signature. A human commit
  // like `chore(release): bump pnpm/action-setup` (valid Conventional
  // Commit for a dependency update) would otherwise be silently
  // excluded from the changelog and the changes it represents would
  // never appear in release notes.
  const real = all.filter(
    (c) => !(
      c.subject.startsWith('chore(release)') &&
      c.committer === RELEASE_BOT_NAME
    ),
  );

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
