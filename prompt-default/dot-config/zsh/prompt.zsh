# prompt-default: the original hand-rolled prompt, now on the gitstatus engine.
#   ~/p/…/dir [branch↓1↑2x1●2+3…4≡1] $              [12:34:56]

prompt_git_render() {
  PROMPT_GIT=''
  (( PROMPT_GIT_REPO )) || return 0
  local s=" [%F{#c6c6c0}${PROMPT_GIT_BRANCH}"
  (( PROMPT_GIT_DETACHED ))   && s=" [%F{#83c3bd}:%F{#c6c6c0}${PROMPT_GIT_BRANCH}"
  (( PROMPT_GIT_BEHIND ))     && s+="%F{#83c3bd}↓${PROMPT_GIT_BEHIND}"
  (( PROMPT_GIT_AHEAD ))      && s+="%F{#83c3bd}↑${PROMPT_GIT_AHEAD}"
  (( PROMPT_GIT_CONFLICTED )) && s+="%F{#d88c82}⇵${PROMPT_GIT_CONFLICTED}"
  (( PROMPT_GIT_STAGED ))     && s+="%F{#b4c982}●${PROMPT_GIT_STAGED}"
  (( PROMPT_GIT_UNSTAGED ))   && s+="%F{#d88c82}○${PROMPT_GIT_UNSTAGED}"
  (( PROMPT_GIT_UNTRACKED ))  && s+="%F{#d88c82}+${PROMPT_GIT_UNTRACKED}"
  (( PROMPT_GIT_STASHED ))    && s+="%F{#86b8c9}%B≡${PROMPT_GIT_STASHED}%b"
  PROMPT_GIT="${s}%f]"
}

local _path='%F{#86b8c9}%(4~|%-1~/…/%2~|%3~)%f'
local _prompt=${PROMPT_CHAR:-\$}
(( SHLVL > 1 )) && _prompt+='′'

prompt_apply_layout 0 1 \
  "${_path}"'${PROMPT_GIT}' \
  "${_prompt}%b%f%k%F{#c6c6c0} " \
  '%F{246}[%*]%f' \
  "${SSH_CLIENT:+⇄}"
