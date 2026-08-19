# Dotfiles GNU Stow Package Migration Implementation Plan

> **Status: superseded on 2026-08-20.** The migration was completed manually; the executed steps are recorded in `docs/stow-migration.md`. The layout below is partly historical: submodules stayed at the repository root instead of moving into `.vendor/`, and documentation/templates were not moved into `.maintenance/`. Keep this file for design rationale only; do not execute it.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate `taiansu/dotfiles` into ten manifest-declared GNU Stow packages consumed safely by the shell-only Kaisian wrapper.

**Architecture:** Each non-hidden root package is an installation image relative to `$HOME`, with every leading dot represented by GNU Stow's `dot-` convention. External Git submodules remain in a hidden non-payload `.vendor/` tree; installed Zsh files discover the actual checkout through their own resolved Stow link, so custom checkout paths remain usable. Repository documentation/tests/patches/templates move under hidden `.maintenance/`, while generated state and credentials stay outside the checkout.

**Tech Stack:** Git, GNU Stow, `/bin/bash`, `/bin/zsh`, `/usr/bin/plutil`, Kaisian `~/Projects/kaisian/setup.sh`.

## Global Constraints

- Complete `2026-08-18-kaisian-shell-stow-wrapper.md` Tasks 1–6 before final end-to-end Kaisian smoke; layout tasks may begin after its manifest/Stow contract is stable.
- Work only in `/Users/tai/Projects/dotfiles/.worktrees/kaisian-migration` on `feature/kaisian-stow-wrapper` until integration.
- Credential containment/history rewrite is already complete at rewritten base `0b3b0c3`; never inspect, print, restore, or recommit deleted credential contents.
- Preserve the old checkout at `~/Projects/dotfiles.pre-credential-rewrite.20260818161031` until every ignored/untracked file is accounted for; deleting it requires a separate explicit user approval.
- Live manifest is `.kaisian.json` schema 1. Declared groups in stable order: `shell`, `git`, `mise`, `terminal`, `editors`, `agents`, `cli`, `macos`, `homebrew`, `dev`.
- Profiles are `minimal=[shell,git]`, `default=[shell,git,mise]`, and `workstation=[shell,git,mise,terminal,editors,agents,cli,macos,homebrew,dev]`.
- No hidden component, non-ASCII component, source symlink, empty directory, gitlink, or nested repository may exist inside a selectable package.
- Every dot target component uses `dot-`: `shell/dot-zshrc` maps to `~/.zshrc`; never store `.zshrc` directly in a package.
- Submodules and `.gitmodules` are repository metadata only; submodule roots move under hidden `.vendor/` and are never Stow payload.
- Generated logs, locks, histories, sessions, automatic backups, release caches, `*.bak`, `.tmp*`, and credentials are not payload. Move user-valued generated data outside the checkout before deleting a tracked path.
- Tests use real GNU Stow in a temporary target HOME with an empty controlled global ignore and `--dotfiles --no-folding --compat`.
- Do not delete the legacy `setup.sh` until all ten packages pass real Stow and local Kaisian checks.

## File Map

- `.kaisian.json` — live bilingual group/profile contract.
- `shell/` — Zsh startup, alias/hash config, executable helpers; discovers `.vendor` from resolved installed link.
- `git/` — `.gitconfig`, `.gitignore`, and `.config/git/ignore`.
- `mise/` — mise config/default package files.
- `terminal/` — Ghostty, Kitty, and cmux stable configuration.
- `editors/` — Zed stable settings/keymap/themes.
- `agents/` — OMP, Pi, Claude/Codex, and stable agent config.
- `cli/` — btop, mactop, superfile, Tidewave, lazygit, cabal, and stable Herdr config.
- `macos/` — Karabiner and Paneru stable configuration/assets.
- `homebrew/` — `.Brewfile`.
- `dev/` — language/tool dotfiles and `~/.local/bin/rust` helper.
- `.vendor/` — `fzf-git` and `git-prompt.zsh` submodule checkouts only.
- `.maintenance/tests/` — manifest, Stow mapping, Zsh startup, and repository invariant tests.
- `.maintenance/docs/`, `.maintenance/patches/`, `.maintenance/templates/` — tracked non-payload material.

