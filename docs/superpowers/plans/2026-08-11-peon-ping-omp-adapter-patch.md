# Peon-ping OMP Adapter Patch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve the desired OMP notification lifecycle as a tracked git patch and reapply it fail-closed after every upstream peon-ping adapter installation.

**Architecture:** Keep the upstream adapter installer authoritative, then apply one reviewable unified diff from the dotfiles repository. A Bun contract test loads the patched adapter with a fake `peon.sh`, captures registered OMP handlers and emitted payloads, and verifies completion, question, and error routing without producing real notifications.

**Tech Stack:** Just, Bash, git unified diff/`git apply`, TypeScript, Bun test, OMP ExtensionAPI, peon-ping

## Global Constraints

- Keep the upstream adapter installer; do not fork peon-ping or track a complete adapter copy.
- Store only relative, machine-independent paths in the patch.
- Mark main completion at main-only `session_stop`, emit it from the following `agent_end` only when `willContinue !== true`, emit questions from accepted `ask` `tool_execution_start`, and include peon.sh-compatible fields for `tool_result` errors.
- Run `git apply --check` before `git apply`; any incompatibility must exit nonzero without fuzzy apply, three-way merge, or silent fallback.
- Do not read, print, modify, or commit peon-ping mobile notification credentials.
- Preserve unrelated existing changes in `justfile`, `pi/agent/settings.json`, `pi/agent/npm/`, and `zsh/zshenv`.

## Review-driven amendments

Final review identified lifecycle races in the initially planned snippets below. The implemented patch and contract tests make these corrections:

- `session_stop` records pending main completion; terminal `agent_end` emits it. A continuation clears pending state and cannot produce an early `done`.
- `tool_execution_start`, not blockable `tool_call`, emits the main-UI `ask` notification only after its args pass the mirrored ask-schema guard; validation-failure synthetic starts stay silent.
- Error payloads include nonempty `error` plus the Claude-hook `tool_name: "Bash"` sentinel required by peon.sh's `task.error` route.
- `quote(justfile_directory())` shell-quotes the checkout path before Bash evaluates it.
- `tests/fixtures/peon-ping-adapter-runner.ts` runs the patched adapter in a child process whose HOME points to a fake peon hook, so tests never produce real notifications.

The original task snippets remain as the pre-review execution record; the amended design specification and tracked implementation files are authoritative.

---

### Task 1: Create and contract-test the adapter patch

**Files:**
- Create: `patches/peon-ping/omp-notification-lifecycle.patch`
- Create: `tests/peon-ping-omp-adapter.test.ts`
- Reference only: `~/.omp/agent/extensions/peon-ping/peon-ping.ts`

**Interfaces:**
- Consumes: an unmodified upstream `peon-ping.ts` and environment variable `PEON_PING_ADAPTER_PATH` naming the adapter under test.
- Produces: a patch applicable from the adapter directory and a Bun test proving emitted `hook_event_name`/`notification_type` payloads.

- [ ] **Step 1: Write the failing adapter contract test**

Create `tests/peon-ping-omp-adapter.test.ts` with:

