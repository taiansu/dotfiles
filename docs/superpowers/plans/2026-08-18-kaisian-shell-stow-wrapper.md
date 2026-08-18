# Kaisian Shell + GNU Stow Wrapper Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create `taiansu/kaisian` as a macOS Bash 3.2 wrapper that safely acquires a pinned dotfiles repository, selects manifest packages, backs up exact conflicts, and delegates links to GNU Stow.

**Architecture:** One released `setup.sh` owns CLI, locale, manifest validation, source acquisition, preflight, backup, and Stow orchestration. One isolated shell suite invokes the public CLI with fake Git/fzf boundaries and real GNU Stow behavioral fixtures. Git and Stow run only through sanitized runners; package mapping is validation/preflight data, never a second link engine.

**Tech Stack:** macOS 13+, `/bin/bash` 3.2, Git, GNU Stow, fzf, `/usr/bin/plutil`, POSIX/macOS base utilities, GitHub Actions.

## Global Constraints

- Repository does not exist yet; create it at `~/Projects/kaisian` with public target `taiansu/kaisian`.
- Runtime dependencies are exactly Bash, Git, GNU Stow, fzf, plutil, and standard macOS utilities; never add Node.js, Python, Rust, jq, yq, gettext, Homebrew installation, or a package manager.
- `setup.sh` is both the executable release asset and the script served at `https://kaisian.phx.tw`.
- Keep macOS Bash 3.2 compatibility: indexed arrays only; no associative arrays, `mapfile`, `readarray`, `${var,,}`, `globstar`, or Bash 4 syntax.
- All user-visible messages have English and Traditional Chinese (Taiwan) variants in the same script.
- Every task that introduces a user-visible failure adds the same message key to both language tables and a parity test that enumerates all keys.
- Default source is `taiansu/dotfiles`, default checkout is the captured physical `$HOME/.dotfiles`, and default ref is an exact 40-hex commit embedded before release.
- Public HTTPS repositories only. Reject SSH/scp, local/file/ext, authenticated URLs, raw Unicode URL text, explicit ports, query/fragment, percent encoding, traversal, and option/refspec-like input.
- No WAL, rollback, recover command, automatic restore, destructive Git cleanup, Stow `--adopt`, or Stow `--override`.
- Source symlinks, hidden payload components, non-ASCII payload components, package gitlinks/nested repositories, untracked/ignored payload, and structurally colliding targets are invalid.
- Every Stow operation uses absolute `--dir`/`--target` plus `--dotfiles --no-folding --compat` through the sanitized runner.
- Follow test-first order. Each task ends with its named focused suite and commit; do not run project-wide gates between tasks.

## File Map

- `~/Projects/kaisian/setup.sh` — complete released runtime and public CLI.
- `~/Projects/kaisian/tests/setup_test.sh` — isolated behavioral harness; fake Git/fzf inputs and real Stow fixtures.
- `~/Projects/kaisian/tests/fixtures/` — tracked repository/manifest/package fixture sources only.
- `~/Projects/kaisian/.github/workflows/ci.yml` — Bash syntax and shell behavior gate on macOS.
- `~/Projects/kaisian/.github/workflows/release.yml` — immutable tagged `setup.sh` and SHA-256 publication.
- `~/Projects/kaisian/README.md` — Traditional Chinese primary documentation.
- `~/Projects/kaisian/README.en.md` — structural English counterpart.
- `~/Projects/kaisian/LICENSE` — MIT license, Copyright (c) 2026 Tai An Su.
- `~/Projects/kaisian/.gitignore` — test scratch and rendered release artifacts only.

---

### Task 1: Create the Repository, Public CLI Skeleton, and Test Harness

**Files:**
- Create: `~/Projects/kaisian/setup.sh`
- Create: `~/Projects/kaisian/tests/setup_test.sh`
- Create: `~/Projects/kaisian/LICENSE`
- Create: `~/Projects/kaisian/.gitignore`

**Interfaces:**
- Produces executable `setup.sh [OPTIONS]` with `main "$@"` guarded by `KAISIAN_TESTING`.
- Produces test helpers `run_case NAME COMMAND...`, `assert_status`, `assert_contains`, `assert_not_exists`, and `make_home`.
- Later tasks append behavior to the same CLI and suite; they do not add a second executable.