---

### Task 1: Define the JSON Manifest and Root/Typed-Tree Contract

**Files:**
- Create: `.maintenance/fixtures/core-manifest.json`
- Create: `.maintenance/fixtures/final-manifest.json`
- Create: `.maintenance/tests/manifest-contract.sh`
- Create later from final fixture: `.kaisian.json`

**Interfaces:**
- Core fixture declares `shell`, `git`, `mise` and profiles `minimal`, `default`.
- Final fixture declares all ten groups and profiles `minimal`, `default`, `workstation`.
- Test accepts a repository root argument and validates schema, order, bilingual descriptions, exact root-package alignment, safe names, and typed target collisions.

- [ ] **Step 1: Write the failing manifest contract test**

Create a Bash 3.2 test that uses only plutil plus shell path checks. It must:

```text
validate schema == 1
extract group count and each groups.N.name/description.en/description.zh-TW
extract profile dictionary keys with `plutil -extract profiles raw`
reject unknown/duplicate/empty group/profile values
assert package names match ^[a-z][a-z0-9_-]*$
assert every declared group has one non-hidden root directory
assert every non-hidden root directory is declared
transform every dot- path component
build an ASCII-case-folded typed path list
allow directory/directory sharing only
reject duplicate leaves and leaf/directory/descendant collisions
```

Use a temporary copied plist for unknown-key detection: extract each object, remove every known key with `plutil -remove`, convert to JSON, and require the remainder to equal `{}`. Do not parse JSON with grep/sed/eval.

- [ ] **Step 2: Run the test before fixtures exist**

Run: `/bin/bash .maintenance/tests/manifest-contract.sh`

Expected: nonzero with an explicit missing `core-manifest.json` failure.

- [ ] **Step 3: Create both exact schema 1 fixtures**

Use this group order and bilingual descriptions:

```text
shell    Shell configuration / Shell 設定
git      Git configuration / Git 設定
mise     Runtime and tool versions / 執行環境與工具版本
terminal Terminal configuration / 終端機設定
editors  Editor configuration / 編輯器設定
agents   Agent configuration / Agent 設定
cli      CLI application configuration / CLI 應用程式設定
macos    macOS application configuration / macOS 應用程式設定
homebrew Homebrew bundle / Homebrew 套件清單
dev      Development tool configuration / 開發工具設定
```

Profiles are exactly the arrays in Global Constraints; fixture files contain no recommendations or runtime dependency metadata.

- [ ] **Step 4: Run fixture positive and generated negative cases**

Run: `/bin/bash .maintenance/tests/manifest-contract.sh`

Expected: core/final fixtures pass; missing package, extra package, unsafe name, transformed traversal, ASCII-case duplicate, duplicate leaf, and leaf/descendant generated fixtures fail as expected while the suite exits 0.

- [ ] **Step 5: Commit the manifest contract**

```bash
git add .maintenance/fixtures .maintenance/tests/manifest-contract.sh
git -c commit.gpgsign=false commit -m "test: define dotfiles package contract"
```

---

### Task 2: Migrate `shell`, `git`, and `mise` with Non-Payload Vendor Submodules

