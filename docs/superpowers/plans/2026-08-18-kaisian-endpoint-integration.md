# Kaisian Endpoint Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish the verified Kaisian binary installer and a pinned personal bootstrap at `https://kaisian.phx.tw`, then verify default, custom, interactive, locale, and dry-run flows across both repositories.

**Architecture:** A shared installer template renders both the generic release installer and a personal wrapper. GitHub Pages serves the personal wrapper as the exact root response; a manually dispatched workflow pins one Kaisian release and one clean dotfiles commit, preventing `main` drift.

**Tech Stack:** GitHub Actions, GitHub Releases, GitHub Pages, Bash, SHA-256, custom DNS CNAME `kaisian.phx.tw → taiansu.github.io`.

## Global Constraints

- Complete `2026-08-18-kaisian-cli.md` and `2026-08-18-dotfiles-stow-migration.md` first.
- The endpoint pins an exact Kaisian version, both platform checksums, and an exact `taiansu/dotfiles` commit.
- `curl -fsSL https://kaisian.phx.tw | bash` uses the dotfiles `default` profile and needs no input.
- The endpoint accepts only `--profile`, `--groups`, `--interactive`, `--all`, `--dry-run`, and `--lang` and rejects every other argument.
- Explicit selection replaces the default profile; selection options remain mutually exclusive through Kaisian.
- Personal `--dry-run` must not install the binary, create/update a checkout, create transaction state, backups, or links.
- GitHub Pages must serve the generated script byte-for-byte; `.nojekyll` is mandatory.
- Configure the Pages custom domain before adding DNS to avoid a subdomain-takeover window.
- If the DNS provider offers HTTP proxying, keep the CNAME unproxied until GitHub provisions and enforces HTTPS.
- Never place GitHub, DNS, or release credentials in either repository.

---

### Task 1: Render a personal wrapper from the shared installer core

**Repository:** `~/Projects/kaisian`

**Files:**
- Refactor: `installer/install.sh.in`
- Modify: `scripts/render-installer.sh`
- Create: `installer/personal-wrapper.sh.in`
- Create: `scripts/render-personal-wrapper.sh`
- Create: `tests/personal_wrapper_test.sh`

**Interfaces:**
- `render-personal-wrapper.sh` consumes `VERSION`, `RELEASE_BASE_URL`, `CHECKSUMS_FILE`, `DOTFILES_URL`, `DOTFILES_COMMIT`, `CHECKOUT_DIR`, and `OUTPUT` as positional arguments.
- Generated wrapper exposes only the six allowed user options.
- Shared shell functions select/download/verify/smoke-test a binary either to the installed path or a temporary path.

- [ ] **Step 1: Write failing wrapper tests with fake release assets**

Use temporary HOME/PATH and fake `curl`, `uname`, `shasum`, and Kaisian binaries. Cover:

- no args adds `--profile=default --yes`;
- `--groups=shell,git` suppresses the implicit profile and forwards `--yes`;
- `--interactive` suppresses the implicit profile;
- `--all` and `--profile=minimal` forward unchanged;
- `--lang=zh-TW` affects wrapper messages and reaches the binary;
- shell locale `zh_TW.UTF-8` selects Traditional Chinese without an explicit flag;
- unknown args fail before download;
- checksum mismatch fails before installation/apply;
- normal mode atomically installs `~/.local/bin/kaisian` then invokes it by absolute path;
- dry-run runs a temporary verified binary and leaves no `~/.local/bin/kaisian`, checkout, XDG state, backup, or link.

- [ ] **Step 2: Run the wrapper test**

Run: `bash tests/personal_wrapper_test.sh`

Expected: FAIL because the personal renderer/template do not exist.

- [ ] **Step 3: Extract shared installer functions without sourcing remote code**

The generated scripts remain self-contained. Refactor the template source so the renderer can include the same functions in either output:

```text
resolve_language
message
select_asset
expected_checksum
download_verified_binary
install_verified_binary
```

