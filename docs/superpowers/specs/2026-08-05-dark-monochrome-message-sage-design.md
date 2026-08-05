# OMP Dark Monochrome Message Sage Design

## Goal

Make user-authored messages easy to locate while reviewing long OMP conversations, without disrupting the `dark-monochrome` theme's restrained visual hierarchy.

## Change

Update `~/.omp/agent/themes/dark-monochrome-custom.json`:

- Add `vars.messageSage` with the value `#46594d`.
- Change `colors.userMessageBg` from `gray4` to `messageSage`.
- Keep `colors.userMessageText` as `gray9` (`#e0e0e0`).

## Scope

Only the user-message background token and its reference change. All other colors, including the cyan `accent`, status line, tool panels, Markdown, syntax colors, and exported colors remain unchanged.

## Rationale

`#46594d` is a low-saturation, mid-lightness moss green selected from the visual comparison. It separates user messages from the neutral near-black page and gray assistant content without turning the theme into a colored UI. A named token keeps the one-purpose non-gray color explicit and avoids a literal color in `colors`.

## Verification

Parse the customized theme as JSON and compare it with its prior version. Confirm that the only changes are the new `messageSage` variable and the `userMessageBg` reference. Reload OMP and visually verify that user messages are readily scannable, readable with `gray9` text, and visually subordinate to neither the page nor the cyan accent.
