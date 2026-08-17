# Dotfiles Stow Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove exposed credentials and migrate `taiansu/dotfiles` into a dependency-tolerant, root-group Stow-style repository consumed by Kaisian.

**Architecture:** Every non-hidden root directory becomes one installable group whose leaf paths map directly to `$HOME`. `.kaisian.toml` defines the default profile and bilingual metadata; repository maintenance material moves under hidden `.maintenance/` so it is never discovered as payload.

**Tech Stack:** Git, `git-filter-repo`, Gitleaks, Kaisian from `~/Projects/kaisian`, Zsh, shell smoke tests.

## Global Constraints

- Plan `2026-08-18-kaisian-cli.md` must be complete first; use `~/Projects/kaisian/target/debug/kaisian` until a release binary exists.
- The exposed GitHub token was revoked on 2026-08-18; never print or copy its value into a command, plan, log, fixture, commit, or replacement file.
- Credential removal and history verification happen before layout migration.
- Obtain explicit approval immediately before force-pushing rewritten branches or tags.
- Preserve the current worktree and all uncommitted/ignored user files before replacing it with a post-rewrite clone.
- Do not install Homebrew packages or language runtimes as part of the resulting setup flow; one-time security tooling is development-only.
- Source symlinks are prohibited because Kaisian first release rejects them.
- Generated state, logs, sessions, histories, backups, temporary files, and credentials are not payload.
- Default profile is exactly `shell`, `git`, and `mise`.
- Every migration task must pass a temporary-HOME Kaisian dry-run/apply check before commit.

---

### Task 1: Remove credential files and rewrite distributable history

**Files:**
- Create: `.maintenance/templates/git_credential.example`
- Modify: `.gitignore`
- Remove: `git/git_credential`
- Remove: `credential`
- Verify: every local branch/tag in an isolated mirror

**Interfaces:**
- Produces: a public history with neither credential-bearing path.
- Produces: a local untracked credential at `~/.config/dotfiles/credential` with mode `0600` when the existing `credential` file is non-empty.
- Produces: a sanitized identity template containing no token/password fields.

- [ ] **Step 1: Preserve local credential data without displaying it**

Run from the current dotfiles checkout:

```bash
mkdir -p "$HOME/.config/dotfiles" "$HOME/.local/state/kaisian-migration"
if test -s credential; then
  install -m 600 credential "$HOME/.config/dotfiles/credential"
  cmp -s credential "$HOME/.config/dotfiles/credential"
fi
git diff --binary -- setup.sh > "$HOME/.local/state/kaisian-migration/pre-rewrite-setup.patch"
```

Expected: `cmp` exits 0; no credential contents appear on stdout/stderr. The patch preserves the user's pre-existing `setup.sh` modification.

- [ ] **Step 2: Create sanitized replacement metadata**

Create `.maintenance/templates/git_credential.example` with only non-secret fields:

```gitconfig
[user]
  name = Tai An Su
  email = taiansu@gmail.com
  signingkey = ~/.ssh/id_ed25519.pub
[github]
  user = taiansu
[gpg]
  format = ssh
[gpg "ssh"]
  program = /Applications/1Password.app/Contents/MacOS/op-ssh-sign
[credential]
  helper = osxkeychain
```

Add anchored ignores:

```gitignore
/credential
/git/git_credential
```

Remove the tracked files with `git rm -- credential git/git_credential`.

- [ ] **Step 3: Verify the current tree no longer contains credential paths**

Run:

```bash
test ! -e credential
test ! -e git/git_credential
git diff --check
git diff --cached --name-status
```

Expected: both `test` commands exit 0; staged output lists deletion of both files and creation of only the sanitized template plus ignore update.

- [ ] **Step 4: Commit current-tree containment**

```bash
git add .gitignore .maintenance/templates/git_credential.example
git commit -m "security: remove tracked credentials"
```

- [ ] **Step 5: Prepare isolated history-rewrite tooling and mirror**

Verify tools:

```bash
command -v git-filter-repo
command -v gitleaks
```

If either is absent, install only the missing development tool with Homebrew before continuing:

```bash
brew install git-filter-repo gitleaks
```

Create the mirror from the just-pushed/accessible origin after pushing the containment commit normally:

```bash
git push origin main
SECURITY_ROOT="$(mktemp -d)"
git clone --mirror git@github.com:taiansu/dotfiles.git "$SECURITY_ROOT/dotfiles.git"
git -C "$SECURITY_ROOT/dotfiles.git" filter-repo \
  --path credential \
  --path git/git_credential \
  --invert-paths \
  --force
git -C "$SECURITY_ROOT/dotfiles.git" remote add origin git@github.com:taiansu/dotfiles.git
```

