# directories
alias -g ...='../..'
alias -g ....='../../..'
alias -g .....='../../../..'
alias -g ......='../../../../..'

# vim
alias vim="/Applications/MacVim.app/Contents/MacOS/Vim"
alias v="mvim"
alias vd="mvim -d"
alias gvimdiff="mvim -d"
alias nv="nvim"
alias u="subl"
alias uu="subl ."

# zsh configs
alias szr="source ~/.zshrc"

# git
alias g='git'
alias h='hub'

# tail
alias tf='tail -f'
alias tn='tail -n'

# bundler
alias b="nocorrect bundle"
alias bb="nocorrect bundle -j4"
alias be="nocorrect bundle exec"
alias br="nocorrect bundle exec rake"
alias bt="nocorrect bundle exec rspec"
alias bnp="nocorrect bundle --without production"

# rake
alias k="rake"

# emacs
alias em="open -a Emacs"
alias emacs="/Applications/Emacs.app/Contents/MacOS/Emacs -nw"
alias emacsclient="/Applications/Emacs.app/Contents/MacOS/bin/emacsclient"
alias emd="emacs --daemon"
alias ec="emacsclient -c"
alias et="emacsclient -t"

# postgresql
alias pgup="pg_ctl -D /usr/local/var/postgres -l /usr/local/var/postgres/server.log start"
alias pghalt="pg_ctl -D /usr/local/var/postgres stop -s -m fast"

# nocorrect zsh
alias cap="nocorrect cap"
alias spec="nocorrect spec"
alias mmv="noglob zmv -W"

#clean open_with
alias cleanOpenWith="/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -kill -r -domain local -domain system -domain user"

# usually typed
topTypedHistory(){
  awk '{a[$2]++}END{for(i in a){print a[i] " " i}}'
}

alias topTyped='history 0 | topTypedHistory | sort -rn | head -20'

# uninstall rails
uninstallRails(){
  gems=("activemodel" "activerecord" "activesupport" "actionmailer" "actionpack" "railties" "rails")
  if [ $1 =~ "^3" ] ; then
    gems+=("activeresource" )
  else
    gems+=("actionview")
  fi

  for gem in $gems; do
    gem uninstall $gem -v=$1 --force
  done
}

# fix dirs
alias dv="dirs -v"

# fasd
alias a='fasd -a'        # any
alias s='fasd -si'       # show / search / select
alias d='fasd -d'        # directory
alias f='fasd -f'        # file
alias z='fasd_cd -d'     # cd, same functionality as j in autojump
alias vf='f -e mvim'        # file
alias o='a -e open'        # file

# youtube-dl
alias yt='youtube-dl -f bestvideo+bestaudio'
alias yt4='youtube-dl -o "%(title)s.%(ext)s" -q --extract-audio --audio-format "m4a" '
alias yt3='youtube-dl -o "%(title)s.%(ext)s" -q --extract-audio --audio-format "mp3" '

c(){
  gcc "$@"
  ./a.out
}

alias cov='open ./coverage/index.html'

# MiddleMan
alias mm='middleman'

# less
alias lf='less +F'

# Vagrant
alias vg='vagrant'

# boot2docker
alias bd='boot2docker'

# docker
alias dk='docker'
alias dl='docker ps -l -q'

# mkdir + autocd
mkd () {
  mkdir -p "$@" && cd "$@"
}

# name tab
nt () {
  printf "\e]0;$@\a"
}

# dump website
dump () {
  wget --recursive --no-clobber --page-requisites --html-extension --convert-links --restrict-file-names=unix --show-progress --domains "$@" --no-parent "$@"
}

# god object
alias god_object='find . -not \( -name .git* -prune \) -type f | xargs wc -l | sort -r | head -n 20'

# some other applications
alias vlc="open -a /Applications/VLC.app"
alias deckset="open -a /Applications/Deckset.app"

# Webpack
alias wp="webpack --progress --colors --watch"
alias ws="webpack-dev-server --progress --colors"

# Fix Moom
alias fix_moom="defaults write com.manytricks.Moom "Ignore Dock" -bool YES"
