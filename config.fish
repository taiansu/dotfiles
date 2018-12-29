[ -f /usr/local/share/autojump/autojump.fish ]; and source /usr/local/share/autojump/autojump.fish
[ -f ~/.iterm2_shell_integration.fish ]; and source ~/.iterm2_shell_integration.fish
[ -f ~/.asdf/asdf.fish ]; and source ~/.asdf/asdf.fish

## Variables
set -U WORDCHARS '*?[]~=&;!#$%^(){}<>'

set -U EDITOR nvim

set -U GOPATH $HOME/projects/gocode/bin
set -U GO_CUSTOM_PATH /usr/local/opt/go/libexec/bin

set -U YARN_PATH $HOME/.config/yarn/global/node_modules/.bin

set -U ERL_AFLAGS "-kernel shell_history enabled"

# vagrant
set -U VAGRANT_DEFAULT_PROVIDER 'virtualbox'

# FZF
# set -U FZF_DEFAULT_COMMAND 'ag -l'

### Path

#GOPATH
[ -d $GOPATH ]; and set PATH $PATH $GOPATH
[ -d $GO_CUSTOM_PATH ]; and set PATH $PATH $GO_CUSTOM_PATH

# Yarn
[ -d $YARN_PATH ]; and set PATH $PATH $YARN_PATH

### aliases
alias vim "nvim"
alias v "vim"

alias ll "ls -al"

alias g "git"

alias tl "tail"
alias tlf "tail -f"
alias tln "tail -n"

# Headless Browsers
alias chrome "/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome"
alias firefox "/Applications/Firefox.app/Contents/MacOS/firefox"

# Youtube mp3
alias youtube-mp3 "youtube-dl --extract-audio --audio-format mp3"

# less
alias lf "less +F"

# Make unified diff syntax the default
alias diff "diff -u"

# octal+text permissions for files
alias perms "stat -c '%A %a %n'"

#clean open_with
alias cleanOpenWith "/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -kill -r -domain local -domain system -domain user"

# bundle & rake
alias k "rake"
alias b "bundle"
alias br "bundle exec rake"

# mix
alias m "mix"
alias im "iex -S mix"

alias gt "gittower"

alias vg "vagrant"

# terraform
alias tf "terraform"
alias tg "terragrunt"

### functions
function fish_prompt
  set_color yellow
  echo -n [(date "+%H:%M:%S")]
  set_color cyan
  echo -n " "(whoami)" "
  set_color green
  echo -n (prompt_pwd)" "
  set_color $fish_color_cwd
  set_color normal
  echo -n "λ "
  # echo -n "∀ "
end

function fish_right_prompt
  echo -n (/usr/local/bin/gitHUD)
end

function vc
  set CMD "cd /vagrant; $ARGV";
  vagrant ssh -c "$CMD"
end
