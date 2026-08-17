# Kaisian CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and release a generic macOS Rust CLI that safely applies compatible Stow-style dotfiles repositories.

**Architecture:** The `kaisian` binary separates pure manifest/group/plan logic from Git acquisition and transactional filesystem mutation. A versioned shell installer downloads a fixed release asset, verifies its checksum, smoke-tests it, and atomically installs it under `~/.local/bin`.

**Tech Stack:** Rust 2024 edition (MSRV 1.85), `clap`, `serde`, `toml`, `semver`, `dialoguer`, `thiserror`, `signal-hook`, `uuid`, macOS Bash, GitHub Actions.

## Global Constraints

- Create the new repository at `~/Projects/kaisian`; do not add Kaisian implementation files to `taiansu/dotfiles`.
- First release supports only `aarch64-apple-darwin` and `x86_64-apple-darwin`.
- The installed CLI requires Git, but never requires Node.js, Rust, fzf, gum, GNU Stow, or gettext.
- English and Traditional Chinese are the only UI languages; locale precedence is `--lang`, `LC_ALL`, `LC_MESSAGES`, `LANG`, English.
- Never install Homebrew, mise, Node.js, or any package managed by them.
- Never reset, clean, stash, or delete a user Git checkout.
- No filesystem mutation may occur before the complete apply plan passes validation.
- Tests use temporary HOME/XDG directories and local Git fixtures; they must never touch the developer's real HOME.
- Each task is committed in `taiansu/kaisian`; do not include unrelated `taiansu/dotfiles` changes.

---

### Task 1: Create the Rust repository and CLI contract

**Files:**
- Create: `~/Projects/kaisian/Cargo.toml`
- Create: `~/Projects/kaisian/rust-toolchain.toml`
- Create: `~/Projects/kaisian/src/main.rs`
- Create: `~/Projects/kaisian/src/lib.rs`
- Create: `~/Projects/kaisian/src/cli.rs`
- Create: `~/Projects/kaisian/src/error.rs`
- Create: `~/Projects/kaisian/tests/cli_contract.rs`

**Interfaces:**
- Produces: `cli::Cli`, `cli::Command`, `cli::ApplyArgs`, `cli::RecoverArgs`, and `run(Cli) -> Result<(), KaisianError>`.
- Selection flags are represented directly on `ApplyArgs` and are mutually exclusive through Clap.

- [ ] **Step 1: Initialize the repository and failing CLI tests**

Run:

```bash
mkdir -p "$HOME/Projects/kaisian"
cd "$HOME/Projects/kaisian"
git init -b main
mkdir -p src tests
```

Create tests that parse all public command forms and assert that `--profile`, `--groups`, `--interactive`, and `--all` conflict. The test must include:

```rust
use clap::Parser;
use kaisian::cli::{Cli, Command};

#[test]
fn parses_apply_with_explicit_groups() {
    let cli = Cli::try_parse_from([
        "kaisian", "--lang", "zh-TW", "apply", "owner/repo",
        "--groups", "shell,git", "--ref", "abc123", "--dry-run",
    ]).unwrap();
    let Command::Apply(args) = cli.command else { panic!("expected apply") };
    assert_eq!(args.source, "owner/repo");
    assert_eq!(args.groups.as_deref(), Some("shell,git"));
    assert!(args.dry_run);
}

#[test]
fn rejects_two_selection_modes() {
    let error = Cli::try_parse_from([
        "kaisian", "apply", "owner/repo", "--all", "--interactive",
    ]).unwrap_err();
    assert!(error.to_string().contains("cannot be used with"));
}
```

- [ ] **Step 2: Run the test and verify the crate is absent**

Run: `cargo test --test cli_contract`

Expected: FAIL because `Cargo.toml` and the `kaisian` crate do not exist yet.

- [ ] **Step 3: Add the crate and exact public CLI**

Use package metadata:

