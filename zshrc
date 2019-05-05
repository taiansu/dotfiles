 ### Profile
# zmodload zsh/zprof

autoload -Uz compinit

for dump in ~/.zcompdump(N.mh+24); do
  compinit
done

compinit -C

autoload -Uz promptinit colors
colors
promptinit

autoload -Uz url-quote-magic
zle -N self-insert url-quote-magic
autoload -Uz bracketed-paste-url-magic
zle -N bracketed-paste bracketed-paste-url-magic
autoload backward-delete-word
zle -N backward-delete-word

# Default colors:
# White for users, red for root, magenta for system users
local _time="%{$fg[yellow]%}[%*]"
local _path="%{$fg[green]%}%(8~|...|)%7~"
local _usercol
if [[ $EUID -lt 1000 ]]; then
  # red for root, magenta for system users
  _usercol="%(!.%{$fg[red]%}.%F{154})"
else
  _usercol="$fg[magenta]"
fi
local _user="%{$_usercol%}%n"
local _prompt
if [[ $SHLVL -gt 1 ]]; then
  _prompt="%{$reset_color%}𝝠"
else
  _prompt="%{$reset_color%}𝝺"
fi

PROMPT='$_time $_user $_path $_prompt%b%f%k%{$fg[white]%} '

if type "gitHUD" > /dev/null; then
  RPROMPT="\$(gitHUD zsh)"
else
  RPROMPT="${vcs_info_msg_0_}" # git branch
fi

if [[ ! -z "$SSH_CLIENT" ]]; then
  RPROMPT="$RPROMPT ⇄" # ssh icon
fi

##
# Environment variables
#

# basedir defaults, in case they're not already set up.
# http://standards.freedesktop.org/basedir-spec/basedir-spec-latest.html
if [[ -z $XDG_DATA_HOME ]]; then
  export XDG_DATA_HOME=$HOME/.local/share
fi

if [[ -z $XDG_CONFIG_HOME ]]; then
  export XDG_CONFIG_HOME=$HOME/.config
fi

if [[ -z $XDG_CACHE_HOME ]]; then
  export XDG_CACHE_HOME=$HOME/.cache
fi

if [[ -z $XDG_DATA_DIRS ]]; then
  export XDG_DATA_DIRS=/usr/local/share:/usr/share
fi

if [[ -z $XDG_CONFIG_DIRS ]]; then
  export XDG_CONFIG_DIRS=/etc/xdg
else
  export XDG_CONFIG_DIRS=/etc/xdg:$XDG_CONFIG_DIRS
fi

# add ~/.config/zsh/completion to completion paths
# NOTE: this needs to be a directory with 0755 permissions, otherwise you will
# get "insecure" warnings on shell load!
# fpath=($XDG_CONFIG_HOME/zsh/completion $fpath)


##
# zsh configuration
#

# Keep 1000 lines of history within the shell and save it to ~/.cache/shell_history
HISTSIZE=1000
SAVEHIST=1000
HISTFILE=$XDG_CACHE_HOME/shell_history

# shell options
setopt autocd # assume "cd" when a command is a directory
setopt histignorealldups # Substitute commands in the prompt
setopt sharehistory # Share the same history between all shells
setopt promptsubst # required for git plugin
setopt histignorespace # Ignore command start with space
# setopt extendedglob
# Extended glob syntax, eg ^ to negate, <x-y> for range, (foo|bar) etc.
# Backwards-incompatible with bash, so disabled by default.

# Colors!

# 256 color mode
export TERM="xterm-256color"

# Color aliases
if command -V dircolors >/dev/null 2>&1; then
  eval "$(dircolors -b)"
  # Only alias ls colors if dircolors is installed
  alias dir="dir --color=auto"
  alias vdir="vdir --color=auto"
fi

alias ls="ls -G"
alias grep="grep --color=auto"
alias fgrep="fgrep --color=auto"
alias egrep="egrep --color=auto"
alias dmesg="dmesg --color=auto"
# make less accept color codes and re-output them
alias less="less -R"

# WORDCHARS
export WORDCHARS='*?[]~=&;!#$%^(){}<>'

# Headless Chrome
alias chrome="/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --headless --disable-gpu --crash-dumps-dir=/tmp"

# Headless Firefox
alias firefox="/Applications/Firefox.app/Contents/MacOS/firefox"

# Youtube mp3
alias youtube-mp3="youtube-dl --extract-audio --audio-format mp3"

# sed
if command -V gsed >/dev/null 2>&1; then
  alias sed=gsed
fi

##
# Completion system
#

zstyle ":completion:*" auto-description "specify: %d"
zstyle ":completion:*" completer _expand _complete _correct _approximate
zstyle ":completion:*" format "Completing %d"
zstyle ":completion:*" group-name ""
zstyle ":completion:*" menu select=2
zstyle ":completion:*:default" list-colors ${(s.:.)LS_COLORS}
zstyle ":completion:*" list-colors ""
zstyle ":completion:*" list-prompt %SAt %p: Hit TAB for more, or the character to insert%s
zstyle ":completion:*" matcher-list "" "m:{a-z}={A-Z}" "m:{a-zA-Z}={A-Za-z}" "r:|[._-]=* r:|=* l:|=*"
zstyle ":completion:*" menu select=long
zstyle ":completion:*" select-prompt %SScrolling active: current selection at %p%s
zstyle ":completion:*" verbose true