`download_verified_binary DESTINATION` downloads, verifies, sets mode, and runs `--version`. `install_verified_binary` creates its temporary file inside `~/.local/bin` and atomically renames it. Neither function executes downloaded shell source.

- [ ] **Step 4: Implement strict personal argument forwarding**

The generated personal script stores args in Bash indexed arrays, validates forms accepted by Clap (`--name=value` and `--name value`), counts explicit selection flags, and rejects more than one before network work. It consumes `--lang` into `RESOLVED_LANGUAGE` instead of forwarding a second language flag. If selection count is zero, append `--profile=default` to apply args. Always append `--yes` after selection resolution.

Normal invocation is equivalent to:

```bash
"$HOME/.local/bin/kaisian" --lang="$RESOLVED_LANGUAGE" apply \
  "https://github.com/taiansu/dotfiles.git" \
  --ref="$PINNED_DOTFILES_COMMIT" \
  --checkout-dir="$HOME/Projects/dotfiles" \
  "${FORWARDED_ARGS[@]}" \
  --yes
```

For dry-run, use a `mktemp -d` directory, install the verified binary only there, trap cleanup, and invoke that absolute temporary path. Preserve `--dry-run` in forwarded args.

- [ ] **Step 5: Verify rendering and Bash syntax**

Run:

```bash
bash tests/personal_wrapper_test.sh
bash -n installer/install.sh.in installer/personal-wrapper.sh.in scripts/render-installer.sh scripts/render-personal-wrapper.sh
```

Expected: all tests and syntax checks PASS.

- [ ] **Step 6: Commit shared wrapper rendering**

```bash
git add installer scripts tests/personal_wrapper_test.sh
git commit -m "feat: render pinned personal bootstrap"
```

---

### Task 2: Publish a verified `v0.1.0` Kaisian release

**Repository:** `~/Projects/kaisian`

**Files:**
- Modify only if verification fails: `.github/workflows/release.yml`
- Generated release assets: two binaries, `checksums.txt`, `install.sh`

**Interfaces:**
- Produces immutable GitHub release `v0.1.0` consumed by the Pages deployment.

- [ ] **Step 1: Verify both repositories are clean and complete**

Run:

```bash
git -C "$HOME/Projects/kaisian" status --short
git -C "$HOME/Projects/dotfiles" status --short
git -C "$HOME/Projects/dotfiles" rev-parse HEAD
```

Expected: both status commands emit nothing; the dotfiles command emits one full commit hash. Stop if either repository is dirty.

- [ ] **Step 2: Run the full Kaisian release gate**

Run:

```bash
cd "$HOME/Projects/kaisian"
cargo fmt --check
cargo clippy --all-targets -- -D warnings
cargo test
bash tests/installer_test.sh
bash tests/personal_wrapper_test.sh
```

Expected: all commands exit 0.

- [ ] **Step 3: Publish the new public repository if it has no origin**

Run `gh auth status`. If `git remote get-url origin` fails, create and push the explicitly approved public repository:

```bash
gh repo create taiansu/kaisian --public --source "$HOME/Projects/kaisian" --remote origin --push
```

If origin exists, verify it normalizes to `github.com/taiansu/kaisian` and run `git push origin main`.

- [ ] **Step 4: Tag the verified source**

Run:

```bash
git tag -s v0.1.0 -m "Kaisian v0.1.0"
git push origin v0.1.0
```

Expected: release workflow starts for exactly `v0.1.0`. Do not move or recreate the tag after publication.

- [ ] **Step 5: Verify release assets and checksums**

After the workflow succeeds:

```bash
RELEASE_DIR="$(mktemp -d)"
gh release view v0.1.0 --repo taiansu/kaisian
gh release download v0.1.0 --repo taiansu/kaisian --dir "$RELEASE_DIR"
```

Expected assets:

```text
kaisian-aarch64-apple-darwin
kaisian-x86_64-apple-darwin
checksums.txt
install.sh
```

Download to a retained temporary directory, run `shasum -a 256 -c checksums.txt`, then run the native binary's `--version`. Expected version: `kaisian 0.1.0`.

