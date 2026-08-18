# Kaisian Git + GNU Stow Wrapper Design

**Date:** 2026-08-18  
**Status:** Approved design; written-spec review passed
**Repositories:** `taiansu/kaisian`, `taiansu/dotfiles`

## 1. Goal

Kaisian is a thin, macOS-only Bash wrapper around Git, GNU Stow, and fzf. It acquires a pinned dotfiles repository, validates a declarative package manifest, selects Stow packages, moves exact target conflicts into a timestamped backup, and delegates all link installation and removal to GNU Stow.

The design optimizes for a small, auditable implementation and native Stow semantics. It intentionally does not provide transactional recovery.

## 2. Non-goals and Removed Guarantees

Kaisian does not:

- implement its own symlink planner or link-creation engine;
- install Homebrew packages or runtimes;
- parse TOML, TSV, or CSV;
- provide WAL, crash-safe recovery, automatic rollback, or a `recover` command;
- reset, clean, stash, or overwrite a dirty Git checkout;
- support SSH/scp-like Git URLs or local source paths;
- support Linux in the first release;
- automatically delete backups.

The archived Rust implementation remains outside the new repository at `~/Projects/rust_kaisian`. The new `~/Projects/kaisian` repository is a clean shell-only implementation, not a compatibility layer over the Rust CLI.

## 3. Runtime Prerequisites

The wrapper supports macOS 13 or newer. Normal execution after help/argument-shape handling requires these commands:

- `/bin/bash`;
- `/usr/bin/git` or `git` on `PATH`;
- GNU `stow` on `PATH`;
- `fzf` on `PATH`;
- `/usr/bin/plutil` from macOS.

Kaisian probes Stow for the required `--dotfiles`, `--no-folding`, `--compat`, mixed-operation, and simulation behavior rather than trusting a version string alone. Probes use the same sanitized Stow runner as real operations, so caller resource files and environment cannot affect feature detection. Kaisian checks every prerequisite and exits with bilingual installation guidance. It never runs `brew install` itself. Node.js, Python, Rust, `jq`, `yq`, and GNU gettext are not required.

## 4. Repository Boundaries

### 4.1 Kaisian repository

The new `taiansu/kaisian` repository contains:

```text
kaisian/
├── setup.sh
├── tests/
│   └── setup_test.sh
├── README.md
├── README.en.md
└── LICENSE
```

`setup.sh` is both the released executable and the script served by the personal bootstrap endpoint. It remains compatible with macOS Bash 3.2.

### 4.2 Dotfiles repository

`taiansu/dotfiles` is the Stow directory. Every selectable category is a top-level package directory:

```text
dotfiles/
├── .git/
├── .gitmodules
├── .kaisian.json
├── README.md
├── shell/
├── git/
├── mise/
├── terminal/
├── editors/
├── agents/
├── cli/
├── macos/
├── homebrew/
└── dev/
```

Root regular files may contain repository documentation or metadata. Every non-hidden root directory, excluding Git's hidden metadata, must be declared as a Stow package in `.kaisian.json`. Hidden maintenance directories may contain only tracked, clean repository content and must never be package payload. Generated state, caches, backups, and worktrees live outside the managed checkout.

## 5. GNU Stow Package Layout

Each package is an installation image relative to `$HOME`. Every path component that should begin with `.` in `$HOME` is represented with a `dot-` prefix in the package.

Example:

```text
shell/
├── dot-zshrc
├── dot-zprofile
├── dot-zshenv
├── dot-config/
│   └── zsh/
│       └── aliasrc
└── dot-local/
    └── share/
        └── zsh/
            └── git-prompt.zsh

git/
├── dot-gitconfig
└── dot-gitignore
```

Mappings:

```text
shell/dot-zshrc                         -> $HOME/.zshrc
shell/dot-config/zsh/aliasrc            -> $HOME/.config/zsh/aliasrc
shell/dot-local/share/zsh/git-prompt.zsh -> $HOME/.local/share/zsh/git-prompt.zsh
git/dot-gitconfig                       -> $HOME/.gitconfig
```