Expected: filter-repo reports rewritten refs; it must not print file contents.

- [ ] **Step 6: Verify rewritten paths and secrets locally**

Run:

```bash
test -z "$(git -C "$SECURITY_ROOT/dotfiles.git" log --all --format=%H -- credential git/git_credential)"
gitleaks git "$SECURITY_ROOT/dotfiles.git" --redact --no-banner
```

Expected: the path-history command emits nothing; Gitleaks exits 0 and never prints a secret value because `--redact` is mandatory. Investigate every nonzero Gitleaks result before proceeding; do not suppress rules globally.

- [ ] **Step 7: Stop for destructive remote approval**

Present the rewritten branch/tag list and verification output to the user. Explicitly state that one public fork and prior clones retain old objects, and that revocation—not rewriting—is containment. Do not run any force push until the user approves this exact rewrite.

- [ ] **Step 8: Force-update branches/tags only after approval**

Run:

```bash
git -C "$SECURITY_ROOT/dotfiles.git" push --force origin 'refs/heads/*:refs/heads/*'
git -C "$SECURITY_ROOT/dotfiles.git" push --force origin 'refs/tags/*:refs/tags/*'
```

Do not use `push --mirror`; it can modify unrelated remote refs.

- [ ] **Step 9: Preserve the old checkout and clone rewritten history**

Run from `~/Projects`:

```bash
OLD_CHECKOUT="$HOME/Projects/dotfiles.pre-credential-rewrite.$(date +%Y%m%d%H%M%S)"
mv dotfiles "$OLD_CHECKOUT"
printf '%s\n' "$OLD_CHECKOUT" > "$HOME/.local/state/kaisian-migration/old-checkout-path"
git clone --recurse-submodules git@github.com:taiansu/dotfiles.git dotfiles
cd dotfiles
git log --all -- credential git/git_credential
```

Expected: fresh clone succeeds; final command emits no commits. Keep the preserved checkout until the entire migration is complete and all ignored/user files are accounted for.

---

### Task 2: Define and test the root-group manifest contract

**Files:**
- Create: `.maintenance/fixtures/core-manifest.toml`
- Create: `.maintenance/fixtures/final-manifest.toml`
- Create: `.maintenance/tests/manifest-contract.sh`

**Interfaces:**
- Core fixture produces groups `shell`, `git`, and `mise` with `default = ["shell", "git", "mise"]`.
- Final fixture adds `terminal`, `editors`, `agents`, `cli`, `macos`, `homebrew`, and `dev`.
- The live root `.kaisian.toml` is installed only in Task 5, after legacy non-group directories are gone.

- [ ] **Step 1: Write a failing fixture contract test**

The shell test creates temporary repositories from each manifest fixture, creates one regular payload file per declared group, runs Kaisian dry-run, and then proves an intentionally missing and an intentionally extra group both fail. Use temporary HOME/XDG variables and the exact binary `~/Projects/kaisian/target/debug/kaisian`.

- [ ] **Step 2: Run the test before adding the manifest**

Run: `bash .maintenance/tests/manifest-contract.sh`

Expected: FAIL because the manifest fixtures do not exist.

- [ ] **Step 3: Add schema 1 manifest fixtures**

Both fixtures define `minimum_kaisian_version = "0.1.0"`. The core fixture defines the default profile and three groups; the final fixture has the same default profile and all ten groups. Each group gets `en` and `zh-TW` descriptions. Recommendations:

- `shell`: `mise`, `fzf`, `omp`;
- `git`: `git`, `nvim`, `diff-so-fancy`;
- `mise`: `mise`;
- app-specific groups list only commands their startup path actually invokes.

Do not declare recommendations as requirements.

- [ ] **Step 4: Run manifest fixture contract tests**

Run: `bash .maintenance/tests/manifest-contract.sh`

Expected: PASS for both valid fixtures and expected failure assertions for missing/extra groups.

- [ ] **Step 5: Commit the contract test and fixtures**

```bash
git add .maintenance/fixtures .maintenance/tests/manifest-contract.sh
git commit -m "test: define dotfiles group contract"
```

---

### Task 3: Migrate and harden the default shell, Git, and mise groups