---

### Task 3: Generate and deploy the pinned GitHub Pages site

**Repository:** `~/Projects/kaisian`

**Files:**
- Create: `.github/workflows/pages.yml`
- Create: `site/.nojekyll`
- Create: `site/CNAME`
- Create: `site/README.txt`
- Generated during workflow: `site/index.html`
- Test: `tests/pages_artifact_test.sh`

**Interfaces:**
- Workflow dispatch inputs: `kaisian_version` and `dotfiles_commit`.
- Root response at `https://kaisian.phx.tw/` is the generated Bash wrapper, despite the Pages filename `index.html`.
- `site/CNAME` contains exactly `kaisian.phx.tw`.

- [ ] **Step 1: Write a failing Pages artifact test**

The test renders with fixture checksums/commit and asserts:

- `site/index.html` starts with `#!/bin/bash`;
- `bash -n site/index.html` succeeds;
- no renderer token remains;
- `site/CNAME` is exactly `kaisian.phx.tw` plus newline;
- `.nojekyll` exists;
- executing the page through the existing fake-release harness preserves the expected pinned version, dotfiles URL, commit, and checkout directory.

- [ ] **Step 2: Run the Pages artifact test**

Run: `bash tests/pages_artifact_test.sh`

Expected: FAIL because the Pages files/workflow do not exist.

- [ ] **Step 3: Create the static site contract**

Create:

```text
site/CNAME      => kaisian.phx.tw
site/.nojekyll  => empty file
site/README.txt => states that index.html intentionally contains a Bash program served at site root
```

Do not put HTML markup around the shell program. Bash consumes response bytes; HTTP `Content-Type` is not trusted for execution.

- [ ] **Step 4: Add manually dispatched Pages deployment**

`pages.yml` must:

1. accept `kaisian_version` matching `v<semver>` and a 40-hex `dotfiles_commit`;
2. download `checksums.txt` from that exact GitHub release;
3. extract both named platform checksums;
4. render `site/index.html` with the release URL, `https://github.com/taiansu/dotfiles.git`, supplied commit, and `$HOME/Projects/dotfiles` literal;
5. run `bash -n` and `tests/pages_artifact_test.sh`;
6. upload `site/` with `actions/upload-pages-artifact`;
7. deploy only through the GitHub Pages environment using `actions/deploy-pages`;
8. grant only `contents: read`, `pages: write`, and `id-token: write`.

The workflow must not build from `main` dotfiles or infer its current HEAD; the dispatcher supplies the already-reviewed commit.

- [ ] **Step 5: Verify workflow and artifact locally**

Run:

```bash
bash tests/pages_artifact_test.sh
bash -n site/index.html
```

Expected: PASS; generated wrapper contains fixed values and no credentials.

- [ ] **Step 6: Commit Pages deployment**

```bash
git add .github/workflows/pages.yml site tests/pages_artifact_test.sh
git commit -m "ci: deploy pinned kaisian bootstrap"
git push origin main
```

---

### Task 4: Configure `kaisian.phx.tw` safely

**Repository:** GitHub repository settings plus DNS provider for `phx.tw`

**Files:**
- Existing deployed artifact: `site/CNAME`

**Interfaces:**
- DNS record: `CNAME kaisian.phx.tw → taiansu.github.io`.
- Pages source: GitHub Actions.

- [ ] **Step 1: Verify or add GitHub domain ownership**

In GitHub account Settings → Pages, verify `phx.tw` if it is not already verified. Add the exact `_github-pages-challenge-taiansu.phx.tw` TXT record and value shown by GitHub, then wait until GitHub marks the domain verified. This dynamic ownership value comes from GitHub and must not be committed.

- [ ] **Step 2: Enable Pages workflow mode before DNS**

Run:

```bash
gh api --method POST repos/taiansu/kaisian/pages -f build_type=workflow
```

If Pages already exists, use:

```bash
gh api --method PUT repos/taiansu/kaisian/pages -f build_type=workflow -f cname=kaisian.phx.tw
```

