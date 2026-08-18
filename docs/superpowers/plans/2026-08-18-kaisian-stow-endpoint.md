# Kaisian Shell Release + Personal Endpoint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish one immutable, checksum-verified Kaisian `setup.sh`, serve those exact bytes at `https://kaisian.phx.tw`, and smoke-test default, custom, interactive, locale, and dry-run flows against the pinned dotfiles commit.

**Architecture:** The reviewed dotfiles commit is embedded directly in `setup.sh` before tagging Kaisian. GitHub Releases publishes that script and its SHA-256; a manually dispatched GitHub Pages workflow downloads the exact tagged assets, verifies the checksum, and copies the script byte-for-byte to `site/index.html`. The personal endpoint adds no wrapper, renderer, or second argument parser.

**Tech Stack:** GitHub Actions, GitHub Releases, GitHub Pages, Bash, SHA-256, GitHub CLI, DNS CNAME `kaisian.phx.tw → taiansu.github.io`.

## Global Constraints

- Complete and review `2026-08-18-kaisian-shell-stow-wrapper.md` and `2026-08-18-dotfiles-stow-packages.md` first.
- Both repositories must be clean, reviewed, and pushed before pinning/tagging.
- Endpoint bytes must equal the `setup.sh` release asset exactly; no HTML wrapper, generated bootstrap, redirect script, binary installer, or branch-head fetch.
- The Kaisian tag and embedded dotfiles SHA are immutable. Never move/recreate a published tag.
- Release asset set is exactly `setup.sh` and `setup.sh.sha256`.
- `curl -fsSL https://kaisian.phx.tw | bash` defaults to all declared packages and needs no prompt when there are no conflicts; conflict confirmation still follows generic CLI rules.
- Generic options remain available through `bash -s --`: profile, groups, interactive, all, repo/ref/repo-dir, language, dry-run, and yes.
- Configure GitHub Pages custom domain before DNS to avoid a subdomain-takeover window.
- Keep DNS unproxied until GitHub provisions and enforces HTTPS.
- Never place GitHub, DNS, or release credentials in either repository or command output.
- Remote/DNS/tag creation and destructive settings require the user's authenticated environment; stop with exact evidence if access is unavailable rather than inventing credentials, assets, or results.

## File Map

- `~/Projects/kaisian/setup.sh` — exact release and endpoint body with final default dotfiles commit.
- `~/Projects/kaisian/.github/workflows/release.yml` — tag-only release assets.
- `~/Projects/kaisian/.github/workflows/pages.yml` — manual exact-release Pages deployment.
- `~/Projects/kaisian/site/.nojekyll` — disables Jekyll processing.
- `~/Projects/kaisian/site/CNAME` — exactly `kaisian.phx.tw`.
- `~/Projects/kaisian/site/README.txt` — explains why `index.html` is Bash.
- `~/Projects/kaisian/tests/pages_artifact_test.sh` — byte equality, checksum, syntax, and pinned-behavior contract.
- `~/Projects/kaisian/README.md`, `README.en.md` — published release/checksum/domain instructions.

---

### Task 1: Pin the Reviewed Dotfiles Commit and Verify Cross-Repository Behavior

**Files:**
- Modify: `~/Projects/kaisian/setup.sh` constant `DEFAULT_DOTFILES_COMMIT`
- Modify: `~/Projects/kaisian/tests/setup_test.sh`

**Interfaces:**
- Consumes one reviewed/pushed 40-hex commit from `taiansu/dotfiles` whose `.kaisian.json` and ten packages passed the migration plan.
- Produces a clean Kaisian commit whose default source/ref exactly match that remote object.

- [ ] **Step 1: Verify clean repositories and capture immutable inputs**

Run:

```bash
git -C "$HOME/Projects/kaisian" status --short
git -C "$HOME/Projects/dotfiles" status --short
DOTFILES_COMMIT=$(git -C "$HOME/Projects/dotfiles" rev-parse HEAD)
test ${#DOTFILES_COMMIT} -eq 40
VERIFY_REPO=$(mktemp -d)
git -C "$VERIFY_REPO" init
git -C "$VERIFY_REPO" fetch --depth=1 https://github.com/taiansu/dotfiles.git "$DOTFILES_COMMIT"
test "$(git -C "$VERIFY_REPO" rev-parse 'FETCH_HEAD^{commit}')" = "$DOTFILES_COMMIT"
rm -rf -- "$VERIFY_REPO"
```