Every Stow invocation uses both `--dotfiles` and `--no-folding`. The first gives `dot-` its documented meaning; the second produces predictable leaf links rather than folded directory links.

Package validation rejects:

- any hidden path component; users must use `dot-` instead;
- source symlinks;
- non-ASCII or control characters in payload path components;
- a source component whose `dot-` transformation is empty, `.` or `..` (including `dot-` and `dot-.`);
- two transformed targets that collide after unconditional ASCII case-folding;
- package names outside `^[a-z][a-z0-9_-]*$`;
- a regular-file leaf not tracked by the top-level superproject;
- an empty payload directory, gitlink, or nested Git repository anywhere inside a selectable package.

Kaisian transforms every source component once, normalizes the resulting HOME-relative target once, ASCII-case-folds that value for conservative collision checks on both case-sensitive and case-insensitive macOS filesystems, and uses the original normalized value for containment, backup, and display decisions. Rejecting non-ASCII payload names avoids dependence on APFS/HFS Unicode normalization tables. Kaisian never constructs a backup path from an unnormalized source name.

Across every declared package, Kaisian merges transformed paths into one ASCII-case-folded typed tree before selection or backup. Directory/directory prefixes may be shared. Duplicate leaves, a leaf where another package requires a directory, and every leaf/descendant or file/directory prefix collision are rejected. This validation completes before confirmation and ensures every default, profile, and explicit selection is structurally representable by Stow.

## 6. Manifest Contract

The dotfiles root contains one JSON file:

```text
.kaisian.json
```

Schema 1 example:

```json
{
  "schema": 1,
  "groups": [
    {
      "name": "shell",
      "description": {
        "en": "Shell configuration",
        "zh-TW": "Shell 設定"
      }
    },
    {
      "name": "git",
      "description": {
        "en": "Git configuration",
        "zh-TW": "Git 設定"
      }
    },
    {
      "name": "mise",
      "description": {
        "en": "Runtime and environment management",
        "zh-TW": "執行環境與工具版本管理"
      }
    }
  ],
  "profiles": {
    "minimal": ["shell", "git", "mise"]
  }
}
```

`groups` is an array because its order defines the stable display and Stow argument order. JSON object key order is not used as an ordering contract.

Validation requires:

1. JSON is accepted by `/usr/bin/plutil -convert json`.
2. `schema` is exactly integer `1`.
3. `groups` is a non-empty array.
4. Every group has exactly one valid, unique `name` and non-empty `description.en` and `description.zh-TW` strings. Descriptions must be single-line, contain no tab or control characters, and are therefore safe for tab-delimited fzf candidate transport.
5. Every declared group has a matching non-hidden root package directory.
6. Every non-hidden root directory is declared exactly once.
7. `profiles` is a dictionary of non-empty arrays.
8. Profile names obey the same safe-name grammar as package names.
9. Every profile entry references a declared group and appears at most once in that profile.
10. Unknown top-level keys and unknown group keys are rejected in schema 1.

Kaisian parses JSON only through `/usr/bin/plutil`. It does not use regex, `grep`, `sed`, or `eval` as a JSON parser. On the target macOS version, JSON syntax validation uses `plutil -convert json -o /dev/null`; `plutil -lint` is not used because it does not accept JSON consistently. Array sizes and values are read with `plutil -extract <keypath> raw`. Schema 1 defines duplicate object-key semantics as the last value returned by `plutil`; Kaisian does not claim to diagnose duplicates that `plutil` has already collapsed.

## 7. Source and Checkout Semantics

### 7.1 Defaults

Each immutable Kaisian release embeds:

- default repository: `taiansu/dotfiles`;
- default checkout: `$HOME/.dotfiles`;
- exact default dotfiles commit.

The release must not track an unpinned default branch.

### 7.2 Accepted sources

`--repo` accepts:

- a GitHub `owner/repo` slug; or
- a public HTTPS Git URL in canonical form.

