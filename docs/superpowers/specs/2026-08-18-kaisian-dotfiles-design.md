# Kaisian and Dotfiles Design

## Problem

The current `setup.sh` cannot bootstrap a new machine. It assumes `~/.dotfiles` already exists, uses invalid shell collection syntax at runtime, iterates the literal word `files`, builds relative source paths, and cannot safely handle directories, conflicting links, repeat runs, or input while the script itself arrives through stdin.

The replacement must serve two distinct uses:

1. Install Kaisian as a third-party CLI that can apply any compatible Stow-style dotfiles repository.
2. Preserve a personal zero-argument `curl https://myurl | bash` path that installs a fixed Kaisian release and applies a fixed `taiansu/dotfiles` commit.

Kaisian only installs and links dotfiles. It does not install Homebrew packages, language runtimes, or other CLIs.

## Decisions

- Create a new public repository named `taiansu/kaisian`.
- Implement Kaisian as a Rust standalone binary.
- Distribute prebuilt macOS binaries; users do not need Rust or Node.js.
- Keep installer code, release automation, tests, and full product documentation in `kaisian`.
- Restructure `taiansu/dotfiles` into root-level Stow-style groups.
- Permit one non-payload metadata file, `.kaisian.toml`, in compatible dotfiles repositories.
- Keep the generic installer independent of any particular dotfiles repository.
- Keep a separate personal endpoint, `https://myurl`, whose response pins both the Kaisian release and the `taiansu/dotfiles` commit.
- Use shell locale by default; `--lang=en` and `--lang=zh-TW` override it.
- Support macOS only in the first release.

## Repository Boundaries

### `taiansu/kaisian`

The repository owns:

- the Rust CLI;
- a small shell installer for fixed release binaries;
- manifest parsing and validation;
- Git source acquisition;
- profile and group selection;
- the interactive checkbox UI;
- plan generation, backup, transaction, rollback, and recovery;
- English and Traditional Chinese product messages;
- release CI, checksums, tests, and Kaisian documentation.

The installed binary lives at `~/.local/bin/kaisian`. A source checkout at `~/Projects/kaisian` is only a developer working tree and is never required by an end user.

Suggested Rust boundaries:

- `cli`: command and option parsing with `clap`;
- `locale`: locale precedence, normalization, and message selection;
- `manifest`: `.kaisian.toml` schema and compatibility validation using `serde` and `toml`;
- `source`: local source validation and managed Git checkout operations through the installed `git` command;
- `groups`: group discovery, profile resolution, and command recommendations;
- `ui`: terminal checkbox selection;
- `plan`: source-to-target mapping and collision/path validation;
- `transaction`: backup, apply, rollback, persistent journal, and crash recovery;
- `output`: localized plan, warning, error, and completion rendering.

The modules communicate through typed domain values such as `GroupName`, `ProfileName`, `SourceRepo`, `TargetPath`, `ApplyPlan`, and `TransactionId`. Filesystem mutation occurs only in `source` and `transaction`.

### `taiansu/dotfiles`

The repository owns personal configuration payload and its `.kaisian.toml`. It does not own installer code.

Each non-hidden root directory is a group. Paths inside a group are relative to `$HOME`:

```text
dotfiles/
├── shell/
│   ├── .zshrc
│   ├── .zprofile
│   ├── .zshenv
│   ├── .config/zsh/aliasrc
│   └── .local/libexec/dotfiles/...
├── git/
│   ├── .gitconfig
│   └── .gitignore
├── mise/
│   └── .config/mise/config.toml
├── terminal/
├── editors/
├── agents/
├── cli/
├── macos/
├── homebrew/
├── dev/
├── .kaisian.toml
├── README.md
└── README.en.md
```

For example, `shell/.zshrc` maps to `~/.zshrc`, and `terminal/.config/ghostty/config` maps to `~/.config/ghostty/config`.

Root files are repository metadata, not groups. Hidden root directories such as `.git` and `.github` are not groups. Root-level non-hidden directories that are not payload groups are prohibited; installer tests, docs directories, and installer runtime belong in `kaisian`. Submodules must live inside their owning group.

## Installation and Bootstrap

### Generic installation

The generic release installer performs only these actions:

1. Detect `uname -s` and `uname -m`.
2. Select a fixed release asset.
3. Create the temporary download in `~/.local/bin` so the final rename stays on one filesystem.
4. Download the asset to that temporary file.
5. Verify its SHA-256 against the value embedded in the versioned installer.
6. Set executable permissions and run `<temporary-binary> --version` as a smoke check.
7. Atomically replace `~/.local/bin/kaisian`.

