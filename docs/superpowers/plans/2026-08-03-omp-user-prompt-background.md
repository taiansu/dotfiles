# OMP User Prompt Background Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render OMP user-authored prompt bubbles with a subtle neutral-gray background in the active dark theme.

**Architecture:** The OMP agent loads `dark-lunar-custom` from `~/.omp/agent/themes/dark-lunar-custom.json`, as selected by `~/.omp/agent/config.yml`. Change only the `userMessageBg` token to the existing `crater` palette variable; the theme resolves that variable to `#1a1d26`.

**Tech Stack:** OMP theme JSON; `jq` for syntax and semantic validation; OMP terminal UI for the smoke test.

## Global Constraints

- Modify only `userMessageBg` in `~/.omp/agent/themes/dark-lunar-custom.json`.
- Set `userMessageBg` to `crater`, whose existing value is `#1a1d26`.
- Do not add variables or alter `userMessageText`, other message colors, tool colors, or status-line colors.
- The updated user-message background must be visibly lighter than `pageBg` (`#0a0c11`) without a blue cast.

---

### Task 1: Update the active OMP dark theme

**Files:**
- Modify: `~/.omp/agent/themes/dark-lunar-custom.json:29`
- Test: `~/.omp/agent/themes/dark-lunar-custom.json` via `jq`

**Interfaces:**
- Consumes: the `crater` variable defined in `.vars` as `#1a1d26`.
- Produces: `.colors.userMessageBg = "crater"`, which OMP resolves when rendering user-authored messages.

- [ ] **Step 1: Confirm the active theme and source palette value**

Run:

```bash
jq -e '.name == "dark-lunar-custom" and .vars.crater == "#1a1d26" and .colors.userMessageBg == "#1a2030"' ~/.omp/agent/themes/dark-lunar-custom.json
```

Expected: `true`.

- [ ] **Step 2: Change only the user-message background token**

Replace this JSON property:

```json
"userMessageBg": "#1a2030"
```

with:

```json
"userMessageBg": "crater"
```

- [ ] **Step 3: Validate JSON and the exact theme contract**

Run:

```bash
jq -e '.vars.crater == "#1a1d26" and .colors.userMessageBg == "crater" and .colors.userMessageText == "moonlight" and .export.pageBg == "#0a0c11"' ~/.omp/agent/themes/dark-lunar-custom.json
```

Expected: `true`.

- [ ] **Step 4: Smoke-test the rendered prompt**

Start a new OMP session so it reloads the theme, submit a short user prompt, and inspect its message bubble.

Expected: the user message bubble is a neutral gray (`#1a1d26`), visibly lighter than the page background (`#0a0c11`), with no blue cast. Assistant messages, tool cards, and the status line retain their prior colors.

- [ ] **Step 5: Commit the implementation plan**

```bash
git add docs/superpowers/plans/2026-08-03-omp-user-prompt-background.md
git commit -m "docs: plan OMP user prompt background update"
```

Expected: Git creates a commit containing the implementation plan. The runtime theme file remains outside this repository.