Before invoking Git, Kaisian requires ASCII URL/slug host and path text (internationalized hosts must already be punycode) and rejects URL userinfo, passwords/tokens, control characters, query strings, fragments, any explicit port (including `:443`), any percent encoding, empty path segments, `.`/`..` segments, repeated slashes, and option-like or refspec-like source text. Canonical comparison lowercases the ASCII host, strips one trailing slash, then strips one trailing `.git`, and compares the validated repository path. A GitHub slug expands to that same canonical HTTPS form.

SSH URLs, scp-like sources, `file://`, other schemes, local paths, and authenticated/private repositories are unsupported. Supplying a non-default `--repo` requires an explicit `--ref`; there is no implicit custom-repository branch. Ref text must be non-empty and must not begin with `-`, contain whitespace/control characters, contain `:`, or otherwise form a Git refspec. Git operands are separated from options with `--` wherever the Git subcommand supports it.

### 7.3 Ref acquisition

`--ref` accepts an advertised full branch or tag ref, an unambiguous shorthand branch/tag name, remote `HEAD`, or an exact 40-hex SHA-1 commit ID. Kaisian resolves names only against the requested origin's advertised refs: shorthand that exists as both a branch and tag is rejected, annotated tags are peeled to their advertised commit, and an unadvertised commit fetch is allowed only if the remote itself serves that exact object. Fetch writes the requested origin object only to `FETCH_HEAD` or a dedicated temporary ref owned by the current invocation. Kaisian peels that fetched object to a commit and checks out the commit detached; it never resolves the raw user text against local branches or tags after fetch. The default embedded SHA must equal the fetched and checked-out commit exactly.

### 7.4 Git execution and submodule trust

Every Git command runs through one sanitized runner with a minimal environment: only required path/locale/HOME values are preserved, askpass and inherited `GIT_CONFIG_*` injection are removed, system/global Git configuration and system attributes are disabled (`GIT_ATTR_NOSYSTEM=1`), terminal prompting is disabled, replacement objects are disabled with `GIT_NO_REPLACE_OBJECTS=1`, only HTTPS network transport is permitted, and hooks plus shell filter/update/fsmonitor commands are disabled. A new checkout is created with `git init`, an exact canonical origin, and one validated fetch to `FETCH_HEAD`; no ordinary clone fetch, remote-tracking ref, or local branch is created before the requested object is validated.

Existing local config is read with includes disabled. Accepted `core` keys and values are exactly: `repositoryformatversion=0`, `bare=false`, `logallrefupdates=true`, `filemode=true|false`, `ignorecase=true|false`, `precomposeunicode=true|false`, and absent-or-true `symlinks`, `protectHFS`, and `protectNTFS`. ASCII-only payload validation and unconditional case-fold collision detection make either detected filesystem value for `ignorecase`/`precomposeunicode` safe; `symlinks=false` is rejected because it would materialize a Git symlink as a regular file and bypass source-symlink rejection. `core.worktree` and every other core key are rejected.

Outside `core`, the allowlist is limited to canonical `remote.origin.url` plus the standard heads-only origin fetch mapping; ordinary branch remote/merge pairs whose values point to origin and `refs/heads/*`; and exact validated `submodule.*.url`, `.active`, and absent-or-`checkout` `.update` entries. Includes, `url.*.insteadOf`, external filters/diffs/fsmonitors, hooks, unsafe protocols, command-valued updates, unexpected remotes/refspecs, and every other local key are rejected. Configuration is rechecked before and after network/checkout operations.

Before each submodule level is initialized, Kaisian reads the tracked `.gitmodules` at the fetched superproject/submodule commit through Git's config parser. It requires unique normalized relative paths contained below their parent checkout, canonical HTTPS URLs, and absent or `checkout` update modes; it rejects relative, SSH, file, ext, command, option-like, overlapping, symlinked, or duplicate paths and URLs. Each child checkout is created through the same sanitized `git init` plus exact-gitlink fetch flow, one validated level at a time; unvalidated recursive update is never invoked. Each resulting nested checkout is pinned to its recorded gitlink commit, subjected to the same local-config rules, and validated before its own children are initialized. Submodule roots and their tracked `.gitmodules` metadata must remain outside selectable package trees; schema 1 does not treat a submodule checkout as Stow payload.