```ts
import { afterEach, expect, test } from "bun:test"
import { mkdtemp, mkdir, rm } from "node:fs/promises"
import { tmpdir } from "node:os"
import * as path from "node:path"
import { pathToFileURL } from "node:url"

type Handler = (event: any, context: any) => unknown

let testRoot = ""

afterEach(async () => {
  if (testRoot) await rm(testRoot, { recursive: true, force: true })
  testRoot = ""
})

async function waitForPayloads(capturePath: string, count: number): Promise<any[]> {
  const deadline = Date.now() + 2_000
  while (Date.now() < deadline) {
    const file = Bun.file(capturePath)
    if (await file.exists()) {
      const lines = (await file.text()).trim().split("\n").filter(Boolean)
      if (lines.length >= count) return lines.map((line) => JSON.parse(line))
    }
    await Bun.sleep(20)
  }
  throw new Error(`Timed out waiting for ${count} peon payloads`)
}

test("routes only actionable OMP lifecycle events", async () => {
  const adapterPath = process.env.PEON_PING_ADAPTER_PATH
  if (!adapterPath) throw new Error("PEON_PING_ADAPTER_PATH is required")

  testRoot = await mkdtemp(path.join(tmpdir(), "peon-ping-adapter-test-"))
  const fakeHome = path.join(testRoot, "home")
  const hookDir = path.join(fakeHome, ".claude", "hooks", "peon-ping")
  const capturePath = path.join(testRoot, "payloads.jsonl")
  await mkdir(hookDir, { recursive: true })
  await Bun.write(
    path.join(hookDir, "peon.sh"),
    "#!/bin/bash\nset -euo pipefail\nIFS= read -r payload\nprintf '%s\\n' \"$payload\" >> \"$PEON_CAPTURE_FILE\"\n",
  )

  process.env.HOME = fakeHome
  process.env.PEON_CAPTURE_FILE = capturePath

  const imported = await import(`${pathToFileURL(adapterPath).href}?test=${Date.now()}`)
  const handlers = new Map<string, Handler>()
  imported.default({
    on(event: string, handler: Handler) {
      handlers.set(event, handler)
    },
  })

  expect(handlers.has("turn_end")).toBe(false)
  expect(handlers.has("session_stop")).toBe(true)
  expect(handlers.has("tool_call")).toBe(true)
  expect(handlers.has("tool_result")).toBe(true)

  await handlers.get("tool_call")?.({ toolName: "ask" }, { hasUI: false })
  await handlers.get("session_stop")?.({}, { hasUI: false })
  await handlers.get("tool_result")?.({ isError: true }, { hasUI: false })

  const payloads = await waitForPayloads(capturePath, 3)
  expect(payloads).toEqual(expect.arrayContaining([
    expect.objectContaining({
      hook_event_name: "Notification",
      notification_type: "elicitation_dialog",
    }),
    expect.objectContaining({ hook_event_name: "Stop" }),
    expect.objectContaining({ hook_event_name: "PostToolUseFailure" }),
  ]))
})
```

- [ ] **Step 2: Run the test against the unmodified adapter**

Run:

```bash
PEON_PING_ADAPTER_PATH="$HOME/.omp/agent/extensions/peon-ping/peon-ping.ts" \
  bun test tests/peon-ping-omp-adapter.test.ts
```

Expected before the patch: FAIL because `turn_end` is registered while `session_stop` and the `ask` `tool_call` handler are absent.

- [ ] **Step 3: Create the unified diff**

Create `patches/peon-ping/omp-notification-lifecycle.patch` with:

```diff
diff --git a/peon-ping.ts b/peon-ping.ts
--- a/peon-ping.ts
+++ b/peon-ping.ts
@@ -16,8 +16,9 @@
  * Event mapping (omp ExtensionAPI → peon.sh hook_event_name):
  *   session_start                       → SessionStart
  *   turn_start                          → UserPromptSubmit
- *   turn_end                            → Stop
+ *   session_stop                        → Stop
+ *   tool_call (event.toolName === "ask") → Notification (elicitation_dialog)
  *   tool_result (event.isError === true) → PostToolUseFailure
  *   auto_compaction_start               → PreCompact
  *   session_shutdown                    → SessionEnd
@@ -62,10 +63,10 @@ export default function peonPingExtension(pi: ExtensionAPI): void {
   const projectName = path.basename(cwd) || "omp"
   const sessionId = `omp-${Date.now()}`
 
-  function firePeon(event: string): void {
+  function firePeon(event: string, notificationType = ""): void {
     const payload = JSON.stringify({
       hook_event_name: event,
-      notification_type: "",
+      notification_type: notificationType,
       cwd,
       session_id: sessionId,
       permission_mode: "",
@@ -92,11 +93,17 @@ export default function peonPingExtension(pi: ExtensionAPI): void {
     firePeon("UserPromptSubmit")
   })
 
-  pi.on("turn_end", async (_event, ctx) => {
+  pi.on("session_stop", async (_event, ctx) => {
     if (ctx.hasUI) setTabTitle(`\u25cf ${projectName}: done`)
     firePeon("Stop")
   })
 
+  pi.on("tool_call", async (event) => {
+    if (event.toolName === "ask") {
+      firePeon("Notification", "elicitation_dialog")
+    }
+  })
+
   pi.on("tool_result", async (event, ctx) => {
     if (!event.isError) return
     if (ctx.hasUI) setTabTitle(`\u25cf ${projectName}: error`)
```

