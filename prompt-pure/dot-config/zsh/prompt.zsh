# prompt-pure: starship "Pure Prompt" preset.
#   ~/projects/foo main* ⇣⇡ ≡
#   ❯

prompt_git_render() {
  PROMPT_GIT=''
  (( PROMPT_GIT_REPO )) || return 0
  local s=" %F{242}${PROMPT_GIT_BRANCH}%f"
  (( PROMPT_GIT_DIRTY )) && s+="%F{218}*%f"
  local ab=''
  (( PROMPT_GIT_BEHIND ))  && ab+='⇣'
  (( PROMPT_GIT_AHEAD ))   && ab+='⇡'
  (( PROMPT_GIT_STASHED )) && ab+='≡'
  [[ -n $ab ]] && s+=" %F{cyan}${ab}%f"
  [[ -n $PROMPT_GIT_ACTION ]] && s+=" %F{242}(${PROMPT_GIT_ACTION})%f"
  PROMPT_GIT=$s
}

PROMPT='%F{blue}%~%f${PROMPT_GIT}'
PROMPT+=$'\n'
PROMPT+="%F{%(?.magenta.red)}${PROMPT_CHAR:-❯}%f "
RPROMPT=''