```toml
[package]
name = "kaisian"
version = "0.1.0"
edition = "2024"
rust-version = "1.85"
license = "MIT"
repository = "https://github.com/taiansu/kaisian"

[dependencies]
clap = { version = "4.5", features = ["derive"] }
dialoguer = "0.12"
dirs = "6.0"
semver = { version = "1.0", features = ["serde"] }
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
signal-hook = "0.3"
thiserror = "2.0"
toml = "0.8"
url = "2.5"
tempfile = "3.14"
uuid = { version = "1.11", features = ["v4"] }

[dev-dependencies]
assert_cmd = "2.0"
predicates = "3.1"
rexpect = "0.6"
```

Pin the toolchain:

```toml
[toolchain]
channel = "1.85.0"
profile = "minimal"
components = ["clippy", "rustfmt"]
targets = ["aarch64-apple-darwin", "x86_64-apple-darwin"]
```

Define `Cli` with global `--lang`, `apply`, and `recover`; define an `ArgGroup` named `selection` over the four selection flags. `RecoverArgs` contains one `transaction_id: String`. `main` parses and calls `kaisian::run`.

`KaisianError` starts with typed variants for CLI orchestration, IO paths, unsupported platform, and external-command failure. It must retain the failing path/command and source error rather than flattening everything into strings.

- [ ] **Step 4: Verify CLI parsing and help**

Run:

```bash
cargo test --test cli_contract
cargo run -- --help
cargo run -- apply --help
```

Expected: tests PASS; help lists every accepted option and marks selection options as conflicting.

- [ ] **Step 5: Commit the CLI contract**

```bash
git add Cargo.toml rust-toolchain.toml src tests/cli_contract.rs
git commit -m "feat: define kaisian CLI contract"
```

---

### Task 2: Implement locale resolution and bilingual messages

**Files:**
- Create: `src/locale.rs`
- Create: `src/messages.rs`
- Modify: `src/lib.rs`
- Test: `tests/locale.rs`

**Interfaces:**
- Produces: `Language::{English, TraditionalChinese}`.
- Produces: `resolve_language(explicit: Option<&str>, env: &impl Environment) -> Result<Language, KaisianError>`.
- Produces: `Messages::for_language(Language)` and stable message methods used by all later tasks.

- [ ] **Step 1: Write precedence and normalization tests**

Cover explicit override, `LC_ALL`, `LC_MESSAGES`, `LANG`, unset fallback, `zh_TW.UTF-8`, `zh-Hant`, `zh_CN`, and invalid explicit values. Assert every Chinese locale resolves to `TraditionalChinese`, while `ja_JP.UTF-8` resolves to English.

- [ ] **Step 2: Run the focused test**

Run: `cargo test --test locale`

Expected: FAIL because `locale` and `messages` modules are absent.

- [ ] **Step 3: Implement locale as a pure dependency-injected function**

Define:

```rust
pub trait Environment {
    fn var(&self, key: &str) -> Option<String>;
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Language { English, TraditionalChinese }
```

Normalize `_` to `-`, lowercase only for matching, and accept explicit values exactly `en` and `zh-TW`. Environment values beginning with `zh`, after normalization, map to Traditional Chinese. Other values map to English.

Create one `Messages` struct with methods for validation failures, plan headings, confirmation, backup, rollback, recovery, missing recommendations, and completion. Do not duplicate control flow between languages; only returned copy differs.

- [ ] **Step 4: Run locale tests and Clippy**

Run:

```bash
cargo test --test locale
cargo clippy --all-targets -- -D warnings
```

Expected: PASS with no warnings.

- [ ] **Step 5: Commit localization**

```bash
git add src/locale.rs src/messages.rs src/lib.rs tests/locale.rs
git commit -m "feat: add bilingual locale handling"
```

---

### Task 3: Parse manifests and resolve groups/profiles

**Files:**
- Create: `src/manifest.rs`
- Create: `src/groups.rs`
- Modify: `src/lib.rs`
- Test: `tests/manifest.rs`
- Test fixtures: `tests/fixtures/manifests/valid.toml`, `tests/fixtures/manifests/missing-group.toml`, `tests/fixtures/manifests/newer-cli.toml`

