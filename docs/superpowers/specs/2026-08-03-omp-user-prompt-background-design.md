# OMP User Prompt Background Design

## Goal

Make the background of user-authored prompts in OMP's dark theme a subtle neutral gray. It must remain distinguishable from the page background without drawing unnecessary attention.

## Change

Update `userMessageBg` in `~/.omp/agent/themes/dark-lunar-custom.json`:

- Current value: `#1a2030` (blue-gray)
- New value: `crater`, resolving to the existing neutral gray `#1a1d26`

## Scope

Only the background of user messages changes. `userMessageText` remains `moonlight`; assistant messages, tool output, status-line colors, and other theme values are unchanged.

## Rationale

`crater` is already part of the theme palette and is visibly lighter than the page background (`#0a0c11`). Reusing it avoids a new color token and removes the current blue cast while preserving a low-contrast visual hierarchy.

## Verification

Reload OMP and submit a user prompt. Confirm that the user message background appears as a subtle neutral gray, remains readable, and that other UI regions retain their existing colors.
