# Kaisian Shell Release + Personal Endpoint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish one immutable Kaisian `setup.sh` with its SHA-256, serve those exact bytes at `https://kaisian.phx.tw`, and smoke-test the default and dry-run flows against the pinned dotfiles commit.

**Architecture:** The reviewed dotfiles commit is embedded in `setup.sh` before tagging. GitHub Releases publishes the script and its checksum; a GitHub Pages workflow copies the tagged script byte-for-byte to `site/index.html`. The endpoint adds no wrapper, renderer, or second argument parser.

**Tech Stack:** GitHub Actions, GitHub Releases, GitHub Pages, Bash, SHA-256, GitHub CLI, DNS CNAME `kaisian.phx.tw → taiansu.github.io`.

## Global Constraints

- Complete `2026-08-18-kaisian-shell-stow-wrapper.md` Tasks 6 and 7 first.
- Both repositories must be clean and pushed before pinning or tagging.
- Endpoint bytes must equal the released `setup.sh` exactly; no HTML wrapper, redirect, or branch-head fetch.
- The tag and the embedded dotfiles SHA are immutable. Never move or recreate a published tag.
- Release asset set is exactly `setup.sh` and `setup.sh.sha256`.
- Configure the Pages custom domain before creating the DNS record, to avoid a subdomain-takeover window.
- Keep DNS unproxied until GitHub provisions and enforces HTTPS.
- Never place GitHub, DNS, or release credentials in either repository or in command output.
- Remote, DNS, and tag operations need the user's authenticated environment; stop with exact evidence if access is unavailable rather than inventing results.

## File Map

- `~/Projects/kaisian/setup.sh` — release and endpoint body with the final `DEFAULT_DOTFILES_COMMIT`.
- `~/Projects/kaisian/.github/workflows/pages.yml` — deploys the tagged script to Pages.
- `~/Projects/kaisian/site/index.html` — generated copy of the released `setup.sh`.
- `~/Projects/kaisian/site/CNAME` — exactly `kaisian.phx.tw`.
- `~/Projects/kaisian/site/.nojekyll` — disables Jekyll processing.
- `~/Projects/kaisian/README.md`, `README.en.md` — published release, checksum, and domain instructions.

---

### Task 1: Pin the Final Dotfiles Commit and Tag the Release

**Files:**
- Modify: `~/Projects/kaisian/setup.sh` constant `DEFAULT_DOTFILES_COMMIT`

- [ ] **Step 1: Resolve and embed the reviewed dotfiles commit**

Take the pushed `taiansu/dotfiles` `main` head, confirm it is remotely fetchable, and replace the development pin in `setup.sh`.

```bash
cd ~/Projects/dotfiles && git rev-parse HEAD && git status --short
cd ~/Projects/kaisian && git status --short
```

Expected: both trees clean; the dotfiles SHA matches `origin/main`.

- [ ] **Step 2: Verify the pinned commit end to end**

```bash
cd ~/Projects/kaisian
/bin/bash -n setup.sh tests/setup_test.sh
/bin/bash tests/setup_test.sh
TMP_HOME=$(mktemp -d)
HOME="$TMP_HOME" /bin/bash setup.sh --dry-run --yes
```

Expected: suite passes; the dry run prints the planned actions against the real pinned commit and mutates nothing.

- [ ] **Step 3: Commit and tag**

```bash
cd ~/Projects/kaisian
git add setup.sh
git -c commit.gpgsign=false commit -m "release: pin reviewed dotfiles commit"
git push
git tag v0.1.0
git push origin v0.1.0
```

Expected: the release workflow from wrapper Task 7 runs and attaches exactly `setup.sh` and `setup.sh.sha256`.

---

### Task 2: Serve the Released Script at the Personal Endpoint

**Files:**
- Create: `~/Projects/kaisian/.github/workflows/pages.yml`
- Create: `~/Projects/kaisian/site/CNAME`
- Create: `~/Projects/kaisian/site/.nojekyll`

- [ ] **Step 1: Create the Pages workflow**

`pages.yml` runs on manual dispatch with a tag input. It downloads `setup.sh` and `setup.sh.sha256` from that release, verifies with `shasum -a 256 -c`, copies the script to `site/index.html`, asserts `cmp -s setup.sh site/index.html`, then deploys `site/`.

- [ ] **Step 2: Add the domain and Jekyll files**

`site/CNAME` contains exactly `kaisian.phx.tw`. `site/.nojekyll` is empty.

- [ ] **Step 3: Configure Pages, then DNS, in that order**

Enable Pages with the GitHub Actions source, set the custom domain to `kaisian.phx.tw`, and only afterwards create the DNS `CNAME` to `taiansu.github.io`. Leave the record unproxied and wait for GitHub to report HTTPS as provisioned, then enable Enforce HTTPS.

- [ ] **Step 4: Deploy the tagged release**

Dispatch `pages.yml` with `v0.1.0` and wait for a successful deployment.

---

### Task 3: Smoke-Test the Deployed Endpoint

- [ ] **Step 1: Verify the served bytes**

```bash
curl -fsSL https://kaisian.phx.tw -o /tmp/kaisian-served.sh
gh release download v0.1.0 --repo taiansu/kaisian --pattern 'setup.sh' --dir /tmp/kaisian-asset
cmp /tmp/kaisian-served.sh /tmp/kaisian-asset/setup.sh
/bin/bash -n /tmp/kaisian-served.sh
```

Expected: `cmp` and `bash -n` both exit 0, proving the endpoint serves the exact release asset.

- [ ] **Step 2: Run the documented flows against a throwaway HOME**

```bash
TMP_HOME=$(mktemp -d)
HOME="$TMP_HOME" bash /tmp/kaisian-served.sh --dry-run --yes
HOME="$TMP_HOME" bash /tmp/kaisian-served.sh --yes
HOME="$TMP_HOME" ls -la "$TMP_HOME"
```

Expected: the dry run mutates nothing; the real run creates symlinks resolving into `$TMP_HOME/.dotfiles`; a second run is idempotent.

- [ ] **Step 3: Finalize both READMEs**

Replace any placeholder release version or checksum instructions with the published `v0.1.0` values in `README.md` and `README.en.md`, then commit:

```bash
cd ~/Projects/kaisian
git add README.md README.en.md
git -c commit.gpgsign=false commit -m "docs: document verified kaisian endpoint"
git push
```
