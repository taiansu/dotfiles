# Collie Action Recipe Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the one-off `collie-start` recipe with `just collie <action>`, forwarding every action to the installed `herdr.collie` plugin.

**Architecture:** A single required Just parameter is shell-quoted and passed to Herdr's existing plugin action dispatcher. Just validates that the parameter exists; Herdr remains the only source of truth for valid action names and preserves its native output and exit status.

**Tech Stack:** Just, Zsh, Herdr 0.8 plugin CLI

## Global Constraints

- Support all current and future actions registered by `herdr.collie`.
- Do not duplicate an action allowlist in `justfile`.
- Do not retain `collie-start` or add per-action aliases.
- Do not change Collie, Herdr, or plugin configuration.
- Do not stop the running Collie bridge during verification.

---

### Task 1: Parameterize the Collie action recipe

**Files:**
- Modify: `justfile:80-81`
- Test: command-level Just expansion and Herdr action smoke checks

**Interfaces:**
- Consumes: required Just parameter `action`; `herdr plugin action invoke <ACTION_ID> --plugin herdr.collie`
- Produces: command interface `just collie <action>` with Herdr's stdout, stderr, and exit status unchanged

- [ ] **Step 1: Run the pre-change command to verify the requested interface is absent**

Run:

```bash
just --dry-run collie start
```

Expected: non-zero exit with Just reporting that recipe `collie` does not exist; the current recipe is named `collie-start`.

- [ ] **Step 2: Replace the one-off recipe with the parameterized recipe**

Replace:

```just
collie-start:
    herdr plugin action invoke start --plugin herdr.collie
```

with:

```just
# 執行 Collie plugin action
collie action:
    herdr plugin action invoke {{quote(action)}} --plugin herdr.collie
```

- [ ] **Step 3: Verify start and stop command expansion without changing service state**

Run:

```bash
just --dry-run collie start
just --dry-run collie stop
```

Expected output contains exactly these command lines:

```text
herdr plugin action invoke 'start' --plugin herdr.collie
herdr plugin action invoke 'stop' --plugin herdr.collie
```


- [ ] **Step 4: Verify the required parameter fails closed**

Run:

```bash
just collie
```

Expected: non-zero exit with Just reporting that recipe `collie` requires one argument; no Herdr action is invoked.

- [ ] **Step 5: Smoke-test real forwarding with a non-destructive action**

Run:

```bash
just collie version
```

Expected: successful Herdr JSON response naming plugin `herdr.collie` and action `version`.

Because plugin actions execute asynchronously, verify the resulting log separately:

```bash
herdr plugin log list --plugin herdr.collie --limit 5 \
  | jq -e '.result.logs | any(.action_id == "version" and .status == "succeeded")'
```

Expected: `true` and exit status 0. The matching log's stdout contains the Collie version.

- [ ] **Step 6: Commit only the recipe change**

```bash
git add justfile
git commit -m "feat: parameterize Collie just actions" -- justfile
```