**Files:**
- Move: `zsh/zshrc` → `shell/.zshrc`
- Move: `zsh/zprofile` → `shell/.zprofile`
- Move: `zsh/zshenv` → `shell/.zshenv`
- Move: `zsh/aliasrc` → `shell/.config/zsh/aliasrc`
- Move: `scripts/fzf_listoldfiles.sh`, `scripts/zoxide_openfiles_nvim.sh`, `scripts/vimr_wait.sh` → `shell/.local/libexec/dotfiles/`
- Move submodule: `git-prompt.zsh` → `shell/.local/share/zsh/git-prompt.zsh`
- Move submodule: `fzf-git` → `shell/.local/share/zsh/fzf-git`
- Remove duplicate: `scripts/fzf-git.sh`
- Modify: `.gitmodules`
- Move: `git/gitconfig` → `git/.gitconfig`
- Move: `git/gitignore` → `git/.gitignore`
- Move: `config/mise/config.toml` → `mise/.config/mise/config.toml`
- Move: `mise/asdfrc` → `mise/.asdfrc`
- Move: `mise/default-npm-packages` → `mise/.default-npm-packages`
- Move: `mise/default-gems` → `mise/.default-gems`
- Move: `mise/default-mix-commands` → `mise/.default-mix-commands`
- Create: `.maintenance/tests/default-profile.sh`
- Consume: `.maintenance/fixtures/core-manifest.toml`

**Interfaces:**
- The applied shell reads support files only through `$HOME/.config`, `$HOME/.local/share`, and `$HOME/.local/libexec`.
- The shell starts successfully when fzf, omp, and Node.js are absent.

- [ ] **Step 1: Write the default-profile smoke test**

The test must:

1. create a temporary repository containing the core manifest renamed to `.kaisian.toml` plus only the migrated `shell`, `git`, and `mise` directories;
2. create temporary HOME/XDG directories;
3. run Kaisian `apply <temporary-repo> --profile=default --yes`;
4. assert all expected links and link destinations;
5. run it again and assert every target remains the same link;
6. create a restricted PATH containing symlinks only for `zsh`, `git`, `brew`, and `mise` plus required macOS base commands;
7. launch `/bin/zsh -dfc 'source \"$HOME/.zshenv\"; source \"$HOME/.zprofile\"; source \"$HOME/.zshrc\"'`;
8. fail on `command not found` output for fzf or omp.

- [ ] **Step 2: Run the smoke test before migration**

Run: `bash .maintenance/tests/default-profile.sh`

Expected: FAIL because default group paths do not exist.

- [ ] **Step 3: Move files and submodules**

Use `git mv` for tracked files. Update `.gitmodules` paths before `git submodule sync --recursive`, then run `git submodule update --init --recursive`. Remove the vendored `scripts/fzf-git.sh` only after confirming the moved submodule contains `fzf-git.sh`.

- [ ] **Step 4: Harden Zsh startup paths**

Required behavior changes:

```zsh
source "${XDG_CONFIG_HOME:-$HOME/.config}/zsh/aliasrc"
[[ -f "${XDG_CONFIG_HOME:-$HOME/.config}/zsh/hashrc" ]] && source "${XDG_CONFIG_HOME:-$HOME/.config}/zsh/hashrc"

if command -v fzf >/dev/null 2>&1 && [[ -t 1 ]]; then
  source <(fzf --zsh)
fi

if command -v mise >/dev/null 2>&1; then
  eval "$(mise activate zsh)"
fi

_git_prompt="${XDG_DATA_HOME:-$HOME/.local/share}/zsh/git-prompt.zsh/git-prompt.zsh"
[[ -f "$_git_prompt" ]] && source "$_git_prompt"
unset _git_prompt

_fzf_git="${XDG_DATA_HOME:-$HOME/.local/share}/zsh/fzf-git/fzf-git.sh"
if command -v fzf >/dev/null 2>&1 && [[ -f "$_fzf_git" ]]; then
  source "$_fzf_git"
fi
unset _fzf_git
```

Guard OMP completion generation with `command -v omp`; source the cache only when it exists. In `.zshenv`, replace `~/.dotfiles/credential` with `~/.config/dotfiles/credential` and retain the file-exists guard.

- [ ] **Step 5: Verify actual default apply and Zsh startup**

Run:

```bash
/bin/zsh -n shell/.zshenv shell/.zprofile shell/.zshrc
bash .maintenance/tests/default-profile.sh
```

Expected: syntax and behavioral smoke tests PASS twice.

- [ ] **Step 6: Commit the default profile**

```bash
git add .gitmodules shell git mise .maintenance/fixtures/core-manifest.toml .maintenance/tests/default-profile.sh
git commit -m "feat: migrate default dotfiles profile"
```

---

### Task 4: Migrate stable application groups

**Files:**
- Move stable configs under `terminal/`, `editors/`, `agents/`, `cli/`, `macos/`, `homebrew/`, and `dev/`
- Create: `.maintenance/tests/all-groups.sh`
- Consume: `.maintenance/fixtures/final-manifest.toml`