**Interfaces:**
- Produces: `Manifest`, `GroupMetadata`, `RepositoryGroups`, `Selection`, and `ResolvedSelection`.
- Produces: `Manifest::load(root: &Path, cli_version: &Version) -> Result<Option<Manifest>, KaisianError>`.
- Produces: `RepositoryGroups::discover(root: &Path, manifest: Option<&Manifest>)`.
- Produces: `resolve_selection(groups, manifest, selection) -> Result<ResolvedSelection, KaisianError>`.

- [ ] **Step 1: Write failing contract tests**

Tests must prove:

- root non-hidden directories are discovered in lexical order;
- root files and hidden directories are ignored;
- manifest `[groups]` and root directories must match exactly;
- profiles cannot reference missing groups;
- duplicate/empty names fail;
- `minimum_kaisian_version` is enforced;
- explicit selection overrides the default profile;
- no explicit selection and no default profile is an error;
- comma-separated groups are trimmed, deduplicated, validated, and returned in repository order.

- [ ] **Step 2: Run the focused tests**

Run: `cargo test --test manifest`

Expected: FAIL because manifest types are absent.

- [ ] **Step 3: Implement the schema without installer behavior**

Deserialize:

```rust
#[derive(Debug, Deserialize)]
pub struct Manifest {
    pub schema: u32,
    pub minimum_kaisian_version: Version,
    #[serde(default)] pub profiles: BTreeMap<String, Vec<String>>,
    #[serde(default)] pub groups: BTreeMap<String, GroupMetadata>,
}

#[derive(Debug, Deserialize)]
pub struct GroupMetadata {
    #[serde(default)] pub description: BTreeMap<String, String>,
    #[serde(default)] pub recommends: Vec<String>,
}
```

Only schema `1` is valid. Discovery uses `read_dir`, rejects non-UTF-8 group names, and sorts before validation. Group descriptions fall back to the group name.

- [ ] **Step 4: Verify manifest behavior**

Run:

```bash
cargo test --test manifest
cargo test
```

Expected: all tests PASS.

- [ ] **Step 5: Commit manifest/group resolution**

```bash
git add src/manifest.rs src/groups.rs src/lib.rs tests/manifest.rs tests/fixtures/manifests
git commit -m "feat: validate dotfiles manifests and groups"
```

---

### Task 4: Acquire local and remote sources safely

**Files:**
- Create: `src/source.rs`
- Create: `src/process.rs`
- Modify: `src/lib.rs`
- Test: `tests/source.rs`

**Interfaces:**
- Produces: `SourceSpec::{Local, Remote}`, `PreparedSource { root, commit, cleanup }`, and `SourceManager`.
- Consumes: apply source, `--ref`, `--checkout-dir`, dry-run, and XDG data path.
- `PreparedSource` owns any temporary checkout so it remains alive through planning/apply.

- [ ] **Step 1: Write local Git fixture tests**

Use temporary bare remotes and working repositories. Cover GitHub slug normalization, local path read-only behavior, default managed checkout, explicit checkout creation, dirty managed refusal, wrong remote refusal, exact ref checkout, existing explicit checkout HEAD mismatch, recursive submodule initialization, and dry-run temporary checkout.

- [ ] **Step 2: Verify tests fail before implementation**

Run: `cargo test --test source`

Expected: FAIL because `SourceManager` is absent.

- [ ] **Step 3: Implement Git through argv, never shell strings**

Define a `CommandRunner` trait whose production implementation invokes `std::process::Command`. Every Git call uses separate argv values and `--` where paths follow options.

Rules:

- `owner/repo` becomes `https://github.com/owner/repo.git` only when both slug components pass conservative ASCII validation.
- Default managed checkouts live below `${XDG_DATA_HOME:-~/.local/share}/kaisian/repos/<owner>/<repo>`.
- Managed checkouts may fetch and checkout only when remote matches and worktree is clean.
- Explicit existing `--checkout-dir` is never checked out or updated; requested ref must already match HEAD.
- Local source performs no Git command except optional read-only `rev-parse HEAD` for reporting.
- Dry-run remote acquisition uses `tempfile::TempDir` and never creates the managed path.

- [ ] **Step 4: Run source tests**

Run:

```bash
cargo test --test source
cargo clippy --all-targets -- -D warnings
```

Expected: PASS; injected runner tests show no `reset`, `clean`, or `stash` argv.