First-release assets are:

- `kaisian-aarch64-apple-darwin`;
- `kaisian-x86_64-apple-darwin`;
- release checksums.

Installing the same version is a no-op. The installer does not edit shell startup files. If `~/.local/bin` is absent from `PATH`, it prints the exact export required. The installer invokes the binary by absolute path whenever it performs a same-process follow-up action.

The checksum detects corruption and a mismatched release asset. It does not protect a user if the installer endpoint itself is compromised. Both READMEs must provide an inspect-before-execute path in addition to `curl | bash`.

### Personal endpoint

`https://myurl` serves a fixed wrapper configuration. Its response pins:

- an exact Kaisian release and per-platform checksum;
- `https://github.com/taiansu/dotfiles.git`;
- an exact dotfiles commit;
- `~/Projects/dotfiles` as the checkout directory;
- the manifest `default` profile;
- non-interactive confirmation through `--yes`.

The wrapper accepts and forwards `--profile`, `--groups`, `--interactive`, `--all`, `--dry-run`, and `--lang`. An explicit selection option replaces the wrapper's `default` profile; otherwise the default profile is used. The wrapper rejects every other argument. In `--dry-run` mode it downloads the verified Kaisian binary to a temporary directory and runs it there instead of installing it, so neither the CLI, a checkout, backups, nor links persist.

After installing Kaisian, the wrapper performs the equivalent of:

```bash
~/.local/bin/kaisian apply https://github.com/taiansu/dotfiles.git \
  --ref="$PINNED_DOTFILES_COMMIT" \
  --checkout-dir="$HOME/Projects/dotfiles" \
  --profile=default \
  --yes
```

The hostname and routing deployment for `https://myurl` are external to the two repositories. Kaisian must provide a versioned, configurable installer wrapper that can be deployed at that endpoint without changing the generic binary.

## CLI Contract

The first release exposes:

```text
kaisian apply <source> [selection] [options]
kaisian recover <transaction-id>
kaisian --version
kaisian --help
```

`<source>` accepts:

- an HTTPS Git URL;
- a GitHub `owner/repo` slug;
- a local directory.

Selection options are mutually exclusive:

```text
--profile=<name>
--groups=<comma-separated-groups>
--interactive
--all
```

Apply options:

```text
--ref=<git-tag-or-commit>
--checkout-dir=<path>
--dry-run
--yes
```

`--lang=en|zh-TW` is a global option accepted by `apply` and `recover`.

Selection precedence is:

1. an explicit selection option;
2. the manifest `default` profile;
3. otherwise an error that names `--interactive`, `--groups`, and `--all`.

Kaisian never treats all groups as an implicit safe default. `--yes` skips only the apply confirmation; it never skips manifest, source, path, collision, backup, or transaction checks.

## Manifest Contract

A compatible repository may omit `.kaisian.toml`. Without it, group discovery, `--groups`, `--all`, and `--interactive` still work, but no implicit profile exists.

A repository that provides a default profile uses:

```toml
schema = 1
minimum_kaisian_version = "0.1.0"

[profiles]
default = ["shell", "git", "mise"]

[groups.shell]
description = { en = "Zsh configuration", "zh-TW" = "Zsh 設定" }
recommends = ["mise", "fzf", "omp"]

[groups.git]
description = { en = "Git configuration", "zh-TW" = "Git 設定" }

[groups.mise]
description = { en = "mise configuration", "zh-TW" = "mise 設定" }
recommends = ["mise"]
```

Rules:

- `schema` must be a supported integer schema version.
- Kaisian stops before mutation when its version is lower than `minimum_kaisian_version`.
- Profile and group names are unique and non-empty.
- Every profile references existing groups.
- When `[groups]` exists, its entries and the repository's non-hidden root directories must match exactly.
- `recommends` produces a localized completion warning when a command is unavailable. It never triggers package installation.
- A missing translation falls back to the group name, not to a different natural language.

The `taiansu/dotfiles` default profile is `shell`, `git`, and `mise`.

## Locale and Interactive UI

Locale precedence is:

1. `--lang`;
2. `LC_ALL`;
3. `LC_MESSAGES`;
4. `LANG`;
5. English.

`--lang` accepts only `en` and `zh-TW`. Any Chinese shell locale maps to Traditional Chinese `zh-TW`; every other recognized locale maps to English. Invalid explicit values are errors.