Confirm repository Settings → Pages shows custom domain `kaisian.phx.tw` before creating the public CNAME.

- [ ] **Step 3: Add the DNS record**

At the authoritative DNS provider, create:

```text
Type:   CNAME
Name:   kaisian
Target: taiansu.github.io
Proxy:  DNS only / disabled
TTL:    automatic
```

Do not point the record to `taiansu.github.io/kaisian`; DNS targets are hostnames, not URLs.

- [ ] **Step 4: Verify DNS and GitHub certificate provisioning**

Run:

```bash
dig +short CNAME kaisian.phx.tw
curl -I https://kaisian.phx.tw/
```

Expected: DNS returns `taiansu.github.io.`; after provisioning, HTTPS returns a successful response from GitHub Pages. Do not continue while certificate warnings or a repository-not-found page remain.

- [ ] **Step 5: Enforce HTTPS**

Run:

```bash
gh api --method PUT repos/taiansu/kaisian/pages -F https_enforced=true -f cname=kaisian.phx.tw -f build_type=workflow
```

Expected: repository Pages settings show “Enforce HTTPS” enabled.

---

### Task 5: Deploy the pinned personal endpoint and smoke-test real behavior

**Repositories:** `~/Projects/kaisian`, `~/Projects/dotfiles`

**Files:**
- No source changes unless verification exposes a defect
- Deployment artifact: root script at `https://kaisian.phx.tw/`

**Interfaces:**
- Deploys Kaisian `v0.1.0` and the exact clean dotfiles commit obtained at execution time.

- [ ] **Step 1: Capture the reviewed dotfiles commit**

Run:

```bash
test -z "$(git -C "$HOME/Projects/dotfiles" status --porcelain)"
DOTFILES_COMMIT="$(git -C "$HOME/Projects/dotfiles" rev-parse HEAD)"
printf '%s\n' "$DOTFILES_COMMIT"
```

Expected: one 40-character commit hash. Record it in the deployment review; it is public metadata, not a secret.

- [ ] **Step 2: Dispatch the pinned Pages deployment**

Run:

```bash
gh workflow run pages.yml --repo taiansu/kaisian \
  -f kaisian_version=v0.1.0 \
  -f dotfiles_commit="$DOTFILES_COMMIT"
RUN_ID="$(gh run list --repo taiansu/kaisian --workflow pages.yml --event workflow_dispatch --limit 1 --json databaseId --jq '.[0].databaseId')"
gh run watch "$RUN_ID" --repo taiansu/kaisian --exit-status
```

Expected: workflow and Pages deployment succeed.

- [ ] **Step 3: Verify deployed bytes before execution**

Download and compare exact deployed bytes:

```bash
PAGES_ARTIFACT="$(mktemp -d)"
DEPLOYED_SCRIPT="$(mktemp)"
gh run download "$RUN_ID" --repo taiansu/kaisian --name github-pages --dir "$PAGES_ARTIFACT"
tar -xf "$PAGES_ARTIFACT/artifact.tar" -C "$PAGES_ARTIFACT"
curl -fsSL https://kaisian.phx.tw/ > "$DEPLOYED_SCRIPT"
cmp "$PAGES_ARTIFACT/index.html" "$DEPLOYED_SCRIPT"
bash -n "$DEPLOYED_SCRIPT"
shasum -a 256 "$DEPLOYED_SCRIPT"
```

Compare the SHA-256 with the workflow summary.

Expected: exact match and valid Bash syntax. A redirect is acceptable only when `curl -L` resolves to the same bytes.

- [ ] **Step 4: Smoke-test dry-run with zero persistence**

Run in an isolated temporary HOME:

```bash
SMOKE_HOME="$(mktemp -d)"
HOME="$SMOKE_HOME" XDG_DATA_HOME="$SMOKE_HOME/.local/share" XDG_STATE_HOME="$SMOKE_HOME/.local/state" \
  bash -c 'curl -fsSL https://kaisian.phx.tw | bash -s -- --dry-run --groups=shell'
test ! -e "$SMOKE_HOME/.local/bin/kaisian"
test ! -e "$SMOKE_HOME/Projects/dotfiles"
test ! -e "$SMOKE_HOME/.local/state/kaisian"
```

