# Async git status engine for the prompt layouts in ~/.config/zsh/prompt.zsh.
#
# Backend: gitstatusd (brew install gitstatus). One daemon per shell, results
# arrive asynchronously; the prompt is redrawn when they land.
#
# Contract for a layout file:
#   - define `prompt_git_render` which reads the PROMPT_GIT_* variables below and
#     sets PROMPT_GIT (a prompt-escaped string, may be empty)
#   - reference ${PROMPT_GIT} inside PROMPT / RPROMPT (prompt_subst is on)
#   - render the input marker as ${PROMPT_CHAR:-<layout default>} so a single
#     machine-local setting (~/.config/zsh/local.zsh) overrides it in every layout
#
# Variables set before every prompt_git_render call:
#   PROMPT_GIT_REPO        1 inside a git work tree, else 0
#   PROMPT_GIT_BRANCH      branch name; tag or short commit when detached
#   PROMPT_GIT_DETACHED    1 when not on a branch
#   PROMPT_GIT_AHEAD       commits ahead of upstream
#   PROMPT_GIT_BEHIND      commits behind upstream
#   PROMPT_GIT_STAGED      staged change count
#   PROMPT_GIT_UNSTAGED    unstaged change count
#   PROMPT_GIT_UNTRACKED   untracked file count
#   PROMPT_GIT_CONFLICTED  conflicted file count
#   PROMPT_GIT_STASHED     stash count
#   PROMPT_GIT_ACTION      merge / rebase / cherry-pick / ... or empty
#   PROMPT_GIT_DIRTY       1 when staged+unstaged+untracked+conflicted > 0

typeset -g PROMPT_GIT=''
typeset -gi PROMPT_GIT_REPO=0 PROMPT_GIT_DETACHED=0 PROMPT_GIT_DIRTY=0
typeset -gi PROMPT_GIT_AHEAD=0 PROMPT_GIT_BEHIND=0 PROMPT_GIT_STAGED=0 PROMPT_GIT_UNSTAGED=0
typeset -gi PROMPT_GIT_UNTRACKED=0 PROMPT_GIT_CONFLICTED=0 PROMPT_GIT_STASHED=0
typeset -g PROMPT_GIT_BRANCH='' PROMPT_GIT_ACTION=''

_prompt_git_reset() {
  PROMPT_GIT='' PROMPT_GIT_REPO=0 PROMPT_GIT_DETACHED=0 PROMPT_GIT_DIRTY=0
  PROMPT_GIT_AHEAD=0 PROMPT_GIT_BEHIND=0 PROMPT_GIT_STAGED=0 PROMPT_GIT_UNSTAGED=0
  PROMPT_GIT_UNTRACKED=0 PROMPT_GIT_CONFLICTED=0 PROMPT_GIT_STASHED=0
  PROMPT_GIT_BRANCH='' PROMPT_GIT_ACTION=''
}

# Assemble PROMPT and RPROMPT from theme defaults and optional Kaisian prompt flags.
# Args: default_multiline default_show_time info input [native_rprompt] [rprompt_suffix] [legacy_inline_info]
prompt_apply_layout() {
  local default_multiline=$1
  local default_show_time=$2
  local info=$3
  local input=$4
  local native_rprompt=${5-}
  local rprompt_suffix=${6-}
  local legacy_inline_info=${7-}

  local multiline=$default_multiline
  case ${KAISIAN_PROMPT_MULTILINE-} in
    true)  multiline=1 ;;
    false) multiline=0 ;;
  esac

  local show_time=$default_show_time
  local time_controlled=0
  case ${KAISIAN_PROMPT_SHOW_TIME-} in
    true)  show_time=1; time_controlled=1 ;;
    false) show_time=0; time_controlled=1 ;;
  esac

  # Single-line must always move an existing visible time to RPROMPT.
  if (( default_multiline && ! multiline && show_time && ! time_controlled )); then
    time_controlled=1
  fi

  local active_info=$info
  if (( multiline && show_time && ! time_controlled )) && [[ -n $legacy_inline_info ]]; then
    active_info=$legacy_inline_info
  fi

  if (( multiline )); then
    PROMPT="${active_info}"$'\n'"${input}"
  else
    PROMPT="${active_info} ${input}"
  fi

  if (( ! show_time )); then
    RPROMPT=''
  elif (( time_controlled )); then
    RPROMPT='%F{#9ca3b5}%D{%H:%M:%S}%f'
  else
    RPROMPT=$native_rprompt
  fi
  RPROMPT+=$rprompt_suffix

  (( $+functions[prompt_git_render] )) && prompt_git_render
}