**Files:**
- Move: `zsh/zshrc` → `shell/dot-zshrc`
- Move: `zsh/zprofile` → `shell/dot-zprofile`
- Move: `zsh/zshenv` → `shell/dot-zshenv`
- Move: `zsh/aliasrc` → `shell/dot-config/zsh/aliasrc`
- Move if tracked: `hashrc` → `shell/dot-config/zsh/hashrc`
- Move: `scripts/fzf_listoldfiles.sh`, `scripts/zoxide_openfiles_nvim.sh`, `scripts/vimr_wait.sh` → `shell/dot-local/libexec/dotfiles/`
- Move submodules: `fzf-git` → `.vendor/fzf-git`; `git-prompt.zsh` → `.vendor/git-prompt.zsh`
- Modify: `.gitmodules`
- Remove duplicate after comparison: `scripts/fzf-git.sh`
- Move: `git/gitconfig` → `git/dot-gitconfig`
- Move: `git/gitignore` → `git/dot-gitignore`
- Move: `config/git/ignore` → `git/dot-config/git/ignore`
- Move: `config/mise/config.toml` → `mise/dot-config/mise/config.toml`
- Move: `mise/asdfrc`, `default-npm-packages`, `default-gems`, `default-mix-commands` → corresponding `mise/dot-*` names
- Create: `.maintenance/tests/default-packages.sh`

**Interfaces:**
- Installed Zsh files locate the checkout root by resolving the source path of the Stow-created `~/.zshrc` link, then source `.vendor` only when the expected file exists.
- Shell startup succeeds when `fzf`, `omp`, mise, Node.js, and either vendor submodule are absent.
- Core Stow operation produces leaf links only; submodule directories never appear under target HOME.

- [ ] **Step 1: Write the failing default-package Stow/startup test**

The test copies core packages into a temporary Stow root, writes an empty controlled `.stow-global-ignore`, and runs:

```bash
env -i HOME="$sandbox_home" PATH="$PATH" LC_ALL=C \
  stow --dir "$fixture_root" --target "$target_home" \
  --dotfiles --no-folding --compat -R shell git mise
```

Assert exact links for `.zshrc`, `.zprofile`, `.zshenv`, `.config/zsh/aliasrc`, `.gitconfig`, `.gitignore`, `.config/git/ignore`, `.config/mise/config.toml`, and every mise default file. Assert no target path contains `.vendor`, `.git`, or `.gitmodules`. Run Stow twice and require unchanged link destinations. Launch `/bin/zsh -dfc` with restricted PATH and source the three startup files; reject `command not found` for optional tools.

- [ ] **Step 2: Run before migration and observe missing dot-path layout**

Run: `/bin/bash .maintenance/tests/default-packages.sh`

Expected: nonzero because `shell/dot-zshrc` and other package paths do not exist.

- [ ] **Step 3: Move tracked files and vendor submodules**

Use `git mv`; update `.gitmodules` paths to `.vendor/fzf-git` and `.vendor/git-prompt.zsh`, then `git submodule sync --recursive` and `git submodule update --init --recursive`. Compare `scripts/fzf-git.sh` with `.vendor/fzf-git/fzf-git.sh` by checksum/content before removing the duplicate; if they differ, preserve the local file as `shell/dot-local/libexec/dotfiles/fzf-git.sh` instead of deleting it.

- [ ] **Step 4: Make Zsh derive the checkout and guard optional dependencies**

In `shell/dot-zshrc`, derive the checkout from the resolved script path rather than hard-coding `~/.dotfiles`:

```zsh
_dotfiles_checkout=${${(%):-%N}:A:h:h}
_aliasrc=${XDG_CONFIG_HOME:-$HOME/.config}/zsh/aliasrc
[[ -r $_aliasrc ]] && source $_aliasrc

_git_prompt=$_dotfiles_checkout/.vendor/git-prompt.zsh/git-prompt.zsh
[[ -r $_git_prompt ]] && source $_git_prompt

_fzf_git=$_dotfiles_checkout/.vendor/fzf-git/fzf-git.sh
if command -v fzf >/dev/null 2>&1 && [[ -r $_fzf_git ]]; then
  source $_fzf_git
fi

if command -v mise >/dev/null 2>&1; then
  eval "$(mise activate zsh)"
fi

unset _aliasrc _git_prompt _fzf_git _dotfiles_checkout
```

Guard OMP completion generation/source with `command -v omp`; guard interactive fzf loading with both `command -v fzf` and a TTY. In `dot-zshenv`, read the local credential only from `~/.config/dotfiles/credential` behind a readable-file check; never recreate it in the repository.

