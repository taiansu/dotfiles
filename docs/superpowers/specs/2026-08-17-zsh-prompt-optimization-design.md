# Zsh Prompt Optimization Design

## Goal

Reduce prompt-render overhead and simplify `zsh/zshrc` while preserving the current path abbreviation, nested-shell marker, right-side time and SSH indicator, asynchronous Git status, and Git status symbols.

## Current Behavior

`git-prompt.zsh` registers an asynchronous `precmd` hook. With `ZSH_GIT_PROMPT_FORCE_BLANK=1`, each prompt cycle clears the cached Git result, starts `git status --show-stash --branch --porcelain=v2` plus AWK in a background process, renders an initially blank Git segment, then renders again when the callback receives the result.

PS1 obtains the cached result through `$(gitprompt)`. In asynchronous mode, `gitprompt` only prints `_ZSH_GIT_PROMPT_STATUS_OUTPUT`, so command substitution creates a subprocess solely to read an existing variable.

Measured in this repository:

- Git renderer: 11.34 ms average, asynchronous.
- Renderer outside a Git repository: 3.91 ms average, asynchronous.
- `$(gitprompt)` prompt expansion: 9,481.4 ms for 20,000 renders, about 0.474 ms each.
- Direct parameter expansion: 33.1 ms for 20,000 renders, about 0.0017 ms each.

These isolated figures measure the Git segment, not total PS1 latency.

## Decision

Keep the vendored asynchronous `git-prompt.zsh` implementation and change only `zsh/zshrc`.

PS1 will directly expand `_ZSH_GIT_PROMPT_STATUS_OUTPUT` instead of invoking `$(gitprompt)`. This deliberately couples the configuration to the vendored plugin's asynchronous result variable. The plugin is maintained in the same repository, so avoiding a subprocess on every prompt render is worth that local coupling.

Disable force-blank behavior. A new `chpwd` hook will clear the primary and secondary cached Git results when the working directory changes. This prevents a status from another repository appearing after `cd`. Within one directory, PS1 may show the previous status for roughly 10 ms to tens of milliseconds after a Git-changing command; the asynchronous callback then replaces it. This brief staleness is accepted in exchange for immediate prompt display and avoiding a second render when status is unchanged.

## Prompt Structure

Preserve these behaviors:

- Left prompt path: blue, up to three path components; deeper paths display the leading component, an ellipsis, and the final two components.
- Shell marker: `𝝺` in the initial shell and `𝝺′` in nested shells.
- Input text: white after prompt styles are reset.
- Right prompt: dim time in brackets and `⇄` during SSH sessions.
- Git segment: branch or detached commit, ahead/behind counts, and unmerged, staged, unstaged, and untracked counts using the existing colors and symbols.

Move the Git segment's leading space into `ZSH_THEME_GIT_PROMPT_PREFIX`. PS1 can then concatenate the path and cached Git result directly. A non-Git directory will have one separator before the shell marker instead of the current double space.

Use `%f` for foreground-color resets and `[[ -n $SSH_CLIENT ]]` for the SSH condition.

## Configuration Cleanup

Remove code and settings that do not affect the retained behavior:

- `_usercol` and `_user`, which are never referenced by either prompt.
- The obsolete commented `PROMPT_COMMAND` experiment.
- Duplicate `PROMPT_SUBST` settings.
- `ZSH_GIT_PROMPT_SHOW_UPSTREAM="no"`; the plugin's empty default already hides the upstream name while retaining ahead/behind counts.
- `ZSH_GIT_PROMPT_SHOW_STASH=0`; the plugin's empty default hides stash output without the shell truthiness ambiguity of the string `0`.
- Theme values equal to plugin defaults, including the untracked symbol.
- Upstream-name and stash styles that cannot be displayed under the selected settings.

Retain only non-default theme values required for the current visible Git segment.

## Data Flow

1. `precmd` starts the existing asynchronous Git renderer.
2. PS1 immediately renders the last cached status through direct parameter expansion.
3. If the new status differs, the existing callback updates the cache and resets the prompt.
4. If the status is unchanged, no second render occurs.
5. `chpwd` clears both caches before the first prompt in a different directory, so cross-directory stale data is never rendered.

## Error Handling

Keep the plugin's existing behavior:

- Outside a Git repository, the renderer produces an empty segment.
- A failed Git command produces no Git segment.
- Missing Git leaves `gitprompt` and its secondary counterpart empty; direct expansion of the initialized cache remains empty.
- The cache-clearing hook performs assignments only and cannot block directory changes.

## Verification

After implementation:

1. Run Zsh syntax validation on `zsh/zshrc`.
2. Start an interactive Zsh and verify the left and right prompt appearance outside a Git repository.
3. Enter a clean Git repository and verify branch rendering.
4. Exercise untracked, staged, unstaged, ahead/behind, and detached states already supported by the plugin.
5. Change between two repositories and verify the previous repository's status is not shown.
6. Run a command that does not change Git state and confirm the cached result remains usable without force-blank behavior.
7. Repeat the prompt-expansion microbenchmark and confirm PS1 no longer invokes `gitprompt` through command substitution.

No `git-prompt.zsh` change, new dependency, daemon, or `vcs_info` migration is in scope.