Expected: both status commands emit nothing; exact-object fetch and equality succeed. Stop if the local dotfiles HEAD is not the reviewed/pushed commit.

- [ ] **Step 2: Add a failing embedded-default contract test**

The test reads the public CLI constants through a `--dry-run` fake-network trace and asserts default repository `taiansu/dotfiles`, default checkout `$PHYSICAL_HOME/.dotfiles`, and exact captured SHA. It rejects the earlier development pin and any branch name.

- [ ] **Step 3: Run and observe old-pin failure**

Run: `cd ~/Projects/kaisian && /bin/bash tests/setup_test.sh`

Expected: nonzero because the embedded default does not equal the reviewed dotfiles commit.

- [ ] **Step 4: Replace only the embedded commit constant**

Set:

```bash
readonly DEFAULT_DOTFILES_COMMIT='<exact DOTFILES_COMMIT from Step 1>'
```

Do not add a runtime lookup of dotfiles `main` and do not generate the value in the release workflow.

- [ ] **Step 5: Run default/all/profile/groups/dry-run integration smoke**

Use disposable HOME/XDG roots and the public HTTPS source. Verify:

```text
no selection installs all ten packages
--profile default installs shell, git, mise and unstows omissions
--groups shell,git preserves manifest order
--dry-run updates only disposable checkout and changes no target/state
repeat all/default application converges without new backups
```

Run the Kaisian full suite afterward.

- [ ] **Step 6: Commit the pin**

```bash
git add setup.sh tests/setup_test.sh
git -c commit.gpgsign=false commit -m "release: pin reviewed dotfiles commit"
```

---

### Task 2: Publish the Public `taiansu/kaisian` Repository and `v0.1.0` Shell Release

**Files:**
- Verify/modify only if contract fails: `.github/workflows/ci.yml`, `.github/workflows/release.yml`
- Generated release assets: `setup.sh`, `setup.sh.sha256`

**Interfaces:**
- Produces public origin `https://github.com/taiansu/kaisian.git` and immutable release `v0.1.0`.
- Pages task consumes exact release URLs and checksum, never source `main`.

- [ ] **Step 1: Run the full local release gate**

Run:

```bash
cd "$HOME/Projects/kaisian"
/bin/bash -n setup.sh tests/setup_test.sh
/bin/bash tests/setup_test.sh
git diff --check
git status --short
```

Expected: syntax/test/diff exit 0 and status emits nothing.

- [ ] **Step 2: Verify authenticated GitHub access and origin state**

Run `gh auth status`. If no `origin` exists, create only after confirming repository name/visibility with the user:

```bash
gh repo create taiansu/kaisian --public \
  --source "$HOME/Projects/kaisian" --remote origin --push
```

If origin exists, canonicalize and require `github.com/taiansu/kaisian`, then push `main`. Do not reuse or overwrite an unrelated repository.

- [ ] **Step 3: Tag the verified source once**

After CI on `main` succeeds:

```bash
cd "$HOME/Projects/kaisian"
git tag -s v0.1.0 -m "Kaisian v0.1.0"
git push origin v0.1.0
```

If signing is unavailable, stop and ask whether to use an unsigned annotated tag; do not silently downgrade.

- [ ] **Step 4: Verify release assets and checksum independently**

After the tag workflow succeeds:

```bash
RELEASE_DIR=$(mktemp -d)
gh release view v0.1.0 --repo taiansu/kaisian
gh release download v0.1.0 --repo taiansu/kaisian --dir "$RELEASE_DIR"
cd "$RELEASE_DIR"
shasum -a 256 -c setup.sh.sha256
cmp setup.sh "$HOME/Projects/kaisian/setup.sh"
/bin/bash -n setup.sh
```

Expected: exactly two assets, checksum OK, byte comparison and syntax exit 0.

---

### Task 3: Build and Verify the Exact-Asset GitHub Pages Artifact