- [ ] **Step 1: Write the failing help/syntax harness**

Create and enter the absent repository before writing the test:

```bash
mkdir -p \"$HOME/Projects/kaisian/tests\"
cd \"$HOME/Projects/kaisian\"
git init -b main
```

Create `tests/setup_test.sh` with strict mode, a temporary root, cleanup trap, counters, and these first cases:

```bash
#!/bin/bash
set -u

ROOT=$(mktemp -d "${TMPDIR:-/tmp}/kaisian-test.XXXXXX") || exit 1
trap 'rm -rf -- "$ROOT"' EXIT HUP INT TERM
SCRIPT=$(cd "$(dirname "$0")/.." && pwd -P)/setup.sh
PASS=0
FAIL=0

run_case() {
  name=$1
  shift
  if "$@"; then
    PASS=$((PASS + 1))
    printf 'ok - %s\n' "$name"
  else
    FAIL=$((FAIL + 1))
    printf 'not ok - %s\n' "$name" >&2
  fi
}

help_case() {
  output=$(/bin/bash "$SCRIPT" --help 2>&1) || return 1
  printf '%s\n' "$output" | /usr/bin/grep -F 'setup.sh [OPTIONS]' >/dev/null || return 1
  printf '%s\n' "$output" | /usr/bin/grep -F -- '--interactive' >/dev/null
}

run_case 'help works' help_case
printf '%s passed; %s failed\n' "$PASS" "$FAIL"
test "$FAIL" -eq 0
```

- [ ] **Step 2: Run the test to verify the missing executable fails**

Run: `cd ~/Projects/kaisian && /bin/bash tests/setup_test.sh`

Expected: nonzero; `help works` is reported `not ok` because `setup.sh` does not exist.

- [ ] **Step 3: Implement the minimal sourceable Bash 3.2 CLI**

Create `setup.sh` with this stable top-level shape:

```bash
#!/bin/bash
set -u

readonly KAISIAN_VERSION='0.1.0'
readonly DEFAULT_REPOSITORY='taiansu/dotfiles'
readonly DEFAULT_DOTFILES_COMMIT='0b3b0c3f206e1f4fb35dac82794a871c5c18f405'

usage() {
  cat <<'USAGE'
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
USAGE
}

main() {
  case ${1-} in
    -h|--help) usage; return 0 ;;
  esac
  printf '%s\n' 'Kaisian is not configured yet.' >&2
  return 1
}

if test "${KAISIAN_TESTING-0}" != 1; then
  main "$@"
fi
```

Create the MIT `LICENSE`, ignore only `/tests/tmp/` and `/dist/`, initialize Git with branch `main`, and set executable mode on both shell files.

- [ ] **Step 4: Verify syntax, help, and Bash 3.2 forbidden-token guard**

Run:

```bash
cd ~/Projects/kaisian
/bin/bash -n setup.sh tests/setup_test.sh
/bin/bash tests/setup_test.sh
! /usr/bin/grep -En 'declare -A|mapfile|readarray|\$\{[^}]+,,|\*\*' setup.sh
```

Expected: syntax exits 0; `1 passed; 0 failed`; forbidden-token grep emits nothing.

- [ ] **Step 5: Commit the repository skeleton**

```bash
cd ~/Projects/kaisian
git add setup.sh tests/setup_test.sh LICENSE .gitignore
git -c commit.gpgsign=false commit -m "feat: create kaisian shell CLI"
```

---

### Task 2: Implement Locale, CLI Validation, Prerequisites, Lock, and Sanitized Runners

**Files:**
- Modify: `~/Projects/kaisian/setup.sh`
- Modify: `~/Projects/kaisian/tests/setup_test.sh`

**Interfaces:**
- Produces globals: `LANGUAGE`, `PHYSICAL_HOME`, `CHECKOUT_DIR`, `STATE_ROOT`, `LOCK_DIR`, `SANDBOX`, `DRY_RUN`, `ASSUME_YES`, `SELECTION_MODE`, `SELECTION_VALUE`, `REPOSITORY`, `REQUESTED_REF`.
- Produces functions: `resolve_language`, `message`, `die`, `parse_args`, `validate_home`, `require_prerequisites`, `acquire_lock`, `cleanup`, `run_git`, `run_stow`.
- `run_git` and `run_stow` are the only permitted process boundaries for those tools in later tasks.