Top-level and child repositories reject every `refs/replace/*` ref, `.git/info/grafts`, `.git/info/attributes`, external object alternate, and inherited object-directory variable even though the sanitized runner also disables their use. All object inspection, manifest extraction, checkout, and verification use that runner, so the fetched commit cannot be locally replaced or transformed by out-of-tree attributes while retaining the same displayed SHA. Fresh-index verification therefore uses only tracked in-tree `.gitattributes`.

### 7.5 New checkout

For an absent checkout, Kaisian:

1. validates the absolute checkout path, physical parent path, and HOME ancestry before creation;
2. creates only the required parent chain;
3. initializes an empty Git repository and writes only the exact canonical origin configuration;
4. fetches the requested origin object once to `FETCH_HEAD` as defined above;
5. validates repository and first-level submodule configuration from the fetched objects;
6. checks out the fetched commit detached with hooks and external filters disabled;
7. validates and initializes submodules one level at a time through exact-gitlink fetches;
8. verifies `HEAD` is the fetched commit and verifies recursive cleanliness and exact gitlink commits.

### 7.6 Existing checkout

For an existing checkout, Kaisian requires:

- a real directory, not a symlink;
- a Git repository;
- canonical `origin` matching the requested repository;
- safe local repository and submodule configuration under the rules above;
- no in-progress merge, rebase, cherry-pick, revert, bisect, or sequencer operation;
- config-independent porcelain status with all untracked and ignored files visible and `ignore-submodules=none`;
- every initialized submodule and nested submodule at the exact superproject-recorded commit and clean under the same tracked/untracked/ignored checks.

The top-level administrative directory must resolve through both `git rev-parse --absolute-git-dir` and `--git-common-dir` to the same real `<checkout>/.git` directory. Bare repositories, linked worktrees, `.git` gitfiles/symlinks, separate/common Git directories, external object alternates, and administrative paths outside the checkout are rejected. No repository-owned or repository-discovered mutable administrative path may be a symlink, and its objects, refs, logs, config, and real index must resolve below that embedded `.git`. Kaisian-created child submodules use the same real embedded `<submodule>/.git` layout below the child checkout; absorbed or externally stored submodule gitdirs are unsupported.

Cleanliness and safe configuration are checked both before fetch/checkout and after staged submodule update. Index-only changes are rejected against HEAD. For worktree verification only, Kaisian explicitly sets `GIT_INDEX_FILE` to a fresh index whose recorded physical path is inside the revalidated invocation sandbox; that tool-owned exception is never read from repository config or metadata. Comparing worktree bytes with HEAD through this isolated index prevents `assume-unchanged`, `skip-worktree`, sparse-index, and sparse-checkout state in the repository index from concealing modified or missing payload. Separate config-independent scans reject all untracked and ignored paths. Any wrong-commit or nested-submodule change is rejected. Package traversal separately proves that each payload leaf is tracked by the top-level superproject. Kaisian never invokes `reset --hard`, `clean`, `stash`, or automatic conflict resolution.

### 7.7 Checkout and target separation

Before source mutation, `HOME` must be nonempty, absolute, existing, owned by the effective user, searchable/writable, and a real directory whose textual path equals its physical path; symlinked/missing/relative HOME values are rejected. Kaisian captures that physical HOME once and uses it for the default checkout, containment, default state/backup paths, and the exact `stow --target` argument.

`--repo-dir` must be absolute. Before checkout creation or update, Kaisian resolves its existing parent physically and rejects a checkout that is the physical HOME, an ancestor of HOME, a symlink, or administratively backed outside itself. After the fetched tree and staged submodules are materialized, but before any conflict move, backup creation, or Stow operation, it requires every declared package root to be a real non-symlink directory directly below the checkout and rejects any normalized mapped target that equals, contains, or is contained by the checkout. The mapping checks are repeated immediately before target mutation.