- [ ] **Step 5: Commit source acquisition**

```bash
git add src/source.rs src/process.rs src/lib.rs tests/source.rs
git commit -m "feat: acquire dotfiles sources safely"
```

---

### Task 5: Build an immutable safe apply plan

**Files:**
- Create: `src/plan.rs`
- Modify: `src/lib.rs`
- Test: `tests/plan.rs`

**Interfaces:**
- Produces: `ApplyPlan`, `PlannedLink`, and `TargetState::{Absent, CorrectLink, Conflict}`.
- Produces: `build_plan(home, source_root, selected_groups) -> Result<ApplyPlan, KaisianError>`.
- Later transaction code consumes `ApplyPlan` without rediscovering files.

- [ ] **Step 1: Write boundary and invariant tests**

Cover hidden leaf files, exact `.git` path-component exclusion for nested submodules, lexical deterministic order, empty directories, source symlink rejection, duplicate target rejection, correct-link no-op, conflicting file/link/directory classification, `..` rejection, target outside HOME rejection, and existing symlink parent rejection.

- [ ] **Step 2: Run the focused test**

Run: `cargo test --test plan`

Expected: FAIL because `build_plan` is absent.

- [ ] **Step 3: Implement plan values and canonical checks**


`PlannedLink` contains absolute `source`, absolute `target`, `home_relative`, selected `group`, and preflight `state`. Recursion must not follow symlinks and must prune any file or directory whose name is exactly `.git`. Canonicalize the source root and each regular source file, but preserve the intended target's lexical HOME-relative path. Walk every existing target parent with `symlink_metadata`; reject a symlink before mutation.

- [ ] **Step 4: Run all pure-domain tests**

Run:

```bash
cargo test --test plan
cargo test --test manifest --test locale
```

Expected: PASS.

- [ ] **Step 5: Commit planning logic**

```bash
git add src/plan.rs src/lib.rs tests/plan.rs
git commit -m "feat: generate validated apply plans"
```

---

### Task 6: Apply plans transactionally with rollback

**Files:**
- Create: `src/transaction.rs`
- Modify: `src/lib.rs`
- Test: `tests/transaction.rs`

**Interfaces:**
- Produces: `Transaction`, `TransactionJournal`, `TransactionState`, and `ApplyOutcome`.
- Consumes: immutable `ApplyPlan`, HOME, XDG state directory, and a signal cancellation flag.
- Journal path: `${XDG_STATE_HOME:-~/.local/state}/kaisian/backups/<uuid>/transaction.json`.

- [ ] **Step 1: Write failure-injection tests**

Cover absent target linking, correct-link no-op, conflicting file/link/directory backup, unique transaction IDs, no backup overwrite, failure after the first and second mutation, rollback ordering, empty created-directory cleanup, retained committed backup, and journal states.

Use an injected filesystem operation trait to fail at exact operation counts without changing production error handling.

- [ ] **Step 2: Run the focused tests**

Run: `cargo test --test transaction`

Expected: FAIL because transaction types are absent.

- [ ] **Step 3: Implement write-ahead journal and rollback**

Before each destructive operation, atomically rewrite and `sync_all` the journal with the intended path and operation. Use a temporary journal file in the same directory, then rename it. The apply order for each conflict is backup rename followed by link creation. On any error or cancellation:

1. remove links created by this transaction in reverse order;
2. restore backups in reverse order;
3. remove transaction-created directories deepest first when empty;
4. mark and flush `rolled_back`.

Use absolute symlink sources. Mark and flush `committed` only after every planned link is complete.

- [ ] **Step 4: Run transaction and integration tests**

Run:

```bash
cargo test --test transaction
cargo test
```

Expected: PASS; temporary HOME contents match pre-apply state after each injected failure.

- [ ] **Step 5: Commit transactional apply**

```bash
git add src/transaction.rs src/lib.rs tests/transaction.rs
git commit -m "feat: apply links with transactional rollback"
```

---

### Task 7: Recover interrupted transactions

**Files:**
- Modify: `src/transaction.rs`
- Create: `src/recovery.rs`
- Modify: `src/lib.rs`
- Test: `tests/recovery.rs`