Expected: a plan is printed; all persistence assertions pass.

- [ ] **Step 5: Smoke-test complete default apply**

Use a second temporary HOME:

```bash
APPLY_HOME="$(mktemp -d)"
HOME="$APPLY_HOME" XDG_DATA_HOME="$APPLY_HOME/.local/share" XDG_STATE_HOME="$APPLY_HOME/.local/state" \
  bash -c 'curl -fsSL https://kaisian.phx.tw | bash'
test -x "$APPLY_HOME/.local/bin/kaisian"
test -d "$APPLY_HOME/Projects/dotfiles/.git"
test -L "$APPLY_HOME/.zshrc"
test -L "$APPLY_HOME/.gitconfig"
```

Expected: fixed binary installed, pinned repo cloned, default links created, and no input requested.

- [ ] **Step 6: Smoke-test custom, locale, and interactive paths**

Run custom English and Traditional Chinese dry-runs in temporary HOMEs and assert localized stable headings. Run `--interactive --dry-run` in a PTY, select a non-default group with Space, confirm with Enter, and assert the plan contains that group while persistence remains absent.

---

### Task 6: Complete cross-repository bilingual documentation

**Files in `~/Projects/kaisian`:**
- Modify: `README.md`
- Modify: `README.en.md`

**Files in `~/Projects/dotfiles`:**
- Modify: `README.md`
- Modify: `README.en.md`

**Interfaces:**
- All four READMEs link their alternate language.
- Kaisian docs distinguish generic installation from the owner-specific endpoint.

- [ ] **Step 1: Document the exact personal commands**

Both Kaisian READMEs include:

```bash
curl -fsSL https://kaisian.phx.tw | bash
curl -fsSL https://kaisian.phx.tw | bash -s -- --groups=shell,git
curl -fsSL https://kaisian.phx.tw | bash -s -- --interactive
curl -fsSL https://kaisian.phx.tw | bash -s -- --all
curl -fsSL https://kaisian.phx.tw | bash -s -- --dry-run
curl -fsSL https://kaisian.phx.tw | bash -s -- --lang=zh-TW
```

Explain that this endpoint is pinned to `taiansu/dotfiles`; generic users install Kaisian from the versioned GitHub release and run `kaisian apply <their-repo>`.

- [ ] **Step 2: Document inspection and trust**

Provide commands to download the endpoint to a file, inspect it, run `bash -n`, compare the published SHA-256 from the latest Pages workflow summary, and then execute it. State that checksum verification cannot protect against compromise of both the endpoint and its published checksum channel.

- [ ] **Step 3: Cross-link dotfiles usage**

Dotfiles READMEs link Kaisian and list the ten actual groups, default profile, optional tool warnings, backup/recovery paths, and the local-source command for contributors:

```bash
kaisian apply "$HOME/Projects/dotfiles" --interactive --dry-run
```

- [ ] **Step 4: Verify docs and final behavior**

Run:

```bash
cd "$HOME/Projects/kaisian"
cargo fmt --check
cargo clippy --all-targets -- -D warnings
cargo test
bash tests/installer_test.sh
bash tests/personal_wrapper_test.sh
bash tests/pages_artifact_test.sh

cd "$HOME/Projects/dotfiles"
bash .maintenance/tests/manifest-contract.sh
bash .maintenance/tests/default-profile.sh
bash .maintenance/tests/all-groups.sh
```

Expected: all checks PASS. Repeat the deployed dry-run once after documentation is pushed.

- [ ] **Step 5: Commit documentation in each repository**

In Kaisian:

```bash
git add README.md README.en.md
git commit -m "docs: add personal bootstrap endpoint"
git push origin main
```

In dotfiles:

```bash
git add README.md README.en.md
git commit -m "docs: link kaisian bootstrap"
git push origin main
```