- [ ] **Step 4: Apply the patch to an isolated adapter copy**

Run:

```bash
tmp_dir="$(mktemp -d)"
cp "$HOME/.omp/agent/extensions/peon-ping/peon-ping.ts" "$tmp_dir/peon-ping.ts"
git -C "$tmp_dir" apply --check "$PWD/patches/peon-ping/omp-notification-lifecycle.patch"
git -C "$tmp_dir" apply "$PWD/patches/peon-ping/omp-notification-lifecycle.patch"
git -C "$tmp_dir" apply --reverse --check "$PWD/patches/peon-ping/omp-notification-lifecycle.patch"
```

Expected: all three `git apply` commands exit 0; reverse-check proves the complete patch is present.

- [ ] **Step 5: Run the contract test against the patched copy**

Run:

```bash
PEON_PING_ADAPTER_PATH="$tmp_dir/peon-ping.ts" \
  bun test tests/peon-ping-omp-adapter.test.ts
```

Expected: `1 pass`, with no real peon notification because the test redirects the adapter to a fake HOME and fake `peon.sh`.

- [ ] **Step 6: Commit the patch and contract test**

```bash
git add patches/peon-ping/omp-notification-lifecycle.patch tests/peon-ping-omp-adapter.test.ts
git commit -m "fix: patch OMP peon notification lifecycle"
```

Expected: the commit contains only the unified diff and its Bun contract test.

---

### Task 2: Apply the tracked patch after upstream installation

**Files:**
- Modify: `justfile:39-43`
- Test: `tests/peon-ping-omp-adapter.test.ts`
- Consume: `patches/peon-ping/omp-notification-lifecycle.patch`

**Interfaces:**
- Consumes: upstream installer output at `$HOME/.omp/agent/extensions/peon-ping/peon-ping.ts` and the tracked patch resolved from `{{justfile_directory()}}`.
- Produces: `just peon-ping`, which installs a clean upstream adapter, checks patch compatibility, and applies it exactly once.

- [ ] **Step 1: Confirm the current recipe lacks patch application**

Run:

```bash
if just --dry-run peon-ping | rg -q 'git -C .* apply --check'; then
  echo "unexpected existing patch application"
  exit 1
fi
```

Expected before the change: exit 0 with no output, proving the recipe does not yet enforce the patch.

- [ ] **Step 2: Replace the `peon-ping` recipe with fail-closed application**

Replace lines 39–43 of `justfile` with:

```just
# 安裝／更新 peon-ping、預設音效包及套用本機 OMP adapter patch
peon-ping: ensure-brew
    #!/usr/bin/env bash
    set -euo pipefail

    brew install peonping/tap/peon-ping
    peon-ping-setup
    bash "$(brew --prefix peonping/tap/peon-ping)/libexec/adapters/omp.sh"

    readonly adapter_dir="$HOME/.omp/agent/extensions/peon-ping"
    readonly adapter_file="$adapter_dir/peon-ping.ts"
    readonly patch_file="{{justfile_directory()}}/patches/peon-ping/omp-notification-lifecycle.patch"

    if [[ ! -f "$adapter_file" ]]; then
        printf 'Error: upstream OMP adapter not found: %s\n' "$adapter_file" >&2
        exit 1
    fi
    if [[ ! -f "$patch_file" ]]; then
        printf 'Error: tracked OMP adapter patch not found: %s\n' "$patch_file" >&2
        exit 1
    fi
    if ! git -C "$adapter_dir" apply --check "$patch_file"; then
        printf 'Error: peon-ping OMP adapter changed upstream; refresh patch: %s\n' "$patch_file" >&2
        exit 1
    fi

    git -C "$adapter_dir" apply "$patch_file"
```