**Interfaces:**
- Produces: `find_incomplete_transactions(state_root)` and `recover_transaction(transaction_id)`.
- `apply` consumes `find_incomplete_transactions` and refuses to start when any journal remains `applying`.

- [ ] **Step 1: Write interrupted-state tests**

Construct journals/filesystems representing interruption before backup, after backup, after link creation, and after a user changed the target post-crash. Safe cases must restore; changed-target cases must refuse without overwriting.

- [ ] **Step 2: Run the focused tests**

Run: `cargo test --test recovery`

Expected: FAIL because recovery is absent.

- [ ] **Step 3: Implement conservative recovery**

Recovery may remove a target only when it is still the exact planned symlink. It may restore a backup only when the intended target is absent after that removal. Any other target state produces a localized manual-recovery error containing paths but no file contents.

- [ ] **Step 4: Verify recovery and blocked apply**

Run:

```bash
cargo test --test recovery
cargo test --test transaction
```

Expected: PASS; changed user targets remain byte-for-byte intact.

- [ ] **Step 5: Commit recovery**

```bash
git add src/recovery.rs src/transaction.rs src/lib.rs tests/recovery.rs
git commit -m "feat: recover interrupted apply transactions"
```

---

### Task 8: Add the bilingual checkbox selector

**Files:**
- Create: `src/ui.rs`
- Modify: `src/lib.rs`
- Test: `tests/interactive.rs`

**Interfaces:**
- Produces: `select_groups(groups, preselected, messages, terminal) -> Result<Vec<GroupName>, KaisianError>`.
- Consumes repository-ordered groups and the manifest default profile.

- [ ] **Step 1: Write PTY behavior tests**

Spawn the real binary in a PTY fixture repository. Test Space toggle, Up/Down, `j`/`k`, Enter, Ctrl-C, default preselection, English labels, Traditional Chinese labels, and non-TTY refusal.

- [ ] **Step 2: Run the PTY test**

Run: `cargo test --test interactive -- --nocapture`

Expected: FAIL because the selector is absent.

- [ ] **Step 3: Implement `dialoguer::MultiSelect` behind a small adapter**

Keep `dialoguer` types inside `ui.rs`. Map selected indexes back to typed group names in repository order. Detect TTY before entering raw mode. Install a guard so normal completion, error, panic unwinding, and Ctrl-C release terminal state.

- [ ] **Step 4: Verify PTY cleanup**

Run:

```bash
cargo test --test interactive -- --nocapture
cargo test
```

Expected: PASS; a command sent after cancel in the same PTY echoes normally.

- [ ] **Step 5: Commit the selector**

```bash
git add src/ui.rs src/lib.rs tests/interactive.rs
git commit -m "feat: add interactive group selection"
```

---

### Task 9: Wire apply/recover commands and localized output

**Files:**
- Create: `src/output.rs`
- Create: `src/app.rs`
- Modify: `src/lib.rs`
- Modify: `src/main.rs`
- Test: `tests/cli_apply.rs`
- Test: `tests/cli_recover.rs`
- Create: `tests/fixtures/basic/.kaisian.toml`
- Create: `tests/fixtures/basic/shell/.zshrc`

**Interfaces:**
- `app::run_apply` composes locale → source → manifest/groups → selection → plan → confirmation → transaction → recommendations.
- `app::run_recover` composes locale → journal lookup → conservative recovery.

- [ ] **Step 1: Write end-to-end CLI tests and a static smoke fixture**

Cover default manifest profile, explicit groups, all, dry-run, yes, confirmation rejection, idempotent second apply, missing recommendations, incomplete-transaction blocking, recover, and both languages. Assert observable files and stable message fragments, not ANSI color codes. Add a static local-source fixture whose manifest defines `default = ["shell"]` and whose `shell/.zshrc` contains only `export KAISIAN_FIXTURE=1`.

- [ ] **Step 2: Run end-to-end tests**

Run: `cargo test --test cli_apply --test cli_recover`

Expected: FAIL because orchestration is absent.

- [ ] **Step 3: Implement orchestration with no duplicate business rules**

