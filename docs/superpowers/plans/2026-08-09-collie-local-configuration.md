# Collie Local Configuration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Collie start reliably under macOS launchd with the mise-installed Bun and restrict access to the current Tailscale user and MagicDNS host.

**Architecture:** Keep all machine-specific values in Herdr's persistent Collie `.env`; do not modify the installed GitHub checkout. `collie-ctl.sh` sources this file before resolving Bun and before launching the bridge, so a restart propagates the same settings through launchd.

**Tech Stack:** Bash, macOS launchd, Bun via mise, Herdr Collie plugin, Tailscale Serve

## Global Constraints

- Modify only local persistent configuration; do not change `config/herdr/plugins/github/herdr.collie-1edf0e1e987e`.
- Keep Collie on `127.0.0.1:8787` with HTTPS Tailscale Serve at `tai-macbook-m5.neko-hake.ts.net`.
- Trust only Tailscale login `taiansu@gmail.com`.
- Store the Collie `.env` with local mode `0600`.

---

### Task 1: Configure and restart Collie

**Files:**
- Create: `config/herdr/plugins/config/herdr.collie/.env`
- Runtime-generated, do not edit: `/Users/tai/Library/LaunchAgents/herdr.collie.plist`
- Verify: `config/herdr/plugins/config/herdr.collie/collie.log`

**Interfaces:**
- Consumes: `collie-ctl.sh` environment variables `BUN_INSTALL`, `COLLIE_TRUSTED_USER`, and `COLLIE_PUBLIC_HOSTS`.
- Produces: a launchd-supervised bridge on `127.0.0.1:8787`, exposed through Tailscale Serve at `https://tai-macbook-m5.neko-hake.ts.net`.

- [ ] **Step 1: Confirm the failing launchd state**

Run:

```bash
launchctl print gui/$(id -u)/herdr.collie
```

Expected before the fix: `active count = 0`, `last exit code = 1`, and launchd's default `PATH` is `/usr/bin:/bin:/usr/sbin:/sbin`.

Run:

```bash
config/herdr/plugins/github/herdr.collie-1edf0e1e987e/scripts/collie-ctl.sh logs
```

Expected before the fix: recent lines contain `error: bun not found on PATH`.

- [ ] **Step 2: Create the persistent Collie environment**

Create `config/herdr/plugins/config/herdr.collie/.env` with exactly:

```dotenv
BUN_INSTALL=/Users/tai/.local/share/mise/installs/bun/latest
COLLIE_TRUSTED_USER=taiansu@gmail.com
COLLIE_PUBLIC_HOSTS=tai-macbook-m5.neko-hake.ts.net
```

Set its local permissions:

```bash
chmod 600 config/herdr/plugins/config/herdr.collie/.env
```

Expected: the file exists and is readable only by its owner.

- [ ] **Step 3: Restart through the supported control path**

Run:

```bash
config/herdr/plugins/github/herdr.collie-1edf0e1e987e/scripts/collie-ctl.sh restart
```

Expected: output includes `bridge started (launchd: herdr.collie)` followed by `✓ Collie is running`; no `isn't answering` warning appears.

- [ ] **Step 4: Verify launchd and bridge logs**

Run:

```bash
launchctl print gui/$(id -u)/herdr.collie
```

Expected: `active count = 1`, `state = running`, and a numeric `pid`.

Run:

```bash
config/herdr/plugins/github/herdr.collie-1edf0e1e987e/scripts/collie-ctl.sh logs
```

Expected: a recent `[bridge] listening on http://127.0.0.1:8787` line and no newly appended `bun not found on PATH` line.

- [ ] **Step 5: Smoke-test both front doors**

Run:

```bash
curl -fsS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8787
```

Expected: `200`.

Run:

```bash
curl -fsS -o /dev/null -w '%{http_code}\n' https://tai-macbook-m5.neko-hake.ts.net
```

Expected: `200` through Tailscale Serve.

- [ ] **Step 6: Commit the persistent configuration**

```bash
git add config/herdr/plugins/config/herdr.collie/.env
git commit -m "chore: configure Collie launch service"
```

Expected: the commit contains only the Collie `.env`; generated launchd and log files remain uncommitted runtime artifacts.