**Files:**
- Create: `~/Projects/kaisian/site/.nojekyll`
- Create: `~/Projects/kaisian/site/CNAME`
- Create: `~/Projects/kaisian/site/README.txt`
- Generated: `~/Projects/kaisian/site/index.html`
- Create: `~/Projects/kaisian/tests/pages_artifact_test.sh`
- Create: `~/Projects/kaisian/.github/workflows/pages.yml`
- Modify: `~/Projects/kaisian/.gitignore` to ignore only generated `/site/index.html`

**Interfaces:**
- Workflow dispatch input: exact `kaisian_version` matching `v<semver>`.
- `site/index.html` is byte-identical to the verified release `setup.sh`.
- Pages artifact contains only `.nojekyll`, `CNAME`, `README.txt`, and `index.html`.

- [ ] **Step 1: Write the failing Pages artifact test**

The test accepts a downloaded release directory and asserts:

```bash
cmp "$release_dir/setup.sh" site/index.html
(cd "$release_dir" && shasum -a 256 -c setup.sh.sha256)
/bin/bash -n site/index.html
test "$(cat site/CNAME)" = 'kaisian.phx.tw'
test -f site/.nojekyll
```

It also executes `site/index.html --help` and a fake-network `--dry-run`, proving the embedded dotfiles SHA/version/default source match the release and no HTML/renderer token exists.

- [ ] **Step 2: Run and observe missing site failure**

Run: `cd ~/Projects/kaisian && /bin/bash tests/pages_artifact_test.sh "$RELEASE_DIR"`

Expected: nonzero because `site/index.html` and Pages workflow do not exist.

- [ ] **Step 3: Create the static site metadata contract**

Create:

```text
site/CNAME      => kaisian.phx.tw plus newline
site/.nojekyll  => empty
site/README.txt => index.html intentionally contains an executable Bash program copied from an immutable release
```

Do not wrap the script in HTML or rely on response `Content-Type`.

- [ ] **Step 4: Add manually dispatched exact-release deployment**

`pages.yml` must:

1. accept only `kaisian_version` matching `^v[0-9]+\.[0-9]+\.[0-9]+$`;
2. download `setup.sh` and `setup.sh.sha256` from that exact `taiansu/kaisian` release;
3. run `shasum -a 256 -c` before copying;
4. copy bytes with `cp setup.sh site/index.html`;
5. run `cmp`, `/bin/bash -n`, full `tests/pages_artifact_test.sh`, and assert exactly four site entries;
6. upload `site/` using `actions/upload-pages-artifact`;
7. deploy only through the protected GitHub Pages environment with `actions/deploy-pages`;
8. grant only `contents: read`, `pages: write`, and `id-token: write`.

The workflow never checks out or fetches dotfiles `main`; the SHA is already embedded in the immutable release.

- [ ] **Step 5: Verify locally and commit Pages integration**

Run:

```bash
cp "$RELEASE_DIR/setup.sh" site/index.html
/bin/bash tests/pages_artifact_test.sh "$RELEASE_DIR"
/bin/bash -n site/index.html
git diff --check
```

Expected: checksum/byte/syntax/pin/artifact tests pass. Remove the generated `site/index.html` after verification; the workflow recreates it from the exact release and the repository never tracks a second copy of released code.

```bash
rm -- site/index.html
git add site/.nojekyll site/CNAME site/README.txt .gitignore \
  tests/pages_artifact_test.sh .github/workflows/pages.yml
git -c commit.gpgsign=false commit -m "feat: deploy exact shell release to Pages"
```

---

### Task 4: Configure Pages, Custom Domain, and DNS in Safe Order

**Files/remote state:**
- GitHub repository Pages settings for `taiansu/kaisian`
- DNS CNAME `kaisian.phx.tw → taiansu.github.io`
- No repository secrets required for Pages OIDC deployment

**Interfaces:**
- Produces HTTPS endpoint whose root body equals release `setup.sh` bytes.

- [ ] **Step 1: Push Pages workflow and configure GitHub Pages first**

Push the reviewed Pages commit. In repository Settings → Pages, select GitHub Actions and set custom domain `kaisian.phx.tw`. Verify GitHub reports the domain as configured before creating DNS.

- [ ] **Step 2: Add the DNS CNAME unproxied**

At the authoritative DNS provider, add exactly:

```text
Type: CNAME
Name: kaisian
Target: taiansu.github.io
Proxy: DNS only / unproxied
```

Do not add A/AAAA records or expose provider/API credentials.

- [ ] **Step 3: Dispatch the exact release deployment**

Run:

```bash
gh workflow run pages.yml --repo taiansu/kaisian -f kaisian_version=v0.1.0
gh run watch --repo taiansu/kaisian
```

Expected: checksum, byte equality, test, artifact upload, and Pages deployment jobs succeed.

- [ ] **Step 4: Wait for GitHub HTTPS provisioning, then enforce HTTPS**

Verify GitHub Pages settings show certificate active; enable Enforce HTTPS. Keep DNS unproxied through provisioning. If later proxying is desired, treat it as a separate change with a byte-equality smoke because proxy transforms/caching would be a new trust boundary.

---

### Task 5: Smoke-Test the Deployed Endpoint and Finalize Both READMEs

**Files:**
- Modify: `~/Projects/kaisian/README.md`, `README.en.md`
- Modify: dotfiles `README.md`, `README.en.md` only if deployed commands differ from the documented contract

**Interfaces:**
- Produces evidence for endpoint byte identity, checksum identity, and real default/explicit/interactive behaviors.
- Produces final cross-repository documentation pointing to immutable release/checksum and inspect-before-run flow.

- [ ] **Step 1: Verify deployed bytes against release asset**

Run:

```bash
SMOKE_DIR=$(mktemp -d)
curl -fsSL https://kaisian.phx.tw -o "$SMOKE_DIR/deployed.sh"
gh release download v0.1.0 --repo taiansu/kaisian \
  --pattern setup.sh --pattern setup.sh.sha256 --dir "$SMOKE_DIR/release"
cmp "$SMOKE_DIR/deployed.sh" "$SMOKE_DIR/release/setup.sh"
(cd "$SMOKE_DIR/release" && shasum -a 256 -c setup.sh.sha256)
/bin/bash -n "$SMOKE_DIR/deployed.sh"
```

Expected: byte equality, checksum, and syntax all exit 0.

- [ ] **Step 2: Smoke default, explicit, locale, and dry-run paths in disposable HOME**

Exercise actual endpoint bytes, never the working-tree script:

```text
bash deployed.sh --dry-run --yes
bash deployed.sh --profile default --yes
bash deployed.sh --groups shell,git,mise --yes
LANG=zh_TW.UTF-8 bash deployed.sh --dry-run --yes
bash deployed.sh --lang en --all --yes
```

For each, use a fresh disposable HOME/XDG root; assert selected packages, detached embedded dotfiles SHA, expected links for apply cases, no target/state changes for dry-run, and idempotent repeat.

- [ ] **Step 3: Smoke interactive checkbox selection on a real TTY**

Run:

```bash
curl -fsSL https://kaisian.phx.tw | bash -s -- --interactive --yes
```

Select `shell`, `git`, and `mise` with fzf multi-select. Verify the three package links exist and omitted package links do not. Because this affects the operator HOME, use an explicit disposable terminal/HOME environment or stop if safe isolation cannot be established.

- [ ] **Step 4: Update paired docs with verified release facts**

Document `v0.1.0`, release checksum URL, byte-identical Pages statement, inspect/download/verify commands, generic argument forwarding, and trust boundaries: endpoint/DNS, GitHub Pages, immutable Kaisian tag, public Git transport, embedded dotfiles commit.

- [ ] **Step 5: Run final cross-repository verification and commit docs**

Run:

```bash
cd "$HOME/Projects/kaisian"
/bin/bash -n setup.sh tests/setup_test.sh tests/pages_artifact_test.sh
/bin/bash tests/setup_test.sh
/bin/bash tests/pages_artifact_test.sh "$SMOKE_DIR/release"
git diff --check

cd "$HOME/Projects/dotfiles"
/bin/bash .maintenance/tests/manifest-contract.sh .
/bin/bash .maintenance/tests/default-packages.sh
/bin/bash .maintenance/tests/all-packages.sh
git diff --check
```

Expected: all commands exit 0. Commit only actual documentation changes in their owning repository with `docs: document verified kaisian endpoint`.
