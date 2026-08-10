import { readFile, watch } from "node:fs/promises"
import { pathToFileURL } from "node:url"

type Handler = (
  event: Record<string, unknown>,
  context: { hasUI: boolean },
) => unknown

type AdapterModule = {
  default(api: { on(event: string, handler: Handler): void }): void
}

function parsePayload(line: string): Record<string, unknown> {
  const value: unknown = JSON.parse(line)
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error("Captured peon payload must be an object")
  }
  return value as Record<string, unknown>
}

async function capturePayloads(
  capturePath: string,
  count: number,
): Promise<Record<string, unknown>[]> {
  for await (const _event of watch(capturePath)) {
    const lines = (await readFile(capturePath, "utf8"))
      .trim()
      .split("\n")
      .filter(Boolean)
    if (lines.length >= count) return lines.map(parsePayload)
  }
  throw new Error("Peon payload watcher closed before all events arrived")
}

const adapterPath = process.env.PEON_PING_ADAPTER_PATH
const capturePath = process.env.PEON_CAPTURE_FILE
if (!adapterPath) throw new Error("PEON_PING_ADAPTER_PATH is required")
if (!capturePath) throw new Error("PEON_CAPTURE_FILE is required")

// The adapter path is the runtime-selected artifact under contract.
const imported = await import(
  `${pathToFileURL(adapterPath).href}?test=${Date.now()}`,
) as unknown as AdapterModule
const handlers = new Map<string, Handler>()
imported.default({
  on(event: string, handler: Handler) {
    handlers.set(event, handler)
  },
})

if (handlers.has("turn_end")) throw new Error("turn_end must not emit completion")
if (handlers.has("tool_call")) throw new Error("tool_call must not emit question alerts")
if (!handlers.has("session_stop")) throw new Error("session_stop handler is required")
if (!handlers.has("agent_end")) throw new Error("agent_end handler is required")
if (!handlers.has("tool_execution_start")) {
  throw new Error("tool_execution_start handler is required")
}
if (!handlers.has("tool_result")) throw new Error("tool_result handler is required")

const payloadPromise = capturePayloads(capturePath, 3)
await handlers.get("session_stop")?.({}, { hasUI: false })
await handlers.get("agent_end")?.({ willContinue: true }, { hasUI: false })
await handlers.get("tool_execution_start")?.(
  { toolCallId: "ask-invalid", toolName: "ask", args: {} },
  { hasUI: true },
)
await handlers.get("tool_execution_start")?.(
  {
    toolCallId: "ask-valid",
    toolName: "ask",
    args: {
      questions: [{
        id: "choice",
        question: "Continue?",
        options: [{ label: "Continue" }],
      }],
    },
  },
  { hasUI: true },
)
await handlers.get("tool_result")?.(
  {
    toolCallId: "read-1",
    toolName: "read",
    input: {},
    content: [{ type: "text", text: "permission denied" }],
    isError: true,
  },
  { hasUI: false },
)
await handlers.get("session_stop")?.({}, { hasUI: false })
await handlers.get("agent_end")?.({ willContinue: false }, { hasUI: false })

console.log(JSON.stringify(await payloadPromise))
