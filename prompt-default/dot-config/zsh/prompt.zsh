# prompt-default: the original hand-rolled prompt, now on the gitstatus engine.
#   ~/p/…/dir [branch↓1↑2x1●2+3…4≡1] $              [12:34:56]

prompt_git_render() {
  PROMPT_GIT=''
  (( PROMPT_GIT_REPO )) || return 0
  local s=" [%F{white}${PROMPT_GIT_BRANCH}"
  (( PROMPT_GIT_DETACHED ))   && s=" [%F{cyan}:%F{white}${PROMPT_GIT_BRANCH}"
  (( PROMPT_GIT_BEHIND ))     && s+="%F{cyan}↓${PROMPT_GIT_BEHIND}"
  (( PROMPT_GIT_AHEAD ))      && s+="%F{cyan}↑${PROMPT_GIT_AHEAD}"
  (( PROMPT_GIT_CONFLICTED )) && s+="%F{red}⇵${PROMPT_GIT_CONFLICTED}"
  (( PROMPT_GIT_STAGED ))     && s+="%F{green}●${PROMPT_GIT_STAGED}"
  (( PROMPT_GIT_UNSTAGED ))   && s+="%F{red}○${PROMPT_GIT_UNSTAGED}"
  (( PROMPT_GIT_UNTRACKED ))  && s+="%F{red}+${PROMPT_GIT_UNTRACKED}"
  (( PROMPT_GIT_STASHED ))    && s+="%F{blue}%B≡${PROMPT_GIT_STASHED}%b"
  PROMPT_GIT="${s}%f]"
}

local _path='%F{blue}%(4~|%-1~/…/%2~|%3~)%f'
local _prompt=${PROMPT_CHAR:-\$}
(( SHLVL > 1 )) && _prompt+='′'

PROMPT='${_path}${PROMPT_GIT} ${_prompt}%b%f%k%F{white} '

RPROMPT='%F{246}[%*]%f'
if [[ -n $SSH_CLIENT ]]; then RPROMPT+='⇄'; fi
