# prompt-jetpack: starship "Jetpack" preset (geometry / spaceship flavoured).
#   ~/pro/foo △ main ⎪▴│2│●◦⎥                         12:34
#   ◎
# Runtime version segments are intentionally omitted.

local _it=$'%{\e[3m%}'   # italic on
local _ni=$'%{\e[23m%}'  # italic off

prompt_git_render() {
  PROMPT_GIT=''
  (( PROMPT_GIT_REPO )) || return 0
  local b=$PROMPT_GIT_BRANCH
  (( $#b > 11 )) && b="${b[1,11]}⋯"
  local s=" %F{12}%B△%b%f %F{12}${_it}${b}${_ni}%f"
  local st=''
  if (( PROMPT_GIT_AHEAD && PROMPT_GIT_BEHIND )); then
    st+="%F{13}◇ ▴┤%F{white}${PROMPT_GIT_AHEAD}%F{13}│▿┤%F{white}${PROMPT_GIT_BEHIND}%F{13}│%f"
  elif (( PROMPT_GIT_AHEAD )); then
    st+="%F{green}▴│%F{white}%B${PROMPT_GIT_AHEAD}%b%F{green}│%f"
  elif (( PROMPT_GIT_BEHIND )); then
    st+="%F{red}▿│%F{white}%B${PROMPT_GIT_BEHIND}%b%F{red}│%f"
  fi
  (( PROMPT_GIT_STAGED ))     && st+="%F{14}▪┤%F{white}%B${PROMPT_GIT_STAGED}%b%F{14}│%f"
  (( PROMPT_GIT_UNSTAGED ))   && st+="%F{yellow}●◦%f"
  (( PROMPT_GIT_UNTRACKED ))  && st+="%F{11}◌◦%f"
  (( PROMPT_GIT_CONFLICTED )) && st+="%F{13}◪◦%f"
  (( PROMPT_GIT_STASHED ))    && st+="%F{white}◃◈%f"
  [[ -n $st ]] && s+=" %F{12}%B${_it}⎪${_ni}%b%f${st}%F{12}%B${_it}⎥${_ni}%b%f"
  PROMPT_GIT=$s
}

PROMPT='%F{blue}'"${_it}"'%2~'"${_ni}"'%f${PROMPT_GIT}'
PROMPT+=$'\n'
PROMPT+='%(?.%F{11}%B'"${_it}"'◎'"${_ni}"'%b%f.%F{magenta}'"${_it}"'○'"${_ni}"'%f) '
RPROMPT='%F{245}'"${_it}"' %T'"${_ni}"'%f'