- [ ] **Step 1: Add failing table-driven CLI/locale/lock tests**

Extend `tests/setup_test.sh` with cases that invoke the script under temporary HOME/PATH and assert:

```text
--help succeeds when git/stow/fzf are absent
--profile/--groups/--interactive/--all reject every pair
unknown arguments and missing values fail
--lang accepts only en and zh-TW
LC_ALL > LC_MESSAGES > LANG > English fallback
zh, zh_TW.UTF-8, and zh-Hant select zh-TW text
normal execution reports every missing prerequisite without installing it
relative, missing, symlinked, unowned, or unwritable HOME fails
existing /private/tmp/kaisian-$UID.lock fails and is never removed
runs with different TMPDIR values contend on the same fixed lock
repo-dir/state paths equal to, above, or below the lock fail; sibling paths pass
cleanup leaves an unrecognized lock entry untouched
```

Implement test fakes as executable files under `$ROOT/bin`; fake `uname` prints `Darwin` and fake missing tools are omitted rather than installed.

- [ ] **Step 2: Run focused tests and confirm the first unsupported option fails**

Run: `cd ~/Projects/kaisian && /bin/bash tests/setup_test.sh`

Expected: nonzero with the first new case failing because `parse_args` and localized messages are absent.

- [ ] **Step 3: Implement deterministic parsing and bilingual messages**

Add two message functions selected by stable keys rather than translated control flow:

```bash
message_en() {
  case $1 in
    error_prefix) printf 'Error' ;;
    missing_tools) printf 'Missing required commands: %s' "$2" ;;
    no_tty) printf 'A controlling terminal is required.' ;;
    *) return 64 ;;
  esac
}

message_zh_tw() {
  case $1 in
    error_prefix) printf '錯誤' ;;
    missing_tools) printf '缺少必要指令：%s' "$2" ;;
    no_tty) printf '此操作需要可控制的終端機。' ;;
    *) return 64 ;;
  esac
}
```

`resolve_language` consumes explicit `--lang` first, then `LC_ALL`, `LC_MESSAGES`, `LANG`; values beginning `zh` select `zh-TW`, all others select `en`. `parse_args` uses a `while test "$#" -gt 0; do case $1 in ...` loop, counts selection options, accepts both `--name value` and `--name=value`, and resolves all argument-shape failures before prerequisite probes.

- [ ] **Step 4: Implement HOME/lock validation and cleanup invariants**

Capture HOME once with `cd -P -- "$HOME" && pwd -P`; require the original absolute string to equal the result, owner UID from `/usr/bin/stat -f '%u'`, and `-r -w -x`. Validate root-owned sticky `/private/tmp`, then acquire exactly `/private/tmp/kaisian-$(/usr/bin/id -u).lock` using `umask 077; mkdir`. Record lock and sandbox physical identities. Cleanup removes only known sandbox children, then PID record, then the empty lock; it refuses recursive cleanup after identity/containment mismatch.

- [ ] **Step 5: Implement sanitized Git and Stow runners and probes**

`run_git` invokes `env -i` with only controlled `PATH`, `HOME=$SANDBOX/git-home`, `LC_ALL=C`, `GIT_CONFIG_NOSYSTEM=1`, `GIT_CONFIG_GLOBAL=/dev/null`, `GIT_ATTR_NOSYSTEM=1`, `GIT_TERMINAL_PROMPT=0`, `GIT_ASKPASS=/usr/bin/false`, and `GIT_NO_REPLACE_OBJECTS=1`. Explicitly omit inherited `GIT_*` object/config variables.

`run_stow` changes to `$SANDBOX/stow-cwd`, sets process `HOME=$SANDBOX/stow-home`, creates an empty `$SANDBOX/stow-home/.stow-global-ignore`, and uses `env -i PATH=... LC_ALL=C HOME=...`; inherited `STOW_DIR` and every `PERL*` variable disappear. `require_prerequisites` probes the exact Stow behaviors in disposable sandbox source/target trees: `--dotfiles`, `--no-folding`, `--compat`, mixed `-R/-D`, `--simulate`, built-in-ignore disabling, and anchored compatibility subtree exclusion.