## 8. CLI Contract

```text
setup.sh [OPTIONS]

Selection, exactly zero or one:
  --profile NAME
  --groups GROUPS
  --interactive
  --all

Source and execution:
  --repo URL|OWNER/REPO
  --ref REF
  --repo-dir PATH
  --lang en|zh-TW
  --dry-run
  --yes
  -h, --help
```

Selection rules:

- No selection option means all declared packages.
- `--all` explicitly means all declared packages.
- `--profile` selects the ordered package list in the named manifest profile.
- `--groups` accepts a comma-separated list, trims whitespace, rejects empty/unknown names, deduplicates, and returns packages in manifest order.
- `--interactive` presents all groups in manifest order through `fzf --multi`, with localized descriptions, and rejects an empty confirmed selection.
- Selection flags are pairwise mutually exclusive.

`--yes` skips only the conflict-backup confirmation. It does not bypass validation, dirty-checkout refusal, or prerequisite checks. `--help` and argument-shape errors are resolved before runtime prerequisite probes, so help remains available on an unconfigured machine.

## 9. Locale and Interactive I/O

One `setup.sh` contains both English and Traditional Chinese (Taiwan) messages. Language resolution order is:

1. explicit `--lang`;
2. `LC_ALL`;
3. `LC_MESSAGES`;
4. `LANG`;
5. English fallback.

All Chinese locales use Traditional Chinese (Taiwan). Explicit language values accept only `en` and `zh-TW`.

Because `curl ... | bash` consumes standard input, confirmations read from `/dev/tty`. fzf receives control-free, tab-delimited candidates from a generated pipeline and opens `/dev/tty` for its terminal interface. Interactive mode fails clearly when no controlling TTY is available. Esc or Ctrl-C from fzf is a user cancellation and exits zero without target mutation; an empty selection confirmed with Enter or any unexpected fzf failure exits nonzero.

## 10. Preflight and Conflict Backups

Kaisian computes every selected package's target mapping using Stow's `dot-` transformation before mutating `$HOME`.

For each selected leaf:

- an absent target is installable;
- a symlink already resolving to the expected package leaf is unchanged;
- an exact regular file, directory, broken symlink, or wrong symlink is a backup conflict;
- a FIFO, socket, device, or any other non-regular target node is rejected for manual resolution;
- an existing parent that is not a real directory, including a symlink parent, is rejected for manual resolution;
- every resolved target path must remain below the physical `$HOME` root.

Preflight also applies the typed-tree collision validation across all declared packages. It completes before confirmation or any conflict move.

Conflicts are moved, never copied, to:

```text
${XDG_STATE_HOME:-$HOME/.local/state}/kaisian/backups/<UTC_TIMESTAMP>-<PID>/files/<HOME_RELATIVE_PATH>
```

The relative hierarchy is preserved. `XDG_STATE_HOME`, when set, must be absolute. Before mutation, Kaisian resolves the physical state root and computed backup tree; rejects symlink ancestors; rejects equality or ancestor/descendant overlap among the state/backup tree, checkout, normalized mapped targets, and canonical lock/sandbox tree; and verifies every conflict and the nearest existing ancestor of its backup destination are on the same filesystem device. If same-device atomic rename cannot be guaranteed, Kaisian stops before creating the backup root; it never falls back to cross-device copy-and-delete. The unique backup root is reserved only after successful confirmation and all device checks. Backup directories are created only when conflicts exist and the operation is not a dry run.

Confirmation behavior:

- no conflicts: continue without confirmation;
- conflicts: print every source and backup destination, then read `y/N` from `/dev/tty`;
- `--yes`: move listed conflicts without prompting;
- explicit rejection: exit zero without moving conflicts or changing target links; any already completed managed-checkout update remains;
- missing, unreadable, or unwritable controlling TTY, or a failed confirmation read: exit nonzero before creating the backup root or moving conflicts.

`--dry-run` never requests backup confirmation and does not require `/dev/tty` merely because conflicts exist; it reports planned moves and exits according to preflight success. `--interactive` still requires a TTY independently.

