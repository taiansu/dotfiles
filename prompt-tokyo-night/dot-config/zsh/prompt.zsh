# prompt-tokyo-night: starship "Tokyo Night" preset (powerline).
# Requires a Nerd Font and a true-colour terminal.
#   ░▒▓   ~/foo   main !?   12:34 
#   ❯
# Runtime version segments are intentionally omitted.

local _c_os='#a3aed2' _c_dir='#769ff0' _c_git='#394260' _c_time='#1d2230'
local _c_dirfg='#e3e5e5' _c_timefg='#a0a9cb' _c_osfg='#090c0c'

prompt_git_render() {
  PROMPT_GIT=''
  (( PROMPT_GIT_REPO )) || return 0
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
  PROMPT_GIT="  ${PROMPT_GIT_BRANCH} "
  [[ -n $st ]] && PROMPT_GIT+="${st} "
}

PROMPT="%F{${_c_os}}░▒▓%K{${_c_os}}%F{${_c_osfg}}  "
PROMPT+="%K{${_c_dir}}%F{${_c_os}}%F{${_c_dirfg}} %(4~|…/%3~|%~) "
PROMPT+="%K{${_c_git}}%F{${_c_dir}}%F{${_c_dir}}"'${PROMPT_GIT}'
PROMPT+="%K{${_c_time}}%F{${_c_git}}%F{${_c_timefg}}  %T "
PROMPT+="%k%F{${_c_time}}%f"
PROMPT+=$'\n'
PROMPT+="%F{%(?.green.red)}%B${PROMPT_CHAR:-❯}%b%f "
RPROMPT=''