- [ ] **Step 6: Run the focused suite and syntax gate**

Run:

```bash
cd ~/Projects/kaisian
/bin/bash -n setup.sh tests/setup_test.sh
/bin/bash tests/setup_test.sh
```

Expected: all Task 1–2 cases pass; no path outside temporary HOME or the fixed lock changes.

- [ ] **Step 7: Commit the runtime boundary**

```bash
git add setup.sh tests/setup_test.sh
git -c commit.gpgsign=false commit -m "feat: validate kaisian runtime boundary"
```

---

### Task 3: Parse JSON Manifests and Resolve Default, Profile, Groups, and fzf Selection

**Files:**
- Modify: `~/Projects/kaisian/setup.sh`
- Modify: `~/Projects/kaisian/tests/setup_test.sh`
- Create: `~/Projects/kaisian/tests/fixtures/manifest-valid.json`

**Interfaces:**
- Produces files inside sandbox: `groups.tsv`, `profiles.tsv`, `selected.txt`, `unselected.txt`.
- Produces functions: `parse_manifest MANIFEST`, `resolve_selection`, `select_interactively`.
- `selected.txt` and `unselected.txt` contain one validated package name per line in manifest order; no downstream task reparses JSON.

- [ ] **Step 1: Add failing manifest and selection fixtures**

Create a valid fixture with groups `shell`, `git`, `mise`, `terminal`; profiles `minimal=[shell,git]`, `default=[shell,git,mise]`. Add generated invalid fixtures for malformed JSON, wrong schema/type, unknown keys, duplicate group/profile entries, empty descriptions, tab/newline/control descriptions, invalid names, missing/extra package directories, and documented plutil last-duplicate-key behavior.

Selection assertions:

```text
no flag and --all => shell git mise terminal
--profile minimal => shell git
--groups 'terminal, shell,terminal' => shell terminal in manifest order
unknown/empty group => nonzero
fzf output 'git\nterminal' => git terminal
fzf Esc/Ctrl-C => zero cancellation before target mutation
fzf confirmed empty or unexpected failure => nonzero
non-TTY interactive => localized nonzero
```

- [ ] **Step 2: Run and observe manifest parsing failure**

Run: `cd ~/Projects/kaisian && /bin/bash tests/setup_test.sh`

Expected: nonzero because `.kaisian.json` extraction is not implemented.

- [ ] **Step 3: Implement strict plutil-only parsing**

Validate syntax with:

```bash
/usr/bin/plutil -convert json -o /dev/null -- "$manifest"
```

Use `/usr/bin/plutil -extract KEY raw -- "$manifest"` for scalar/array sizes and indexed values. Reject unknown top/group keys by converting once to XML inside the sandbox and enumerating dictionary keys through plutil-supported extraction, never `eval`, sed, grep, jq, or a language runtime as a JSON parser. Emit validated tab-separated group records:

```text
<name>\t<english description>\t<traditional chinese description>
```

Descriptions are nonempty single-line strings without tab/control bytes. Validate every non-hidden root directory equals one declared group and vice versa.

- [ ] **Step 4: Implement stable selection and fzf cancellation semantics**

Resolve default/all/profile/groups from manifest order. For interactive mode, send localized `name<TAB>description` records to `fzf --multi --with-nth=1,2` while its terminal is `/dev/tty`. Interpret fzf 130 as successful cancellation, confirmed empty as error, and all other nonzero values as error. Do not read options or candidate data through `eval`.

- [ ] **Step 5: Verify selection behavior**

Run: `cd ~/Projects/kaisian && /bin/bash tests/setup_test.sh`

Expected: all manifest, duplicate-key-policy, ordering, fzf, locale, cancellation, and non-TTY cases pass.

- [ ] **Step 6: Commit manifest selection**

```bash
git add setup.sh tests/setup_test.sh tests/fixtures/manifest-valid.json
git -c commit.gpgsign=false commit -m "feat: select stow packages from JSON manifest"
```

---

### Task 4: Acquire and Verify Pinned Git Sources and Non-Payload Submodules

**Files:**
- Modify: `~/Projects/kaisian/setup.sh`
- Modify: `~/Projects/kaisian/tests/setup_test.sh`
- Create: `~/Projects/kaisian/tests/fixtures/fake-git`

