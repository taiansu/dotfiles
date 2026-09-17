# prompt-default: the original hand-rolled prompt, now on the gitstatus engine.
#   ~/p/…/dir [branch ↓↑ x o +] 𝝺              [12:34:56]

prompt_git_render() {
  PROMPT_GIT=''
  (( PROMPT_GIT_REPO )) || return 0
  local s=" [%F{white}${PROMPT_GIT_BRANCH}"
  (( PROMPT_GIT_DETACHED ))   && s=" [%F{cyan}:%F{white}${PROMPT_GIT_BRANCH}"
  (( PROMPT_GIT_BEHIND ))     && s+="%F{cyan}↓"
  (( PROMPT_GIT_AHEAD ))      && s+="%F{cyan}↑"
  (( PROMPT_GIT_CONFLICTED )) && s+="%F{red}x"
  (( PROMPT_GIT_STAGED ))     && s+="%F{green}o"
  (( PROMPT_GIT_UNSTAGED ))   && s+="%F{red}+"
  PROMPT_GIT="${s}%f]"
}

local _path='%F{blue}%(4~|%-1~/…/%2~|%3~)%f'
local _prompt='𝝺'
(( SHLVL > 1 )) && _prompt+='′'

PROMPT='${_path}${PROMPT_GIT} ${_prompt}%b%f%k%F{white} '

RPROMPT='%F{246}[%*]%f'
if [[ -n $SSH_CLIENT ]]; then RPROMPT+=' ⇄'; fi