**Interfaces:**
- Every moved leaf maps to the same current `$HOME` location previously implied by its config directory or dotfile name.
- No runtime state or backup file is moved.

- [ ] **Step 1: Write a failing all-groups mapping test**

Create an expected target list containing at least:

```text
.config/ghostty/config
.config/kitty/kitty.conf
.config/cmux/cmux.json
.config/zed/settings.json
.config/zed/keymap.json
.config/karabiner/karabiner.json
.config/paneru/paneru.toml
.config/btop/btop.conf
.config/mactop/config.json
.config/superfile/config.toml
.config/tidewave/app.toml
.config/lazygit/config.yml
.config/cabal/config
.omp/agent/config.yml
.pi/agent/settings.json
.Brewfile
.ctags
.gemrc
.gnuplot
.agignore
.iex.exs
.credo.exs
```

The test applies `--all` to a temporary HOME and asserts every expected path is a symlink into the correct root group.

- [ ] **Step 2: Run the test before migration**

Run: `bash .maintenance/tests/all-groups.sh`

Expected: FAIL because optional groups are absent.

- [ ] **Step 3: Move stable terminal/editor/macOS configs**

Mappings:

- `config/ghostty` → `terminal/.config/ghostty`;
- stable `config/kitty` files except backups → `terminal/.config/kitty`;
- `config/cmux` → `terminal/.config/cmux`;
- `config/zed/settings.json`, `keymap.json`, and `themes/` → `editors/.config/zed/`;
- `config/karabiner/karabiner.json` and stable `assets/` → `macos/.config/karabiner/`;
- `config/paneru` → `macos/.config/paneru`.

Do not move `settings_backup.json`, `.tmp*`, `automatic_backups/`, or `*.bak`.

- [ ] **Step 4: Move stable agent/CLI configs**

Mappings:

- `omp/agent/config.yml` and `no-superpowers.yml` → `agents/.omp/agent/`;
- `pi/agent/settings.json`, `pi/npm/`, and `pi/extensions/` → `agents/.pi/` preserving relative paths;
- root `AGENTS.md` → `agents/.omp/agent/AGENTS.md`;
- `claude_codex_instructions.md` → `agents/.claude/CLAUDE.md`;
- stable Peon Ping config → `agents/.config/peon-ping/`;
- `config/btop`, `mactop`, `superfile`, `tidewave`, `lazygit`, and `cabal` → matching `cli/.config/<app>` paths;
- stable Herdr `config.toml` and plugin config, excluding logs/sessions/release notes → `cli/.config/herdr/`.

Do not move `*.lock`, logs, session JSON, or release-note cache.

- [ ] **Step 5: Move Homebrew and development dotfiles**

Mappings:

- `homebrew/Brewfile` → `homebrew/.Brewfile`;
- `ctags` → `dev/.ctags`;
- `gemrc` → `dev/.gemrc`;
- `gnuplot` → `dev/.gnuplot`;
- `agignore` → `dev/.agignore`;
- `iex.exs` → `dev/.iex.exs`;
- `credo.exs` → `dev/.credo.exs`;
- executable helper `rust` → `dev/.local/bin/rust` with its executable bit preserved.

- [ ] **Step 6: Verify all groups and target collisions**

`all-groups.sh` must assemble a temporary repository from the final manifest fixture and the ten migrated group directories, excluding remaining legacy root directories.

Run: `bash .maintenance/tests/all-groups.sh`

Expected: PASS; its internal dry-run reports no unknown group, source symlink, or duplicate target.

- [ ] **Step 7: Commit application groups**

```bash
git add terminal editors agents cli macos homebrew dev .maintenance/fixtures/final-manifest.toml .maintenance/tests/all-groups.sh
git commit -m "feat: migrate optional dotfiles groups"
```

---

### Task 5: Quarantine maintenance material and remove generated state

**Files:**
- Move: `docs/` → `.maintenance/docs/`
- Move: `patches/` → `.maintenance/patches/`
- Move: `tests/` → `.maintenance/tests/peon-ping/`
- Move: `templates/` → `.maintenance/templates/`
- Create: `.kaisian.toml` from `.maintenance/fixtures/final-manifest.toml`
- Remove: `.maintenance/fixtures/core-manifest.toml`
- Remove: `.maintenance/fixtures/final-manifest.toml`
- Modify: `justfile`
- Modify: `.gitignore`
- Remove tracked generated files and obsolete directories
- Remove: `setup.sh`