The interactive selector is a real terminal multi-select UI:

- Up/Down and `j`/`k` move;
- Space toggles `[ ]` and `[x]`;
- Enter confirms;
- the manifest default profile is preselected;
- cancellation makes no filesystem changes;
- `--interactive` without a TTY is an error.

A Rust terminal UI library owns raw-mode restoration through a guard. Tests must verify restoration after confirmation, cancellation, and injected failure.

## Source Acquisition

Remote repositories default to:

```text
${XDG_DATA_HOME:-$HOME/.local/share}/kaisian/repos/<owner>/<repo>
```

The default XDG location is Kaisian-managed. If it exists, Kaisian requires the expected normalized remote and a clean worktree before fetching, checking out the resolved ref, and updating recursive submodules. It never stashes, resets, cleans, or deletes user data.

An explicit `--checkout-dir` is treated as user-managed:

- if absent, Kaisian clones the requested remote and ref there;
- if present, Kaisian requires the expected normalized remote but never changes its branch, HEAD, index, worktree, or submodules;
- when `--ref` is present for an existing checkout, its current HEAD must already equal the resolved commit or apply stops with instructions;
- when `--ref` is absent, Kaisian applies the existing checkout and reports its current commit.

This distinction lets a personal endpoint create `~/Projects/dotfiles` on a new machine without later detaching or downgrading a working branch.

A local directory source is read-only from Kaisian's perspective. It may be dirty and is never checked out or updated.

For `--dry-run`, a remote source is resolved in a temporary checkout. Kaisian does not create or update a managed checkout.

## Plan and Path Safety

Kaisian creates a complete immutable `ApplyPlan` before any `$HOME` mutation. Planning must:

- validate manifest schema and compatibility;
- resolve and validate selected groups;
- recursively enumerate regular leaf files, including hidden files inside groups;
- reject source symlinks in the first release;
- ignore empty source directories;
- reject duplicate targets across groups;
- reject absolute relative paths, `..`, and any target outside `$HOME`;
- reject a target whose existing parent component is a symlink;
- record whether each target is absent, already correct, or conflicting;
- report every planned link and backup in `--dry-run`.

Kaisian creates parent directories as real directories and links individual leaf files. It never replaces the whole `~/.config` directory with one symlink.

Links use absolute source paths. An existing symlink is a no-op only when its canonical source is the planned source.

## Transaction, Backup, and Recovery

Conflicts are moved to:

```text
${XDG_STATE_HOME:-$HOME/.local/state}/kaisian/backups/<transaction-id>/<home-relative-path>
```

A transaction identifier must be unique even for multiple runs in one second. Backups are never overwritten.

Before apply, Kaisian creates a persistent transaction journal containing the full plan and state. Journal updates use temporary-file-plus-rename and are flushed before the corresponding destructive operation. The journal records:

- parent directories created by Kaisian;
- links created by Kaisian;
- original targets moved to backup;
- transaction state: `applying`, `committed`, or `rolled_back`.

On an ordinary error, `SIGINT`, or `SIGTERM`, Kaisian automatically:

1. removes links created by the transaction;
2. restores targets moved to backup;
3. removes transaction-created directories that are still empty;
4. marks the journal `rolled_back`;
5. retains the journal and error summary.

`SIGKILL` cannot run rollback. A later apply detects any `applying` journal and refuses to start. It prints the exact `kaisian recover <transaction-id>` command. Recovery inspects the known source, target, and backup paths, refuses to overwrite post-crash user changes, and otherwise completes rollback before marking the transaction `rolled_back`.

A successful apply marks the journal `committed` and retains conflict backups. Automatic backup pruning and an undo command are not part of the first release.

## Dotfiles Migration

Initial groups are:

| Group | Payload |
|---|---|
| `shell` | Zsh startup files, alias/hash files, shell runtime scripts, Git prompt submodule |
| `git` | Git config and global ignore; no credentials |
| `mise` | mise config and default package files |
| `terminal` | Ghostty, Kitty, and cmux stable config |
| `editors` | Zed and other editor stable config |
| `agents` | OMP, Pi, shared agent instructions, and stable Peon Ping config |
| `cli` | btop, mactop, superfile, lazygit, Tidewave, Cabal, and similar CLI config |
| `macos` | Karabiner, Paneru, and other macOS app config |
| `homebrew` | Brewfile; linking only |
| `dev` | ctags, Gem, IEx, Credo, and similar development config |