- [ ] **Step 5: Verify syntax, custom checkout discovery, Stow, and startup**

Run:

```bash
/bin/zsh -n shell/dot-zshenv shell/dot-zprofile shell/dot-zshrc
/bin/bash .maintenance/tests/default-packages.sh
```

Expected: all assertions pass when the fixture checkout path is not named `.dotfiles`; optional tools absent produces no startup error.

- [ ] **Step 6: Commit core packages**

```bash
git add .gitmodules .vendor shell git mise .maintenance/tests/default-packages.sh
git -c commit.gpgsign=false commit -m "feat: migrate core Stow packages"
```

---

### Task 3: Migrate Stable Terminal, Editor, Agent, CLI, macOS, Homebrew, and Dev Packages

**Files:**
- Create/move under: `terminal/`, `editors/`, `agents/`, `cli/`, `macos/`, `homebrew/`, `dev/`
- Create: `.maintenance/tests/all-packages.sh`

**Interfaces:**
- Every leaf maps to the same current HOME location implied by its old root/config path.
- Test consumes all ten groups, uses real Stow, and asserts exact target→source links plus no structural collision.

- [ ] **Step 1: Write the failing all-package link matrix test**

The expected matrix must include at least:

```text
terminal/dot-config/ghostty/config                 .config/ghostty/config
terminal/dot-config/kitty/kitty.conf               .config/kitty/kitty.conf
terminal/dot-config/cmux/cmux.json                 .config/cmux/cmux.json
editors/dot-config/zed/settings.json               .config/zed/settings.json
editors/dot-config/zed/keymap.json                 .config/zed/keymap.json
agents/dot-omp/agent/config.yml                    .omp/agent/config.yml
agents/dot-pi/agent/settings.json                  .pi/agent/settings.json
cli/dot-config/btop/btop.conf                      .config/btop/btop.conf
cli/dot-config/mactop/config.json                  .config/mactop/config.json
cli/dot-config/superfile/config.toml               .config/superfile/config.toml
cli/dot-config/tidewave/app.toml                   .config/tidewave/app.toml
cli/dot-config/lazygit/config.yml                  .config/lazygit/config.yml
cli/dot-config/cabal/config                        .config/cabal/config
macos/dot-config/karabiner/karabiner.json          .config/karabiner/karabiner.json
macos/dot-config/paneru/paneru.toml                .config/paneru/paneru.toml
homebrew/dot-Brewfile                              .Brewfile
dev/dot-ctags                                      .ctags
dev/dot-gemrc                                      .gemrc
dev/dot-gnuplot                                    .gnuplot
dev/dot-agignore                                   .agignore
dev/dot-iex.exs                                    .iex.exs
dev/dot-credo.exs                                  .credo.exs
dev/dot-local/bin/rust                             .local/bin/rust
```

Apply all groups twice with sanitized real Stow and assert every target is a leaf symlink into its owning package.

- [ ] **Step 2: Run before migration and observe absent package failure**

Run: `/bin/bash .maintenance/tests/all-packages.sh`

Expected: nonzero on the first missing optional package mapping.

- [ ] **Step 3: Move terminal, editor, and macOS stable files**

Use exact destinations:

```text
config/ghostty/**                    → terminal/dot-config/ghostty/**
config/kitty/{kitty.conf,current-theme.conf,kitty.app.icns} → terminal/dot-config/kitty/
config/cmux/cmux.json                → terminal/dot-config/cmux/cmux.json
config/zed/{settings.json,keymap.json,themes/} → editors/dot-config/zed/
config/karabiner/{karabiner.json,assets/} → macos/dot-config/karabiner/
config/paneru/paneru.toml            → macos/dot-config/paneru/paneru.toml
```

Exclude `settings_backup.json`, `automatic_backups/`, `.tmp*`, and `*.bak`.

