import { afterEach, expect, test } from "bun:test"
import { mkdtemp, mkdir, rm } from "node:fs/promises"
import { tmpdir } from "node:os"
import * as path from "node:path"

let testRoot = ""

afterEach(async () => {
  if (testRoot) await rm(testRoot, { recursive: true, force: true })
  testRoot = ""
})

function parsePayloads(value: string): Record<string, unknown>[] {
  const parsed: unknown = JSON.parse(value)
  if (
    !Array.isArray(parsed)
    || parsed.some((item) => !item || typeof item !== "object" || Array.isArray(item))
  ) {
    throw new Error("Runner output must be an array of payload objects")
  }
  return parsed as Record<string, unknown>[]
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
    "#!/bin/bash\nset -euo pipefail\npayload=\"\"\nIFS= read -r -d '' payload || true\nprintf '%s\\n' \"$payload\" >> \"$PEON_CAPTURE_FILE\"\n",
  )
  await Bun.write(capturePath, "")

  const child = Bun.spawn([
    process.execPath,
    path.join(import.meta.dir, "fixtures", "peon-ping-adapter-runner.ts"),
  ], {
    env: {
      ...process.env,
      HOME: fakeHome,
      PEON_CAPTURE_FILE: capturePath,
      PEON_PING_ADAPTER_PATH: adapterPath,
    },
    stdout: "pipe",
    stderr: "pipe",
  })
  const [exitCode, stdout, stderr] = await Promise.all([
    child.exited,
    new Response(child.stdout).text(),
    new Response(child.stderr).text(),
  ])

  expect({ exitCode, stderr }).toEqual({ exitCode: 0, stderr: "" })
  const payloads = parsePayloads(stdout)
  expect(payloads).toEqual(expect.arrayContaining([
    expect.objectContaining({
      hook_event_name: "Notification",
      notification_type: "elicitation_dialog",
    }),
    expect.objectContaining({ hook_event_name: "Stop" }),
    expect.objectContaining({
      hook_event_name: "PostToolUseFailure",
      tool_name: "Bash",
      error: "read: permission denied",
    }),
  ]))
})
