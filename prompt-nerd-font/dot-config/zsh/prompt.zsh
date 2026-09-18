# prompt-nerd-font: starship default layout with the "Nerd Font Symbols" preset.
# Requires a Nerd Font (pick one with kaisian --font).
#   ~/projects/foo on  main [!?]
#   ❯

prompt_git_render() {
  PROMPT_GIT=''
  (( PROMPT_GIT_REPO )) || return 0
  local s=" on %F{magenta}%B ${PROMPT_GIT_BRANCH}%b%f"
  local st=''
  (( PROMPT_GIT_CONFLICTED )) && st+='='
  if (( PROMPT_GIT_AHEAD && PROMPT_GIT_BEHIND )); then st+='⇕'
  elif (( PROMPT_GIT_AHEAD ));  then st+='⇡'
  elif (( PROMPT_GIT_BEHIND )); then st+='⇣'
  fi
  (( PROMPT_GIT_UNTRACKED )) && st+='?'
  (( PROMPT_GIT_STASHED ))   && st+='$'
  (( PROMPT_GIT_UNSTAGED ))  && st+='!'
  (( PROMPT_GIT_STAGED ))    && st+='+'
  [[ -n $st ]] && s+=" %F{red}%B[${st}]%b%f"
  [[ -n $PROMPT_GIT_ACTION ]] && s+=" %F{yellow}%B(${PROMPT_GIT_ACTION})%b%f"
  PROMPT_GIT=$s
}

PROMPT='%F{cyan}%B%~%b%f${PROMPT_GIT}'
PROMPT+=$'\n'
PROMPT+="%F{%(?.green.red)}${PROMPT_CHAR:-❯}%f "
RPROMPT=''