zstyle ":completion:*:*:kill:*:processes" list-colors "=(#b) #([0-9]#)*=0=01;31"
zstyle ":completion:*:kill:*" command "ps -u $USER -o pid,%cpu,tty,cputime,cmd"


##
# Keybinds
#

# Use emacs-style keybindings
bindkey -e

bindkey "$terminfo[khome]" beginning-of-line # Home
bindkey "$terminfo[kend]" end-of-line # End
bindkey "$terminfo[kich1]" overwrite-mode # Insert
bindkey "$terminfo[kdch1]" delete-char # Delete
# bindkey "$terminfo[kcuu1]" up-line-or-history # Up
# bindkey "$terminfo[kcud1]" down-line-or-history # Down
bindkey "$terminfo[kcub1]" backward-char # Left
bindkey "$terminfo[kcuf1]" forward-char # Right
# bindkey "$terminfo[kpp]" # PageUp
# bindkey "$terminfo[knp]" # PageDown
zmodload zsh/terminfo

# Bind shift-tab to backwards-menu
# NOTE this won't work on Konsole if the new tab button is shown
bindkey "\e[Z" reverse-menu-complete

# Make ctrl-v edit the current command line
autoload edit-command-line
zle -N edit-command-line
bindkey "^v" edit-command-line

# Make sure the terminal is in application mode, when zle is
# active. Only then are the values from $terminfo valid.
if (( ${+terminfo[smkx]} )) && (( ${+terminfo[rmkx]} )); then
  function zle-line-init {
    printf "%s" ${terminfo[smkx]}
  }
  function zle-line-finish {
    printf "%s" ${terminfo[rmkx]}
  }
  zle -N zle-line-init
  zle -N zle-line-finish
fi

# typing ... expands to ../.., .... to ../../.., etc.
rationalise-dot() {
  if [[ $LBUFFER = *.. ]]; then
    LBUFFER+=/..
  else
    LBUFFER+=.
  fi
}
zle -N rationalise-dot
bindkey . rationalise-dot
bindkey -M isearch . self-insert # history search fix

# zsh tab title
setTerminalText () {
    # echo works in bash & zsh
    local mode=$1 ; shift
    echo -ne "\033]$mode;$@\007"
}
stt_both  () { setTerminalText 0 $@; }
stt_tab   () { setTerminalText 1 $@; }
stt_title () { setTerminalText 2 $@; }

tb () { stt_tab "${PWD/${HOME}/~}" }

# alias diablo='/Applications/Diablo\ III/Diablo\ III.app/Contents/MacOS/Diablo\ III -launch'

alias topTyped='history 0 | topTypedHistory | sort -rn | head -20'

topTypedHistory(){
  awk '{a[$2]++}END{for(i in a){print a[i] " " i}}'
}

##
# god file
alias god_file='find . -not \( -name .git* -prune \) -type f | xargs wc -l | sort -r | head -n 20'

# Functions
#
function mkcd() {
  mkdir "$1"
  cd "$1"
}

# make a backup of a file
# https://github.com/grml/grml-etc-core/blob/master/etc/zsh/zshrc
# bk() {
#   cp -a "$1" "${1}_$(date --iso-8601=seconds)"
# }

# # display a list of supported colors
# function lscolors {
#   ((cols = $COLUMNS - 4))
#   s=$(printf %${cols}s)
#   for i in {000..$(tput colors)}; do
#     echo -e $i $(tput setaf $i; tput setab $i)${s// /=}$(tput op);
#   done
# }

# get the content type of an http resource
# function htmime {
#   if [[ -z $1 ]]; then
#     print "USAGE: htmime <URL>"
#     return 1
#   fi
#   mime=$(curl -sIX HEAD $1 | sed -nr "s/Content-Type: (.+)/\1/p")
#   print $mime
# }

# open a web browser on google for a query
# function google {
#   xdg-open "https://www.google.com/search?q=`urlencode "${(j: :)@}"`"
# }

# print a separator banner, as wide as the terminal
function hr {
  print ${(l:COLUMNS::=:)}
}

# urlencode text
# function urlencode {
#   print "${${(j: :)@}//(#b)(?)/%$[[##16]##${match[1]}]}"
# }

# uninstall rails
uninstallRails() {
  gems=("activemodel" "activerecord" "activesupport" "actionmailer" "actionpack" "railties" "rails" "arel")
  if [[ "$1" =~ "^3" ]] ; then
    gems+=("activeresource")
  else
    gems+=("actionview" "activejob" "nio4r" "actioncable" "rails-dom-testing")
  fi

  for gem in $gems; do
    gem uninstall $gem -v=$1 --force
  done
}

# Hide desktop icons
function desktopIcons() {
  defaults write com.apple.finder CreateDesktop ${1:-true} && killall Finder
}

# Download Gist

function gistDownload() {
  curl -L ${1}/download | tar -xvz --strip-components=1
}

# Extras
#

function precmd() {
    # Clear the terminal title before running any command.
    # This is a somewhat hacky workaround to Neovim not refreshing the title
    # after it exits.
    echo -ne "\e]1;${PWD##*/}\a"
}

# export GIT_RADAR_FORMAT="%{$fg_bold[white]%}git:(%{$reset_color%}%{remote: }%{branch}%{ :local}%{$fg_bold[white]%})%{$reset_color%}%{ :stash}%{ :changes}"