Migration requirements:

- inventory and approve every source-to-target mapping before moving files;
- change Zsh references from clone-internal `~/.dotfiles/...` paths to installed XDG or `.local` paths;
- activate mise from `PATH` rather than a fixed `~/.local/bin/mise` path;
- guard fzf, omp, and other optional integrations with command/file checks;
- move submodules under their owning group;
- exclude logs, sessions, history, temporary files, automatic backups, and credentials from payload;
- move repository-maintenance patches and tests under a hidden `.maintenance/` directory so they remain available without being discovered as payload groups; retain root maintenance files such as `justfile` only when they remain useful;
- remove the old `setup.sh` only after Kaisian's end-to-end replacement passes; do not retain a compatibility shim.

The migration must specifically audit current Herdr logs and session data, Zed temporary/backup files, Kitty backup files, and `credential`. Credentials move to an untracked local file or a secrets manager; Kaisian does not manage them.

## Verification

### Kaisian

Unit tests cover:

- manifest parsing and validation;
- locale precedence and normalization;
- profile/group resolution and option conflicts;
- source and target path normalization;
- group target collisions;
- deterministic plan generation;
- journal state transitions and recovery decisions.

Integration tests use temporary HOME and local Git fixtures to cover:

- manifest default, explicit groups, all groups, and local source;
- idempotent repeat apply;
- conflict backup;
- ordinary-failure rollback;
- interrupted transaction recovery;
- dirty checkout and wrong remote refusal;
- exact ref verification and recursive submodules;
- dry-run with no persistent checkout or HOME/state mutation;
- English and Traditional Chinese output contracts.

PTY tests cover checkbox navigation, toggling, confirmation, cancellation, non-TTY refusal, and terminal restoration.

Installer tests cover platform asset selection, checksum mismatch, same-version no-op, atomic replacement, and PATH warning.

Release CI runs Rust formatting, Clippy with warnings denied, the complete test suite, builds both macOS targets, generates checksums, and smoke-runs each executable where the CI architecture permits. A release candidate is also smoke-tested by applying a fixture repository to a temporary HOME.

### Dotfiles

Verification covers:

- `.kaisian.toml` validation;
- applying the `shell`, `git`, and `mise` default profile to a temporary HOME;
- matching target sets between dry-run and apply;
- idempotent second apply;
- launching actual Zsh with the applied files in an environment that includes Zsh, Git, Homebrew, and mise but excludes fzf, omp, and Node.js, confirming the optional integrations do not cause startup errors.

## Documentation

Both repositories provide linked bilingual entry documents:

- `README.md`: Traditional Chinese;
- `README.en.md`: English.

The Kaisian READMEs document:

- generic binary installation;
- the personal one-line endpoint as an owner-specific example;
- default, custom, interactive, all, and dry-run flows;
- the complete CLI contract;
- `.kaisian.toml` and the Stow-style repository contract;
- managed remote and local source behavior;
- trust, checksum, backup, rollback, and recovery behavior;
- how to inspect the installer before execution.

The dotfiles READMEs document its groups, default profile, prerequisites, and exact Kaisian commands. They do not duplicate installer implementation details.

## First-Release Non-goals

- installing Homebrew, mise, Node.js, or other packages;
- managing third-party CLI packages;
- Linux or Windows binaries;
- secrets management;
- plugin or provider systems;
- Homebrew tap distribution;
- automatic self-update;
- automatic backup pruning;
- undoing committed transactions;
- resetting, cleaning, or stashing a user's Git checkout.

## Acceptance Criteria

1. A macOS user can install the fixed Kaisian release without Rust or Node.js.
2. `curl -fsSL https://myurl | bash` installs Kaisian and applies the pinned `taiansu/dotfiles` default profile to a fresh HOME without additional input.
3. `kaisian apply` works with another compatible root-group Stow-style repository.
4. Default, explicit group, all-group, interactive checkbox, and dry-run selection paths work through both `kaisian apply` and the personal curl endpoint as documented.
5. Locale follows shell settings and can be overridden by `--lang=en` or `--lang=zh-TW`.
6. Existing targets are never overwritten; conflicts are uniquely backed up.
7. Ordinary failures roll back the entire apply, and interrupted transactions block future applies until safe recovery.
8. Dirty or unexpected Git checkouts are never reset or adopted.
9. The migrated default dotfiles profile starts Zsh without fzf, omp, or Node.js installed.
10. Both repositories contain mutually linked Traditional Chinese and English READMEs.