**Interfaces:**
- Produces `canonicalize_repository INPUT`, `resolve_remote_ref`, `validate_git_config`, `validate_git_admin`, `verify_clean_tree`, `initialize_repository`, `update_repository`, `initialize_submodules`.
- Produces a detached, recursively verified checkout at `CHECKOUT_DIR`; later tasks consume only that path and commit ID.
- Fake Git delegates safe local inspection to the real Git path but simulates public HTTPS `ls-remote`/fetch into `FETCH_HEAD` and logs every argument/environment boundary.

- [ ] **Step 1: Add failing source/ref/config/admin fixtures**

Cover the exact design matrix:

```text
owner/repo and canonical public HTTPS normalize identically
userinfo, private/auth, SSH/scp/file/ext/local, raw Unicode, explicit port, %, query, fragment, //, . or .., leading option/refspec reject
custom repo without --ref rejects
full branch, full tag, unambiguous shorthand, remote HEAD, exact 40-hex SHA resolve only from advertised origin
branch/tag shorthand ambiguity rejects
same-named malicious local branch/tag never wins over FETCH_HEAD
new checkout uses git init + one requested fetch and creates no local branch/remote-tracking ref
existing origin mismatch, dirty/untracked/ignored tree, operation markers, wrong submodule commit reject
local includes, insteadOf, filters, hooks, fsmonitor, unsafe protocols, custom update/refspec, and every unlisted config reject
all accepted core key/value pairs pass; core.worktree, symlinks=false, and unknown core fail
replace refs, grafts, info/system attributes, alternates, object/admin symlinks, linked worktree, separate gitdir, bare repo reject
assume-unchanged, skip-worktree, sparse index/checkout, and attribute-hidden worktree changes fail through fresh-index verification
relative/SSH/file/ext/command/overlapping/duplicate submodule definitions reject before initialization
validated submodules initialize one level at a time into embedded child .git and exact gitlink commits
submodule roots inside selectable packages reject
```

- [ ] **Step 2: Run and observe unsafe source acceptance/failure**

Run: `cd ~/Projects/kaisian && /bin/bash tests/setup_test.sh`

Expected: nonzero on the first source test because canonicalization/acquisition functions are absent.

- [ ] **Step 3: Implement ASCII canonical source and origin-only ref resolution**

Accept GitHub slug grammar and `https://HOST/PATH[.git][/]`; reject every byte/segment listed above before Git. Resolve refs with advertised `ls-remote` records, reject shorthand ambiguity, fetch only the selected full ref/object into `FETCH_HEAD`, peel `FETCH_HEAD^{commit}`, and compare the embedded/default SHA exactly. Never pass raw user text to local `rev-parse` after fetch.

- [ ] **Step 4: Implement new/existing checkout and exact config/admin allowlists**

For a new path: validate parent/lock/HOME boundaries; create parent; `git init`; add only canonical origin; fetch once; inspect fetched `.gitmodules`; detached checkout. For existing paths: require embedded real `.git` and same physical common dir; validate the exact core/remote/branch/submodule allowlists; reject all administrative symlinks, alternates, replacement/graft/info-attribute state, in-progress markers, and out-of-tree mutable paths.

Worktree verification uses `GIT_INDEX_FILE=$SANDBOX/verify-index`, `read-tree HEAD`, refresh/diff against worktree, a separate real-index comparison, and config-independent untracked/ignored scans. The sandbox index is the sole administrative path permitted outside embedded `.git`.

- [ ] **Step 5: Implement staged HTTPS submodule initialization**

Read each tracked `.gitmodules` from the fetched object before checkout. Validate unique relative contained paths, canonical public HTTPS URLs, absent/checkout update modes, and package-tree exclusion. For each gitlink, create an embedded child repo with the same sanitized `git init` + exact SHA fetch; verify it before reading/initializing the next level. Never invoke unvalidated `git submodule update --recursive`.

- [ ] **Step 6: Verify source acquisition and executed command trace**

Run:

```bash
cd ~/Projects/kaisian
/bin/bash tests/setup_test.sh
! /usr/bin/grep -E -- 'reset --hard|clean -f|stash|submodule update --recursive' tests/tmp/last-command-trace.log
```