- [ ] **Step 4: Move agent and CLI stable files**

Use exact destinations:

```text
omp/agent/{config.yml,no-superpowers.yml} → agents/dot-omp/agent/
pi/agent/settings.json                    → agents/dot-pi/agent/settings.json
pi/agent/extensions/*.ts                  → agents/dot-pi/agent/extensions/
copy `AGENTS.md`                      → agents/dot-omp/agent/AGENTS.md; keep root `AGENTS.md` as repository instructions and assert both copies match
claude_codex_instructions.md              → agents/dot-claude/CLAUDE.md
config/{btop,mactop,superfile,tidewave,lazygit,cabal}/** → cli/dot-config/<app>/**
config/herdr/config.toml and stable plugins/ → cli/dot-config/herdr/
```

Do not move `config.yml.lock`, `pi/agent/npm/.gitignore`, Herdr `.plugins.lock`, release notes, logs, sessions, or cache state into packages. If Pi npm metadata is required by Pi at runtime, represent it as a regular tracked non-hidden file with a `dot-` target name; never copy its nested `.gitignore` into the package.

- [ ] **Step 5: Move Homebrew and development files**

Move `homebrew/Brewfile` to `homebrew/dot-Brewfile`; move root `ctags`, `gemrc`, `gnuplot`, `agignore`, `iex.exs`, `credo.exs` to corresponding `dev/dot-*`; move executable `rust` to `dev/dot-local/bin/rust` and preserve mode `0755`.

- [ ] **Step 6: Verify all packages and commit**

Run:

```bash
/bin/bash .maintenance/tests/manifest-contract.sh
/bin/bash .maintenance/tests/all-packages.sh
git diff --check
```

Expected: all mappings and idempotent reapply pass; generated/hidden/package-gitlink scans pass.

```bash
git add terminal editors agents cli macos homebrew dev .maintenance/tests/all-packages.sh
git -c commit.gpgsign=false commit -m "feat: migrate optional Stow packages"
```

---

### Task 4: Quarantine Maintenance Material, Generated State, and Legacy Layout

**Files:**
- Move: `docs/` → `.maintenance/docs/`
- Move: `patches/` → `.maintenance/patches/`
- Move existing `tests/` → `.maintenance/tests/peon-ping/`
- Merge each tracked file from `templates/` into the existing `.maintenance/templates/`; do not create `.maintenance/templates/templates/`
- Create: `.kaisian.json` from final fixture
- Modify: `.gitignore`, `justfile`, `.gitmodules`
- Remove after verification: legacy `setup.sh`, empty `config/`, `zsh/`, `scripts/`, `omp/`, `pi/`, old non-package directories

**Interfaces:**
- Final non-hidden root directories are exactly the ten package names.
- Hidden tracked roots are repository metadata, `.maintenance`, and `.vendor`; no generated state lives there.
- Existing just recipes use new maintenance paths and new config locations.

- [ ] **Step 1: Extend the root and generated-state invariant test**

Require sorted non-hidden root directories to equal:

```text
agents cli dev editors git homebrew macos mise shell terminal
```

Require `.kaisian.json` to equal the final fixture semantically. Reject tracked paths matching known generated classes: lock, log, session/history, automatic backup, release-note cache, `.tmp*`, and `*.bak`, except explicit immutable test fixtures.

- [ ] **Step 2: Run and observe legacy-root failure**

Run: `/bin/bash .maintenance/tests/manifest-contract.sh .`

Expected: nonzero listing legacy non-hidden roots such as `config`, `zsh`, `scripts`, `omp`, or `pi`.

- [ ] **Step 3: Move tracked maintenance trees and update recipes**

Use `git mv`; update `justfile` references, especially Peon Ping patch/test paths, to `.maintenance/patches/...` and `.maintenance/tests/...`. Move the currently executing design/spec/plan documents with `docs/`; do not leave a compatibility copy at root.

Install the live manifest:

```bash
cp .maintenance/fixtures/final-manifest.json .kaisian.json
git rm .maintenance/fixtures/core-manifest.json .maintenance/fixtures/final-manifest.json
```

- [ ] **Step 4: Remove or externalize generated tracked state**

Remove tracked Zed settings backup, OMP/Pi/Herdr locks, release notes, logs, sessions, temp/backup files, and obsolete backup markers only after determining they are generated. If a generated file contains user-valued local state, copy it without printing to `~/.local/state/dotfiles-migration/<HOME-relative-path>`, verify with `cmp`, then remove it from Git. Add precise anchored ignore rules; never broadly ignore all JSON/TOML.

- [ ] **Step 5: Remove legacy installer/layout only after Stow tests pass**

Run core/all tests first. Require `test -f dotfiles_backup/all_your_original_dotfiles_belong_to_us.txt` and `test ! -s dotfiles_backup/all_your_original_dotfiles_belong_to_us.txt`, then remove root `setup.sh`, empty legacy directories, and that zero-byte tracked marker directory. Do not remove the preserved pre-rewrite checkout.

- [ ] **Step 6: Verify final root and commit repository hygiene**

Run:

```bash
/bin/bash .maintenance/tests/manifest-contract.sh .
/bin/bash .maintenance/tests/default-packages.sh
/bin/bash .maintenance/tests/all-packages.sh
/bin/zsh -n shell/dot-zshenv shell/dot-zprofile shell/dot-zshrc
git diff --check
```

Expected: all pass; only ten non-hidden root package directories remain.

```bash
git add -A
git -c commit.gpgsign=false commit -m "refactor: isolate dotfiles payload packages"
```

---

### Task 5: Add Bilingual Dotfiles Documentation and Cross-Repository Smoke

**Files:**
- Modify: `README.md`
- Create: `README.en.md`
- Modify: `.maintenance/tests/all-packages.sh`

**Interfaces:**
- Both READMEs describe only the shell/Stow design, package table, prerequisites, selection examples, local config boundary, and manual backup recovery.
- Produces one clean dotfiles commit that the Kaisian release embeds.

- [ ] **Step 1: Add failing README parity and command checks**

Assert both files contain the same heading count/order, all ten package names, `.kaisian.json`, `.vendor` non-payload explanation, `dot-` example, and these commands:

```bash
curl -fsSL https://kaisian.phx.tw | bash
curl -fsSL https://kaisian.phx.tw | bash -s -- --profile default
curl -fsSL https://kaisian.phx.tw | bash -s -- --groups shell,git,mise
curl -fsSL https://kaisian.phx.tw | bash -s -- --interactive
curl -fsSL https://kaisian.phx.tw | bash -s -- --dry-run
```

- [ ] **Step 2: Write paired Traditional Chinese and English docs**

Traditional Chinese is `README.md`; English is `README.en.md`. State the macOS/Bash/Git/GNU Stow/fzf/plutil assumptions and present Homebrew only as the recommended installer for missing tools; Kaisian itself does not require Node.js. Explain that package-specific applications remain optional and guarded where shell startup references them. Document XDG backup path, move-only same-device behavior, no automatic rollback, and inspect-before-run.

- [ ] **Step 3: Run local full layout verification**

Run:

```bash
/bin/bash .maintenance/tests/manifest-contract.sh .
/bin/bash .maintenance/tests/default-packages.sh
/bin/bash .maintenance/tests/all-packages.sh
/bin/zsh -n shell/dot-zshenv shell/dot-zprofile shell/dot-zshrc
git diff --check
```

Expected: all pass.

- [ ] **Step 4: Commit documentation, then perform committed-source Kaisian smoke**

```bash
git add README.md README.en.md .maintenance/tests
git -c commit.gpgsign=false commit -m "docs: document Stow dotfiles layout"
DOTFILES_COMMIT=$(git rev-parse HEAD)
```