**Interfaces:**
- After this task, every non-hidden root directory is one of the ten manifest groups.
- Existing maintenance recipes reference `.maintenance` paths.

- [ ] **Step 1: Write a root-layout invariant test**

Add to `.maintenance/tests/manifest-contract.sh` an assertion that sorted non-hidden root directories exactly equal:

```text
agents cli dev editors git homebrew macos mise shell terminal
```

- [ ] **Step 2: Move maintenance trees and update recipes**

Use `git mv` for docs, patches, tests, and templates. Update `justfile` references, especially the Peon Ping patch path, to `.maintenance/patches/peon-ping/omp-notification-lifecycle.patch`. Keep `justfile` as a root file because root files are metadata, not groups.
Install the live manifest and remove migration-only fixtures:

```bash
cp .maintenance/fixtures/final-manifest.toml .kaisian.toml
git rm .maintenance/fixtures/core-manifest.toml .maintenance/fixtures/final-manifest.toml
```

The root contract becomes live only after all non-hidden legacy directories are moved or removed in this task.

- [ ] **Step 3: Remove generated tracked state**

Remove tracked generated files including Herdr release notes, Zed settings backup, OMP lock, and any tracked log/session/temp/backup discovered by:

```bash
git ls-files | sed -nE '/(^|\/)(logs?|sessions?|history|automatic_backups)(\/|$)|(^|\/).*\.(bak|log)$|(^|\/)\.tmp/p'
```

Before each deletion, confirm the path is generated state rather than stable configuration. Add precise ignore patterns for the confirmed generated paths; do not add a broad `*.json` or entire app-directory ignore.

- [ ] **Step 4: Remove obsolete setup and empty legacy directories**

Remove `setup.sh` only now that Kaisian default/all apply tests pass. Remove empty `config/`, `zsh/`, `scripts/`, `omp/`, `pi/`, and old `mise/` directories. Remove the obsolete tracked backup marker directory if it contains no user data.

- [ ] **Step 5: Verify root and manifest invariants**

Run:

```bash
bash .maintenance/tests/manifest-contract.sh
bash .maintenance/tests/default-profile.sh
bash .maintenance/tests/all-groups.sh
git diff --check
```

Expected: all tests PASS; only ten non-hidden root directories remain.

- [ ] **Step 6: Commit repository hygiene**

```bash
git add -A
git commit -m "refactor: isolate dotfiles payload groups"
```

---

### Task 6: Add bilingual dotfiles documentation and final smoke test

**Files:**
- Modify: `README.md`
- Create: `README.en.md`
- Modify: `.maintenance/tests/default-profile.sh`
- Modify: `.maintenance/tests/all-groups.sh`

**Interfaces:**
- Both READMEs document the exact manifest groups and commands delivered above.

- [ ] **Step 1: Rewrite both entry documents**

Traditional Chinese is primary in `README.md`; English is primary in `README.en.md`. Link the alternate language at the top. Include prerequisites, default group, group table, generic/local Kaisian commands, interactive selection, all groups, dry-run, backup location, credential policy, and the fact that Homebrew/mise/Node packages are not installed.

- [ ] **Step 2: Verify every documented command against actual help**

Run:

```bash
"$HOME/Projects/kaisian/target/debug/kaisian" --help
"$HOME/Projects/kaisian/target/debug/kaisian" apply --help
```

Expected: every documented option appears exactly.

- [ ] **Step 3: Run final temporary-HOME behavior**

Run:

```bash
bash .maintenance/tests/manifest-contract.sh
bash .maintenance/tests/default-profile.sh
bash .maintenance/tests/all-groups.sh
/bin/zsh -n shell/.zshenv shell/.zprofile shell/.zshrc
```

Expected: all commands exit 0. Confirm the real HOME and current shell files were not modified by checking that every test logged its temporary HOME.

- [ ] **Step 4: Commit migration documentation**

```bash
git add README.md README.en.md .maintenance/tests
git commit -m "docs: document kaisian dotfiles groups"
```

- [ ] **Step 5: Retire the preserved pre-rewrite checkout**

Read the recorded path and audit user-only files without displaying credential contents:

```bash
OLD_CHECKOUT="$(cat \"$HOME/.local/state/kaisian-migration/old-checkout-path\")"
git -C "$OLD_CHECKOUT" status --short --ignored
```

Copy any still-needed ignored/untracked files to their explicit new destinations and verify them with `cmp`. Present the remaining path and size to the user, then obtain explicit approval before running `rm -rf -- "$OLD_CHECKOUT"`. Remove `old-checkout-path` only after the directory is gone. This cleanup matters because the preserved checkout still contains the revoked credential files.