Expected: source/ref/config/admin/submodule fixtures pass; forbidden command trace is empty.

- [ ] **Step 7: Commit safe source acquisition**

```bash
git add setup.sh tests/setup_test.sh tests/fixtures/fake-git
git -c commit.gpgsign=false commit -m "feat: acquire pinned Git sources safely"
```

---

### Task 5: Validate Package Trees, Preflight Targets, and Move Exact Conflicts

**Files:**
- Modify: `~/Projects/kaisian/setup.sh`
- Modify: `~/Projects/kaisian/tests/setup_test.sh`

**Interfaces:**
- Produces sandbox files `mapping.tsv`, `conflicts.tsv`, `stow-ignore.txt`.
- Produces functions: `build_package_map`, `validate_typed_tree`, `preflight_targets`, `confirm_conflicts`, `move_conflicts`.
- `mapping.tsv`: `type<TAB>package<TAB>source-relative<TAB>target-relative<TAB>ascii-folded-target`.
- `conflicts.tsv`: `source-target<TAB>backup-destination`; all values are normalized absolute paths without control bytes.

- [ ] **Step 1: Add failing package and target safety fixtures**

Cover:

```text
dot-zshrc => .zshrc and dot-config/zsh/aliasrc => .config/zsh/aliasrc
hidden, non-ASCII/control, dot-/dot-., source symlink, untracked/ignored leaf, empty dir, gitlink/nested repo reject
ASCII-case duplicate leaf rejects on every filesystem
shared directory prefixes pass
leaf/leaf, leaf/directory, and leaf/descendant collisions across declared packages reject before confirmation
checkout/state/backup/lock equality and ancestor/descendant overlap reject; siblings pass
absent target plans link; exact expected symlink is no-op
regular file, directory, broken/wrong symlink are backup conflicts
symlink parent, FIFO, socket, and device target reject
same-device backup preserves HOME-relative hierarchy
cross-device backup refuses before creating backup root
failed `/dev/tty` read refuses before backup; explicit no is zero no-op; --yes proceeds
dry-run conflicts skip prompt/TTY and create no backup
```

- [ ] **Step 2: Run and observe mapping failure**

Run: `cd ~/Projects/kaisian && /bin/bash tests/setup_test.sh`

Expected: nonzero because package mapping/preflight functions do not exist.

- [ ] **Step 3: Implement one normalized typed mapping**

Traverse regular package leaves without following symlinks. Transform each `dot-` component once, reject transformed traversal, normalize HOME-relative paths, and ASCII-fold only for collision keys. Merge all declared packages into a typed tree: directory/directory sharing only; reject duplicate leaves and every leaf/directory/prefix collision. Use the original normalized target for containment, backup, and display.

- [ ] **Step 4: Implement target/state/lock preflight**

Capture physical HOME and validate each parent without following symlinks. Compute `${XDG_STATE_HOME:-$PHYSICAL_HOME/.local/state}/kaisian/backups/<UTC>-<PID>/files/...`; validate absolute state root, symlink ancestors, checkout/state/mapped/lock overlap, and source/destination device IDs using `/usr/bin/stat -f '%d'` on each conflict and nearest existing destination ancestor. Never copy/delete across devices.

- [ ] **Step 5: Implement confirmation and move-only backup**

Print every exact move. Read `y/N` from `/dev/tty` only for non-dry-run conflicts without `--yes`; failed/missing TTY is nonzero, explicit rejection is zero without target changes, and dry-run never prompts. After approval reserve a unique root and use only `mv` for each exact conflict. On partial failure preserve completed moves and print the backup root plus manual restore commands; never auto-restore or delete backups.

- [ ] **Step 6: Verify preflight and backup behavior**

Run: `cd ~/Projects/kaisian && /bin/bash tests/setup_test.sh`

Expected: every package/collision/target/node/device/TTY/backup fixture passes and no test writes outside its temporary roots plus validated lock.

- [ ] **Step 7: Commit package preflight**

```bash
git add setup.sh tests/setup_test.sh
git -c commit.gpgsign=false commit -m "feat: preflight and back up dotfile conflicts"
```

---

### Task 6: Execute Deterministic Stow Plans, Dry Runs, Switching, and Upgrades