After pushing this feature commit to an explicitly named review branch, run in a disposable HOME with `~/Projects/kaisian/setup.sh --repo taiansu/dotfiles --ref "$DOTFILES_COMMIT" --repo-dir "$TMP_HOME/.dotfiles" --all --yes`, verify all expected links, rerun for idempotency, then run `--dry-run` and verify no target/state change. Do not embed/tag the commit until review passes.

---

### Task 6: Integrate the Reviewed Migration and Remove Generated Checkout Control State

**Files/state:**
- Integrate: `feature/kaisian-stow-wrapper` into rewritten `main` using the finishing-a-development-branch workflow
- Remove through Git worktree commands: `/Users/tai/Projects/dotfiles/.worktrees/kaisian-migration`
- Relocate generated `.superpowers/` session state outside the managed checkout
- Ensure future worktrees use an external root such as `~/Projects/.worktrees/dotfiles/`

**Interfaces:**
- Produces the clean `~/Projects/dotfiles` checkout consumed by the endpoint plan.
- Preserves all tracked `.maintenance/` docs/tests and removes only generated control/session/worktree state.

- [ ] **Step 1: Run the final branch review and choose integration**

Use `requesting-code-review`, then `finishing-a-development-branch`. Verify the feature branch contains only reviewed specification/plans and package migration commits, and the rewritten `main` lineage is its base. Present merge/PR choices; follow the user's selection.

- [ ] **Step 2: Preserve generated session records outside the checkout**

If `.superpowers/` contains reports needed for audit, move them to `~/.local/state/kaisian-migration/sdd/` and verify path/mode/size plus checksums without reopening credential material. Do not copy `.superpowers/` into `.maintenance/`; it is generated state.

- [ ] **Step 3: Remove the completed worktree through Git**

After integration and after no process uses the feature worktree, run from `~/Projects/dotfiles`:

```bash
git worktree remove .worktrees/kaisian-migration
git worktree prune
rmdir .worktrees
mkdir -p \"$HOME/Projects/.worktrees/dotfiles\"
```

`rmdir` must succeed only on an empty directory; never recursively remove `.worktrees`. Future feature worktrees go under the external directory.

- [ ] **Step 4: Verify the managed checkout is acceptable to Kaisian**

Run config-independent tracked/untracked/ignored scans equivalent to Kaisian. Expected: clean rewritten `main`, no in-progress operation, no `.worktrees` or `.superpowers` below checkout, exact remote origin, and recursively exact clean `.vendor` submodules. Run the public Kaisian `--dry-run --all` against this existing checkout and require no dirty/admin/state-boundary refusal.

---

### Task 7: Account for Preserved Pre-Rewrite Files and Request Cleanup Approval

**Files:**
- Inspect metadata only: `~/.local/state/kaisian-migration/old-checkout-path`
- Preserve/copy only user-approved ignored/untracked files into explicit external state locations
- Delete preserved checkout only after a new explicit approval

**Interfaces:**
- Produces an evidence list of remaining ignored/untracked paths and sizes without printing credential contents.
- This task is not required to publish the migrated repository; it is the separate local cleanup gate promised during history rewrite.

- [ ] **Step 1: Compare tracked and ignored/untracked inventories without contents**

Read the recorded old path, list only path/mode/size metadata, and classify each entry as migrated tracked payload, generated discardable state, externally preserved user state, or unresolved. Never open credential paths.

- [ ] **Step 2: Preserve approved user state and verify copies**

Copy each retained item to its explicit XDG state/config destination with restrictive modes; verify using `cmp` without stdout content. Do not place generated state back under dotfiles.

- [ ] **Step 3: Present exact cleanup evidence and stop for approval**

Report old checkout path, remaining unresolved path metadata, and verification commands. Ask explicitly whether to delete that directory. Do not infer approval from the earlier migration/spec approval.

- [ ] **Step 4: Delete only after approval and verify absence**

After explicit approval, remove exactly the recorded old checkout, remove the state pointer, and verify both are absent. Never use a glob or parent-directory recursive removal.
