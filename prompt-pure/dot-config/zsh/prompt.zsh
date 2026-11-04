# prompt-pure: starship "Pure Prompt" preset.
#   ~/projects/foo main* ⇣⇡ ≡
#   ❯

prompt_git_render() {
  PROMPT_GIT=''
  (( PROMPT_GIT_REPO )) || return 0
  local s=" %F{#c6c6c0}${PROMPT_GIT_BRANCH}%f"
  (( PROMPT_GIT_DIRTY )) && s+="%F{#c4a1cd}*%f"
  local ab=''
  (( PROMPT_GIT_BEHIND ))  && ab+='⇣'
  (( PROMPT_GIT_AHEAD ))   && ab+='⇡'
  (( PROMPT_GIT_STASHED )) && ab+='≡'
  [[ -n $ab ]] && s+=" %F{#83c3bd}${ab}%f"
  [[ -n $PROMPT_GIT_ACTION ]] && s+=" %F{#c6c6c0}(${PROMPT_GIT_ACTION})%f"
  PROMPT_GIT=$s
}

prompt_apply_layout 1 0 \
  '%F{#86b8c9}%~%f${PROMPT_GIT}' \
  "%F{%(?.#c4a1cd.#d88c82)}${PROMPT_CHAR:-❯}%f "