**Files:**
- Modify: `~/Projects/kaisian/setup.sh`
- Modify: `~/Projects/kaisian/tests/setup_test.sh`
- Create: `~/Projects/kaisian/tests/fixtures/stable-package-names.txt`

**Interfaces:**
- Produces `build_stow_ignores`, `simulate_stow`, `apply_stow_plan`.
- Consumes ordered `selected.txt`, `unselected.txt`, validated `mapping.tsv`, and conflict plan.
- Executes one mixed plan where possible: selected `-R`, explicitly omitted `-D`; default/all restow every package.

- [ ] **Step 1: Add failing real-Stow behavioral fixtures**

With actual GNU Stow and temporary target HOME, cover:

```text
first apply creates only expected leaf links using dotfiles/no-folding/compat
second apply converges without new backup
profile/groups switching deletes omitted package links and keeps selected links
never-stowed unselected deletion is filtered only when behavior probe requires it
retained package update removes obsolete payload link under --compat
`stable-package-names.txt` exactly matches manifest order and package removal/rename fixtures reject
hostile caller/target .stowrc, .stow-global-ignore, STOW_DIR, and Perl vars do not alter result
README/LICENSE package leaves are installed because controlled global ignore is empty
literal anchored checkout/state subtree ignores preserve current and prior backup symlinks during --compat
ignore regex metacharacters are escaped and cannot suppress neighboring valid payload
dry-run no-conflict calls --simulate --verbose and changes no target
dry-run conflict reports plan without running misleading Stow failure or requiring TTY
Stow failure preserves backup and reports manual recovery
command trace never contains --adopt or --override
```

Add a `tests/setup_test.sh --smoke-default` mode that builds one canonical existing fixture checkout with a matching fake HTTPS origin/fetch boundary, invokes the public `main` path rather than internal functions, applies it to a fresh target HOME twice, and asserts actual link destinations plus no second-run backup.

- [ ] **Step 2: Run and observe first real-Stow failure**

Run: `cd ~/Projects/kaisian && /bin/bash tests/setup_test.sh`

Expected: nonzero because mixed Stow orchestration is absent.

- [ ] **Step 3: Create the cumulative stable-package contract**

Create `tests/fixtures/stable-package-names.txt` with exactly one name per line in manifest order:

```text
shell
git
mise
terminal
editors
agents
cli
macos
homebrew
dev
```

Every future release appends new package names but never edits/removes an existing line; Task 7 compares this file with all prior release tags and the fetched default manifest.

- [ ] **Step 4: Generate validated compatibility exclusions**

For checkout and computed state/backup trees below target HOME, convert their normalized HOME-relative paths into literal anchored Perl regexes by escaping every metacharacter and matching the subtree boundary. Require preflight to prove no payload equals/contains/is contained by an excluded tree. Pass repeated `--ignore=<regex>` through the sanitized runner. The prerequisite probe must prove these expressions exclude target traversal under `--compat`; otherwise normal execution fails before mutation.

- [ ] **Step 5: Implement simulation and mixed apply**

Build arguments as Bash indexed arrays. Always include absolute dir/target and `--dotfiles --no-folding --compat`. Append selected packages under `-R`; append explicit/profile/interactive omissions under `-D`; default/all use only all-package `-R`. With no backup conflicts, dry-run adds `--simulate --verbose`. With planned conflicts, dry-run reports them and skips Stow because occupied targets are expected. Real apply moves approved conflicts first, then calls Stow; a Stow error returns nonzero without deleting backups.

- [ ] **Step 6: Verify full runtime suite and actual CLI smoke**

Run:

```bash
cd ~/Projects/kaisian
/bin/bash -n setup.sh tests/setup_test.sh
/bin/bash tests/setup_test.sh
TMP_HOME=$(mktemp -d)
# Harness creates a canonical existing fixture checkout and fake network boundary.
HOME="$TMP_HOME" /bin/bash tests/setup_test.sh --smoke-default
```

Expected: all cases pass; smoke output identifies selected packages and actual symlinks resolve into the fixture checkout.

- [ ] **Step 7: Commit Stow orchestration**

```bash
git add setup.sh tests/setup_test.sh tests/fixtures/stable-package-names.txt
git -c commit.gpgsign=false commit -m "feat: apply deterministic GNU Stow plans"
```