`output.rs` receives typed plans/outcomes and renders them. `app.rs` is the only layer allowed to sequence modules. Dry-run prints the resolved source commit, selected groups, every link/no-op/backup, and then exits before creating state. `--yes` skips only confirmation. Recommendation checks use `PATH` lookup after commit and never change the exit status.

- [ ] **Step 4: Smoke-test the actual binary**

Run:

```bash
cargo test
cargo run -- apply tests/fixtures/basic --all --dry-run
```

Expected: all tests PASS; smoke output contains a commit/source summary and plan, while the fixture HOME remains unchanged.

- [ ] **Step 5: Commit command orchestration**

```bash
git add src/app.rs src/output.rs src/lib.rs src/main.rs tests/cli_apply.rs tests/cli_recover.rs tests/fixtures/basic
git commit -m "feat: complete apply and recovery commands"
```

---

### Task 10: Build the fixed binary installer and release CI

**Files:**
- Create: `installer/install.sh.in`
- Create: `scripts/render-installer.sh`
- Create: `tests/installer_test.sh`
- Create: `.github/workflows/ci.yml`
- Create: `.github/workflows/release.yml`
- Create: `.gitignore`

**Interfaces:**
- Installer template tokens: `@VERSION@`, `@AARCH64_SHA256@`, `@X86_64_SHA256@`, and `@RELEASE_BASE_URL@`.
- `render-installer.sh VERSION RELEASE_BASE_URL CHECKSUMS_FILE OUTPUT` produces a self-contained versioned installer.

- [ ] **Step 1: Write shell installer tests with fake `uname`, `curl`, and binary assets**

Tests cover arm64/x86 selection, unsupported OS, checksum mismatch, failed `--version`, same-version no-op, atomic replacement, and PATH warning. Each test sets temporary HOME and PATH.

- [ ] **Step 2: Run the installer test**

Run: `bash tests/installer_test.sh`

Expected: FAIL because installer files are absent.

- [ ] **Step 3: Implement rendering and installation**

The rendered installer uses `set -euo pipefail`, creates `~/.local/bin`, creates the temporary download with `mktemp "$HOME/.local/bin/.kaisian.XXXXXX"`, installs a trap that removes only that temp file, verifies with `shasum -a 256`, runs the executable's `--version`, and finishes with `mv -f` in the same directory. It never uses `eval`, sources downloaded content, or edits shell files.

- [ ] **Step 4: Add CI and release workflows**

CI runs format, Clippy, tests, installer tests, and an actual temporary-HOME fixture apply. Release builds both target assets, computes checksums, renders `install.sh`, smoke-tests the native asset, and uploads assets only for `v*` tags.

- [ ] **Step 5: Verify the release path locally**

Run:

```bash
cargo fmt --check
cargo clippy --all-targets -- -D warnings
cargo test
bash tests/installer_test.sh
```

Expected: every command exits 0.

- [ ] **Step 6: Commit installer and CI**

```bash
git add installer scripts tests/installer_test.sh .github .gitignore
git commit -m "ci: release verified kaisian binaries"
```

---

### Task 11: Document the generic CLI in both languages

**Files:**
- Create: `README.md`
- Create: `README.en.md`
- Create: `LICENSE`

**Interfaces:**
- Documentation describes only released Task 1–10 behavior; personal endpoint integration remains in the third plan.

- [ ] **Step 1: Write Traditional Chinese and English READMEs**

Both documents must include fixed binary installation, inspect-before-run installation, CLI examples, locale behavior, `.kaisian.toml`, Stow root-group rules, managed versus explicit/local checkouts, trust model, backups, rollback, and recovery. Put a language switch at the top of each file.

- [ ] **Step 2: Check command examples against real help**

Run:

```bash
cargo run -- --help
cargo run -- apply --help
cargo run -- recover --help
```

Expected: every documented flag and command appears exactly as written.

- [ ] **Step 3: Run complete verification**

Run:

```bash
cargo fmt --check
cargo clippy --all-targets -- -D warnings
cargo test
bash tests/installer_test.sh
```

Expected: all checks pass.

- [ ] **Step 4: Commit generic documentation**

```bash
git add README.md README.en.md LICENSE
git commit -m "docs: document kaisian CLI"
```