- [ ] **Step 3: Validate Just syntax and rendered commands**

Run:

```bash
just --summary
just --dry-run peon-ping | rg -n 'adapter_dir=|git -C .* apply --check|git -C .* apply '
```

Expected: `just --summary` exits 0; dry-run output shows one compatibility check before one apply, and the patch path resolves under this dotfiles checkout.

- [ ] **Step 4: Commit the recipe integration without unrelated user changes**

Because `justfile` already contains unrelated user edits, stage only this recipe hunk interactively or with a path-limited patch, then inspect the staged diff before committing:

```bash
git add -p justfile
git diff --cached -- justfile
git commit -m "chore: reapply peon OMP adapter patch"
```

Expected: the commit contains only the `peon-ping` recipe change; all unrelated `justfile` hunks and other working-tree files remain unstaged.

---

### Task 3: Verify update, conflict, and runtime behavior end to end

**Files:**
- Verify: `justfile`
- Verify: `patches/peon-ping/omp-notification-lifecycle.patch`
- Verify: `tests/peon-ping-omp-adapter.test.ts`
- Runtime artifact: `~/.omp/agent/extensions/peon-ping/peon-ping.ts`

**Interfaces:**
- Consumes: the completed patch and installation recipe.
- Produces: evidence that a fresh upstream installation is patched, incompatible input is rejected unchanged, and OMP can load the patched extension.

- [ ] **Step 1: Prove incompatible adapter input fails without modification**

Run:

```bash
conflict_dir="$(mktemp -d)"
truncate -s 0 "$conflict_dir/peon-ping.ts"
before_hash="$(sha256sum "$conflict_dir/peon-ping.ts")"
if git -C "$conflict_dir" apply --check "$PWD/patches/peon-ping/omp-notification-lifecycle.patch"; then
  echo "expected incompatible patch check to fail"
  exit 1
fi
after_hash="$(sha256sum "$conflict_dir/peon-ping.ts")"
test "$before_hash" = "$after_hash"
```

Expected: `git apply --check` exits nonzero and the before/after hashes are identical. On macOS, use the available `sha256sum` utility as shown.

- [ ] **Step 2: Run the complete update recipe**

Run:

```bash
just peon-ping
```

Expected: Homebrew/setup and the upstream OMP adapter installer succeed, followed by successful patch check/application. No patch conflict message appears.

- [ ] **Step 3: Verify the installed adapter contains exactly one applied patch**

Run:

```bash
git -C "$HOME/.omp/agent/extensions/peon-ping" \
  apply --reverse --check "$PWD/patches/peon-ping/omp-notification-lifecycle.patch"
```

Expected: exit 0. A normal forward `git apply --check` at this point must fail because the patch is already present.

- [ ] **Step 4: Run the adapter contract test against the installed artifact**

Run:

```bash
PEON_PING_ADAPTER_PATH="$HOME/.omp/agent/extensions/peon-ping/peon-ping.ts" \
  bun test tests/peon-ping-omp-adapter.test.ts
```

Expected: `1 pass`; captured payloads include `Notification/elicitation_dialog`, `Stop`, and `PostToolUseFailure`.

- [ ] **Step 5: Smoke-test OMP extension loading**

Run:

```bash
omp -p --no-session "Reply with exactly: PEON_PATCH_OK"
```

Expected: OMP exits 0 and prints `PEON_PATCH_OK`; stderr contains no peon-ping extension load or TypeScript error.

- [ ] **Step 6: Confirm repository scope**

Run:

```bash
git status --short
```

Expected: no uncommitted files from this implementation. Pre-existing user changes in `justfile`, `pi/agent/settings.json`, `pi/agent/npm/`, and `zsh/zshenv` remain exactly as they were unless the selected `justfile` recipe hunk was committed separately.