---

### Task 7: Add Bilingual Documentation and Tagged Shell Release CI

**Files:**
- Create: `~/Projects/kaisian/README.md`
- Create: `~/Projects/kaisian/README.en.md`
- Create: `~/Projects/kaisian/.github/workflows/ci.yml`
- Create: `~/Projects/kaisian/.github/workflows/release.yml`
- Modify: `~/Projects/kaisian/tests/setup_test.sh`
- Modify before release only: `~/Projects/kaisian/setup.sh` constant `DEFAULT_DOTFILES_COMMIT`

**Interfaces:**
- CI proves Bash syntax and full shell suite on macOS.
- Release workflow consumes tag `vX.Y.Z`; publishes exact repository `setup.sh` and `setup.sh.sha256` only after the embedded dotfiles SHA is remotely fetchable and its manifest package list equals the cumulative stable-package contract.
- Endpoint plan consumes those immutable assets.

- [ ] **Step 1: Add failing documentation/release contract checks**

Add a suite mode that asserts README structural parity, both curl forms, all CLI flags, prerequisites, public-source limitation, backup/manual recovery, dry-run mutation boundary, inspect-before-run, and explicit trust boundaries. Add static workflow checks for macOS runner, `bash -n`, full suite, tag-only release, SHA-256 generation, and absence of branch-head publication.

- [ ] **Step 2: Run and observe missing docs/workflows**

Run: `cd ~/Projects/kaisian && /bin/bash tests/setup_test.sh`

Expected: nonzero because README/workflow files do not exist.

- [ ] **Step 3: Write structurally paired README files**

Both files use the same sections and command blocks. Required quick starts:

```bash
curl -fsSL https://kaisian.phx.tw | bash
curl -fsSL https://kaisian.phx.tw | bash -s -- --interactive
```

Include an inspect-first alternative that downloads `setup.sh` and its SHA-256, verifies with `shasum -a 256 -c`, reads it, then executes it. State the macOS 13+, Bash, Git, GNU Stow, fzf, and plutil prerequisites; present Homebrew only as the recommended way to install missing Git/Stow/fzf, not as a runtime command requirement. State that Node.js is not required, only public HTTPS repos are accepted, conflicts are moved to XDG state on the same filesystem, and rollback/recovery are manual.

- [ ] **Step 4: Create CI and release workflows**

`ci.yml` checks out source on `macos-13` and latest macOS, installs only `stow` and `fzf` with Homebrew for CI, runs `/bin/bash -n setup.sh tests/setup_test.sh`, then `/bin/bash tests/setup_test.sh`.

`release.yml` triggers only on `v*` tags, verifies tag version equals `KAISIAN_VERSION`, and requires the embedded commit to be 40-hex/nonzero. It creates a temporary empty Git repository, fetches exactly that SHA from `https://github.com/taiansu/dotfiles.git` into `FETCH_HEAD`, verifies `FETCH_HEAD^{commit}` equals the embedded value, and extracts `.kaisian.json`; `ls-remote <sha>` is not used because a raw object ID is not a ref-pattern lookup. The manifest group list must exactly equal `tests/fixtures/stable-package-names.txt`. For every earlier `v*` tag, each name in that tag's stable-package file must remain in the current file and manifest, so removal/rename cannot bypass a direct-upgrade release. The workflow reruns CI commands, writes `setup.sh.sha256` with `shasum -a 256`, and uploads only `setup.sh` plus checksum via GitHub CLI/action. It never renders from `main` after tag checkout.

- [ ] **Step 5: Run the complete local release gate**

Run:

```bash
cd ~/Projects/kaisian
/bin/bash -n setup.sh tests/setup_test.sh
/bin/bash tests/setup_test.sh
git diff --check
```

Expected: all tests pass, syntax exits 0, diff check emits nothing. Do not tag until the endpoint plan replaces the development pin `0b3b0c3f206e1f4fb35dac82794a871c5c18f405` with the final reviewed package-layout commit.

- [ ] **Step 6: Commit documentation and release automation**

```bash
git add README.md README.en.md .github/workflows setup.sh tests/setup_test.sh
git -c commit.gpgsign=false commit -m "docs: publish kaisian shell release contract"
```