setopt prompt_subst prompt_percent no_prompt_bang

[[ -o interactive ]] || return 0

: ${HOMEBREW_PREFIX:=/opt/homebrew}
[[ -r $HOMEBREW_PREFIX/opt/gitstatus/gitstatus.plugin.zsh ]] || return 0
# The plugin uses $1 as a function-name suffix; pass an explicit empty one so the
# caller's positional parameters never leak in.
source "$HOMEBREW_PREFIX/opt/gitstatus/gitstatus.plugin.zsh" '' || return 0

# Copy VCS_STATUS_* into PROMPT_GIT_* and let the layout render.
_prompt_git_apply() {
  emulate -L zsh
  case $VCS_STATUS_RESULT in
    ok-sync|ok-async)
      PROMPT_GIT_REPO=1
      if [[ -n $VCS_STATUS_LOCAL_BRANCH ]]; then
        PROMPT_GIT_BRANCH=${VCS_STATUS_LOCAL_BRANCH//\%/%%}
        PROMPT_GIT_DETACHED=0
      elif [[ -n $VCS_STATUS_TAG ]]; then
        PROMPT_GIT_BRANCH=${VCS_STATUS_TAG//\%/%%}
        PROMPT_GIT_DETACHED=1
      else
        PROMPT_GIT_BRANCH=${VCS_STATUS_COMMIT[1,8]}
        PROMPT_GIT_DETACHED=1
      fi
      PROMPT_GIT_AHEAD=$VCS_STATUS_COMMITS_AHEAD
      PROMPT_GIT_BEHIND=$VCS_STATUS_COMMITS_BEHIND
      PROMPT_GIT_STAGED=$VCS_STATUS_NUM_STAGED
      PROMPT_GIT_UNSTAGED=$VCS_STATUS_NUM_UNSTAGED
      PROMPT_GIT_UNTRACKED=$VCS_STATUS_NUM_UNTRACKED
      PROMPT_GIT_CONFLICTED=$VCS_STATUS_NUM_CONFLICTED
      PROMPT_GIT_STASHED=$VCS_STATUS_STASHES
      PROMPT_GIT_ACTION=$VCS_STATUS_ACTION
      PROMPT_GIT_DIRTY=$(( (PROMPT_GIT_STAGED + PROMPT_GIT_UNSTAGED + PROMPT_GIT_UNTRACKED + PROMPT_GIT_CONFLICTED) > 0 ))
      ;;
    *)
      _prompt_git_reset
      ;;
  esac
  (( $+functions[prompt_git_render] )) && prompt_git_render
}

# Async callback: results arrived after the prompt was drawn.
_prompt_git_callback() {
  _prompt_git_apply
  zle && zle reset-prompt
}

_prompt_git_precmd() {
  # -t 0: never block. Cached results come back synchronously (ok-sync / norepo-sync);
  # otherwise VCS_STATUS_RESULT=tout and the callback fires later.
  gitstatus_query -t 0 -c _prompt_git_callback KAISIAN || { _prompt_git_reset; return 0; }
  [[ $VCS_STATUS_RESULT == tout ]] && return 0
  _prompt_git_apply
}

_prompt_git_chpwd() {
  _prompt_git_reset
  (( $+functions[prompt_git_render] )) && prompt_git_render
}

gitstatus_stop KAISIAN && gitstatus_start -s -1 -u -1 -c -1 -d -1 KAISIAN

autoload -Uz add-zsh-hook
add-zsh-hook precmd _prompt_git_precmd
add-zsh-hook chpwd  _prompt_git_chpwd