Once conflict moves begin, failures preserve the backup and return nonzero with exact manual restore guidance. Kaisian does not automatically restore moved conflicts. Backups are never automatically removed. Before acquisition, Kaisian rejects a physical checkout or computed backup tree equal to, above, or below the canonical lock path; siblings remain valid. Kaisian then validates root-owned sticky `/private/tmp` and atomically acquires the fixed per-UID directory `/private/tmp/kaisian-<UID>.lock` with mode `0700` before source or target mutation. The lock contains only the current PID record and an invocation sandbox. Exit/signal traps revalidate the recorded lock/sandbox identity and containment, remove only the exact sandbox entries they created, then remove the empty lock; they never recursively cross a persistent-tree boundary or automatically clean an unrecognized/stale lock. An existing lock causes a nonzero refusal with owner/type/mode verification and stale-lock inspection/removal guidance. The non-overridable canonical location rejects concurrent invocations even when they have different `TMPDIR` or XDG values.

## 11. Stow Operations

Kaisian delegates target mutation to one GNU Stow mixed-operation plan whenever possible:

- selected packages are restowed (`-R`);
- packages omitted from an explicit/profile/interactive selection are unstowed (`-D`);
- no-option and `--all` selection restow all packages.

Every invocation supplies:

```text
--dir <checkout>
--target <HOME>
--dotfiles
--no-folding
--compat
```

Every probe, simulation, and apply runs through one sanitized Stow runner. It uses an empty controlled working directory and a temporary process HOME inside the invocation lock, creates an empty `.stow-global-ignore` there to disable Stow's built-in ignore list deterministically, and supplies only a minimal locale/PATH environment. Caller `.stowrc`, target-HOME `.stowrc`/`.stow-global-ignore`, `STOW_DIR`, and Perl injection variables including `PERL5OPT`, `PERL5LIB`, `PERLLIB`, `PERL_LOCAL_LIB_ROOT`, `PERL_MB_OPT`, and `PERL_MM_OPT` are absent. Absolute `--dir` and `--target` values remain explicit. Consequently the preflight payload set and Stow payload set are identical, including README/LICENSE-like filenames that Stow would otherwise ignore by default.

When the checkout or computed state/backup tree lies below the physical Stow target, the runner also passes literal, anchored subtree ignore expressions generated by escaping every regex metacharacter in their HOME-relative paths. Preflight already forbids payload mappings at, above, or below those excluded trees, so these rules cannot suppress valid payload. Kaisian behaviorally probes that the supported Stow applies these ignores during `--compat` target traversal; if not, it fails before target mutation. Paths outside the target require no ignore rule. Current and historical backups, state files, and the managed checkout therefore remain outside compatibility deletion scans.

The implementation must verify first-run deletion of never-stowed unselected packages against the supported GNU Stow version. If Stow requires filtering no-op deletes, Kaisian may omit only packages for which no Stow-owned target link exists; observable selection semantics must remain identical and no persistent Kaisian selection state may be introduced.

`--compat` is passed on every restow and delete invocation, including mixed operations; there is no runtime detection branch. This whole-target compatibility scan removes links for payload files deleted from an existing package. Schema 1 package names are stable across every supported pinned dotfiles release: removing or renaming a package is a breaking manifest change and release CI rejects it until a separately designed migration exists. Upgrade tests remove a payload file within a retained package and prove its obsolete HOME link is removed.

Stow's own deferred conflict analysis remains authoritative after Kaisian's preflight. A Stow failure returns nonzero, preserves all backups, and prints the backup root and manual recovery instructions. Kaisian never uses `--adopt` or `--override`.

## 12. Dry Run

`--dry-run` performs source acquisition/update, manifest parsing, package validation, selection, mapping, and conflict discovery. It may create or update the physical managed checkout selected by `--repo-dir` and, when that checkout is absent, create only its minimal missing ancestor chain. It also creates the ephemeral lock and sanitized Stow sandbox under `/private/tmp`; both are removed before exit. It skips backup confirmation and its TTY requirement, does not create compatibility-sensitive backup content, and reports planned moves. No other HOME path may change. It must not:

- move conflicts or mutate paths outside that managed checkout and its newly required ancestors;
- create backup directories;
- create, remove, or change target links;
- write persistent Kaisian state.

The output identifies selected packages, unselected packages, planned backup moves, and the Stow operations. When preflight finds no conflicts, Kaisian invokes Stow with `--simulate --verbose` using the same sanitized runner, subtree exclusions, and semantic operations as the real apply. When planned backup conflicts still occupy target paths, Kaisian reports those conflicts as the dry-run result and does not misrepresent Stow's expected conflict exit as an unrelated failure; the real operation will move only the approved conflicts before invoking Stow.

## 13. Error Model

Errors are bilingual, identify the failing phase, and return nonzero except user-declined conflict confirmation, which is a successful no-op.

Required distinct failures include:

- unsupported OS;
- missing Git, Stow, fzf, or plutil;
- unsupported Stow feature behavior;
- malformed CLI or mutually exclusive selection;
- unsupported/unsafe source, ambiguous ref, or missing `--ref` for a custom repository;
- dirty, mismatched, symlinked, externally administered, linked-worktree, or non-Git checkout;
- invalid/missing/symlinked/unowned HOME or unsafe checkout/HOME overlap;
- unsafe local Git core value/config, replacement/graft/attribute/alternate/admin path, submodule path/URL/update mode, protocol, hook, or filter;
- unresolved/unadvertised/replaced ref or dirty/wrong-commit submodule;
- malformed/unsupported manifest;
- manifest/package mismatch;
- untracked payload, source symlink, hidden source entry, transformed traversal, filesystem alias, or target collision;
- unsafe target/state/backup/lock parent, overlap, or target outside HOME;
- unavailable TTY when confirmation is required;
- concurrent/stale invocation lock;
- cross-filesystem or otherwise failed backup move;
- Stow simulation/apply failure.

No error output may contain credential contents, Git authentication tokens, or full environment dumps.

## 14. Release and Endpoint

Kaisian releases are tagged shell-script releases, not binary matrices. Release CI:

1. runs shell syntax and isolated behavior tests;
2. validates macOS Bash 3.2 compatibility;
3. records the exact embedded dotfiles commit;
4. compares schema 1 package names with every earlier supported pinned release and rejects removal or rename;
5. publishes the immutable `setup.sh` and SHA-256 checksum;
6. never publishes from an untagged branch head.

The personal endpoint serves the exact verified script for a pinned Kaisian release:

```bash
curl -fsSL https://kaisian.phx.tw | bash
```

Arguments use Bash's stdin-script convention:

```bash
curl -fsSL https://kaisian.phx.tw |
  bash -s -- --interactive
```

README files provide inspect-before-run instructions and explain that the endpoint, Git host, pinned release, and embedded dotfiles commit are trust boundaries.

## 15. Verification Strategy

The shell suite runs in temporary HOME/XDG roots with fake network Git remotes and, where behavior matters, real GNU Stow. It covers:

1. prerequisite probes, help without prerequisites, and macOS refusal;
2. pairwise CLI selection conflicts and argument validation;
3. language precedence and stable bilingual output;
4. canonical ASCII HTTPS/GitHub slug handling, punycode-host rule, trailing-slash/`.git` order, and userinfo, raw-Unicode, percent-encoding, explicit-port, query, fragment, traversal, option-like, and refspec rejection;
5. custom repository requiring explicit `--ref`, remote namespace ambiguity rejection, and fetched-object pinning despite malicious same-named local refs;
6. empty-repository initialization, one fetched top-level object, no clone-created refs/branches, pinned detached checkout, staged exact-gitlink submodules, and existing clean update;
7. tracked, untracked, ignored, in-progress-operation, mismatched, symlinked, linked-worktree, separate-gitdir, bare, and recursively dirty checkout refusal and absence of destructive Git commands;
8. hostile `.gitmodules`, nested relative/SSH/file/ext URLs, overlapping paths, command update modes, local includes, `url.*.insteadOf`, external filters/hooks, global/system config, and protocol bypass attempts;
9. exact acceptance/rejection fixtures for every allowed `core` key/value plus rejection of `core.worktree`, `core.symlinks=false`, and unknown local keys;
10. replacement refs, grafts, info attributes, system attributes, alternates, object/admin symlinks, and out-of-tree mutable Git paths cannot alter fetched-object identity, worktree bytes, or dry-run boundaries;
11. modified/missing payload hidden by attributes, `assume-unchanged`, `skip-worktree`, sparse index, or sparse checkout is found through a fresh isolated index;
12. empty, relative, missing, symlinked, unowned, or unwritable HOME refusal and one captured physical HOME used by containment, default paths, backup, and Stow;
13. JSON syntax, schema, types, unknown keys, documented duplicate-key behavior, package alignment, stable package names, and profile references;
14. manifest-order default/all/profile/groups selection;
15. fzf multi-selection, cancellation/empty/error status handling, control-free descriptions, and non-TTY refusal;
16. `dot-` mapping, post-transform traversal, non-ASCII path, ASCII case-fold collision, typed directory sharing, duplicate-leaf and leaf/descendant collision rejection, hidden/untracked source, empty directory, source symlink, package gitlink/nested-repository rejection, non-payload submodule metadata, and staged physical checkout/target/state separation checks;
17. correct-link idempotency and selected/unselected package switching;
18. conflict detection, special-node refusal, confirmation read failure, `--yes`, dry-run conflict reporting without TTY/confirmation, atomic same-device hierarchy-preserving backup moves, cross-device refusal, safe unique backup roots, canonical lock exclusion across differing `TMPDIR` values, and user rejection no-op;
19. checkout and computed XDG backup paths equal to, above, and below the lock/sandbox are rejected while siblings remain valid; cleanup removes only revalidated invocation-owned sandbox entries;
20. real Stow apply with `--dotfiles --no-folding --compat` into a temporary target HOME, with anchored literal compatibility exclusions preserving current/prior backup and state symlinks;
21. hostile caller/target `.stowrc`, `.stow-global-ignore`, `STOW_DIR`, Perl environment, and built-in-ignore filenames cannot alter sanitized Stow probes/simulation/apply or preflight parity;
22. upgrade of a retained package removing an obsolete payload link, plus release rejection for package removal/rename;
23. Stow failure preserving backup and reporting manual recovery;
24. arbitrary absolute `--repo-dir` dry-run creating only its minimal missing parent chain and embedded Git directory plus removable `/private/tmp` lock/sandbox while leaving targets, backups, and persistent state untouched;
25. repeat application converging without new backups.

Tests assert observable filesystem state, command arguments, statuses, and messages. They do not assert implementation source text except to prove forbidden destructive Git/Stow arguments are absent from executed command traces.

## 16. Migration and Cutover

The existing TOML fixture work on `feature/kaisian-migration` is obsolete but preserved in Git history. New work proceeds from rewritten `main` on `feature/kaisian-stow-wrapper`.

Implementation order:

1. create the new shell-only Kaisian repository and its isolated test harness;
2. implement prerequisite, locale, CLI, JSON manifest, source, selection, preflight, backup, and Stow orchestration in focused increments;
3. migrate dotfiles into package directories using `dot-` names and create `.kaisian.json`;
4. move tracked non-payload maintenance material under hidden maintenance paths, and move generated state, caches, backups, and worktrees outside the managed checkout;
5. run real temporary-HOME Stow apply and idempotency checks;
6. publish a pinned script release;
7. deploy the pinned endpoint and smoke-test default, explicit, and interactive paths;
8. update both repositories' Traditional Chinese and English documentation;
9. retain the pre-rewrite checkout until every ignored/untracked file is accounted for and obtain separate approval before deletion.

No compatibility aliases, deprecated TOML manifest, Rust binary shim, or automatic migration from the unpublished Rust CLI is retained.
